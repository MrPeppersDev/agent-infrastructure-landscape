#!/usr/bin/env python3
"""
validate.py — fast round-trip + schema validation for the landscape catalog.

Issue #7. Run before committing data changes (also enforced via CI). All
checks are cheap: no external API calls, no Semantic Scholar fetches —
those have their own determinism gate that runs only when the cache is
explicitly refreshed.

Gates (all run; non-zero exit on any failure):

  1. JSON schema validation
     - landscape.json:       SCHEMA.md §7.1 rules per record (delegated to
                             scripts/extract.py's validate_record).
     - landscape.edges.json: SCHEMA.md §7.2 rules per edge (referential
                             integrity, type enum, isInfluential iff cites,
                             pair+type uniqueness, no self-edges, ...).

  2. Determinism of fast steps
     - extract.py twice → byte-identical JSON.
     - reconcile.py from that → byte-identical to committed
       data/landscape.json.
     - build_edges.py twice → byte-identical (and equal to committed
       data/landscape.edges.json minus the cites edges).
     - fetch_citations.py --offline (cache-only, no network) twice →
       byte-identical to committed data/landscape.edges.json.

     Network-side fetch_citations is NOT run here — its determinism is
     verified separately when the cache is refreshed via
     `make refresh-citations`.

  3. Cycle stability (the meaningful round-trip test)
     - render.py(landscape.json) → HTML_A
     - extract.py(HTML_A)        → landscape_cycle.json
     - render.py(landscape_cycle.json, template=HTML_A) → HTML_B
     - diff(HTML_A, HTML_B) ≤ 16 lines.

     The 16-line ceiling is the documented cross-listing-marker drift
     (4 cross-listed records × 4 diff lines each). See
     docs/DECISIONS.md "render.py — cross-listings render once with an
     inline marker".

  4. Cache integrity
     - Every extraction/s2-cache/*.json file is well-formed JSON.

Usage:
  python3 scripts/validate.py            # run all gates
  python3 scripts/validate.py --gate 1   # run only gate N
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data"
S2_CACHE = ROOT / "extraction" / "s2-cache"

LANDSCAPE_JSON = DATA / "landscape.json"
LANDSCAPE_EDGES_JSON = DATA / "landscape.edges.json"
LANDSCAPE_HTML = ROOT / "landscape.html"

# Cycle-stability ceiling. See docstring + docs/DECISIONS.md.
CYCLE_DIFF_CEILING = 16

VALID_EDGE_TYPES = {
    "built-on",
    "extends",
    "forks",
    "integrates-with",
    "competes-with",
    "inspired-by",
    "cites",
    "same-team-as",
    "succeeds",
}

# Claim-tier validation regex (SCHEMA.md §3a / scripts/extract.py).
TIER_GITHUB_URL_RE = re.compile(r"^https?://github\.com/", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Reporting helpers.
# ---------------------------------------------------------------------------


class GateFailure(Exception):
    pass


def info(msg: str) -> None:
    print(f"  {msg}")


def gate_header(num: int, name: str) -> None:
    print(f"\n[gate {num}] {name}")


def gate_pass(msg: str) -> None:
    print(f"  PASS — {msg}")


def gate_fail(msg: str) -> None:
    raise GateFailure(msg)


# ---------------------------------------------------------------------------
# Gate 1: JSON schema.
# ---------------------------------------------------------------------------


def _is_http_url(s) -> bool:
    return isinstance(s, str) and (s.startswith("http://") or s.startswith("https://"))


def gate_schema() -> None:
    gate_header(1, "JSON schema validation (SCHEMA.md §7)")

    # Records — delegate per-record validation to extract.py's validator.
    sys.path.insert(0, str(SCRIPTS))
    from extract import validate_record, ID_RE  # noqa: E402

    if not LANDSCAPE_JSON.exists():
        gate_fail(f"{LANDSCAPE_JSON} not found")

    landscape = json.loads(LANDSCAPE_JSON.read_text())

    # 7.1.1 top-level keys
    expected_top = {"schemaVersion", "generatedAt", "sourceHtml", "records"}
    actual_top = set(landscape.keys())
    if actual_top != expected_top:
        gate_fail(
            f"landscape.json top-level keys mismatch: "
            f"missing={sorted(expected_top - actual_top)} "
            f"extra={sorted(actual_top - expected_top)}"
        )

    # 7.1.2 schemaVersion is major-1
    if not str(landscape.get("schemaVersion", "")).startswith("1"):
        gate_fail(f"landscape.json schemaVersion={landscape.get('schemaVersion')!r} not v1.x")

    records = landscape.get("records") or []
    if not isinstance(records, list) or not records:
        gate_fail("landscape.json records must be a non-empty array")

    # Per-record validation.
    record_errors: list[str] = []
    seen_ids: set[str] = set()
    for rec in records:
        rid = rec.get("id")
        if rid in seen_ids:
            record_errors.append(f"{rid}: duplicate id (7.1.5)")
        seen_ids.add(rid)
        record_errors.extend(validate_record(rec))

    if record_errors:
        for e in record_errors[:20]:
            info(f"  - {e}")
        if len(record_errors) > 20:
            info(f"  ... and {len(record_errors) - 20} more")
        gate_fail(f"{len(record_errors)} record validation errors")

    info(f"records: {len(records)} validated, all schema-conformant")

    # Edges — implement §7.2 inline (no existing validator we can reuse cleanly).
    if not LANDSCAPE_EDGES_JSON.exists():
        gate_fail(f"{LANDSCAPE_EDGES_JSON} not found")

    edges_doc = json.loads(LANDSCAPE_EDGES_JSON.read_text())
    expected_edges_top = {"schemaVersion", "generatedAt", "edges"}
    actual_edges_top = set(edges_doc.keys())
    if actual_edges_top != expected_edges_top:
        gate_fail(
            f"landscape.edges.json top-level keys mismatch: "
            f"missing={sorted(expected_edges_top - actual_edges_top)} "
            f"extra={sorted(actual_edges_top - expected_edges_top)}"
        )

    # 7.3 cross-file: same schemaVersion
    if edges_doc.get("schemaVersion") != landscape.get("schemaVersion"):
        gate_fail(
            f"schemaVersion mismatch: records={landscape.get('schemaVersion')!r} "
            f"edges={edges_doc.get('schemaVersion')!r}"
        )

    edges = edges_doc.get("edges") or []
    if not isinstance(edges, list):
        gate_fail("landscape.edges.json edges must be array")

    edge_errors: list[str] = []
    seen_triples: set[tuple] = set()
    for i, e in enumerate(edges):
        tag = f"edge[{i}]({e.get('source')}→{e.get('target')}|{e.get('type')})"
        # 7.2.3 required keys
        for key in ("source", "target", "type", "evidence", "citation"):
            if key not in e:
                edge_errors.append(f"{tag}: missing key {key!r}")
        if "source" not in e or "target" not in e or "type" not in e:
            continue
        # 7.2.4 referential integrity
        if e["source"] not in seen_ids:
            edge_errors.append(f"{tag}: source id not in records")
        if e["target"] not in seen_ids:
            edge_errors.append(f"{tag}: target id not in records")
        # 7.2.5 no self-edges
        if e["source"] == e["target"]:
            edge_errors.append(f"{tag}: self-edge")
        # 7.2.6 type enum
        if e["type"] not in VALID_EDGE_TYPES:
            edge_errors.append(f"{tag}: type {e['type']!r} not in vocabulary")
        # 7.2.7 isInfluential iff cites
        has_inf = "isInfluential" in e
        if e["type"] == "cites":
            if has_inf and not isinstance(e["isInfluential"], bool):
                edge_errors.append(f"{tag}: isInfluential must be bool")
        else:
            if has_inf:
                edge_errors.append(f"{tag}: isInfluential present on non-cites edge")
        # 7.2.8 pair+type uniqueness
        triple = (e.get("source"), e.get("target"), e.get("type"))
        if triple in seen_triples:
            edge_errors.append(f"{tag}: duplicate (source, target, type) triple")
        seen_triples.add(triple)
        # 7.2.9 citation must be http(s)
        if not _is_http_url(e.get("citation", "")):
            edge_errors.append(f"{tag}: citation must be non-empty http(s) URL")
        # 7.2.10 evidence non-empty string ≤ 500
        ev = e.get("evidence", "")
        if not isinstance(ev, str) or not ev:
            edge_errors.append(f"{tag}: evidence must be non-empty string")
        elif len(ev) > 500:
            edge_errors.append(f"{tag}: evidence length {len(ev)} > 500 (soft cap)")

    if edge_errors:
        for e in edge_errors[:20]:
            info(f"  - {e}")
        if len(edge_errors) > 20:
            info(f"  ... and {len(edge_errors) - 20} more")
        gate_fail(f"{len(edge_errors)} edge validation errors")

    info(f"edges: {len(edges)} validated, all schema-conformant")
    gate_pass("schema OK")


# ---------------------------------------------------------------------------
# Gate 2: Determinism of fast steps.
# ---------------------------------------------------------------------------


def _run(cmd: list[str], cwd: Path = ROOT) -> None:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        info(f"  command failed: {' '.join(cmd)}")
        info(f"  stdout: {res.stdout[-500:]}")
        info(f"  stderr: {res.stderr[-500:]}")
        gate_fail(f"command exited {res.returncode}: {' '.join(cmd)}")


def _diff_files(a: Path, b: Path, label: str) -> None:
    res = subprocess.run(["diff", "-q", str(a), str(b)], capture_output=True, text=True)
    if res.returncode != 0:
        info(f"  {label} differ: {res.stdout.strip()}")
        # Show first few diff lines for triage.
        d = subprocess.run(["diff", str(a), str(b)], capture_output=True, text=True)
        for line in (d.stdout or "").splitlines()[:20]:
            info(f"    {line}")
        gate_fail(f"{label} are not byte-identical")


def gate_determinism() -> None:
    gate_header(2, "Determinism of fast pipeline steps")
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)

        # extract.py × 2
        extract_a = tdp / "extract_a.json"
        extract_b = tdp / "extract_b.json"
        _run(["python3", str(SCRIPTS / "extract.py"), "--output", str(extract_a)])
        _run(["python3", str(SCRIPTS / "extract.py"), "--output", str(extract_b)])
        _diff_files(extract_a, extract_b, "extract.py runs")
        info("extract.py: byte-stable across runs")

        # reconcile.py from extract_a → must equal committed landscape.json
        reconciled = tdp / "reconciled.json"
        # reconcile.py also writes side-effect files (merges/cross-listings/ambiguous)
        # to extraction/. We accept that — they're idempotent and committed.
        _run(
            [
                "python3",
                str(SCRIPTS / "reconcile.py"),
                "--input",
                str(extract_a),
                "--output",
                str(reconciled),
            ]
        )
        _diff_files(reconciled, LANDSCAPE_JSON, "reconcile output vs committed landscape.json")
        info("reconcile.py: output matches committed landscape.json")

        # build_edges.py — verify byte-stability, but DO NOT clobber the
        # committed data/landscape.edges.json (which contains S2 cites edges
        # appended by fetch_citations.py and shouldn't be overwritten by
        # the no-citations builder).
        #
        # build_edges.py only supports a default output path
        # (data/landscape.edges.json), so we snapshot the committed file,
        # run twice, compare the two runs, then restore the snapshot.
        snapshot = LANDSCAPE_EDGES_JSON.read_bytes()
        try:
            _run(["python3", str(SCRIPTS / "build_edges.py")])
            run1 = LANDSCAPE_EDGES_JSON.read_bytes()
            _run(["python3", str(SCRIPTS / "build_edges.py")])
            run2 = LANDSCAPE_EDGES_JSON.read_bytes()
        finally:
            LANDSCAPE_EDGES_JSON.write_bytes(snapshot)
        if run1 != run2:
            gate_fail(
                "build_edges.py is non-deterministic — two consecutive runs produced different bytes"
            )
        # The build_edges output is the committed file MINUS the cites edges
        # appended by fetch_citations.py. We sanity-check that the structure
        # matches by parsing both and checking that the build_edges output is
        # a subset of the committed file (every non-cites edge is present and
        # identical, in the same order).
        committed_doc = json.loads(snapshot)
        builder_doc = json.loads(run1)
        committed_non_cites = [
            e for e in committed_doc["edges"] if e.get("type") != "cites"
        ]
        if committed_non_cites != builder_doc["edges"]:
            gate_fail(
                "build_edges.py output diverges from committed non-cites edges "
                "(expected committed - cites = builder output)"
            )
        info(
            f"build_edges.py: byte-stable across runs; "
            f"output matches committed minus {len(committed_doc['edges']) - len(builder_doc['edges'])} cites edges"
        )

        # fetch_citations.py --offline — must be cache-only and reproduce the
        # committed edges file exactly, including all cites edges. Two runs
        # must be byte-identical to each other AND to the committed snapshot.
        snapshot2 = LANDSCAPE_EDGES_JSON.read_bytes()
        try:
            _run(["python3", str(SCRIPTS / "fetch_citations.py"), "--offline"])
            fc_run1 = LANDSCAPE_EDGES_JSON.read_bytes()
            _run(["python3", str(SCRIPTS / "fetch_citations.py"), "--offline"])
            fc_run2 = LANDSCAPE_EDGES_JSON.read_bytes()
        finally:
            LANDSCAPE_EDGES_JSON.write_bytes(snapshot2)
        if fc_run1 != fc_run2:
            gate_fail(
                "fetch_citations.py --offline is non-deterministic — two runs differed"
            )
        if fc_run1 != snapshot2:
            gate_fail(
                "fetch_citations.py --offline output differs from committed "
                "data/landscape.edges.json (rebuild required, or cache drift)"
            )
        info(
            "fetch_citations.py --offline: byte-stable, output matches committed"
        )

    gate_pass("all fast pipeline steps are deterministic and match committed artifacts")


# ---------------------------------------------------------------------------
# Gate 3: Cycle stability.
# ---------------------------------------------------------------------------


def gate_cycle() -> None:
    gate_header(3, "Cycle stability: render → extract → render ≤ {} line diff".format(CYCLE_DIFF_CEILING))
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        html_a = tdp / "render_a.html"
        cycle_json = tdp / "cycle.json"
        html_b = tdp / "render_b.html"

        _run(
            [
                "python3",
                str(SCRIPTS / "render.py"),
                "--input",
                str(LANDSCAPE_JSON),
                "--output",
                str(html_a),
            ]
        )
        _run(
            [
                "python3",
                str(SCRIPTS / "extract.py"),
                "--input",
                str(html_a),
                "--output",
                str(cycle_json),
            ]
        )
        _run(
            [
                "python3",
                str(SCRIPTS / "render.py"),
                "--input",
                str(cycle_json),
                "--output",
                str(html_b),
                "--template",
                str(html_a),
            ]
        )

        d = subprocess.run(["diff", str(html_a), str(html_b)], capture_output=True, text=True)
        diff_lines = len(d.stdout.splitlines()) if d.stdout else 0
        info(f"diff lines = {diff_lines} (ceiling = {CYCLE_DIFF_CEILING})")
        if diff_lines > CYCLE_DIFF_CEILING:
            for line in (d.stdout or "").splitlines()[:30]:
                info(f"    {line}")
            gate_fail(
                f"cycle drift exceeds ceiling: {diff_lines} > {CYCLE_DIFF_CEILING} lines"
            )
    gate_pass("render → extract → render is stable within documented bound")


# ---------------------------------------------------------------------------
# Gate 4: Cache integrity.
# ---------------------------------------------------------------------------


def gate_cache() -> None:
    gate_header(4, "S2 cache integrity (extraction/s2-cache/*.json)")
    if not S2_CACHE.exists():
        gate_fail(f"{S2_CACHE} not found — fetch_citations cache is missing")
    files = sorted(S2_CACHE.glob("*.json"))
    if not files:
        gate_fail(f"{S2_CACHE} contains no .json files")
    bad: list[tuple[Path, str]] = []
    for f in files:
        try:
            json.loads(f.read_text())
        except json.JSONDecodeError as e:
            bad.append((f, str(e)))
    if bad:
        for f, msg in bad[:10]:
            info(f"  - {f.name}: {msg}")
        gate_fail(f"{len(bad)} cache file(s) malformed JSON")
    info(f"{len(files)} cache files, all parse as JSON")
    gate_pass("S2 cache is well-formed")


# ---------------------------------------------------------------------------
# Gate 5: Claim-tier validation (SCHEMA.md §3a).
# ---------------------------------------------------------------------------


def gate_claim_tiers() -> None:
    gate_header(5, "Claim-tier provenance (SCHEMA.md §3a / §7.1.12)")
    if not LANDSCAPE_JSON.exists():
        gate_fail(f"{LANDSCAPE_JSON} not found")

    landscape = json.loads(LANDSCAPE_JSON.read_text())
    records = landscape.get("records") or []

    tier_errors: list[str] = []
    counts = {"T1": 0, "T2": 0, "T3": 0}
    for rec in records:
        rid = rec.get("id", "<unknown>")
        for slug, cell in (rec.get("cells") or {}).items():
            tier = cell.get("tier")
            if tier not in counts:
                tier_errors.append(
                    f"{rid}.cells[{slug}]: tier {tier!r} not in {{T1,T2,T3}}"
                )
                continue
            counts[tier] += 1
            citation = cell.get("citation")
            if tier == "T1":
                if not citation or not TIER_GITHUB_URL_RE.match(citation):
                    tier_errors.append(
                        f"{rid}.cells[{slug}]: T1 requires GitHub citation "
                        f"(got {citation!r})"
                    )
            elif tier == "T2":
                if not citation or not _is_http_url(citation):
                    tier_errors.append(
                        f"{rid}.cells[{slug}]: T2 requires non-empty http(s) "
                        f"citation (got {citation!r})"
                    )

    if tier_errors:
        for e in tier_errors[:20]:
            info(f"  - {e}")
        if len(tier_errors) > 20:
            info(f"  ... and {len(tier_errors) - 20} more")
        gate_fail(f"{len(tier_errors)} claim-tier validation errors")

    info(
        f"tier distribution: T1={counts['T1']} T2={counts['T2']} T3={counts['T3']}"
    )
    gate_pass("all cells satisfy their tier's citation requirement")


# ---------------------------------------------------------------------------
# Driver.
# ---------------------------------------------------------------------------


GATES = {
    1: ("schema", gate_schema),
    2: ("determinism", gate_determinism),
    3: ("cycle", gate_cycle),
    4: ("cache", gate_cache),
    5: ("claim-tiers", gate_claim_tiers),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Round-trip validation for the landscape catalog.")
    ap.add_argument(
        "--gate",
        type=int,
        choices=sorted(GATES),
        help="run only one gate by number (1–5)",
    )
    args = ap.parse_args()

    selected = [args.gate] if args.gate else sorted(GATES)

    print(f"validate.py — {len(selected)} gate(s) selected")
    failed: list[str] = []
    for n in selected:
        name, fn = GATES[n]
        try:
            fn()
        except GateFailure as e:
            print(f"  FAIL — {e}")
            failed.append(f"gate-{n} ({name})")

    print()
    if failed:
        print(f"validate.py: {len(failed)} gate(s) failed: {', '.join(failed)}")
        return 1
    print(f"validate.py: all {len(selected)} gate(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

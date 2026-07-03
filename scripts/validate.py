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
import datetime as _dt
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
    "runtime-dependency",
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

# last_verified_at validation regex (SCHEMA.md §3b).
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Decay-cause enum (SCHEMA.md §3c, issue #56). Mirrors
# scripts/extract.py's DECAY_CAUSE_VALUES.
DECAY_CAUSE_VALUES = {
    "acquired",
    "pivoted",
    "unfunded",
    "lost-benchmark-race",
    "superseded",
    "archived",
    "research-complete",
    "unknown",
}

# Survivorship-classifier date parsing — mirrors the priority used by
# web/src/lib/analyses/survivorship.ts (1. latest-release, 2. code-release
# "last commit YYYY-MM", 3. created). Used by gate 5 to identify
# stale / abandoned rows for the decay-cause warning.
DATE_RE = re.compile(r"(\d{4})-(\d{1,2})(?:-(\d{1,2}))?")
LAST_COMMIT_RE = re.compile(r"last[- ]commit\s+(\d{4})-(\d{1,2})", re.IGNORECASE)

# Tier 3/4/5 records are research artefacts; survivorship classifier
# routes them to 'research' (no decay expectation).
RESEARCH_TIERS = {3, 4, 5}

# Bucket boundaries in months (matches survivorship.ts).
ACTIVE_MAX_MONTHS = 12
STALE_MAX_MONTHS = 24

# Today's date used for freshness bucketing. Kept as a module-level
# constant for deterministic test reporting (the value isn't reset
# from system time on every call — change in lock-step with the
# survivorship analyses if/when the catalog snapshot date moves).
FRESHNESS_TODAY = _dt.date.fromisoformat("2026-05-14")


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


def _parse_date_latest(raw: str | None) -> _dt.date | None:
    """Latest YYYY-MM(-DD) date from free text — mirrors survivorship.ts."""
    if not raw:
        return None
    v = raw.strip()
    if not v:
        return None
    lower = v.lower()
    if (
        lower == "no-release no-release"
        or lower.startswith("no-release")
        or lower == "no data"
        or lower == "searched not found"
        or "pre-existing" in lower
    ):
        return None
    latest: _dt.date | None = None
    for m in DATE_RE.finditer(v):
        try:
            year = int(m.group(1))
            month = int(m.group(2))
            day = int(m.group(3)) if m.group(3) else 15
            if (
                year < 1900 or year > 2099
                or month < 1 or month > 12
                or day < 1 or day > 31
            ):
                continue
            d = _dt.date(year, month, day)
        except ValueError:
            continue
        if latest is None or d > latest:
            latest = d
    return latest


def _parse_last_commit(raw: str | None) -> _dt.date | None:
    if not raw:
        return None
    m = LAST_COMMIT_RE.search(raw)
    if not m:
        return None
    try:
        year = int(m.group(1))
        month = int(m.group(2))
        if year < 1900 or year > 2099 or month < 1 or month > 12:
            return None
        return _dt.date(year, month, 15)
    except ValueError:
        return None


def _months_between(from_d: _dt.date, to_d: _dt.date) -> int:
    days = (to_d - from_d).days
    # 30.4375 days/month (mirrors survivorship.ts).
    return round(days / 30.4375)


def _classify_survivorship(rec: dict) -> str:
    """Return one of 'active' | 'stale' | 'abandoned' | 'unknown' | 'research'.

    Mirrors web/src/lib/analyses/survivorship.ts. Used by gate 5 to
    decide whether to expect a decay_cause on a row. Tier 3/4/5 routes
    to 'research' (no decay expectation regardless of dates).
    """
    if rec.get("tier") in RESEARCH_TIERS:
        return "research"
    cells = rec.get("cells") or {}
    today = FRESHNESS_TODAY

    # Priority 1: latest-release.
    lr = cells.get("latest-release") or {}
    if lr.get("status") == "real-data":
        d = _parse_date_latest(lr.get("value"))
        if d:
            age = _months_between(d, today)
            if age <= ACTIVE_MAX_MONTHS:
                return "active"
            if age <= STALE_MAX_MONTHS:
                return "stale"
            return "abandoned"

    # Priority 2: code-release last-commit.
    cr = cells.get("code-release") or {}
    if cr.get("value"):
        d = _parse_last_commit(cr.get("value"))
        if d:
            age = _months_between(d, today)
            if age <= ACTIVE_MAX_MONTHS:
                return "active"
            if age <= STALE_MAX_MONTHS:
                return "stale"
            return "abandoned"

    # Priority 3: created.
    created = cells.get("created") or {}
    if created.get("value"):
        d = _parse_date_latest(created.get("value"))
        if d:
            age = _months_between(d, today)
            if age <= ACTIVE_MAX_MONTHS:
                return "active"
            # Older created with no release/commit signal → unknown
            # (the JS classifier also routes here).
            return "unknown"

    return "unknown"


def gate_claim_tiers() -> None:
    gate_header(
        5,
        "Claim-tier provenance + freshness (SCHEMA.md §3a / §3b / §7.1.12)",
    )
    if not LANDSCAPE_JSON.exists():
        gate_fail(f"{LANDSCAPE_JSON} not found")

    landscape = json.loads(LANDSCAPE_JSON.read_text())
    records = landscape.get("records") or []

    tier_errors: list[str] = []
    counts = {"T1": 0, "T2": 0, "T3": 0}
    # Freshness buckets — see SCHEMA.md §3b. We bucket every record by
    # its row-level last_verified_at, NOT every cell, because the
    # row-level date is what an audit / re-sweep workflow keys off.
    freshness = {"fresh": 0, "aging": 0, "stale": 0, "very_stale": 0}
    missing_lva = 0
    bad_lva: list[str] = []
    bad_cell_lva: list[str] = []
    cell_lva_count = 0
    # Decay-cause forensics (SCHEMA.md §3c, issue #56).
    decay_cause_dist: dict[str, int] = {v: 0 for v in DECAY_CAUSE_VALUES}
    decay_cause_errors: list[str] = []
    decay_cause_warnings: list[str] = []
    active_with_decay: list[str] = []
    stale_abandoned_without_decay: list[str] = []
    stale_abandoned_count = 0

    for rec in records:
        rid = rec.get("id", "<unknown>")
        # Row-level last_verified_at (SCHEMA.md §3b).
        row_lva = rec.get("last_verified_at")
        if not isinstance(row_lva, str) or not ISO_DATE_RE.match(row_lva or ""):
            bad_lva.append(
                f"{rid}: row last_verified_at must match YYYY-MM-DD (got {row_lva!r})"
            )
            missing_lva += 1
        else:
            try:
                d = _dt.date.fromisoformat(row_lva)
                age_days = (FRESHNESS_TODAY - d).days
                if age_days < 183:
                    freshness["fresh"] += 1
                elif age_days < 365:
                    freshness["aging"] += 1
                elif age_days < 730:
                    freshness["stale"] += 1
                else:
                    freshness["very_stale"] += 1
            except ValueError:
                bad_lva.append(
                    f"{rid}: row last_verified_at unparseable ({row_lva!r})"
                )

        # Decay-cause validation (SCHEMA.md §3c). Three rules:
        #   1. enum / shape check (also enforced by extract.py's
        #      validate_record — repeated here for resilience).
        #   2. active rows MUST NOT carry a decay_cause (hard failure).
        #   3. stale/abandoned rows SHOULD carry a decay_cause (warning).
        dc = rec.get("decay_cause")
        dd = rec.get("decay_date")
        de = rec.get("decay_evidence")
        if dc is not None:
            if dc in DECAY_CAUSE_VALUES:
                decay_cause_dist[dc] += 1
            else:
                decay_cause_errors.append(
                    f"{rid}: decay_cause {dc!r} not in enum"
                )
        if dd is not None and (
            not isinstance(dd, str) or not ISO_DATE_RE.match(dd)
        ):
            decay_cause_errors.append(
                f"{rid}: decay_date must match YYYY-MM-DD (got {dd!r})"
            )
        if de is not None and (not isinstance(de, str) or not de):
            decay_cause_errors.append(
                f"{rid}: decay_evidence must be non-empty string"
            )
        status = _classify_survivorship(rec)
        if status in ("stale", "abandoned"):
            stale_abandoned_count += 1
            if not dc:
                stale_abandoned_without_decay.append(rid)
        elif status == "active" and dc:
            # `archived` is an explicit state (repo flagged archived on
            # GitHub) and can coexist with `active` survivorship — a repo
            # archived yesterday hasn't yet decayed by activity metrics.
            # Other decay causes (acquired, pivoted, unfunded, ...) imply
            # the project is no longer active and are an error here.
            if dc != "archived":
                active_with_decay.append(
                    f"{rid}: active row carries decay_cause={dc!r}"
                )

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
            # Per-cell last_verified_at (SCHEMA.md §3b). Optional; when
            # present must be ISO date. We don't enforce the volatile-slug
            # check here — that's caught by extract.py's per-record
            # validator (gate 1 invokes the same logic).
            cell_lva = cell.get("last_verified_at")
            if cell_lva is not None:
                cell_lva_count += 1
                if not isinstance(cell_lva, str) or not ISO_DATE_RE.match(cell_lva):
                    bad_cell_lva.append(
                        f"{rid}.cells[{slug}]: last_verified_at "
                        f"must match YYYY-MM-DD (got {cell_lva!r})"
                    )

    errors: list[str] = []
    if tier_errors:
        errors.extend(tier_errors)
    if bad_lva:
        errors.extend(bad_lva)
    if bad_cell_lva:
        errors.extend(bad_cell_lva)
    # Hard failures: enum/shape violations, and active rows that carry
    # a decay_cause (the contradiction the spec calls out).
    if decay_cause_errors:
        errors.extend(decay_cause_errors)
    if active_with_decay:
        errors.extend(active_with_decay)

    if errors:
        for e in errors[:20]:
            info(f"  - {e}")
        if len(errors) > 20:
            info(f"  ... and {len(errors) - 20} more")
        gate_fail(f"{len(errors)} claim-tier / freshness validation errors")

    info(
        f"tier distribution: T1={counts['T1']} T2={counts['T2']} T3={counts['T3']}"
    )
    info(
        "row freshness: "
        f"fresh<6mo={freshness['fresh']}  "
        f"aging=6-12mo={freshness['aging']}  "
        f"stale=12-24mo={freshness['stale']}  "
        f"very-stale>=24mo={freshness['very_stale']}"
    )
    info(f"per-cell last_verified_at populated: {cell_lva_count}")
    # Decay-cause forensics (SCHEMA.md §3c, issue #56). Informational.
    total_with_cause = sum(decay_cause_dist.values())
    info(
        "decay-cause distribution: "
        + " ".join(f"{k}={v}" for k, v in sorted(decay_cause_dist.items()))
        + f"  total={total_with_cause}"
    )
    info(
        f"stale+abandoned rows: {stale_abandoned_count} "
        f"(of which {len(stale_abandoned_without_decay)} lack decay_cause — "
        "soft warning, populate via scripts/research_decay_causes.py)"
    )
    gate_pass(
        "all cells satisfy their tier's citation requirement; "
        "row-level + per-cell freshness are well-formed"
    )


# ---------------------------------------------------------------------------
# Gate 6: Cell-level staleness visibility (soft warning).
# ---------------------------------------------------------------------------


# Cell-level freshness buckets (days). Mirror MAINTAINER.md §2's
# wall-clock thresholds (active <12mo, stale 12-24mo, abandoned >24mo)
# and the row-level buckets reported by gate 5: fresh <6mo, aging
# 6-12mo, stale 12-24mo, very-stale >=24mo.
CELL_FRESH_MAX_DAYS = 183     # <6 months
CELL_AGING_MAX_DAYS = 365     # 6-12 months
CELL_STALE_MAX_DAYS = 730     # 12-24 months; everything >= is very-stale

# How many of the most-stale cells to surface in the report.
CELL_ROT_TOP_N = 10


def gate_cell_rot() -> None:
    """Soft-warning gate: surface per-cell staleness without ever failing.

    Walks every record × cell, computes days since each cell's
    ``last_verified_at`` (skipping cells without one), buckets the
    counts (fresh / aging / stale / very-stale), and prints the top
    N most-stale (record-id, cell-slug, days-since) tuples.

    Rationale: we already track per-cell ``last_verified_at`` and
    gate 5 reports the populated count, but nothing aggregates the
    age distribution. This gate fills that blind spot for human
    triage. It always passes — flipping CI red the moment any cell
    crosses a threshold would explode the moment the gate is added,
    and the row-level staleness signal is the actionable one anyway.

    Only CELL-level ``last_verified_at`` is counted; row-level
    ``last_verified_at`` is reported by gate 5.
    """
    gate_header(6, "Cell-level staleness visibility (soft warning, always passes)")

    if not LANDSCAPE_JSON.exists():
        gate_fail(f"{LANDSCAPE_JSON} not found")

    landscape = json.loads(LANDSCAPE_JSON.read_text())
    records = landscape.get("records") or []

    today = _dt.date.today()
    buckets = {"fresh": 0, "aging": 0, "stale": 0, "very_stale": 0}
    total_cells_with_lva = 0
    # Heap-equivalent: collect (days_since, record_id, slug) and sort.
    aged: list[tuple[int, str, str]] = []
    malformed = 0

    for rec in records:
        rid = rec.get("id", "<unknown>")
        for slug, cell in (rec.get("cells") or {}).items():
            if not isinstance(cell, dict):
                continue
            lva = cell.get("last_verified_at")
            if lva is None:
                continue  # cells without last_verified_at: skip silently
            if not isinstance(lva, str) or not ISO_DATE_RE.match(lva):
                print(
                    f"warning: {rid}.cells[{slug}]: malformed last_verified_at "
                    f"({lva!r}); skipping",
                    file=sys.stderr,
                )
                malformed += 1
                continue
            try:
                d = _dt.date.fromisoformat(lva)
            except ValueError:
                print(
                    f"warning: {rid}.cells[{slug}]: unparseable last_verified_at "
                    f"({lva!r}); skipping",
                    file=sys.stderr,
                )
                malformed += 1
                continue
            days = (today - d).days
            total_cells_with_lva += 1
            if days < CELL_FRESH_MAX_DAYS:
                buckets["fresh"] += 1
            elif days < CELL_AGING_MAX_DAYS:
                buckets["aging"] += 1
            elif days < CELL_STALE_MAX_DAYS:
                buckets["stale"] += 1
            else:
                buckets["very_stale"] += 1
            aged.append((days, rid, slug))

    info(f"per-cell last_verified_at considered: {total_cells_with_lva}")
    if malformed:
        info(f"malformed last_verified_at skipped: {malformed} (see stderr)")

    if total_cells_with_lva == 0:
        info("no cells carry last_verified_at — nothing to bucket")
        gate_pass("cell-level staleness surfaced (no data)")
        return

    def pct(n: int) -> str:
        return f"{(n / total_cells_with_lva) * 100:.1f}%"

    info(
        "cell freshness: "
        f"fresh<6mo={buckets['fresh']} ({pct(buckets['fresh'])})  "
        f"aging=6-12mo={buckets['aging']} ({pct(buckets['aging'])})  "
        f"stale=12-24mo={buckets['stale']} ({pct(buckets['stale'])})  "
        f"very-stale>=24mo={buckets['very_stale']} ({pct(buckets['very_stale'])})"
    )

    # Top-N most-stale cells (descending days_since, deterministic
    # tie-break on (rid, slug)).
    aged.sort(key=lambda t: (-t[0], t[1], t[2]))
    top = aged[:CELL_ROT_TOP_N]
    info(f"top {len(top)} most-stale cells (record id | cell slug | days since):")
    for days, rid, slug in top:
        info(f"  - {rid} | {slug} | {days} days")

    gate_pass("cell-level staleness surfaced (visibility-only; never fails)")


# ---------------------------------------------------------------------------
# Gate 7: Phase 2 cell provenance integrity (issues #95 / #101).
# ---------------------------------------------------------------------------


# Phase 2 / Gate 1 cells. Every populated cell in this list MUST have a
# matching `_provenance[slug]` entry. Mirrored from
# scripts/research_intake.py PHASE_2_CELL_SLUGS and the equivalent list
# in scripts/apply_intake_pr.py — duplicated here to keep validate.py
# free of cross-script imports.
PHASE_2_CELL_SLUGS: tuple[str, ...] = (
    "cost-input-usd-per-mtok",
    "cost-output-usd-per-mtok",
    "cost-tier",
    "cost-pricing-model",
    "cost-last-verified",
    "capability-composite-score",
    "capability-band",
    "capability-benchmark-sources",
    "capability-last-verified",
    "capability-code-score",
    "capability-agentic-score",
    "capability-longcontext-score",
    "use-case-tags",
    "use-case-anti-tags",
)

# Valid provenance source enum. `legacy` is reserved for pre-Phase-2
# backfill; the intake pipeline never writes it on a new cell. `human`
# / `scrape` / `llm` are the live sources from the auto-intake bot.
PROVENANCE_SOURCE_ENUM: frozenset[str] = frozenset({
    "legacy", "human", "scrape", "llm",
})


def gate_phase_2_provenance() -> None:
    """Enforce Phase 2 provenance contract on landscape.json.

    Rules (issue #101 §5):
      - Every populated Phase 2 cell has a matching `_provenance[slug]`
        entry.
      - The provenance `source` is in the enum {legacy, human, scrape, llm}.
      - `source: human` cells carry an `author` field.

    `source: llm, verified: true` cells WITHOUT a verification step are
    surfaced as a soft warning (printed, not a hard fail) — those rows
    are rare and the verification-step convention isn't yet enforced
    catalog-wide, so flagging via warning gives the curator visibility
    without flipping CI red.

    Empty Phase 2 cells (value falsy) are tolerated: depth-floor / not-
    applicable rows that the bot left empty don't require a provenance
    entry, only populated ones do.
    """
    gate_header(
        7,
        "Phase 2 cell provenance integrity (issues #95 / #101)",
    )
    if not LANDSCAPE_JSON.exists():
        gate_fail(f"{LANDSCAPE_JSON} not found")

    landscape = json.loads(LANDSCAPE_JSON.read_text())
    records = landscape.get("records") or []

    errors: list[str] = []
    warnings_soft: list[str] = []
    populated_phase_2_cells = 0
    populated_with_provenance = 0
    source_dist: dict[str, int] = {s: 0 for s in PROVENANCE_SOURCE_ENUM}

    for rec in records:
        rid = rec.get("id", "<unknown>")
        cells = rec.get("cells") or {}
        prov = rec.get("_provenance") or {}
        if not isinstance(prov, dict):
            errors.append(
                f"{rid}: _provenance must be a dict (got {type(prov).__name__})"
            )
            continue
        for slug in PHASE_2_CELL_SLUGS:
            cell = cells.get(slug) or {}
            value = cell.get("value")
            if not value:
                continue  # empty Phase 2 cell — no provenance required
            populated_phase_2_cells += 1
            entry = prov.get(slug)
            if not isinstance(entry, dict):
                errors.append(
                    f"{rid}.cells[{slug}]: populated Phase 2 cell missing "
                    f"_provenance[{slug}] entry"
                )
                continue
            populated_with_provenance += 1
            source = entry.get("source")
            if source not in PROVENANCE_SOURCE_ENUM:
                errors.append(
                    f"{rid}._provenance[{slug}]: source {source!r} not in "
                    f"{sorted(PROVENANCE_SOURCE_ENUM)}"
                )
                continue
            source_dist[source] += 1
            verified = entry.get("verified")
            if source == "human" and not entry.get("author"):
                errors.append(
                    f"{rid}._provenance[{slug}]: source: human requires an "
                    f"`author` field"
                )
            if source == "llm" and verified is True:
                # llm-verified is legal only with an explicit
                # verification step recorded. Soft-warn if absent.
                if not any(k in entry for k in (
                    "verification_step", "verified_by", "verified_at",
                )):
                    warnings_soft.append(
                        f"{rid}._provenance[{slug}]: source: llm, "
                        f"verified: true lacks a verification step "
                        f"(verified_by / verified_at / verification_step)"
                    )

    info(
        f"populated Phase 2 cells: {populated_phase_2_cells}  "
        f"with _provenance: {populated_with_provenance}"
    )
    info(
        "provenance source distribution (Phase 2 cells only): "
        + " ".join(f"{k}={v}" for k, v in sorted(source_dist.items()))
    )

    if warnings_soft:
        for w in warnings_soft[:10]:
            info(f"  warning: {w}")
        if len(warnings_soft) > 10:
            info(f"  ... and {len(warnings_soft) - 10} more soft warning(s)")

    if errors:
        for e in errors[:20]:
            info(f"  - {e}")
        if len(errors) > 20:
            info(f"  ... and {len(errors) - 20} more")
        gate_fail(f"{len(errors)} Phase 2 provenance validation error(s)")

    gate_pass(
        "every populated Phase 2 cell has a well-formed _provenance entry"
    )


# ---------------------------------------------------------------------------
# Driver.
# ---------------------------------------------------------------------------


GATES = {
    1: ("schema", gate_schema),
    2: ("determinism", gate_determinism),
    3: ("cycle", gate_cycle),
    4: ("cache", gate_cache),
    5: ("claim-tiers", gate_claim_tiers),
    6: ("cell-rot", gate_cell_rot),
    7: ("phase-2-provenance", gate_phase_2_provenance),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Round-trip validation for the landscape catalog.")
    ap.add_argument(
        "--gate",
        type=int,
        choices=sorted(GATES),
        help="run only one gate by number (1–7)",
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

#!/usr/bin/env python3
"""
apply_round9.py — integrate 9 Round-9 deep-fill CSVs into the catalog.

Reads:
  - extraction/round-9-quintet-citations.csv (Path A)
  - extraction/round-9-bucket-1-method-papers.csv (Path B1)
  - extraction/round-9-bucket-2-vertical.csv (Path B2)
  - extraction/round-9-bucket-3-dedicated-retrieval.csv (Path B3)
  - extraction/round-9-bucket-4-frameworks-platforms.csv (Path B4)
  - extraction/round-9-bucket-5-pkm-voice-claude-files.csv (Path B5)
  - extraction/round-9-bucket-6-kg-vector-enterprise-research.csv (Path B6)
  - extraction/round-9-bucket-7-benchmarks-governance-observability-theoretical.csv (Path B7)
  - extraction/round-9-bucket-8-round7-sections.csv (Path B8)

Normalises the per-CSV column conventions to a common record shape and
applies each (record_id, column) update to `web/landscape.json` cells.
Then invokes scripts/render.py to write `landscape.html` from the updated
JSON.

Downgrade-protection: skips a row when the existing cell already carries
more-detailed data than the CSV. Detected by:
  - existing status is `real-data` and incoming status is
    `depth-floor-reached` / `not-applicable` / `no-data`
  - existing value length > incoming value length AND existing status is
    `real-data` AND incoming value is a known placeholder
    (e.g. "no public benchmark scores found", "searched not found").

Citation-only writes (Path A) only update `citation` when current value is
non-empty and current citation is null.

Emits extraction/round-9-apply-log.csv (every action: applied / skipped /
unresolved) and prints a console summary.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parent.parent
EXTRACTION = REPO / "extraction"
LANDSCAPE_JSON = REPO / "web" / "landscape.json"
LANDSCAPE_HTML = REPO / "landscape.html"
LOG_CSV = EXTRACTION / "round-9-apply-log.csv"

CSV_INPUTS: list[tuple[str, Path]] = [
    ("quintet", EXTRACTION / "round-9-quintet-citations.csv"),
    ("bucket-1", EXTRACTION / "round-9-bucket-1-method-papers.csv"),
    ("bucket-2", EXTRACTION / "round-9-bucket-2-vertical.csv"),
    ("bucket-3", EXTRACTION / "round-9-bucket-3-dedicated-retrieval.csv"),
    ("bucket-4", EXTRACTION / "round-9-bucket-4-frameworks-platforms.csv"),
    ("bucket-5", EXTRACTION / "round-9-bucket-5-pkm-voice-claude-files.csv"),
    ("bucket-6", EXTRACTION / "round-9-bucket-6-kg-vector-enterprise-research.csv"),
    ("bucket-7", EXTRACTION / "round-9-bucket-7-benchmarks-governance-observability-theoretical.csv"),
    ("bucket-8", EXTRACTION / "round-9-bucket-8-round7-sections.csv"),
]

# Column-name aliases per CSV. We resolve into canonical column names:
#   record_id, column, new_value, citation_url, status
COL_ALIASES = {
    "status": ["status", "new_status"],
    "citation_url": ["citation_url", "new_citation"],
    "new_value": ["new_value"],
    "column": ["column"],
    "record_id": ["record_id"],
}

VALID_STATUSES = {"real-data", "not-applicable", "depth-floor-reached", "no-data"}

# Placeholder phrases — incoming rows whose new_value matches one of these
# (case-insensitive substring) represent a depth-floor "we looked and didn't
# find it". Used for downgrade detection.
PLACEHOLDERS = {
    "no public benchmark scores found",
    "searched not found",
    "not specified",
    "no data",
    "no releases",
    "no headline",
    "no quantitative",
    "no public",
}


def read_csv_normalised(path: Path) -> list[dict]:
    """Read a CSV (skipping `#` comment lines) and return list of normalised dicts."""
    lines = path.read_text(encoding="utf-8").splitlines()
    # Drop leading `#` comments.
    cleaned = [ln for ln in lines if not ln.startswith("#")]
    if not cleaned:
        return []
    reader = csv.DictReader(cleaned)
    out: list[dict] = []
    for row in reader:
        norm = normalise_row(row)
        if norm is None:
            continue
        out.append(norm)
    return out


def normalise_row(row: dict) -> dict | None:
    """Map a heterogeneous CSV row into:
        {record_id, column, new_value, citation_url, status}
    Returns None if the row is malformed (missing record_id or column).
    """
    rec_id = (row.get("record_id") or "").strip()
    col = (row.get("column") or "").strip()
    if not rec_id or not col:
        return None
    value = row.get("new_value")
    if value is None:
        value = ""
    value = value.strip()
    # Citation
    citation = ""
    for k in COL_ALIASES["citation_url"]:
        if row.get(k):
            citation = row[k].strip()
            break
    # Status
    status = ""
    for k in COL_ALIASES["status"]:
        if row.get(k):
            status = row[k].strip()
            break
    return {
        "record_id": rec_id,
        "column": col,
        "new_value": value,
        "citation_url": citation,
        "status": status,
    }


def looks_like_placeholder(value: str) -> bool:
    v = (value or "").strip().lower()
    if not v:
        return True
    for p in PLACEHOLDERS:
        if p in v:
            return True
    return False


def decide_action(
    cur: dict,
    incoming: dict,
) -> tuple[str, str]:
    """Return (action, reason) where action is one of:
        - 'apply-value'      : replace value + status; set citation if new one provided
        - 'apply-citation'   : keep value+status; just set citation
        - 'skip-no-change'   : both value and citation already match the proposed update
        - 'skip-downgrade'   : current cell is richer than the proposed update
        - 'skip-invalid'     : malformed / unknown status / etc.
    """
    in_value = incoming["new_value"]
    in_citation = incoming["citation_url"]
    in_status = incoming["status"]

    # Normalise legacy / non-schema statuses.
    # 'shallow-prose' is a gap-class, not a status. Means "we kept it as is";
    # treat as no-op.
    if in_status == "shallow-prose":
        return ("skip-no-change", "shallow-prose marker — value unchanged by agent")

    if in_status not in VALID_STATUSES:
        return ("skip-invalid", f"unknown incoming status {in_status!r}")

    cur_value = (cur.get("value") or "").strip()
    cur_status = cur.get("status") or ""
    cur_citation = cur.get("citation") or ""

    incoming_is_citation_only = (
        in_status == "real-data"
        and in_value == cur_value
        and in_citation
        and not cur_citation
    )
    if incoming_is_citation_only:
        return ("apply-citation", "value unchanged; backfill citation")

    # Downgrade protection: existing real-data with substantive content
    # versus an incoming placeholder.
    if (
        cur_status == "real-data"
        and len(cur_value) > 30
        and looks_like_placeholder(in_value)
        and in_status != "real-data"
    ):
        return ("skip-downgrade", "current real-data is richer than incoming placeholder")

    # Downgrade protection: existing real-data with substantive content versus
    # a not-applicable / depth-floor downgrade.
    if (
        cur_status == "real-data"
        and len(cur_value) > 0
        and in_status in {"not-applicable", "depth-floor-reached"}
        and looks_like_placeholder(in_value)
    ):
        return ("skip-downgrade", "current real-data; incoming is depth-floor/NA placeholder")

    # No change at all (value, status, citation already match).
    if (
        cur_value == in_value
        and cur_status == in_status
        and (cur_citation or "") == (in_citation or "")
    ):
        return ("skip-no-change", "exact match with current cell")

    # The proposed value is shorter than current AND current also looks fine
    # (real-data, substantive). Skip as downgrade unless statuses differ.
    if (
        cur_status == "real-data"
        and in_status == "real-data"
        and len(cur_value) > len(in_value) + 20
        and not looks_like_placeholder(cur_value)
    ):
        return ("skip-downgrade", "current real-data is significantly longer than incoming")

    return ("apply-value", "")


def apply_to_cell(cur: dict, incoming: dict, action: str) -> None:
    """Mutate `cur` in place per the decided action."""
    if action == "apply-citation":
        cur["citation"] = incoming["citation_url"] or None
        return
    if action == "apply-value":
        cur["value"] = incoming["new_value"]
        cur["status"] = incoming["status"]
        cur["citation"] = incoming["citation_url"] or None
        return
    # apply-no-op / skip — nothing to do
    return


def build_id_index(records: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in records:
        out[r["id"]] = r
    return out


def coalesce_rows(rows: list[dict]) -> list[dict]:
    """Within a single CSV, keep the last update for each (record_id, column).
    Across CSVs, this is handled in the main apply loop (later CSV wins).
    """
    by_key: "OrderedDict[tuple[str, str], dict]" = OrderedDict()
    for r in rows:
        key = (r["record_id"], r["column"])
        by_key[key] = r
    return list(by_key.values())


def run_render(json_path: Path) -> None:
    """Invoke scripts/render.py to regenerate landscape.html from the JSON."""
    cmd = [
        "python3",
        str(REPO / "scripts" / "render.py"),
        "--input",
        str(json_path),
        "--output",
        str(LANDSCAPE_HTML),
        "--template",
        str(LANDSCAPE_HTML),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("render.py stdout:", res.stdout, file=sys.stderr)
        print("render.py stderr:", res.stderr, file=sys.stderr)
        raise RuntimeError("render.py failed")
    print(res.stdout.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="parse + decide, but don't mutate any files",
    )
    args = ap.parse_args()

    # Load landscape.json — our single source of truth for cells.
    landscape = json.loads(LANDSCAPE_JSON.read_text(encoding="utf-8"))
    records = landscape["records"]
    id_index = build_id_index(records)

    # Load all CSVs into a single ordered stream.
    all_rows: list[tuple[str, dict]] = []  # (source-label, row)
    per_source_input_counts: Counter = Counter()
    for label, path in CSV_INPUTS:
        if not path.exists():
            print(f"warn: {path} missing — skipping", file=sys.stderr)
            continue
        rows = read_csv_normalised(path)
        per_source_input_counts[label] = len(rows)
        for row in rows:
            all_rows.append((label, row))

    print(f"loaded {len(all_rows)} rows from {len(CSV_INPUTS)} CSVs")
    for label, n in per_source_input_counts.items():
        print(f"  {label}: {n}")

    # Apply each row. Later rows can overwrite earlier ones (same record_id+column);
    # this is intentional — the CSVs were produced by independent agents and the
    # newer / more-specialised one should win.
    action_counts: Counter = Counter()
    per_source_action_counts: dict[str, Counter] = {}
    log_rows: list[dict] = []

    for label, row in all_rows:
        rec_id = row["record_id"]
        col = row["column"]
        rec = id_index.get(rec_id)
        if rec is None:
            action = "unresolved-id"
            reason = "record_id not found in landscape.json"
        else:
            cells = rec.get("cells") or {}
            cell = cells.get(col)
            if cell is None:
                action = "unresolved-column"
                reason = f"column {col!r} not in record cells"
            else:
                decision, reason = decide_action(cell, row)
                if decision.startswith("apply"):
                    if not args.dry_run:
                        apply_to_cell(cell, row, decision)
                action = decision

        action_counts[action] += 1
        per_source_action_counts.setdefault(label, Counter())[action] += 1
        log_rows.append({
            "source": label,
            "record_id": rec_id,
            "column": col,
            "incoming_value": row["new_value"][:160],
            "incoming_citation": row["citation_url"],
            "incoming_status": row["status"],
            "action": action,
            "reason": reason,
        })

    # Write log CSV.
    LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    with LOG_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "source",
                "record_id",
                "column",
                "incoming_value",
                "incoming_citation",
                "incoming_status",
                "action",
                "reason",
            ],
        )
        w.writeheader()
        for r in log_rows:
            w.writerow(r)
    print(f"wrote apply-log: {LOG_CSV} ({len(log_rows)} rows)")

    print("\nAction summary (across all CSVs):")
    for a, n in sorted(action_counts.items(), key=lambda x: -x[1]):
        print(f"  {a:24s} {n}")

    print("\nPer-source breakdown:")
    for label, _ in CSV_INPUTS:
        c = per_source_action_counts.get(label, Counter())
        total = sum(c.values())
        applied = c.get("apply-value", 0) + c.get("apply-citation", 0)
        print(f"  {label:10s} total={total:5d}  applied={applied:5d}  "
              f"skipped={total - applied:5d}")

    if args.dry_run:
        print("\nDry run — no files mutated")
        return 0

    # Write landscape.json with mutations.
    text = json.dumps(landscape, indent=2, ensure_ascii=False)
    if not text.endswith("\n"):
        text += "\n"
    LANDSCAPE_JSON.write_text(text, encoding="utf-8")
    print(f"\nupdated {LANDSCAPE_JSON}")

    # Re-render landscape.html from the updated JSON.
    print("\nrendering landscape.html from updated landscape.json ...")
    run_render(LANDSCAPE_JSON)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

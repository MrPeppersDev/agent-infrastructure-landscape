#!/usr/bin/env python3
"""
apply_round10.py — integrate 3 Round-10 cleanup CSVs into the catalog.

Reads:
  - extraction/round-10-cleanup-fillable.csv          (56 rows — fillable
    cells that were still missing data after round 9)
  - extraction/round-10-cleanup-taxonomy-citations.csv (106 rows — cells
    that had real-data values but no citation)
  - extraction/round-10-cleanup-shallow-prose.csv     (134 rows — real-data
    prose cells flagged as too-thin by the audit)

Reuses the structure of scripts/apply_round9.py:
  1. read CSVs and normalise each row to (record_id, column, new_value,
     citation_url, status, source_csv)
  2. apply each update in-memory against web/landscape.json with
     downgrade protection (don't shorten an existing real-data cell)
  3. write the updated JSON
  4. invoke scripts/render.py to refresh landscape.html

Status enum normalisation (per the round-10 task brief):
  - the shallow-prose CSV uses status="resolved" with an `action_taken`
    column. All `resolved` rows are treated as `real-data`. The
    `action_taken=terminal-as-is` rows are no-ops: they confirm the
    existing cell is already terminal; we still write the citation if
    the CSV brought a better one (apply-citation path).
  - the fillable CSV uses the canonical statuses already: real-data,
    not-applicable, depth-floor-reached.
  - the taxonomy CSV is all real-data (citation backfill).

Emits extraction/round-10-apply-log.csv (every action: applied / skipped /
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

REPO = Path(__file__).resolve().parent.parent
EXTRACTION = REPO / "extraction"
LANDSCAPE_JSON = REPO / "web" / "landscape.json"
LANDSCAPE_HTML = REPO / "landscape.html"
LOG_CSV = EXTRACTION / "round-10-apply-log.csv"

CSV_INPUTS: list[tuple[str, Path]] = [
    ("fillable", EXTRACTION / "round-10-cleanup-fillable.csv"),
    ("taxonomy-citations", EXTRACTION / "round-10-cleanup-taxonomy-citations.csv"),
    ("shallow-prose", EXTRACTION / "round-10-cleanup-shallow-prose.csv"),
]

VALID_STATUSES = {"real-data", "not-applicable", "depth-floor-reached", "no-data"}

# Map non-canonical CSV status values to SCHEMA.md statuses. The cleanup #3
# agent emitted status="resolved" + action_taken ∈ {enriched, terminal-as-is,
# kept-short-with-citation}; all three of those mean "the final state is
# real-data".
STATUS_ALIAS = {
    "resolved": "real-data",
    # Defensive — should not appear in round-10 CSVs but guard against typos.
    "depth-floor": "depth-floor-reached",
    "na": "not-applicable",
    "n/a": "not-applicable",
}

# Substrings (case-insensitive) that signal "we looked and didn't find it".
# Used both to detect downgrades and to validate depth-floor / NA rows.
PLACEHOLDERS = (
    "no public benchmark scores found",
    "searched not found",
    "not specified",
    "no data",
    "no releases",
    "no headline",
    "no quantitative",
    "no public",
    "— not found",
    "- not found",
)


def looks_like_placeholder(value: str) -> bool:
    v = (value or "").strip().lower()
    if not v:
        return True
    for p in PLACEHOLDERS:
        if p in v:
            return True
    return False


def read_csv_normalised(path: Path, label: str) -> list[dict]:
    """Read a CSV and return normalised rows.

    Each row dict has: record_id, column, new_value, citation_url, status,
    source_csv. Status is normalised against STATUS_ALIAS.
    """
    out: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rid = (row.get("record_id") or "").strip()
            col = (row.get("column") or "").strip()
            if not rid or not col:
                continue
            value = (row.get("new_value") or "").strip()
            citation = (row.get("citation_url") or "").strip()
            status_raw = (row.get("status") or "").strip()
            status = STATUS_ALIAS.get(status_raw, status_raw)
            out.append({
                "record_id": rid,
                "column": col,
                "new_value": value,
                "citation_url": citation,
                "status": status,
                "source_csv": label,
                # Capture the action_taken column from shallow-prose CSV for
                # downgrade decisions (terminal-as-is should never overwrite).
                "action_taken": (row.get("action_taken") or "").strip(),
            })
    return out


def decide_action(cur: dict, incoming: dict) -> tuple[str, str]:
    """Return (action, reason).

    Actions:
      - 'apply-value'      : overwrite value+status; set citation if new
      - 'apply-citation'   : value/status unchanged; backfill citation
      - 'skip-no-change'   : nothing differs
      - 'skip-downgrade'   : current cell richer than incoming
      - 'skip-invalid'     : malformed / unknown status
    """
    in_value = incoming["new_value"]
    in_citation = incoming["citation_url"]
    in_status = incoming["status"]
    in_action = incoming.get("action_taken", "")

    if in_status not in VALID_STATUSES:
        return ("skip-invalid", f"unknown incoming status {in_status!r}")

    cur_value = (cur.get("value") or "").strip()
    cur_status = cur.get("status") or ""
    cur_citation = cur.get("citation") or ""

    # Case 1: incoming is just a citation backfill (value & status unchanged).
    if (
        in_status == "real-data"
        and in_value == cur_value
        and in_citation
        and not cur_citation
    ):
        return ("apply-citation", "value unchanged; backfill citation")

    # Case 2: action_taken=terminal-as-is from shallow-prose CSV. The cell is
    # already terminal; only adopt a new citation if we don't already have one
    # AND one was supplied.
    if in_action == "terminal-as-is":
        if in_citation and not cur_citation:
            return ("apply-citation", "terminal-as-is: backfill citation only")
        return ("skip-no-change", "terminal-as-is: existing cell confirmed terminal")

    # Case 3: downgrade protection — existing substantive real-data, incoming
    # is a depth-floor / NA placeholder.
    #
    # Exception: if the existing cell IS itself a placeholder ("searched not
    # found", "not advertised", etc.) misclassified as real-data, then the
    # round-10 cleanup's job is precisely to re-bucket it as
    # depth-floor-reached / not-applicable. So we let the rewrite through.
    if (
        cur_status == "real-data"
        and len(cur_value) > 30
        and looks_like_placeholder(in_value)
        and in_status != "real-data"
        and not looks_like_placeholder(cur_value)
    ):
        return ("skip-downgrade", "current real-data richer than incoming placeholder")

    if (
        cur_status == "real-data"
        and len(cur_value) > 0
        and in_status in {"not-applicable", "depth-floor-reached"}
        and looks_like_placeholder(in_value)
        and not looks_like_placeholder(cur_value)
    ):
        return ("skip-downgrade", "current real-data; incoming is depth-floor/NA placeholder")

    # Case 4: exact match.
    if (
        cur_value == in_value
        and cur_status == in_status
        and (cur_citation or "") == (in_citation or "")
    ):
        return ("skip-no-change", "exact match with current cell")

    # Case 5: incoming real-data significantly shorter than current real-data
    # without placeholder markers. Skip as a downgrade — this preserves
    # round-9 enrichment work.
    if (
        cur_status == "real-data"
        and in_status == "real-data"
        and len(cur_value) > len(in_value) + 20
        and not looks_like_placeholder(cur_value)
    ):
        return ("skip-downgrade", "current real-data significantly longer than incoming")

    return ("apply-value", "")


def apply_to_cell(cur: dict, incoming: dict, action: str) -> None:
    if action == "apply-citation":
        cur["citation"] = incoming["citation_url"] or None
        return
    if action == "apply-value":
        cur["value"] = incoming["new_value"]
        cur["status"] = incoming["status"]
        cur["citation"] = incoming["citation_url"] or None
        return
    return


def run_render(json_path: Path) -> None:
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
    if res.stdout.strip():
        print(res.stdout.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="parse + decide, but don't mutate files")
    args = ap.parse_args()

    landscape = json.loads(LANDSCAPE_JSON.read_text(encoding="utf-8"))
    records = landscape["records"]
    id_index: dict[str, dict] = {r["id"]: r for r in records}

    all_rows: list[dict] = []
    per_source_input_counts: Counter = Counter()
    for label, path in CSV_INPUTS:
        if not path.exists():
            print(f"warn: {path} missing — skipping", file=sys.stderr)
            continue
        rows = read_csv_normalised(path, label)
        per_source_input_counts[label] = len(rows)
        all_rows.extend(rows)

    print(f"loaded {len(all_rows)} rows from {len(CSV_INPUTS)} CSVs")
    for label, n in per_source_input_counts.items():
        print(f"  {label:24s} {n}")

    action_counts: Counter = Counter()
    per_source_action_counts: dict[str, Counter] = {
        label: Counter() for label, _ in CSV_INPUTS
    }
    log_rows: list[dict] = []

    for row in all_rows:
        rec_id = row["record_id"]
        col = row["column"]
        label = row["source_csv"]
        rec = id_index.get(rec_id)
        if rec is None:
            action = "unresolved-id"
            reason = "record_id not found in landscape.json"
            before = ""
        else:
            cells = rec.get("cells") or {}
            cell = cells.get(col)
            if cell is None:
                action = "unresolved-column"
                reason = f"column {col!r} not in record cells"
                before = ""
            else:
                before = json.dumps({
                    "value": cell.get("value", ""),
                    "status": cell.get("status", ""),
                    "citation": cell.get("citation"),
                }, ensure_ascii=False)
                decision, reason = decide_action(cell, row)
                if decision.startswith("apply") and not args.dry_run:
                    apply_to_cell(cell, row, decision)
                action = decision

        action_counts[action] += 1
        per_source_action_counts[label][action] += 1
        after_v = row["new_value"] if action.startswith("apply") else ""
        log_rows.append({
            "record_id": rec_id,
            "column": col,
            "action": action,
            "before": before[:300],
            "after": after_v[:300],
            "source_csv": label,
            "reason": reason,
        })

    LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    with LOG_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["record_id", "column", "action", "before", "after",
                        "source_csv", "reason"],
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
        print(f"  {label:24s} total={total:4d}  applied={applied:4d}  skipped={total - applied:4d}")

    if args.dry_run:
        print("\nDry run — no files mutated")
        return 0

    text = json.dumps(landscape, indent=2, ensure_ascii=False)
    if not text.endswith("\n"):
        text += "\n"
    LANDSCAPE_JSON.write_text(text, encoding="utf-8")
    print(f"\nupdated {LANDSCAPE_JSON}")

    print("\nrendering landscape.html from updated landscape.json ...")
    run_render(LANDSCAPE_JSON)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

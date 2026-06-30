#!/usr/bin/env python3
"""
cron_recommendation_drift.py — daily replay of canonical-questions through
the Phase 2 recommender to surface top-5 movement.

Phase 2 / Gate 6 (issue #100). Companion workflow:
`.github/workflows/recommendation-drift.yml`.

What it does
------------

1. Loads `docs/canonical-questions.yml`. Each entry maps to a recommender
   invocation (`surface: between` → AnchorPair, `surface: by-constraints`
   → ConstraintSet).
2. Shells into the TypeScript batch runner `mcp/dist/cron-rank-batch.js`
   to score all questions in a single Node process — TypeScript owns the
   ranking math, Python owns the orchestration / diffing / gh side-effects.
3. Loads yesterday's snapshot from `docs/drift-{Y-1}.md` (whichever is the
   most-recent file matching `drift-*.md`). Diffs today's top-5 per
   question against it.
4. Writes today's snapshot to `docs/drift-YYYY-MM-DD.md`.
5. For each question with **material** top-5 movement (see
   `is_material_movement`), opens a `drift-detected` GitHub Issue
   (dedupe-keyed on the question id + date).

"Daily run moves signal, not state" — never writes `data/landscape.json`.

Usage
-----

    python3 scripts/cron_recommendation_drift.py \
        [--questions docs/canonical-questions.yml] \
        [--snapshots-dir docs] \
        [--today YYYY-MM-DD] \
        [--dry-run]

`--dry-run` performs the full computation (loads YAML, calls the Node
batch, writes the snapshot markdown) but skips every `gh` invocation and
exits 0 regardless of label / issue state. Use it for local smoke.

Acceptance
----------
- Idempotent: running twice in a day overwrites the snapshot file but
  does not re-open an already-open `drift-detected` issue for the same
  question (gh-side dedupe by issue title).
- Defensive: missing `canonical-questions.yml` → exit 0 with a friendly
  message (Gate 5 may not have landed yet on `main`).
- Defensive: missing prior snapshot → snapshot today's run and exit 0
  with no diff (first-day behaviour).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUESTIONS = ROOT / "docs" / "canonical-questions.yml"
DEFAULT_SNAPSHOTS_DIR = ROOT / "docs"
NODE_RUNNER = ROOT / "mcp" / "dist" / "cron-rank-batch.js"

DRIFT_LABEL = "drift-detected"

# The 8-tag vocab from canonical-questions.yml is a strict superset of any
# valid `use_case`. We pass it through unchanged.
KNOWN_USE_CASES = {
    "scoped-agentic",
    "long-running-session",
    "multi-agent-coordination",
    "memory-augmented-chat",
    "code-generation-focused",
    "analytical-summarization",
    "latency-sensitive",
    "offline-capable",
}

# `structured` block keys we know how to translate. Anything else is dropped
# silently — defensive against future canonical-questions.yml shape additions.
STRUCTURED_PASSTHROUGH = {
    "use_case_tags",
    "cost_max_input_usd_per_mtok",
    "cost_tier_max",
    "capability_band_min",
}


# ---------------------------------------------------------------------------
# YAML load
# ---------------------------------------------------------------------------


def load_questions(path: Path) -> list[dict[str, Any]]:
    """Load canonical-questions.yml. Top-level is a list (per the Gate 5 file)."""
    import yaml  # noqa: WPS433 — keep the dep optional for environments without yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "questions" in raw:
        # Forward compat — some draft proposals wrapped the list in
        # `{questions: [...]}`. Accept either shape.
        return list(raw["questions"])
    if isinstance(raw, list):
        return raw
    raise ValueError(f"unexpected top-level YAML shape in {path}: {type(raw).__name__}")


# ---------------------------------------------------------------------------
# Question → batch-runner input
# ---------------------------------------------------------------------------


def map_question_to_batch(q: dict[str, Any]) -> dict[str, Any] | None:
    """Translate a canonical-questions entry to the cron-rank-batch input shape.

    Returns None for questions whose surface is not supported by the
    recommender (e.g. `comparison`). The drift cron silently skips those.
    """
    qid = q.get("id")
    if not qid:
        return None
    surface = (q.get("surface") or "").lower()
    inputs = q.get("inputs") or {}

    k = int(q.get("k") or 5)

    if surface == "between":
        low = inputs.get("anchor_low_id")
        high = inputs.get("anchor_high_id")
        if not low or not high:
            return None
        use_case = inputs.get("use_case")
        constraints: dict[str, Any] = {}
        if use_case and use_case in KNOWN_USE_CASES:
            constraints["use_case_tags"] = [use_case]
        return {
            "id": qid,
            "anchors": {"low": low, "high": high},
            "constraints": constraints,
            "k": k,
        }

    if surface == "by-constraints":
        structured = inputs.get("structured") or {}
        constraints = {k_: v for k_, v in structured.items() if k_ in STRUCTURED_PASSTHROUGH}
        return {
            "id": qid,
            "anchors": None,
            "constraints": constraints,
            "k": k,
        }

    # comparison / unknown — skip
    return None


# ---------------------------------------------------------------------------
# Node bridge
# ---------------------------------------------------------------------------


def call_batch_runner(batch_input: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not NODE_RUNNER.exists():
        raise FileNotFoundError(
            f"node runner not built — expected {NODE_RUNNER}. "
            "run `cd mcp && npm install && npm run build` first."
        )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(batch_input, fh)
        tmp_path = fh.name
    try:
        proc = subprocess.run(
            ["node", str(NODE_RUNNER), tmp_path],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
    finally:
        os.unlink(tmp_path)

    if proc.returncode != 0:
        raise RuntimeError(
            f"cron-rank-batch failed (exit {proc.returncode}): {proc.stderr.strip()}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"cron-rank-batch produced invalid JSON: {e}") from e


# ---------------------------------------------------------------------------
# Snapshot diff
# ---------------------------------------------------------------------------


def candidate_ids(result_entry: dict[str, Any]) -> list[str]:
    return [c["record"]["id"] for c in (result_entry.get("candidates") or [])]


def is_material_movement(prev_ids: list[str], cur_ids: list[str]) -> bool:
    """A movement is material if either:
       - the top-1 changed identity, OR
       - the set of top-5 ids changed by ≥ 2 members
    """
    if not prev_ids or not cur_ids:
        return False
    if prev_ids[0] != cur_ids[0]:
        return True
    prev_set = set(prev_ids[:5])
    cur_set = set(cur_ids[:5])
    return len(prev_set.symmetric_difference(cur_set)) >= 2


# ---------------------------------------------------------------------------
# Snapshot read / write
# ---------------------------------------------------------------------------


def snapshot_path(snapshots_dir: Path, day: dt.date) -> Path:
    return snapshots_dir / f"drift-{day.isoformat()}.md"


def find_latest_prior_snapshot(snapshots_dir: Path, today: dt.date) -> Path | None:
    candidates = sorted(snapshots_dir.glob("drift-*.md"))
    for path in reversed(candidates):
        stem = path.stem  # drift-YYYY-MM-DD
        try:
            day = dt.date.fromisoformat(stem.removeprefix("drift-"))
        except ValueError:
            continue
        if day < today:
            return path
    return None


def render_snapshot_markdown(
    today: dt.date,
    results: list[dict[str, Any]],
    diffs: dict[str, dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append(f"# Recommendation drift snapshot — {today.isoformat()}")
    lines.append("")
    lines.append(
        "Daily replay of `docs/canonical-questions.yml` against the Phase 2 "
        "recommender. Generated by `scripts/cron_recommendation_drift.py`."
    )
    lines.append("")
    lines.append(f"- Questions scored: **{len(results)}**")
    lines.append(f"- Material drift detected: **{sum(1 for d in diffs.values() if d.get('material'))}**")
    lines.append("")
    lines.append("## Per-question top-5")
    lines.append("")
    for r in results:
        qid = r["id"]
        cands = r.get("candidates") or []
        err = r.get("error")
        lines.append(f"### {qid}")
        if err:
            lines.append(f"- error: `{err}`")
            lines.append("")
            continue
        if not cands:
            lines.append("- no candidates returned (empty pool — anchors or constraints excluded every row)")
            lines.append("")
            continue
        for i, c in enumerate(cands, 1):
            rec = c["record"]
            lines.append(f"{i}. `{rec['id']}` ({rec.get('name','?')}) — score {c['score']:.3f}")
        diff = diffs.get(qid)
        if diff and diff.get("material"):
            lines.append("")
            lines.append(f"- **drift**: top-1 was `{diff['prev_top1']}`, now `{diff['cur_top1']}`")
            added = diff.get("added") or []
            removed = diff.get("removed") or []
            if added:
                lines.append(f"- entered top-5: {', '.join('`'+x+'`' for x in added)}")
            if removed:
                lines.append(f"- left top-5: {', '.join('`'+x+'`' for x in removed)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_snapshot_markdown(text: str) -> dict[str, list[str]]:
    """Recover the prior day's per-question top-5 ordered list of ids from
    a drift-*.md file. We re-parse the very lines we ourselves emitted; if
    the format changes the parser must change in lockstep.
    """
    out: dict[str, list[str]] = {}
    current: str | None = None
    cur_list: list[str] = []
    for line in text.splitlines():
        if line.startswith("### "):
            if current is not None:
                out[current] = cur_list
            current = line[4:].strip()
            cur_list = []
            continue
        if current is None:
            continue
        # lines look like "1. `record-id` (name) — score 0.500"
        stripped = line.lstrip()
        if stripped and stripped[0].isdigit() and ". `" in stripped:
            tick_start = stripped.index("`") + 1
            tick_end = stripped.index("`", tick_start)
            cur_list.append(stripped[tick_start:tick_end])
    if current is not None:
        out[current] = cur_list
    return out


# ---------------------------------------------------------------------------
# gh side-effects
# ---------------------------------------------------------------------------


def ensure_label(dry_run: bool) -> None:
    if dry_run:
        return
    subprocess.run(
        [
            "gh", "label", "create", DRIFT_LABEL,
            "--description", "Recommendation drift cron detected material top-5 movement.",
            "--color", "F9D0C4",
            "--force",
        ],
        capture_output=True, text=True, cwd=str(ROOT),
    )


def open_drift_issue(
    qid: str,
    question_text: str,
    diff: dict[str, Any],
    today: dt.date,
    dry_run: bool,
) -> None:
    title = f"drift: {qid} ({today.isoformat()})"
    body_lines = [
        f"Daily recommendation-drift cron detected a material top-5 movement "
        f"for canonical question `{qid}`.",
        "",
        f"> {question_text}",
        "",
        f"- Previous top-1: `{diff['prev_top1']}`",
        f"- Current top-1: `{diff['cur_top1']}`",
    ]
    added = diff.get("added") or []
    removed = diff.get("removed") or []
    if added:
        body_lines.append(f"- Entered top-5: {', '.join('`'+x+'`' for x in added)}")
    if removed:
        body_lines.append(f"- Left top-5: {', '.join('`'+x+'`' for x in removed)}")
    body_lines.extend([
        "",
        f"Full snapshot: `docs/drift-{today.isoformat()}.md`",
        "",
        "_Auto-opened by `scripts/cron_recommendation_drift.py` "
        "(Phase 2 / Gate 6, issue #100). Daily runs move signal, not state — "
        "no `data/landscape.json` write happens here._",
    ])
    body = "\n".join(body_lines)
    if dry_run:
        print(f"[dry-run] would open issue: {title}")
        return
    # Dedupe — if there's already an open drift-detected issue with this exact
    # title, skip. Same idempotency pattern as staleness.yml.
    existing = subprocess.run(
        ["gh", "issue", "list", "--state", "open", "--label", DRIFT_LABEL,
         "--search", f"\"{title}\" in:title", "--json", "number", "--jq", "length"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if existing.returncode == 0 and existing.stdout.strip() not in ("", "0"):
        print(f"skip: already-open drift issue for {qid} on {today}")
        return
    subprocess.run(
        ["gh", "issue", "create", "--title", title, "--label", DRIFT_LABEL,
         "--body", body],
        check=False, cwd=str(ROOT),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> int:
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    questions_path: Path = args.questions
    snapshots_dir: Path = args.snapshots_dir
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    if not questions_path.exists():
        # Gate 5 may not have landed on main yet. Don't fail — emit a
        # placeholder snapshot so the workflow stays green and the
        # operational record exists.
        print(
            f"cron_recommendation_drift: {questions_path} not found — "
            "nothing to score (Gate 5 may not be on main yet).",
            file=sys.stderr,
        )
        path = snapshot_path(snapshots_dir, today)
        path.write_text(
            f"# Recommendation drift snapshot — {today.isoformat()}\n\n"
            f"No canonical-questions.yml present yet. Cron is a no-op until Gate 5 lands.\n",
            encoding="utf-8",
        )
        return 0

    questions = load_questions(questions_path)
    batch_input: list[dict[str, Any]] = []
    question_text: dict[str, str] = {}
    for q in questions:
        mapped = map_question_to_batch(q)
        if mapped is None:
            continue
        batch_input.append(mapped)
        question_text[mapped["id"]] = q.get("text") or ""

    print(
        f"cron_recommendation_drift: scoring {len(batch_input)} question(s) "
        f"out of {len(questions)} canonical entries; today={today.isoformat()}",
        file=sys.stderr,
    )

    if not batch_input:
        path = snapshot_path(snapshots_dir, today)
        path.write_text(
            f"# Recommendation drift snapshot — {today.isoformat()}\n\n"
            f"No supported questions in canonical-questions.yml (0 of {len(questions)}).\n",
            encoding="utf-8",
        )
        return 0

    results = call_batch_runner(batch_input)

    prior_path = find_latest_prior_snapshot(snapshots_dir, today)
    prior_top: dict[str, list[str]] = {}
    if prior_path is not None:
        try:
            prior_top = parse_snapshot_markdown(prior_path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 — defensive against corrupted snapshot
            print(f"cron_recommendation_drift: failed to parse {prior_path}: {e}", file=sys.stderr)

    diffs: dict[str, dict[str, Any]] = {}
    material_count = 0
    for r in results:
        qid = r["id"]
        cur = candidate_ids(r)
        prev = prior_top.get(qid, [])
        material = is_material_movement(prev, cur)
        if material:
            material_count += 1
            diffs[qid] = {
                "material": True,
                "prev_top1": prev[0] if prev else "(none)",
                "cur_top1": cur[0] if cur else "(none)",
                "added": sorted(set(cur[:5]) - set(prev[:5])),
                "removed": sorted(set(prev[:5]) - set(cur[:5])),
            }

    # Write snapshot
    md = render_snapshot_markdown(today, results, diffs)
    path = snapshot_path(snapshots_dir, today)
    path.write_text(md, encoding="utf-8")
    print(f"cron_recommendation_drift: wrote {path}", file=sys.stderr)

    if material_count == 0:
        print("cron_recommendation_drift: no material drift today.", file=sys.stderr)
        return 0

    ensure_label(args.dry_run)
    for qid, diff in diffs.items():
        if diff.get("material"):
            open_drift_issue(
                qid=qid,
                question_text=question_text.get(qid, ""),
                diff=diff,
                today=today,
                dry_run=args.dry_run,
            )

    print(
        f"cron_recommendation_drift: {material_count} drift issue(s) "
        f"{'(dry-run, not opened)' if args.dry_run else 'requested via gh'}.",
        file=sys.stderr,
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS,
                   help="Path to canonical-questions.yml (default: docs/canonical-questions.yml).")
    p.add_argument("--snapshots-dir", type=Path, default=DEFAULT_SNAPSHOTS_DIR,
                   help="Directory for drift-YYYY-MM-DD.md files (default: docs/).")
    p.add_argument("--today", default=None,
                   help="Override today (ISO date). Default: actual UTC today.")
    p.add_argument("--dry-run", action="store_true",
                   help="Do full compute + write snapshot, but skip every gh call.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())

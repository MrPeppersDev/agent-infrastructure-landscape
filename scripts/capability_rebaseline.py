#!/usr/bin/env python3
"""Weekly capability rebaseline cron (Phase 2 / Gate 8 — issue #102).

Once a week (Sundays 06:00 UTC), capture every row's current capability
cells and provenance, persist to `data/_baselines/rebaseline-YYYY-MM-DD.json`,
diff against the previous baseline, and emit a human-readable
`docs/FINDINGS-YYYY-MM-DD.md` listing the top movers, new entries, and
band-shift rows. Opens a `phase-2-rebaseline` tracking issue linking to
the FINDINGS doc.

This is the ground-truth anchor that catches drift the daily incremental
cron (Gate 6) misses. Where the daily cron flags rows where the *sources*
cell changed, this weekly pass scans every row's score and band — so any
drift introduced by upstream methodology shifts is visible.

Daily runs move signal, not state — this cron is the same. It opens a
tracking issue but never writes to `data/landscape.json`.

Operational properties:
- Schedule: Sundays 06:00 UTC.
- Output: docs/FINDINGS-YYYY-MM-DD.md + data/_baselines/rebaseline-*.json.
- Issue: phase-2-rebaseline label, opened once per run.
- Movement summary: verified-true cells rank above LLM-unverified ones.
- Dry-run: --dry-run skips `gh issue create` calls.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LANDSCAPE = ROOT / "data" / "landscape.json"
BASELINE_DIR = ROOT / "data" / "_baselines"
DOCS_DIR = ROOT / "docs"

CAPABILITY_CELLS = (
    "capability-composite-score",
    "capability-band",
    "capability-benchmark-sources",
)

# Top-N rows surfaced in the FINDINGS doc for each section.
TOP_MOVERS_N = 30
TOP_BAND_SHIFTS_N = 50


def load_landscape() -> dict[str, Any]:
    return json.loads(LANDSCAPE.read_text(encoding="utf-8"))


def capture_snapshot(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-row snapshot: id → {score, band, sources_hash, provenance}."""
    snap: dict[str, dict[str, Any]] = {}
    for r in records:
        cells = r.get("cells") or {}
        score_cell = cells.get("capability-composite-score") or {}
        band_cell = cells.get("capability-band") or {}
        sources_cell = cells.get("capability-benchmark-sources") or {}
        prov = (r.get("_provenance") or {}).get("capability-composite-score") or {}
        snap[r["id"]] = {
            "name": r.get("name", ""),
            "score": score_cell.get("value"),
            "band": band_cell.get("value"),
            "sources": sources_cell.get("value"),
            "source": prov.get("source"),
            "verified": prov.get("verified"),
        }
    return snap


def find_prior_baseline() -> Path | None:
    if not BASELINE_DIR.exists():
        return None
    files = sorted(BASELINE_DIR.glob("rebaseline-*.json"), reverse=True)
    return files[0] if files else None


def parse_score(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def diff_snapshots(
    prior: dict[str, dict[str, Any]] | None,
    current: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Return movers / band-shifts / new-rows / retired-rows."""
    movers: list[dict[str, Any]] = []
    band_shifts: list[dict[str, Any]] = []
    new_rows: list[dict[str, Any]] = []
    retired_rows: list[dict[str, Any]] = []

    prior = prior or {}
    for rid, cur in current.items():
        old = prior.get(rid)
        if old is None:
            new_rows.append({"id": rid, "name": cur["name"], "band": cur["band"]})
            continue
        old_score = parse_score(old.get("score"))
        new_score = parse_score(cur.get("score"))
        if old_score is not None and new_score is not None and old_score != new_score:
            movers.append({
                "id": rid,
                "name": cur["name"],
                "old": old_score,
                "new": new_score,
                "delta": new_score - old_score,
                "verified": cur.get("verified"),
                "source": cur.get("source"),
            })
        if old.get("band") != cur.get("band"):
            band_shifts.append({
                "id": rid,
                "name": cur["name"],
                "old_band": old.get("band"),
                "new_band": cur.get("band"),
                "verified": cur.get("verified"),
                "source": cur.get("source"),
            })

    for rid, old in prior.items():
        if rid not in current:
            retired_rows.append({"id": rid, "name": old.get("name", "")})

    # Order: verified-true first, then by absolute delta / band shift magnitude.
    def verified_rank(x: dict[str, Any]) -> int:
        return 0 if x.get("verified") is True else 1

    movers.sort(key=lambda x: (verified_rank(x), -abs(x["delta"]), x["id"]))
    band_shifts.sort(key=lambda x: (verified_rank(x), x["id"]))

    return {
        "movers": movers,
        "band_shifts": band_shifts,
        "new_rows": new_rows,
        "retired_rows": retired_rows,
    }


def render_findings(
    today: dt.date,
    prior_path: Path | None,
    current: dict[str, dict[str, Any]],
    diff: dict[str, list[dict[str, Any]]],
) -> str:
    lines = [
        f"# Phase 2 capability rebaseline — {today.isoformat()}",
        "",
        "Weekly full re-snapshot of every row's `capability-composite-score`, "
        "`capability-band`, and `capability-benchmark-sources` provenance. "
        "Generated by `scripts/capability_rebaseline.py` "
        "(Phase 2 / Gate 8, issue #102).",
        "",
        f"- Rows in snapshot: **{len(current)}**",
        f"- Prior baseline: {'`' + prior_path.name + '`' if prior_path else '_none — first run_'}",
        f"- Movers (score changed): **{len(diff['movers'])}**",
        f"- Band shifts: **{len(diff['band_shifts'])}**",
        f"- New rows since prior baseline: **{len(diff['new_rows'])}**",
        f"- Retired rows since prior baseline: **{len(diff['retired_rows'])}**",
        "",
        "## How to read this",
        "",
        "Movers and band shifts are ordered with verified-provenance cells first; "
        "rows where the cell is LLM-unverified appear below. Per Gate 1's "
        "`_provenance` policy (issue #95), a numeric shift on a verified cell "
        "carries more signal than the same shift on an LLM-only cell.",
        "",
    ]

    lines.append(f"## Top {TOP_MOVERS_N} movers")
    lines.append("")
    if not diff["movers"]:
        lines.append("_No score changes since prior baseline._")
    else:
        lines.append("| Row | Δ | Old | New | Provenance |")
        lines.append("|---|---:|---:|---:|---|")
        for m in diff["movers"][:TOP_MOVERS_N]:
            verified_mark = "✔" if m.get("verified") is True else "·"
            src = m.get("source") or "?"
            lines.append(
                f"| `{m['id']}` — {m['name']} | {m['delta']:+.3f} | "
                f"{m['old']:.3f} | {m['new']:.3f} | {verified_mark} {src} |"
            )
    lines.append("")

    lines.append(f"## Band shifts (top {TOP_BAND_SHIFTS_N})")
    lines.append("")
    if not diff["band_shifts"]:
        lines.append("_No band shifts since prior baseline._")
    else:
        lines.append("| Row | Old band | New band | Provenance |")
        lines.append("|---|---|---|---|")
        for b in diff["band_shifts"][:TOP_BAND_SHIFTS_N]:
            verified_mark = "✔" if b.get("verified") is True else "·"
            src = b.get("source") or "?"
            lines.append(
                f"| `{b['id']}` — {b['name']} | "
                f"`{b.get('old_band') or '?'}` | `{b.get('new_band') or '?'}` | "
                f"{verified_mark} {src} |"
            )
    lines.append("")

    lines.append("## New rows since prior baseline")
    lines.append("")
    if not diff["new_rows"]:
        lines.append("_None._")
    else:
        for n in diff["new_rows"][:50]:
            band = n.get("band") or "?"
            lines.append(f"- `{n['id']}` — {n['name']} (band `{band}`)")
        if len(diff["new_rows"]) > 50:
            lines.append(f"- _… and {len(diff['new_rows']) - 50} more_")
    lines.append("")

    lines.append("## Retired rows since prior baseline")
    lines.append("")
    if not diff["retired_rows"]:
        lines.append("_None._")
    else:
        for r in diff["retired_rows"][:50]:
            lines.append(f"- `{r['id']}` — {r['name']}")
        if len(diff["retired_rows"]) > 50:
            lines.append(f"- _… and {len(diff['retired_rows']) - 50} more_")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "_This document is generated by a weekly cron. It is a signal pass — "
        "no automatic edits to `data/landscape.json` are applied. The "
        "`phase-2-rebaseline` tracking issue links here for maintainer review._"
    )
    return "\n".join(lines) + "\n"


def render_issue_body(today: dt.date, diff: dict[str, list[dict[str, Any]]], findings_path: Path) -> str:
    relative = findings_path.relative_to(ROOT)
    return "\n".join([
        f"## Weekly capability rebaseline — {today.isoformat()}",
        "",
        f"- Movers: **{len(diff['movers'])}**",
        f"- Band shifts: **{len(diff['band_shifts'])}**",
        f"- New rows: **{len(diff['new_rows'])}**",
        f"- Retired rows: **{len(diff['retired_rows'])}**",
        "",
        f"Full FINDINGS doc: [`{relative}`](../blob/main/{relative})",
        "",
        "_Auto-opened by `scripts/capability_rebaseline.py` "
        "(Phase 2 / Gate 8). Daily runs move signal, not state._",
    ]) + "\n"


def open_tracking_issue(today: dt.date, body: str, dry_run: bool) -> None:
    title = f"phase-2-rebaseline: weekly capability snapshot — {today.isoformat()}"
    if dry_run:
        print(f"[dry-run] would open issue: {title}", file=sys.stderr)
        return
    try:
        subprocess.run([
            "gh", "issue", "create",
            "--title", title,
            "--label", "phase-2-rebaseline",
            "--body", body,
        ], check=True, cwd=str(ROOT))
    except subprocess.CalledProcessError as e:
        print(f"capability_rebaseline: gh issue create failed: {e}", file=sys.stderr)


def ensure_label(dry_run: bool) -> None:
    if dry_run:
        return
    try:
        subprocess.run([
            "gh", "label", "create", "phase-2-rebaseline",
            "--description", "Weekly capability-rebaseline tracking issue (Phase 2 / Gate 8).",
            "--color", "0E8A16",
            "--force",
        ], check=False, cwd=str(ROOT))
    except FileNotFoundError:
        pass


def run(args: argparse.Namespace) -> int:
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    data = load_landscape()
    records = data.get("records") or []
    current = capture_snapshot(records)

    prior_path = find_prior_baseline()
    prior_snapshot: dict[str, dict[str, Any]] | None = None
    if prior_path:
        try:
            prior_snapshot = json.loads(prior_path.read_text(encoding="utf-8")).get("snapshot")
        except (OSError, json.JSONDecodeError) as e:
            print(f"capability_rebaseline: unreadable prior baseline {prior_path}: {e}", file=sys.stderr)

    diff = diff_snapshots(prior_snapshot, current)

    # Persist today's baseline.
    out_baseline = BASELINE_DIR / f"rebaseline-{today.isoformat()}.json"
    out_baseline.write_text(
        json.dumps({"date": today.isoformat(), "snapshot": current}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Render FINDINGS doc.
    findings_path = DOCS_DIR / f"FINDINGS-{today.isoformat()}.md"
    findings_path.write_text(render_findings(today, prior_path, current, diff), encoding="utf-8")

    print(
        f"capability_rebaseline: rows={len(current)} movers={len(diff['movers'])} "
        f"band_shifts={len(diff['band_shifts'])} new={len(diff['new_rows'])} "
        f"retired={len(diff['retired_rows'])}",
        file=sys.stderr,
    )
    print(f"capability_rebaseline: wrote {out_baseline.relative_to(ROOT)}", file=sys.stderr)
    print(f"capability_rebaseline: wrote {findings_path.relative_to(ROOT)}", file=sys.stderr)

    if args.no_issue:
        return 0

    ensure_label(args.dry_run)
    open_tracking_issue(today, render_issue_body(today, diff, findings_path), args.dry_run)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 2 / Gate 8 — weekly capability rebaseline.")
    p.add_argument("--today", help="Override today's date (YYYY-MM-DD).")
    p.add_argument("--dry-run", action="store_true", help="Skip gh issue create calls.")
    p.add_argument("--no-issue", action="store_true", help="Skip opening the tracking issue entirely.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())

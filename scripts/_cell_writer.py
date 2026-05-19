#!/usr/bin/env python3
"""_cell_writer.py — minimal helper for Path A (JSON-authoritative) cell writes.

Used by the trajectory writer scripts (fetch_commit_trajectories.py,
fetch_download_trajectories.py, bucket_s2_citations.py) to update one
cell at a time on data/landscape.json without re-projecting through
landscape.html. See issue #68 for the Path A flip context.

The underscore prefix marks this as an internal helper, not a top-level
pipeline step. Keep it small and stdlib-only.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def load_landscape(path: Path) -> dict[str, Any]:
    """Read data/landscape.json and return the parsed top-level dict."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_record(landscape: dict[str, Any], record_id: str) -> dict[str, Any] | None:
    """Return the record with matching `id`, or None."""
    for rec in landscape.get("records") or []:
        if rec.get("id") == record_id:
            return rec
    return None


def update_cell(
    record: dict[str, Any],
    cell_slug: str,
    *,
    value: str,
    status: str = "real-data",
    citation: str | None = None,
    last_verified_at: str | None = None,
) -> bool:
    """Update `record["cells"][cell_slug]` in place. Returns True iff anything
    actually changed (lets callers track idempotency and skip writes).

    If `last_verified_at` is None the existing per-cell value (if any) is
    preserved unchanged — matches the legacy HTML-writer behavior where
    trajectory cells inherited their last_verified_at from a separate
    backfill pass. The `tier` field is left alone; extract.py / render.py
    recompute it from (status, citation) on the next round-trip.
    """
    cells = record.setdefault("cells", {})
    existing = cells.get(cell_slug) or {}
    new_cell: dict[str, Any] = {
        "value": value,
        "citation": citation,
        "status": status,
    }
    # Preserve existing tier + last_verified_at unless overridden.
    if "tier" in existing:
        new_cell["tier"] = existing["tier"]
    if last_verified_at is not None:
        new_cell["last_verified_at"] = last_verified_at
    elif "last_verified_at" in existing:
        new_cell["last_verified_at"] = existing["last_verified_at"]
    if new_cell == existing:
        return False
    cells[cell_slug] = new_cell
    return True


def save_landscape(landscape: dict[str, Any], path: Path) -> None:
    """Atomically write landscape.json with the existing format (2-space
    indent, ensure_ascii=False, trailing newline)."""
    path = Path(path)
    text = json.dumps(landscape, indent=2, ensure_ascii=False)
    if not text.endswith("\n"):
        text += "\n"
    # Write to a tempfile in the same directory, then rename — atomic on
    # POSIX and avoids leaving a half-written landscape.json on SIGINT.
    fd, tmp = tempfile.mkstemp(
        prefix=".landscape.json.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

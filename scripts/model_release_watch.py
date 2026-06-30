#!/usr/bin/env python3
"""Event-driven model release watch (Phase 2 / Gate 8 — issue #102).

Runs every 30 minutes via .github/workflows/model-release-watch.yml.
Polls a controlled list of vendor RSS/Atom feeds at data/_feeds.yml.
For each entry that has not been seen before (per data/_feeds-seen.json)
AND matches the release-keyword filter, opens a GitHub issue labelled
`intake` + `intake-release-watch`. The existing intake-research.yml
workflow (already wired for `intake`-labeled issues) takes over for
enrichment and draft-PR creation.

Architectural note: the spec described webhook + RSS poller. This static
site has no webhook receiver, so the gate ships only the poller half.
The "every 30 min" cadence is event-driven enough in practice — most
vendor releases sit on a blog feed for hours before downstream tools
pick them up.

Daily runs move signal, not state — this script opens issues but does
NOT write to data/landscape.json. The downstream draft PR from
intake-research.yml is still subject to maintainer review.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FEEDS_YAML = ROOT / "data" / "_feeds.yml"
SEEN_JSON = ROOT / "data" / "_feeds-seen.json"

# Match titles/summaries shaped like a model or system release. Loose by
# design — better to open one extra issue than miss a release; the
# maintainer-review gate is at intake-research.yml's draft PR step.
RELEASE_KEYWORDS = [
    r"\bintroducing\b",
    r"\blaunch(ing|ed)?\b",
    r"\brelease(d|ing)?\b",
    r"\bannouncing\b",
    r"\bavailable now\b",
    r"\bnow available\b",
    r"\bnew model\b",
    r"\bnew (frontier|reasoning|coding|vision|embedding|multimodal) model\b",
    r"\bunveils?\b",
    r"\b(gpt|claude|gemini|llama|mistral|qwen|deepseek|grok|command|phi|nova|sonnet|opus|haiku|kimi|yi)[- ]?\d",
    r"\bopen[- ]source(d|ing)?\b",
]
KEYWORD_RE = re.compile("|".join(RELEASE_KEYWORDS), re.IGNORECASE)


def load_feeds() -> list[dict[str, Any]]:
    try:
        import yaml
    except ImportError:
        print("model_release_watch: pyyaml is required (pip install pyyaml)", file=sys.stderr)
        raise

    if not FEEDS_YAML.exists():
        return []
    raw = yaml.safe_load(FEEDS_YAML.read_text(encoding="utf-8")) or {}
    feeds = raw.get("feeds") or []
    return [f for f in feeds if isinstance(f, dict) and f.get("url")]


def load_seen() -> dict[str, dict[str, Any]]:
    if not SEEN_JSON.exists():
        return {"schemaVersion": 1, "feeds": {}}
    try:
        return json.loads(SEEN_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schemaVersion": 1, "feeds": {}}


def save_seen(state: dict[str, Any]) -> None:
    SEEN_JSON.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def entry_id(entry: Any) -> str:
    """Stable ID per feed entry. Prefer entry.id, fall back to link, then to
    a hash of (title, published)."""
    candidate = getattr(entry, "id", None) or getattr(entry, "link", None)
    if candidate:
        return str(candidate)
    title = getattr(entry, "title", "") or ""
    published = getattr(entry, "published", "") or getattr(entry, "updated", "") or ""
    return "hash:" + hashlib.sha1(f"{title}|{published}".encode("utf-8")).hexdigest()


def is_release_shaped(entry: Any) -> bool:
    title = getattr(entry, "title", "") or ""
    summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
    return bool(KEYWORD_RE.search(title) or KEYWORD_RE.search(summary))


def render_issue_body(vendor: str, entry: Any, feed_url: str) -> str:
    title = getattr(entry, "title", "") or "(untitled)"
    link = getattr(entry, "link", "") or ""
    summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
    published = getattr(entry, "published", "") or getattr(entry, "updated", "") or ""

    body_lines = [
        f"## Auto-detected release ({vendor})",
        "",
        f"- **Title**: {title}",
        f"- **Link**: {link}",
        f"- **Published**: {published or '(no date)'}",
        f"- **Feed**: `{feed_url}`",
        "",
        "### Summary",
        "",
    ]
    body_lines.append(summary[:2000] if summary else "_(no summary in feed entry)_")
    body_lines.extend([
        "",
        "---",
        "",
        "### Submission scaffold for `intake-research.yml`",
        "",
        f"- url: {link}",
        f"- name: {title}",
        f"- type: model",
        f"- description: {summary[:500] if summary else ''}",
        "",
        "_Auto-opened by `scripts/model_release_watch.py` "
        "(Phase 2 / Gate 8). The existing `intake-research.yml` workflow will "
        "pick this up via the `intake` label and produce a draft PR; the "
        "maintainer review gate is unchanged._",
    ])
    return "\n".join(body_lines) + "\n"


def open_issue(vendor: str, entry: Any, feed_url: str, dry_run: bool) -> bool:
    title = getattr(entry, "title", "") or "(untitled)"
    short = title[:80].rstrip()
    issue_title = f"Intake (release-watch): {vendor} — {short}"
    body = render_issue_body(vendor, entry, feed_url)
    if dry_run:
        print(f"[dry-run] would open issue: {issue_title}", file=sys.stderr)
        return True
    try:
        subprocess.run([
            "gh", "issue", "create",
            "--title", issue_title,
            "--label", "intake",
            "--label", "intake-release-watch",
            "--body", body,
        ], check=True, cwd=str(ROOT))
        return True
    except subprocess.CalledProcessError as e:
        print(f"model_release_watch: gh issue create failed for '{issue_title}': {e}", file=sys.stderr)
        return False


def ensure_label(dry_run: bool) -> None:
    if dry_run:
        return
    try:
        subprocess.run([
            "gh", "label", "create", "intake-release-watch",
            "--description", "Auto-opened by Phase 2 / Gate 8 model-release-watch RSS poller.",
            "--color", "1D76DB",
            "--force",
        ], check=False, cwd=str(ROOT))
    except FileNotFoundError:
        pass


def process_feed(
    feed_def: dict[str, Any],
    seen_ids: set[str],
    *,
    prime_only: bool,
    dry_run: bool,
    max_emit: int,
    emitted_so_far: int,
) -> tuple[set[str], int]:
    """Returns (new seen-ids after this run, count of issues opened)."""
    try:
        import feedparser
    except ImportError:
        print("model_release_watch: feedparser is required (pip install feedparser)", file=sys.stderr)
        raise

    vendor = feed_def.get("vendor") or feed_def.get("url") or "(unknown vendor)"
    url = feed_def["url"]

    parsed = feedparser.parse(url)
    if parsed.bozo and not parsed.entries:
        print(f"model_release_watch: bozo (parse error) — {url}: {parsed.bozo_exception}", file=sys.stderr)
        return seen_ids, 0

    next_seen = set(seen_ids)
    opened = 0
    for entry in parsed.entries:
        eid = entry_id(entry)
        if eid in seen_ids:
            continue
        next_seen.add(eid)
        if prime_only:
            # First time this feed is seen — just prime, never open.
            continue
        if not is_release_shaped(entry):
            continue
        if emitted_so_far + opened >= max_emit:
            print(f"model_release_watch: max-emit cap ({max_emit}) reached", file=sys.stderr)
            break
        if open_issue(vendor, entry, url, dry_run):
            opened += 1

    return next_seen, opened


def run(args: argparse.Namespace) -> int:
    feeds = load_feeds()
    if not feeds:
        print(
            f"model_release_watch: {FEEDS_YAML.relative_to(ROOT)} not found or empty — nothing to poll.",
            file=sys.stderr,
        )
        return 0

    state = load_seen()
    per_feed = state.setdefault("feeds", {})

    ensure_label(args.dry_run)

    total_opened = 0
    for feed_def in feeds:
        url = feed_def["url"]
        prior_seen = set(per_feed.get(url) or [])
        # First time we see this feed in state → prime mode (no issues opened).
        prime_only = url not in per_feed
        next_seen, opened = process_feed(
            feed_def, prior_seen,
            prime_only=prime_only,
            dry_run=args.dry_run,
            max_emit=args.max_emit,
            emitted_so_far=total_opened,
        )
        per_feed[url] = sorted(next_seen)
        total_opened += opened
        if prime_only:
            print(
                f"model_release_watch: primed {url} with {len(next_seen)} entries "
                "(no issues opened on first sight per spec).",
                file=sys.stderr,
            )

    state["lastRunAt"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    save_seen(state)
    print(f"model_release_watch: opened {total_opened} intake issue(s) across {len(feeds)} feed(s).", file=sys.stderr)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 2 / Gate 8 — RSS-poller release watch.")
    p.add_argument("--dry-run", action="store_true", help="Skip gh issue create calls.")
    p.add_argument("--max-emit", type=int, default=5, help="Hard cap on issues opened per run.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())

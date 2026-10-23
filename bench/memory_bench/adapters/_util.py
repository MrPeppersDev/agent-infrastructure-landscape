"""Small shared helpers for the third-party memory-layer adapters.

Stdlib only, so the core still imports without any memory SDK installed.
"""

from __future__ import annotations

import asyncio
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Iterable, TypeVar

T = TypeVar("T")

# Output dimensions of the common OpenAI embedding models, for systems that
# need the vector size spelled out when the model is not their default.
EMBED_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}

_DATE_FORMATS = (
    "%Y/%m/%d %H:%M",           # LongMemEval: "2023/05/20 (Sat) 02:21" (weekday stripped)
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%I:%M %p on %d %B, %Y",    # LoCoMo: "1:56 pm on 8 May, 2023"
    "%I:%M %p on %d %b, %Y",
    "%I:%M %p on %B %d, %Y",
    "%d %B, %Y",
    "%d %B %Y",
    "%B %d, %Y",
)


def parse_session_date(text: str | None) -> datetime | None:
    """Best-effort parse of the free-text session / question dates used by the
    datasets. Returns a timezone-aware datetime (naive values are taken as
    UTC) or None when the text cannot be parsed."""
    if not text:
        return None
    s = re.sub(r"\((?:[A-Za-z]{2,9})\)", " ", str(text))  # drop "(Sat)"
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return None
    dt: datetime | None = None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        for fmt in _DATE_FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def iso_utc(dt: datetime | None) -> str | None:
    """RFC 3339 / ISO 8601 string in UTC with a trailing Z, or None."""
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_tag() -> str:
    """Short random suffix so every run gets fresh, never-before-used ids."""
    return uuid.uuid4().hex[:10]


def safe_id(text: str, maxlen: int = 100, allowed: str = r"A-Za-z0-9_-") -> str:
    """Restrict an id to the characters a system accepts (default
    alphanumerics, '_' and '-'); other characters become '_'."""
    out = re.sub(rf"[^{allowed}]", "_", str(text))
    return (out or "x")[:maxlen]


def chunks(seq: list[T], n: int) -> Iterable[list[T]]:
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def split_text(text: str, limit: int) -> list[str]:
    """Split a string into pieces of at most `limit` characters, preferring
    whitespace boundaries. Used only where a system documents a hard
    per-message size limit."""
    text = text or ""
    if len(text) <= limit:
        return [text]
    parts, rest = [], text
    while len(rest) > limit:
        cut = rest.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(rest[:cut])
        rest = rest[cut:].lstrip()
    if rest:
        parts.append(rest)
    return parts


def poll(check: Callable[[], bool], timeout: float, interval: float = 2.0, what: str = "") -> None:
    """Call `check` until it returns True or `timeout` seconds pass."""
    deadline = time.monotonic() + timeout
    while True:
        if check():
            return
        if time.monotonic() > deadline:
            raise TimeoutError(f"timed out after {timeout:.0f}s waiting for {what or 'ingestion'}")
        time.sleep(interval)


class AsyncRunner:
    """Runs coroutines of an async SDK on one private event loop that lives
    for the adapter's lifetime, so connection pools bound to the loop (Neo4j
    driver, SQLAlchemy engines) keep working between calls. The loop runs in
    a daemon thread, so this also works if the caller already has a loop."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def run(self, coro: Awaitable[T]) -> T:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()  # type: ignore[arg-type]

    def close(self) -> None:
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)


def get(obj: Any, name: str, default: Any = None) -> Any:
    """Attribute-or-key access for SDKs that return either models or dicts."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

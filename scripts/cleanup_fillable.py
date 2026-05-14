#!/usr/bin/env python3
"""
Round-10 cleanup helper for `fillable-and-missing` cells.

Reads `extraction/data-gaps.csv`, filters to fillable-and-missing rows, and
uses `curl` to probe vendor pages / arxiv abstracts for the missing field.
Emits scratch JSON to /tmp/cleanup-fillable/{record_id}__{column}.json so the
operator can inspect the raw evidence.

This script is READ-ONLY with respect to data/landscape.json. It does NOT
modify the landscape. It only emits research artefacts.

Final CSV is built by hand-curating findings into
extraction/round-10-cleanup-fillable.csv.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GAPS = REPO / "extraction" / "data-gaps.csv"
OUT_DIR = Path("/tmp/cleanup-fillable")
OUT_DIR.mkdir(exist_ok=True, parents=True)


def curl(url: str, timeout: int = 12) -> str:
    """Fetch URL via curl and return the body text (html-stripped)."""
    try:
        r = subprocess.run(
            [
                "curl",
                "-sL",
                "--max-time",
                str(timeout),
                "-A",
                "Mozilla/5.0 (compatible; mem-research/1.0)",
                url,
            ],
            capture_output=True,
            timeout=timeout + 3,
        )
        if r.returncode != 0:
            return ""
        return r.stdout.decode("utf-8", errors="ignore")
    except Exception as e:  # noqa: BLE001
        return f"__ERROR__: {e}"


def strip_html(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


TERMS = {
    "mcp-support": [
        "Model Context Protocol",
        "MCP server",
        "MCP integration",
        " MCP ",
    ],
    "a2a-support": [
        "A2A",
        "agent-to-agent",
        "Agent2Agent",
        "agent to agent",
    ],
    "otel": ["OpenTelemetry", "OTel", "OTLP", "otel-collector"],
    "webhooks": ["webhook", "Webhook"],
    "import-export": ["import", "export", "CSV export", "JSON export", "data portability"],
}


def probe(text: str, column: str) -> list[str]:
    """Return list of context snippets for terms matching this column."""
    hits = []
    for term in TERMS.get(column, []):
        for m in re.finditer(re.escape(term), text, re.IGNORECASE):
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 120)
            hits.append(text[start:end])
            if len(hits) >= 3:
                return hits
    return hits


def main():
    with GAPS.open() as f:
        rows = [r for r in csv.DictReader(f) if r["gap_class"] == "fillable-and-missing"]

    # Probe each row.
    only_id = sys.argv[1] if len(sys.argv) > 1 else None
    for row in rows:
        if only_id and only_id not in row["record_id"]:
            continue
        rid = row["record_id"]
        col = row["column"]
        url = row["current_citation"]
        out = OUT_DIR / f"{rid}__{col}.json"
        if out.exists():
            continue
        print(f"-> {rid} / {col} <- {url}", file=sys.stderr)
        html = curl(url)
        text = strip_html(html)[:200000]
        hits = probe(text, col)
        out.write_text(
            json.dumps(
                {"id": rid, "column": col, "url": url, "hits": hits, "text_len": len(text)},
                indent=2,
            )
        )
        time.sleep(0.4)


if __name__ == "__main__":
    main()

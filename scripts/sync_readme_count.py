#!/usr/bin/env python3
"""Keep the README's headline system count equal to data/landscape.json.

Rewrites the first "**N systems**" in README.md. Run by `make build`;
`--check` exits 1 when the README is stale instead of writing.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r"\*\*[\d,]+ systems\*\*")


def main() -> int:
    n = len(json.loads((ROOT / "data" / "landscape.json").read_text())["records"])
    readme = ROOT / "README.md"
    text = readme.read_text()
    new = PATTERN.sub(f"**{n:,} systems**", text, count=1)
    if new == text:
        return 0
    if "--check" in sys.argv:
        print(f"README.md headline count is stale; run `make build` (catalog has {n:,} systems)")
        return 1
    readme.write_text(new)
    print(f"README.md: headline count set to {n:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

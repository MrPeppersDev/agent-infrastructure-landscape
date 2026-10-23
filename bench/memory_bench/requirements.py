"""Print the pip requirements and env vars for a set of systems.

    python -m memory_bench.requirements mem0,graphiti          # pip specs, one per line
    python -m memory_bench.requirements mem0,graphiti --env    # required env vars
"""

from __future__ import annotations

import sys

from .adapters import REGISTRY, get


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    names = [n for n in (argv[0] if argv else "").split(",") if n] or list(REGISTRY)
    want_env = "--env" in argv
    out: list[str] = []
    for n in names:
        cls = get(n)
        out.extend(cls.env if want_env else cls.requires)
    print("\n".join(dict.fromkeys(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
batch_intake.py — run the auto-research intake over a list of candidate
systems and add them all to the working tree in one pass, so a batch of
new systems lands as ONE reviewable PR instead of N conflicting ones
(every intake PR rewrites data/landscape.json and landscape.html).

Input: a JSON list of candidates, e.g. extraction/intake-batches/*.json:
    [{"name": "...", "url": "https://...", "type": "framework",
      "section": "Dedicated memory layers", "description": "...",
      "license": "MIT", "github_repo": "owner/repo or URL",
      "arxiv_url": "", "sources": ["https://..."], "traction": "..."}]

For each candidate: research_intake.py (CLI overrides, no Issue) →
apply_intake_pr.py --no-push --no-comment --no-commit (insert + make
build + make validate). A candidate that fails is reverted and reported;
the rest still land. Writes a markdown summary to --report.

Run by .github/workflows/intake-batch.yml on pushes to intake-batch/**.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

TYPE_MAP = {
    "product": "product (commercial / hosted SaaS)",
    "platform-feature": "product (commercial / hosted SaaS)",
    "framework": "framework (library / SDK / OSS package)",
    "library": "framework (library / SDK / OSS package)",
    "paper": "paper (academic / preprint)",
    "benchmark": "benchmark (eval suite / leaderboard)",
    "harness": "harness (agent runtime / scaffolding)",
    "substrate": "substrate (foundation model / infra primitive)",
}


def gh_url(repo: str) -> str:
    repo = (repo or "").strip()
    if not repo:
        return ""
    if repo.startswith("http"):
        return repo
    return f"https://github.com/{repo.strip('/')}"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates")
    ap.add_argument("--report", required=True)
    ap.add_argument("--push-branch", default=None,
                    help="push after every added system, so a timeout keeps progress")
    ap.add_argument("--start-number", type=int, default=90000,
                    help="synthetic run-trail ids (no Issue exists)")
    args = ap.parse_args()

    cands = json.loads(Path(args.candidates).read_text())
    # Re-runs skip systems an earlier (possibly timed-out) run already added.
    existing = {r["name"].strip().lower() for r in
                json.loads((ROOT / "data" / "landscape.json").read_text())["records"]}
    cands = [c for c in cands if c["name"].strip().lower() not in existing]
    added, failed = [], []
    for i, c in enumerate(cands):
        n = args.start_number + i
        name = c["name"].strip()
        desc = (c.get("description") or "").strip()
        if c.get("traction"):
            desc = f"{desc} Traction: {c['traction'].strip()}"
        rec_path = Path(f"/tmp/batch-record-{n}.json")
        cmd = [sys.executable, str(SCRIPTS / "research_intake.py"),
               "--name", name, "--primary-url", c["url"],
               "--section", c["section"],
               "--type", TYPE_MAP.get(c.get("type", ""), TYPE_MAP["product"]),
               "--brief-description", desc[:600],
               "--output", str(rec_path)]
        if c.get("license"):
            cmd += ["--license", c["license"]]
        if gh_url(c.get("github_repo", "")):
            cmd += ["--github-url", gh_url(c["github_repo"])]
        if c.get("arxiv_url"):
            cmd += ["--arxiv-url", c["arxiv_url"]]
        res = run(cmd)
        if res.returncode != 0:
            reason = "possible duplicate" if res.returncode == 2 else "research failed"
            failed.append((name, reason, (res.stderr or res.stdout).strip()[-400:]))
            print(f"[{i+1}/{len(cands)}] {name}: {reason}")
            continue
        res = run([sys.executable, str(SCRIPTS / "apply_intake_pr.py"),
                   "--record", str(rec_path), "--issue-number", str(n),
                   "--no-push", "--no-comment", "--no-commit"])
        if res.returncode != 0:
            # apply reverts its own build failures; make sure validate
            # failures don't leave a half-applied tree for the next one.
            run(["git", "checkout", "--", "data/landscape.json",
                 "data/landscape.edges.json", "landscape.html"])
            failed.append((name, f"apply exit {res.returncode}",
                           (res.stderr or res.stdout).strip()[-400:]))
            print(f"[{i+1}/{len(cands)}] {name}: apply failed ({res.returncode})")
            continue
        # Commit each success locally so a later failure's revert can't
        # undo it; the workflow pushes the branch at the end.
        run(["git", "add", "data/landscape.json", "data/landscape.edges.json",
             "landscape.html"])
        run(["git", "commit", "-q", "-m", f"intake(batch): add {name}"])
        if args.push_branch:
            pushed = run(["git", "push", "-q", "origin", f"HEAD:{args.push_branch}"])
            if pushed.returncode != 0:
                print(f"warn: push failed: {pushed.stderr.strip()[-300:]}")
        added.append((name, c["section"], c["url"]))
        print(f"[{i+1}/{len(cands)}] {name}: added")

    lines = [f"# Batch intake: {Path(args.candidates).name}", "",
             f"Added **{len(added)}** of {len(cands)} candidates.", "",
             "## Added", ""]
    lines += [f"- [{n}]({u}) — {s}" for n, s, u in added] or ["_none_"]
    lines += ["", "## Not added", ""]
    lines += [f"- **{n}** — {r}\n  <details><summary>detail</summary>\n\n  ```\n  {d}\n  ```\n  </details>"
              for n, r, d in failed] or ["_none_"]
    Path(args.report).write_text("\n".join(lines) + "\n")
    print(f"added={len(added)} failed={len(failed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

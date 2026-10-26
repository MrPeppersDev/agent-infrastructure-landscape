#!/usr/bin/env python3
"""
apply_correction.py — turn a "Correct a record" issue into a reviewable PR.

The issue form (.github/ISSUE_TEMPLATE/correction.yml) carries a record id,
a field (cell slug, or `name` / `url`), the proposed value and a source URL.
This script:

  1. parses the issue body (### headings from the GitHub issue form);
  2. checks the record and field exist and the source URL resolves;
  3. patches the cell (value + citation, status real-data), stamping
     last_verified_at on volatile cells, and canonicalises the JSON;
  4. runs `make build` + `make validate`;
  5. pushes `correction/<issue>-<record>` and opens a draft PR (or, when
     Actions can't open PRs, comments a compare link on the issue).

Nothing auto-merges: a maintainer reviews every correction.

Usage:
  python3 scripts/apply_correction.py --issue-number 123            # fetch body via gh
  python3 scripts/apply_correction.py --body-file issue.md --no-push  # local test
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from _cell_writer import load_landscape, save_landscape, update_cell  # noqa: E402
from extract import CELL_COLUMN_SLUGS, VOLATILE_CELL_SLUGS  # noqa: E402
from apply_intake_pr import (  # noqa: E402
    canonicalize_landscape_json, run_build, run_validate, pr_create_fallback, comment_on_issue,
)

LANDSCAPE = ROOT / "data" / "landscape.json"
FIELDS = {"record": "Record id", "field": "Field", "current": "Current value",
          "proposed": "Correct value", "source": "Source URL", "notes": "Notes"}
RECORD_FIELDS = {"name", "url"}


def parse_form(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    parts = re.split(r"^###\s+(.+?)\s*$", body, flags=re.M)
    # parts = [preamble, heading1, text1, heading2, text2, ...]
    label_to_key = {v.lower(): k for k, v in FIELDS.items()}
    for i in range(1, len(parts) - 1, 2):
        key = label_to_key.get(parts[i].strip().lower())
        if not key:
            continue
        val = parts[i + 1].strip()
        if val in ("_No response_", "_(not provided)_"):
            val = ""
        out[key] = val
    return out


def check_url(url: str) -> tuple[bool, str]:
    if not re.match(r"^https?://[^\s]+$", url):
        return False, "not an http(s) URL"
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "landscape-correction-bot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status < 400, f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        # Many vendor sites 403 bots; the reviewer still sees the link.
        return e.code in (401, 403, 429), f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def validate(form: dict[str, str], landscape: dict) -> tuple[dict | None, list[str]]:
    errs = []
    rec = next((r for r in landscape["records"] if r["id"] == form.get("record", "").strip()), None)
    if rec is None:
        errs.append(f"record id `{form.get('record')}` is not in the catalog (copy it from the /systems/<id> URL)")
    field = form.get("field", "").strip()
    if field not in CELL_COLUMN_SLUGS and field not in RECORD_FIELDS:
        errs.append(f"field `{field}` is not a column slug (see docs/SCHEMA.md)")
    if not form.get("proposed", "").strip():
        errs.append("the correct value is empty")
    if len(form.get("proposed", "")) > 1200:
        errs.append("the correct value is too long (keep it under 1,200 characters)")
    ok, why = check_url(form.get("source", "").strip())
    if not ok:
        errs.append(f"the source URL didn't resolve ({why})")
    return rec, errs


def apply(rec: dict, form: dict[str, str]) -> str:
    field, value, src = form["field"].strip(), " ".join(form["proposed"].split()), form["source"].strip()
    if field in RECORD_FIELDS:
        old = rec.get(field)
        rec[field] = value
        return f"`{field}`: {old!r} → {value!r}"
    old = (rec.get("cells", {}).get(field) or {}).get("value")
    today = dt.date.today().isoformat()
    update_cell(rec, field, value=value, status="real-data", citation=src,
                last_verified_at=today if field in VOLATILE_CELL_SLUGS else None)
    rec["last_verified_at"] = today
    return f"`{field}`: {old!r} → {value!r} (source: {src})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue-number", type=int)
    ap.add_argument("--body-file")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    if args.body_file:
        body = Path(args.body_file).read_text()
    else:
        body = json.loads(subprocess.run(["gh", "issue", "view", str(args.issue_number), "--json", "body"],
                                         capture_output=True, text=True, check=True, cwd=str(ROOT)).stdout)["body"]
    form = parse_form(body)
    landscape = load_landscape(LANDSCAPE)
    rec, errs = validate(form, landscape)
    if errs:
        msg = "The correction bot couldn't apply this yet:\n\n" + "\n".join(f"- {e}" for e in errs) + \
              "\n\nEdit the issue to fix these and the bot will re-run. A maintainer can also apply it by hand."
        print(msg)
        if args.issue_number and not args.no_push:
            comment_on_issue(args.issue_number, msg)
            return 0  # the comment is the outcome; don't fail the run
        return 2

    change = apply(rec, form)
    save_landscape(landscape, LANDSCAPE)
    for step in (canonicalize_landscape_json, run_build, run_validate):
        ok, out = step()
        if not ok:
            print(out[-4000:], file=sys.stderr)
            if args.issue_number and not args.no_push:
                comment_on_issue(args.issue_number, f"The correction applied but `{step.__name__}` failed; a maintainer will take a look.")
            return 3
    print(f"applied {rec['id']}: {change}")
    if args.no_push:
        return 0

    n = args.issue_number
    branch = f"correction/{n}-{rec['id'][:40]}"
    subprocess.run(["git", "checkout", "-B", branch], check=True, cwd=str(ROOT))
    subprocess.run(["git", "add", "data/landscape.json", "data/landscape.edges.json", "landscape.html",
                    "data/stack-index.json"], check=False, cwd=str(ROOT))
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=str(ROOT)).returncode == 0:
        comment_on_issue(n, "This correction matches what the catalog already says; nothing to change.")
        return 0
    title = f"Correction: {rec['name']} {form['field'].strip()} (closes #{n})"
    subprocess.run(["git", "commit", "-m", title], check=True, cwd=str(ROOT))
    if subprocess.run(["git", "push", "-f", "-u", "origin", branch], cwd=str(ROOT)).returncode != 0:
        return 6
    body_path = ROOT / "corrections-pr-body.md"
    body_path.write_text(
        f"Correction from #{n}.\n\n- **Record:** [{rec['name']}](https://mrpeppersdev.github.io/agent-infrastructure-landscape/systems/{rec['id']})\n"
        f"- **Change:** {change}\n- **Notes:** {form.get('notes') or '—'}\n\n"
        "Reviewer: open the source and confirm it states the new value.\n\nCloses #" + str(n) + "\n")
    pr = subprocess.run(["gh", "pr", "create", "--draft", "--base", "main", "--head", branch,
                         "--title", title, "--body-file", str(body_path)], capture_output=True, text=True, cwd=str(ROOT))
    if pr.returncode != 0:
        return pr_create_fallback(branch, title, body_path, pr.stderr, issue_number=n)
    comment_on_issue(n, f"Thanks! The correction is ready for review: {pr.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

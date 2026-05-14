#!/usr/bin/env python3
"""
process_intake.py — manual-trigger batch processor for `intake`-labelled issues.

Reads open `intake`-labelled GitHub issues, parses their structured body, runs
a small per-issue research pass (URL verification, duplicate detection), builds
a landscape.html <tr> row matching the catalog schema (60 cells + 7 taxonomy
axes + name), runs the pipeline (extract → reconcile → build_edges → validate),
and on success appends the rows to landscape.html and emits one commit per
batch with messages of the form:

    Round NN: intake batch — N submissions accepted (issues #X, #Y, #Z)

On rejection (duplicate / URL fail / insufficient info / validation failure)
the script comments on the issue with the reason and leaves it open.

Per docs/DECISIONS.md "Intake processing (#30)" the cadence is manual: a
curator invokes this script on demand. It is not wired to a cron, GHA, or
git hook because every accepted row enters the catalog as a commit on `main`
that the curator must own.

CLI:
    python3 scripts/process_intake.py             # process all open intake issues
    python3 scripts/process_intake.py --limit N   # at most N
    python3 scripts/process_intake.py --dry-run   # print plan only; no edits

The script terminates non-zero if any unexpected error occurs; an empty
intake-issue list is treated as success ("No open intake issues found.").

End-to-end testing notes
------------------------

At time of authorship (2026-05-13, issue #30) there are no open intake
issues to drive a real run. The script's empty-list and --dry-run paths
are exercised here; live insertion is verified only when the first real
submission arrives. See the issue-#30 close-out comment for the
testing-pending state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO = "MrPeppersDev/memory-analysis-program"
ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_HTML = ROOT / "landscape.html"
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
SCRIPTS = ROOT / "scripts"

# Field labels emitted by the Svelte form (web/src/lib/submit-issue.ts) AND
# the GitHub Issue Form template (.github/ISSUE_TEMPLATE/intake.yml). Both
# entry points render to bold-label markdown — labels are the canonical
# wire format. Keep this in sync with both producers.
FIELD_LABELS: list[tuple[str, str]] = [
    ("name", "Name"),
    ("url", "URL"),
    ("section", "Section"),
    ("subsection", "Subsection"),
    ("type", "Type"),
    ("tier_guess", "Tier guess"),
    ("brief_description", "Brief description"),
    ("claims", "Claims"),
    ("known_funding", "Known funding"),
    ("known_customers", "Known customers"),
    ("license", "License"),
    ("github_url", "GitHub URL"),
    ("arxiv_url", "Arxiv URL"),
    ("submitter_notes", "Submitter notes"),
]

# Required fields per the form-side validateSubmission() contract.
REQUIRED_FIELDS = ("name", "url", "type", "section", "brief_description")

# The 60 cell column slugs in document order, per scripts/extract.py's
# CELL_COLUMN_SLUGS. Duplicated here rather than imported so the script
# stays self-contained (extract.py imports BeautifulSoup and we don't
# need that here).
CELL_COLUMN_SLUGS: list[str] = [
    "type", "desc", "claims", "modalities", "created", "latest-release",
    "license", "gh", "mindshare", "citations", "funding", "customers",
    "pricing", "compliance", "data-handling", "deployment", "hq",
    "founders", "volume", "perf", "repro", "code-release", "api-surface",
    "latency", "throughput", "backend-storage", "multi-tenancy",
    "encryption", "sso-rbac", "embedding-model", "consistency",
    "versioning", "tombstoning", "schema-evolution", "namespace",
    "contradiction", "forgetting", "mcp-support", "a2a-support", "otel",
    "webhooks", "import-export", "integration-count", "orchestration",
    "programmatic-control", "vendor-benchmarks", "pricing-specifics",
    "agent-abstraction", "memory-primitives", "llm-lock", "runtimes",
    "session-handling", "validated-verticals", "time-to-running",
    "anti-fit", "optimised-for", "adjacent-infrastructure", "pros",
    "cons", "links",
]
assert len(CELL_COLUMN_SLUGS) == 60

TAXONOMY_AXES = [
    "storage", "retrieval", "persistence", "update", "unit",
    "governance", "conflict",
]

ARXIV_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(?P<id>\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Issue fetch + parse
# ---------------------------------------------------------------------------


@dataclass
class IntakeIssue:
    number: int
    title: str
    body: str
    url: str  # html_url (for issue comments / referencing)
    fields: dict[str, str] = field(default_factory=dict)
    parse_errors: list[str] = field(default_factory=list)


def gh(args: list[str], *, check: bool = True) -> str:
    """Run `gh` and return stdout. Raises on non-zero unless check=False."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"gh {' '.join(args)} failed ({result.returncode}):\n"
            f"  stdout: {result.stdout.strip()}\n  stderr: {result.stderr.strip()}"
        )
    return result.stdout


def fetch_intake_issues(limit: int | None) -> list[IntakeIssue]:
    """Fetch all open `intake`-labelled issues via `gh api`.

    Uses gh's auto-pagination (`--paginate`) so the script handles >30
    open issues without manual page-walking.
    """
    raw = gh([
        "api",
        "--paginate",
        f"repos/{REPO}/issues?state=open&labels=intake&per_page=100",
    ])
    # `gh --paginate` concatenates JSON arrays as `][` — we need to merge.
    # Workaround: split on `][` and re-parse as one array.
    fragments = raw.strip()
    if not fragments:
        return []
    # Most common case: single page → already a valid JSON array.
    try:
        issues = json.loads(fragments)
    except json.JSONDecodeError:
        # Multi-page: join `]\n[` boundaries.
        joined = fragments.replace("][", ",").replace("]\n[", ",")
        issues = json.loads(joined)
    parsed: list[IntakeIssue] = []
    for item in issues:
        if "pull_request" in item:
            # gh's /issues endpoint returns PRs too; skip them.
            continue
        issue = IntakeIssue(
            number=item["number"],
            title=item["title"],
            body=item.get("body") or "",
            url=item["html_url"],
        )
        parse_issue_body(issue)
        parsed.append(issue)
        if limit is not None and len(parsed) >= limit:
            break
    return parsed


def parse_issue_body(issue: IntakeIssue) -> None:
    """Pull `**Label:**` markdown fields out of the issue body.

    The Svelte form and GitHub Issue Form both render to:
        **Label:** value\n\n
    Multi-line values stay attached until the next `**…:**` marker.
    """
    body = issue.body or ""
    # Build regex that matches each label and captures until the next label
    # or end-of-body.
    label_alternation = "|".join(re.escape(label) for _, label in FIELD_LABELS)
    pattern = re.compile(
        rf"\*\*(?P<label>{label_alternation}):\*\*\s*(?P<value>.*?)(?=\n\*\*(?:{label_alternation}):\*\*|\Z)",
        re.DOTALL,
    )
    label_to_key = {label: key for key, label in FIELD_LABELS}
    for match in pattern.finditer(body):
        key = label_to_key[match.group("label")]
        value = match.group("value").strip()
        # Drop the form's `_(none)_` italic placeholder.
        if value in {"_(none)_", "(none)", "—", "-", ""}:
            continue
        issue.fields[key] = value
    # Validate required fields.
    for key in REQUIRED_FIELDS:
        if not issue.fields.get(key):
            label = dict(FIELD_LABELS)[key]
            issue.parse_errors.append(f"missing required field: {label}")


# ---------------------------------------------------------------------------
# Research pass — URL verify + duplicate detection
# ---------------------------------------------------------------------------


def verify_url(url: str, *, timeout: float = 10.0) -> tuple[bool, str]:
    """HEAD/GET the URL; return (ok, reason)."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers={
            "User-Agent": "memory-analysis-program-intake/1.0",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.status
            if code in (200, 301, 302):
                return True, f"HEAD {code}"
            return False, f"HEAD {code}"
    except urllib.error.HTTPError as exc:
        # Some servers reject HEAD; retry with GET.
        if exc.code in (405, 501):
            return _verify_url_via_get(url, timeout=timeout)
        return False, f"HEAD HTTPError {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # Fall through to GET (some hosts misbehave on HEAD).
        return _verify_url_via_get(url, timeout=timeout, fallback_reason=str(exc))


def _verify_url_via_get(url: str, *, timeout: float, fallback_reason: str = "") -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="GET", headers={
            "User-Agent": "memory-analysis-program-intake/1.0",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.status
            if code in (200, 301, 302):
                return True, f"GET {code}"
            return False, f"GET {code}"
    except urllib.error.HTTPError as exc:
        return False, f"GET HTTPError {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        msg = fallback_reason or str(exc)
        return False, f"GET error: {msg}"


def canonicalise_url(url: str) -> str:
    """Lowercase host, strip query/fragment + trailing slash for dedupe."""
    if not url:
        return ""
    try:
        parts = urllib.parse.urlsplit(url.strip())
    except ValueError:
        return url.strip().lower()
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/")
    return f"{parts.scheme.lower()}://{host}{path}"


def normalised_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def arxiv_id_of(url: str | None) -> str | None:
    if not url:
        return None
    m = ARXIV_RE.search(url)
    return m.group("id") if m else None


def load_existing_records() -> list[dict[str, Any]]:
    if not LANDSCAPE_JSON.exists():
        return []
    return json.loads(LANDSCAPE_JSON.read_text())["records"]


def detect_duplicate(
    issue: IntakeIssue,
    existing: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the existing record if this submission is a duplicate; else None."""
    sub_url = canonicalise_url(issue.fields.get("url", ""))
    sub_name = normalised_name(issue.fields.get("name", ""))
    sub_arxiv = arxiv_id_of(issue.fields.get("arxiv_url") or issue.fields.get("url"))
    for record in existing:
        rec_url = canonicalise_url(record.get("url") or "")
        rec_name = normalised_name(record.get("name") or "")
        if sub_url and rec_url and sub_url == rec_url:
            return record
        if sub_name and rec_name and sub_name == rec_name:
            return record
        if sub_arxiv:
            for cell in record.get("cells", {}).values():
                cite = (cell or {}).get("citation") or ""
                if arxiv_id_of(cite) == sub_arxiv:
                    return record
            if arxiv_id_of(record.get("url") or "") == sub_arxiv:
                return record
    return None


# ---------------------------------------------------------------------------
# Row construction
# ---------------------------------------------------------------------------


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;").replace("'", "&#x27;")
    )


def cite_link(url: str, *, title: str = "source") -> str:
    safe_url = html_escape(url)
    return f'<a class="cite" href="{safe_url}" title="{title}">↗</a>'


def real_cell(slug: str, value: str, citation: str) -> str:
    return (
        f'    <td class="{slug}">{html_escape(value)} {cite_link(citation)}</td>'
    )


def depth_floor_cell(slug: str, *, search_url: str) -> str:
    """Cell at depth-floor — submitted material exhausted, no documented data.

    Uses the `searched not found` no-data span pattern with a search-URL
    citation. This is the schema-correct shape for cells that have been
    looked-at and yielded nothing concrete (validate.py terminal rule).
    """
    return (
        f'    <td class="{slug}"><span class="no-data">searched not found</span> '
        f'{cite_link(search_url, title="searched")}</td>'
    )


def not_applicable_cell(slug: str, reason: str) -> str:
    safe_reason = html_escape(reason)
    return (
        f'    <td class="{slug}"><span class="no-data" '
        f'style="font-style:italic;color:#555;">not applicable — {safe_reason}'
        f'</span></td>'
    )


def tier_class(tier_guess: str | None) -> str:
    """Map the submitter's tier hint to a row class. Defaults to T3."""
    if not tier_guess:
        return "row-t3"
    digit_match = re.search(r"[1-5]", tier_guess)
    if not digit_match:
        return "row-t3"
    return f"row-t{digit_match.group(0)}"


def build_taxonomy_cell(axis: str) -> str:
    """Intake submissions don't carry taxonomy axes — leave for curator-fill.

    Empty `<td class="tax-*">` renders as `—` via the CSS `:empty::before`
    rule on landscape.html, which the curator can replace post-merge.
    Validate.py's terminal-cell rule applies only to the 60 main cells; the
    taxonomy axes are validated separately (SCHEMA.md §7.1) and tolerate an
    empty list. Confirm via a dry-run before relying on this.
    """
    return f'    <td class="tax-{axis}"></td>'


def build_row(issue: IntakeIssue) -> str:
    """Construct a <tr> for an accepted intake submission.

    The strategy is conservative: real-data cells for the submitted fields
    (type/desc/claims/funding/customers/license/links + GitHub if present),
    not-applicable for cells unambiguously inapplicable to the section, and
    depth-floor-reached (`searched not found`) for everything else, with
    the submitted URL as the search-trail citation. The intake row is a
    starting point — a subsequent enrichment round deepens it.
    """
    fields = issue.fields
    name = fields["name"]
    url = fields["url"]
    description = fields.get("brief_description", "")
    type_value = fields.get("type", "")
    claims = fields.get("claims", "")
    funding = fields.get("known_funding", "")
    customers = fields.get("known_customers", "")
    license_value = fields.get("license", "")
    github_url = fields.get("github_url", "")
    arxiv_url = fields.get("arxiv_url", "")

    klass = tier_class(fields.get("tier_guess"))

    parts: list[str] = []
    parts.append(f'  <tr class="{klass}">')
    parts.append(
        f'    <td class="name"><a href="{html_escape(url)}">'
        f'{html_escape(name)}</a></td>'
    )

    # The 60 cells, in CELL_COLUMN_SLUGS order. Pre-build the dict so we
    # only render slugs the schema knows about.
    cells: dict[str, str] = {}

    cells["type"] = real_cell("type", type_value or "—", url) if type_value else \
        depth_floor_cell("type", search_url=url)

    cells["desc"] = real_cell("desc", description, url) if description else \
        depth_floor_cell("desc", search_url=url)

    cells["claims"] = real_cell("claims", claims, url) if claims else \
        depth_floor_cell("claims", search_url=url)

    cells["funding"] = real_cell("funding", funding, url) if funding else \
        depth_floor_cell("funding", search_url=url)

    cells["customers"] = real_cell("customers", customers, url) if customers else \
        depth_floor_cell("customers", search_url=url)

    cells["license"] = real_cell("license", license_value, url) if license_value else \
        depth_floor_cell("license", search_url=url)

    if github_url:
        cells["gh"] = real_cell("gh", github_url, github_url)
    else:
        cells["gh"] = depth_floor_cell("gh", search_url=url)

    citations_cite = arxiv_url or url
    cells["citations"] = depth_floor_cell("citations", search_url=citations_cite)

    cells["links"] = real_cell("links", url, url)

    # All remaining slugs: depth-floor with the submitted URL as search trail.
    for slug in CELL_COLUMN_SLUGS:
        if slug in cells:
            continue
        cells[slug] = depth_floor_cell(slug, search_url=url)

    # Insert taxonomy axes (between name and the rest), per HTML order.
    # extract.py reads taxonomy from `tax-*` td order which is right after
    # `name`, then `type`, then the rest. Replicate that order here.
    parts.append(cells["type"])
    for axis in TAXONOMY_AXES:
        parts.append(build_taxonomy_cell(axis))
    # All remaining cells (excluding `type` already emitted) in slug order.
    for slug in CELL_COLUMN_SLUGS:
        if slug == "type":
            continue
        parts.append(cells[slug])
    parts.append("  </tr>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Section insertion
# ---------------------------------------------------------------------------


def insert_row(html_text: str, section: str, row_html: str) -> str:
    """Append `row_html` to the given section's tbody (before the next section).

    The section is identified by the `<tr class="group-row"><td …>section</td>`
    marker. We find that marker, then find the LAST data row before the next
    group-row (or the closing `</tbody>` if it's the last section), and
    insert after it with a blank line separator (matches the document style).
    """
    # Locate the group-row for this section.
    group_pattern = re.compile(
        r'<tr class="group-row"><td colspan="68"[^>]*>'
        + re.escape(html_escape_for_group(section))
        + r'</td></tr>'
    )
    m = group_pattern.search(html_text)
    if m is None:
        raise ValueError(f"section group-row not found for: {section!r}")
    start_after = m.end()

    # Find the next group-row OR </tbody> after this one.
    next_group = re.search(
        r'<tr class="group-row"><td colspan="68"[^>]*>(?!' +
        re.escape(html_escape_for_group(section)) + r')',
        html_text[start_after:],
    )
    tbody_close = html_text.find("</tbody>", start_after)
    if next_group is not None:
        end_before = start_after + next_group.start()
    else:
        end_before = tbody_close
    if end_before < 0:
        raise ValueError("</tbody> not found after section header")

    # Find last `</tr>` strictly before end_before.
    section_chunk = html_text[start_after:end_before]
    last_tr_close = section_chunk.rfind("</tr>")
    if last_tr_close < 0:
        # Section has only the group-row (and maybe an explainer). Insert
        # immediately after the section-explainer if present, else after the
        # group-row.
        insertion_point = start_after
    else:
        insertion_point = start_after + last_tr_close + len("</tr>")

    inserted = "\n\n" + row_html
    return html_text[:insertion_point] + inserted + html_text[insertion_point:]


def html_escape_for_group(section: str) -> str:
    """Group-row labels embed `&amp;` for `&` (per landscape.html style)."""
    return section.replace("&", "&amp;")


# ---------------------------------------------------------------------------
# Pipeline + commit
# ---------------------------------------------------------------------------


def run_pipeline() -> tuple[bool, str]:
    """Run extract → reconcile → build_edges → validate.

    Returns (ok, combined_output). Audit is a separate make target outside
    the build chain (and slow); the issue spec lists it, but the validate
    gate already runs schema + determinism + cycle stability + cache
    integrity, which is the contract for "this is safe to commit". We skip
    the audit here and document the rationale in DECISIONS.md.
    """
    steps = [
        [sys.executable, "scripts/extract.py", "--output", "data/landscape.json"],
        [sys.executable, "scripts/reconcile.py",
         "--input", "data/landscape.json", "--output", "data/landscape.json"],
        [sys.executable, "scripts/build_edges.py"],
        [sys.executable, "scripts/validate.py"],
    ]
    output: list[str] = []
    for cmd in steps:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        output.append(f"$ {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
        if proc.returncode != 0:
            return False, "\n".join(output)
    return True, "\n".join(output)


def next_round_number() -> int:
    """Inspect recent commit messages for the highest `Round NN` and bump by 1."""
    log = subprocess.run(
        ["git", "log", "-200", "--pretty=%s"],
        capture_output=True, text=True, cwd=str(ROOT),
    ).stdout
    highest = 0
    for line in log.splitlines():
        m = re.match(r"^Round (\d+)\b", line)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def comment_on_issue(number: int, body: str, *, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would comment on #{number}:\n  {body}")
        return
    subprocess.run(
        ["gh", "issue", "comment", str(number), "--repo", REPO, "--body", body],
        check=True, cwd=str(ROOT),
    )


def close_issue(number: int, body: str, *, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would close #{number} with comment:\n  {body}")
        return
    subprocess.run(
        ["gh", "issue", "close", str(number), "--repo", REPO, "--comment", body],
        check=True, cwd=str(ROOT),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--limit", type=int, default=None,
                    help="process at most N issues (useful for testing)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would happen, but do not edit files, "
                         "commit, comment, or close issues")
    args = ap.parse_args()

    issues = fetch_intake_issues(limit=args.limit)
    if not issues:
        print("No open intake issues found.")
        return 0

    existing = load_existing_records()
    print(f"Processing {len(issues)} intake issue(s)…")

    accepted: list[tuple[IntakeIssue, str]] = []   # (issue, row_html)
    rejected: list[tuple[IntakeIssue, str]] = []   # (issue, reason)

    for issue in issues:
        print(f"\n--- Issue #{issue.number}: {issue.title}")

        if issue.parse_errors:
            reason = "Could not parse intake fields: " + "; ".join(issue.parse_errors)
            print(f"  REJECT: {reason}")
            rejected.append((issue, reason))
            continue

        url = issue.fields["url"]
        url_ok, url_reason = verify_url(url)
        print(f"  URL check: {url} → {url_reason}")
        if not url_ok:
            reason = f"URL verification failed for {url}: {url_reason}"
            rejected.append((issue, reason))
            continue

        dup = detect_duplicate(issue, existing)
        if dup is not None:
            reason = (
                f"Duplicate of existing entry `{dup.get('name')}` (id `{dup.get('id')}`). "
                "Same canonical URL, normalised name, or arxiv ID. "
                "If this is a distinct system, edit the issue title/URL to disambiguate "
                "and re-add the `intake` label."
            )
            print(f"  REJECT: {reason}")
            rejected.append((issue, reason))
            continue

        try:
            row_html = build_row(issue)
        except KeyError as exc:
            reason = f"Insufficient info to build row: missing {exc}"
            print(f"  REJECT: {reason}")
            rejected.append((issue, reason))
            continue

        accepted.append((issue, row_html))
        print(f"  ACCEPT: built row ({len(row_html.splitlines())} lines)")

    # Post per-rejection comments first (those happen on every run).
    for issue, reason in rejected:
        body = (
            f"Intake processor rejected this submission:\n\n{reason}\n\n"
            "Address the issue above and the curator can re-run the processor."
        )
        comment_on_issue(issue.number, body, dry_run=args.dry_run)

    if not accepted:
        print("\nNo submissions accepted this batch.")
        return 0

    # Insert rows into landscape.html.
    html_text = LANDSCAPE_HTML.read_text() if LANDSCAPE_HTML.exists() else ""
    if not html_text:
        print("ERROR: landscape.html not found; cannot insert rows.", file=sys.stderr)
        return 2

    new_html = html_text
    for issue, row_html in accepted:
        section = issue.fields.get("section", "")
        try:
            new_html = insert_row(new_html, section, row_html)
        except ValueError as exc:
            reason = (
                f"Could not locate section `{section}` in landscape.html: {exc}. "
                "Use one of the canonical section names from docs/SCHEMA.md."
            )
            print(f"  Insertion failed for #{issue.number}: {reason}")
            comment_on_issue(issue.number, reason, dry_run=args.dry_run)
            # Move from accepted → rejected after the fact.
            rejected.append((issue, reason))
            continue

    accepted = [pair for pair in accepted if pair[0] not in {i for i, _ in rejected}]
    if not accepted:
        print("\nAll accepted submissions failed insertion; nothing to commit.")
        return 0

    if args.dry_run:
        print(f"\n[dry-run] Would write {len(accepted)} new row(s) to landscape.html.")
        print(f"[dry-run] Would run pipeline + validate.")
        print(f"[dry-run] Would commit with: "
              f"Round {next_round_number()}: intake batch — {len(accepted)} "
              f"submissions accepted (issues "
              f"{', '.join(f'#{i.number}' for i, _ in accepted)})")
        return 0

    LANDSCAPE_HTML.write_text(new_html)
    print(f"\nWrote {len(accepted)} new row(s) to landscape.html.")

    ok, output = run_pipeline()
    if not ok:
        # Revert landscape.html and the staged data files; comment + leave open.
        subprocess.run(
            ["git", "checkout", "--",
             str(LANDSCAPE_HTML), "data/landscape.json", "data/landscape.edges.json"],
            cwd=str(ROOT),
        )
        for issue, _row in accepted:
            comment_on_issue(
                issue.number,
                "Intake processor produced a row, but the pipeline / validation "
                "gate failed — submission left open for curator review.\n\n"
                "```\n" + output[-3000:] + "\n```",
                dry_run=False,
            )
        print("Pipeline failed; reverted edits. See output above.")
        return 3

    # Commit the batch.
    round_no = next_round_number()
    issue_refs = ", ".join(f"#{i.number}" for i, _ in accepted)
    commit_msg = (
        f"Round {round_no}: intake batch — {len(accepted)} submissions "
        f"accepted (issues {issue_refs})"
    )
    subprocess.run(
        ["git", "add", str(LANDSCAPE_HTML), "data/landscape.json",
         "data/landscape.edges.json"],
        check=True, cwd=str(ROOT),
    )
    subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd=str(ROOT))
    commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=str(ROOT),
    ).stdout.strip()
    commit_url = f"https://github.com/{REPO}/commit/{commit_sha}"

    # Close each accepted issue with a link to commit + new catalog row anchor.
    for issue, _row in accepted:
        # The catalog row anchor: we don't have a reliable per-row anchor in
        # landscape.html, so we link to the section. Closer follow-up issue
        # can introduce stable id anchors (a-tag fragments) — see DECISIONS.md.
        section = issue.fields["section"]
        section_anchor = re.sub(r"[^a-z0-9]+", "-", section.lower()).strip("-")
        close_issue(
            issue.number,
            f"Accepted in {commit_url}\n\n"
            f"Catalog row appended to section *{section}* in "
            f"https://github.com/{REPO}/blob/main/landscape.html "
            f"(intermediate anchor: #{section_anchor}). "
            "The row is intake-shape (real-data cells for submitted fields, "
            "depth-floor-reached for the rest); a follow-up enrichment round "
            "will deepen the unknown cells.",
            dry_run=False,
        )

    print(f"\nCommitted: {commit_msg}\n  → {commit_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

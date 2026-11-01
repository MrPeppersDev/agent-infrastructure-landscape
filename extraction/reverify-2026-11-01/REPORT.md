# Open data questions (HANDOFF §2), 2026-11-01

A research agent checked the leads in HANDOFF §2 on primary sources (notes.md lists every page fetched). Applied with `scripts/apply_reverify.py --date 2026-11-01 results.json`: 10 records, 10 cells (apply-report.md).

## Applied

| Record | Change | Source |
|---|---|---|
| Sinequa | funding: acquired by ChapsVision on 2024-11-18 (was "2024-11") | sinequa.com press release |
| Apex Security | funding: acquired by Tenable, announced 2025-05-29, closed by 2025-07-30 (Tenable Q2 2025 results, SEC) | sec.gov |
| Common Room | funding: acquired by Zoom, announced 2026-07-02, closed July 2026 | zoom.com blog |
| AlphaSense | funding: $350M Jun-2026 at $7.5B, over $1B total | alpha-sense.com press |
| Endor Labs | funding: the stored "$93M total" was the $93M Series B (Apr-2025); now states both rounds | endorlabs.com |
| Databricks Vector Search, MLflow | funding: Databricks' $5B round at $190B (Aug-2026); the conflicting "$20.2B total" / "$43.2B" figures dropped, no Databricks page states a cumulative total | databricks.com newsroom |
| Coalfire AI Operations | links: the live AI Security and Trust Engineering page (old page 404) | coalfire.com |
| K-Scale Labs | desc: shut down late 2025, per its former COO (medium: The Robot Report; kscale.dev doesn't resolve) | therobotreport.com |
| Toplyne | desc: wound down October 2024, per the CEO (medium: Inc42 reporting the CEO's post; toplyne.io 404) | inc42.com |

`apply_reverify.py` no longer maps lifecycle `dead` to `decay_cause: archived`, which the stack index showed as "repository archived". A shutdown is written into the desc or funding cell, which the index reads as dead.

## Not applied

- **Vellum** shuts down its hosted platform on 2026-11-02 (vellum.ai/vellum-assistant-platform-shutdown). Mark it dead after that date; the 2026-11-14 check-in does this together with Hume EVI.
- **linq-ai**: linq.ai is now an unrelated ed-tech company. The intended product is probably LinqAlpha; the record needs re-pointing and fresh research.
- **reggie-ai**: reggie.ai is a parked domain. Regie.ai exists, but the record's founders and funding match nothing verifiable. Retire or rebuild.
- **hyperproof-ai-trust-center**: no standalone product any more; the feature lives in the main platform (hyperproof.io/product/hyperproof-ai/). Candidate for merging into the Hyperproof record.
- **Pachyderm**: repo not archived, last commit 2025-01-09; pachyderm.com unreachable and no HPE end-of-life notice found.
- **Anvilogic**: secondary sources date the Series C to April 2024, not "Jul-2024"; needs Anvilogic's own announcement.
- **11x, Gong, Apollo**: no newer primary round found.

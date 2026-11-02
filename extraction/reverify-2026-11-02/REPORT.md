# linq-ai and reggie-ai (HANDOFF section 2), 2026-11-02

A research agent checked both records on primary sources: 7 pages fetched, 4 searches. Applied with `scripts/apply_reverify.py --date 2026-11-02` (`results.json`, `results-b.json`; reports `apply-report*.md`).

## linq-ai → LinqAlpha (re-pointed, id kept)

linq.ai is now an unrelated higher-education software company. The record's description (an AI agent for financial analysts) matches LinqAlpha, so the record now points there. Several stored facts were wrong:

| Cell | Was | Now | Source |
|---|---|---|---|
| name, url | Linq AI, linq.ai | LinqAlpha, linqalpha.com | linqalpha.com |
| created | 2023 | 2022 | linqalpha.com/about-us |
| hq | San Francisco | New York | company press release, 2026-07-02 (kyodonewsprwire.jp/release/202607021906) |
| founders | "Linq AI founders" (placeholder) | Jacob Choi, Subeen Pang, Jin Kim, Hojun Choi | same press release |
| funding | "small seed round" | $22M Series A Jul-2026 (AVP, Atinum Investment, GFT Ventures); $30M+ total per the company | press release; about page |
| type, desc, claims, links | finance-analyst agent; "data cleansing, model-building" (no source found) | multi-agent investment-research platform, 57,000+ companies, 30+ languages, 70+ institutions | linqalpha.com |
| pros, cons | unsourced opinions about the wrong company | coverage (homepage); name collision with linq.ai (linq.ai) | as cited |

Conflict kept visible: the about page lists two co-CEOs (Jacob Chanyeol Choi, Hojun Choi); the press release names four founders. The record uses the release.

## reggie-ai (removed)

reggie.ai redirects to a GoDaddy for-sale page. None of the stored facts check out for any company: the founders (Tomer Sole, Yair Snir), the $4.7M Lightspeed + Mantis seed (Jul-2024) and the 2023 founding. Regie.ai is a different, real company (founders Srinath Sridhar and Matt Millen, Khosla-backed, founded 2020–21), so re-pointing would keep nothing verifiable. Logged in `extraction/removals-2026-11-02/removed.json`. Regie.ai can be added through intake.

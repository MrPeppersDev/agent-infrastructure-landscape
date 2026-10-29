#!/usr/bin/env python3
"""Remove GitHub star counts from claims / desc / pros prose where the gh
cell carries the live count (#326). Clean standalone clauses
("Traction: ~2.3k GitHub stars", "; ~5k stars;") are stripped by rule;
the 38 in-sentence cases use the hand-written replacements in manual.py.
Only text is removed (plus two rewordings noted in REPORT.md); no new
facts are written. Run from the repo root, then canonicalize + make build.
"""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from strip import strip, STAR  # noqa: E402
from manual import MANUAL  # noqa: E402

p = Path('data/landscape.json')
L = json.loads(p.read_text())
recs = {r['id']: r for r in L['records']}
pat = re.compile(STAR, re.I)
manual = {(i, c) for i, c, _, _ in MANUAL}
changed = 0
for i, c, a, b in MANUAL:
    cell = recs[i]['cells'][c]
    assert cell['value'].count(a) == 1, (i, c, a)
    cell['value'] = cell['value'].replace(a, b).strip()
    changed += 1
for r in L['records']:
    gh = r['cells'].get('gh') or {}
    if gh.get('status') != 'real-data' or not gh.get('value'):
        continue
    for c in ('claims', 'desc', 'pros'):
        cell = r['cells'].get(c)
        if not cell or (r['id'], c) in manual or not pat.search(cell.get('value') or ''):
            continue
        cell['value'] = strip(cell['value'])
        changed += 1
p.write_text(json.dumps(L, indent=2, ensure_ascii=False) + '\n')
print(f'{changed} cells edited')

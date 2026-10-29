import re
STAR = r'(?:~|≈|about |over |nearly |roughly |\+)?\d[\d.,]*\s*[kKmM]?\+?\s*(?:★|GitHub stars|GH stars|stars)'
# a clause that is only a star figure, with an optional lead-in label
CLAUSE = re.compile(r'(?:Traction:\s*|GitHub:\s*|with\s+)?' + STAR + r'(?:\s+on GitHub)?(?:\s*\((?:as of|at)[^)]*\))?', re.I)

def strip(v: str) -> str:
    out = CLAUSE.sub('\x00', v)
    # remove the placeholder together with one adjoining separator
    out = re.sub(r'\s*[;,·]\s*\x00', '', out)
    out = re.sub(r'\x00\s*[;,·]\s*', '', out)
    out = re.sub(r'\(\s*\x00\s*\)', '', out)
    out = re.sub(r'\x00\s*(?:/|and)\s*', '', out)
    out = out.replace('\x00', '')
    out = re.sub(r'\s+([.;,)])', r'\1', out)
    out = re.sub(r'\(\s*\)', '', out)
    out = re.sub(r'\.\s*\.', '.', out)
    out = re.sub(r'^\s*[.;,]\s*', '', out)
    out = re.sub(r'\s{2,}', ' ', out).strip()
    out = re.sub(r'[;,]\s*$', '', out)
    if out and out[0].islower() and not v[:1].islower(): out = out[0].upper() + out[1:]
    return out

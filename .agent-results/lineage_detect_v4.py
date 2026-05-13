"""Python translation of web/src/lib/lineages.ts for v4 refresh."""
import json
import re
from collections import defaultdict

STRONG_DESCENT = {'built-on', 'extends', 'forks', 'succeeds'}
WEAK_DESCENT = 'cites'

# CURATED_SEEDS mirrors lineages.ts
CURATED_SEEDS = [
    {
        'id': 'rssm-world-model',
        'name': 'RSSM / world-model family',
        'anchorId': 'dreamerv3--arxiv-2301-04104',
        'kind': 'descent',
    },
    {
        'id': 'graph-rag-hierarchy',
        'name': 'Graph-RAG hierarchy',
        'anchorId': 'graphrag-microsoft--microsoft-com',
        'kind': 'descent',
    },
    {
        'id': 'files-as-memory',
        'name': 'Files-as-memory thread',
        'anchorId': 'claude-md--docs-claude-com',
        'kind': 'pattern',
        'sections': ['File-backed / editor paradigms', 'Claude Code memory mechanisms'],
    },
    {
        'id': 'specs-as-memory',
        'name': 'Specs-as-memory thread',
        'anchorId': 'kiro--kiro-dev',
        'kind': 'pattern',
        'explicitMembers': [
            'kiro--kiro-dev',
            'windsurf-codeium-openai--windsurf-com',
            'cognition-devin-v2-spec-mode--cognition-ai',
            'cline-memory-bank--docs-cline-bot',
            'roo-code--roocode-com',
        ],
    },
]

UNDATED_YEAR = 9999


def parse_created(value):
    """Parse YYYY-MM or YYYY-QN or YYYY format. Returns (year, quarter)."""
    if not value:
        return None
    v = value.strip()
    m = re.match(r'^(\d{4})-(\d{2})', v)
    if m:
        y = int(m.group(1))
        mo = int(m.group(2))
        q = (mo - 1) // 3 + 1
        return (y, q)
    m = re.match(r'^(\d{4})-Q([1-4])', v, re.I)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = re.match(r'^(\d{4})', v)
    if m:
        return (int(m.group(1)), 1)
    return None


def date_of(rec):
    val = rec.get('cells', {}).get('created', {}).get('value')
    p = parse_created(val)
    if not p:
        return (UNDATED_YEAR, 1)
    return p


def date_key(d):
    return d[0] * 10 + d[1]


class DSU:
    def __init__(self):
        self.parent = {}
        self.size = {}

    def add(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.size[x] = 1

    def find(self, x):
        if x not in self.parent:
            self.add(x)
            return x
        r = x
        while self.parent[r] != r:
            r = self.parent[r]
        # path compress
        while self.parent[x] != r:
            nxt = self.parent[x]
            self.parent[x] = r
            x = nxt
        return r

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        sa, sb = self.size[ra], self.size[rb]
        if sa < sb:
            self.parent[ra] = rb
            self.size[rb] = sa + sb
        else:
            self.parent[rb] = ra
            self.size[ra] = sa + sb

    def components(self):
        out = defaultdict(list)
        for x in self.parent:
            r = self.find(x)
            out[r].append(x)
        return dict(out)


def is_descent_edge(e):
    if e['type'] in STRONG_DESCENT:
        return True
    if e['type'] == WEAK_DESCENT and e.get('isInfluential') is True:
        return True
    return False


def build_adj(edges, valid_ids):
    adj = defaultdict(set)
    for e in edges:
        if not is_descent_edge(e):
            continue
        s, t = e['source'], e['target']
        if s not in valid_ids or t not in valid_ids:
            continue
        adj[s].add(t)
        adj[t].add(s)
    return adj


def expand(seed, adj, max_depth):
    seen = {seed: 0}
    queue = [(seed, 0)]
    while queue:
        nxt = []
        for node, depth in queue:
            if depth >= max_depth:
                continue
            for n in adj.get(node, ()):
                if n not in seen:
                    seen[n] = depth + 1
                    nxt.append((n, depth + 1))
        queue = nxt
    return set(seen)


def detect(records, edges, top_n=999, min_size=3, curated_max_depth=2):
    by_id = {r['id']: r for r in records}
    valid_ids = set(by_id.keys())
    adj = build_adj(edges, valid_ids)

    claimed = set()
    curated_lineages = []
    for seed in CURATED_SEEDS:
        if seed['anchorId'] not in by_id:
            continue
        kind = seed.get('kind', 'descent')
        if kind == 'pattern':
            want = set(seed.get('sections', []))
            members = set()
            if want:
                for r in records:
                    for s in r.get('sections', []):
                        if s.get('section') in want:
                            members.add(r['id'])
                            break
            for m in seed.get('explicitMembers', []):
                if m in by_id:
                    members.add(m)
            edges_within = []
        else:
            members = expand(seed['anchorId'], adj, curated_max_depth)
            edges_within = [e for e in edges if is_descent_edge(e) and e['source'] in members and e['target'] in members]
        sorted_mem = sorted(members, key=lambda m: (date_key(date_of(by_id[m])), m))
        for m in sorted_mem:
            claimed.add(m)
        curated_lineages.append({
            'id': seed['id'],
            'name': seed['name'],
            'kind': kind,
            'members': sorted_mem,
            'edges': edges_within,
            'curated': True,
            'size': len(sorted_mem),
        })

    # auto
    dsu = DSU()
    for r in records:
        if r['id'] in claimed:
            continue
        dsu.add(r['id'])
    for e in edges:
        if not is_descent_edge(e):
            continue
        s, t = e['source'], e['target']
        if s in claimed or t in claimed:
            continue
        if s not in valid_ids or t not in valid_ids:
            continue
        dsu.union(s, t)

    auto = []
    for root, members in dsu.components().items():
        if len(members) < min_size:
            continue
        member_set = set(members)
        sorted_mem = sorted(members, key=lambda m: (date_key(date_of(by_id[m])), m))
        anchor = sorted_mem[0]
        edges_within = [e for e in edges if is_descent_edge(e) and e['source'] in member_set and e['target'] in member_set]
        auto.append({
            'id': f'auto-{root}',
            'name': by_id[anchor].get('name', anchor) + ' family',
            'kind': 'descent',
            'members': sorted_mem,
            'edges': edges_within,
            'curated': False,
            'anchor': anchor,
            'size': len(sorted_mem),
        })
    auto.sort(key=lambda l: (-l['size'], date_key(date_of(by_id[l]['anchor'] if isinstance(l['anchor'], str) else l['anchor'])) if False else 0))
    auto.sort(key=lambda l: -l['size'])
    return curated_lineages, auto


def main():
    with open('web/landscape.json') as f:
        lj = json.load(f)
    records = lj['records']
    with open('web/landscape.edges.json') as f:
        ej = json.load(f)
    edges = ej['edges']

    descent_edges = [e for e in edges if is_descent_edge(e)]
    print(f'Total records: {len(records)}')
    print(f'Total edges: {len(edges)}')
    print(f'Descent edges: {len(descent_edges)}')
    print()

    curated, auto = detect(records, edges, top_n=999, min_size=3, curated_max_depth=2)

    print('=== Curated lineages ===')
    for l in curated:
        print(f"  [{l['kind']}] {l['name']:40s} size={l['size']:3d}")
        if l['kind'] == 'descent':
            print(f'    edges within: {len(l["edges"])}')
    print()
    print('=== Auto-discovered lineages (size>=3) ===')
    print(f'  total: {len(auto)}')
    by_id = {r['id']: r for r in records}
    for l in auto:
        anchor_name = by_id[l['anchor']].get('name', l['anchor'])
        print(f"  size={l['size']:3d}  anchor={anchor_name}")
        if l['size'] <= 10:
            for m in l['members']:
                rec = by_id[m]
                sec = rec.get('sections', [{}])[0].get('section', '?')
                print(f"      - {rec.get('name', m)}  [{sec}]")
        else:
            print(f"      (first 5 by date)")
            for m in l['members'][:5]:
                rec = by_id[m]
                sec = rec.get('sections', [{}])[0].get('section', '?')
                print(f"      - {rec.get('name', m)}  [{sec}]")
    print()
    print(f'TOTAL LINEAGES OF SIZE >=3:  curated={len(curated)} ({sum(1 for l in curated if l["size"]>=3)})  auto={len(auto)}')
    total_size3 = sum(1 for l in curated if l["size"] >= 3) + len(auto)
    print(f'GRAND TOTAL: {total_size3}')

if __name__ == '__main__':
    main()

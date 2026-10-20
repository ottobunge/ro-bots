#!/usr/bin/env python3
"""Ingest the iRO Wiki (MediaWiki API: https://irowiki.org/w/api.php) into a
local searchable corpus: JSONL per section + SQLite FTS5 index.

NOTE: the wiki moved from wiki.irowiki.org (now NXDOMAIN / Cloudflare 1016) to
https://irowiki.org with article path /wiki/$1. The item/monster/map *data*
tables live on the separate site db.irowiki.org; this MediaWiki is the guide
wiki (skills, quests, dungeons). Section roots below reflect what actually
exists here (verified via the API on 2026-10-15):
  items    -> Category:Items tree
  monsters -> Category:Monsters (ABSENT on this wiki; template-transclusion
              fallback is probed and recorded honestly in the receipt)
  maps     -> Category:Maps (files only) + Category:Dungeons tree
              + transclusions of dungeon infobox templates
  skills   -> Category:Skills tree
Plus all_pages.jsonl: every main-namespace non-redirect page (full corpus;
pages that belong to no section above are searchable under 'all_pages').

Run:  python3 ingest_iro_wiki.py
Outputs (this directory): items.jsonl monsters.jsonl maps.jsonl skills.jsonl
  all_pages.jsonl category_tree.json iro-wiki.db
Receipt: run/reviews/iro-wiki-ingest.json

Politeness: sequential requests, DELAY s between requests, maxlag=5,
exponential backoff on 429/5xx/connection errors; request counters recorded
in the receipt. Content is GFDL 1.3+ per the wiki's rightsinfo (recorded).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
REVIEWS = os.path.join(REPO, 'run', 'reviews')
API = 'https://irowiki.org/w/api.php'
ARTICLE = 'https://irowiki.org/wiki/'
UA = 'iro-wiki-corpus-ingest/1.0 (local research corpus; polite; contact: otto)'
DELAY = 0.6          # seconds between successful API calls
BATCH = 50           # titles per content request
DEPTH = 3            # subcategory recursion depth
SECTIONS = ('items', 'monsters', 'maps', 'skills')

STATS = {'requests': 0, 'retries': 0, 'rate_limit_hits': 0, 'maxlag_waits': 0}


def api(params, tries=8):
    params = dict(params)
    params.update({'format': 'json', 'formatversion': '2', 'maxlag': '5'})
    url = API + '?' + urllib.parse.urlencode(params)
    backoff = 2.0
    last_exc = None
    for attempt in range(1, tries + 1):
        STATS['requests'] += 1
        try:
            # curl instead of urllib: works on NixOS without cert-store plumbing
            out = subprocess.run(
                ['curl', '-sS', '-m', '60', '-A', UA, '-w', '\n%{http_code}', url],
                capture_output=True, text=True)
            if out.returncode != 0:
                raise RuntimeError(f'curl rc={out.returncode}: {out.stderr.strip()[:160]}')
            body, _, code = out.stdout.rpartition('\n')
            if code in ('429', '503'):
                STATS['rate_limit_hits'] += 1
                raise RuntimeError(f'HTTP {code}')
            data = json.loads(body)
        except Exception as e:  # curl errors, timeouts, JSON errors, resets
            last_exc = e
            if attempt == tries:
                raise
            STATS['retries'] += 1
            time.sleep(backoff + random.random())
            backoff = min(backoff * 2, 60)
            continue
        if isinstance(data, dict) and data.get('error', {}).get('code') == 'maxlag':
            STATS['maxlag_waits'] += 1
            time.sleep(5)
            continue
        time.sleep(DELAY)
        return data
    raise RuntimeError(f'API exhausted retries: {last_exc}')


def subcats_of(cat):
    out, cont = [], {}
    while True:
        d = api({'action': 'query', 'list': 'categorymembers', 'cmtitle': cat,
                 'cmtype': 'subcat', 'cmlimit': 'max', **cont})
        out += [m['title'] for m in d.get('query', {}).get('categorymembers', [])]
        cont = d.get('continue') or {}
        if not cont:
            return out


def cat_tree(root, depth=DEPTH):
    """BFS subcategory tree rooted at `root`; returns (tree, all category titles)."""
    tree, seen, frontier = {}, {root}, [root]
    for _ in range(depth + 1):
        nxt = []
        for cat in frontier:
            subs = subcats_of(cat)
            tree[cat] = {'subcats': subs}
            for sc in subs:
                if sc not in seen:
                    seen.add(sc)
                    nxt.append(sc)
        frontier = nxt
        if not frontier:
            break
    return tree, seen


def attach_catinfo(tree):
    cats = list(tree.keys())
    for i in range(0, len(cats), BATCH):
        chunk = cats[i:i + BATCH]
        d = api({'action': 'query', 'prop': 'categoryinfo', 'titles': '|'.join(chunk)})
        for p in d.get('query', {}).get('pages', []):
            if 'categoryinfo' in p and p['title'] in tree:
                tree[p['title']]['info'] = p['categoryinfo']


def cat_exists(cat):
    d = api({'action': 'query', 'prop': 'categoryinfo', 'titles': cat})
    page = next(iter(d['query']['pages']))
    return 'missing' not in page, page.get('categoryinfo')


def all_main_pages():
    titles, cont = [], {}
    while True:
        d = api({'action': 'query', 'list': 'allpages', 'apnamespace': '0',
                 'apfilterredir': 'nonredirects', 'aplimit': 'max', **cont})
        titles += [p['title'] for p in d.get('query', {}).get('allpages', [])]
        cont = d.get('continue') or {}
        if not cont:
            return titles


def transclusions(template):
    out, cont = [], {}
    while True:
        d = api({'action': 'query', 'list': 'alltransclusions', 'attitle': template,
                 'atnamespace': '0', 'atlimit': 'max', **cont})
        out += [m['title'] for m in d.get('query', {}).get('alltransclusions', [])]
        cont = d.get('continue') or {}
        if not cont:
            return out


def templates_prefix(prefix):
    d = api({'action': 'query', 'list': 'alltemplates', 'atlprefix': prefix, 'atlimit': '500'})
    if 'query' not in d:
        print(f'  [warn] alltemplates prefix={prefix!r}: unexpected response '
              f'{json.dumps(d)[:240]}', flush=True)
        return []
    return [t['title'] for t in d['query'].get('alltemplates', [])]


def normalize(text):
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.S)
    text = re.sub(r'<ref[^>]*>.*?</ref>', ' ', text, flags=re.S | re.I)
    text = re.sub(r'<ref[^>]*/>', ' ', text, flags=re.I)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def fetch_content(titles):
    """Fetch wikitext + categories for titles, batched; returns {title: rec} keyed
    by the ORIGINAL requested title (redirect aliases mapped back)."""
    pages, missing = {}, set()
    total = len(titles)
    for i in range(0, total, BATCH):
        chunk = titles[i:i + BATCH]
        merged, redir = {}, {}
        cont = {}
        while True:
            d = api({'action': 'query', 'prop': 'revisions|categories',
                     'titles': '|'.join(chunk), 'rvprop': 'content', 'rvslots': 'main',
                     'cllimit': 'max', 'redirects': 1, **cont})
            for r in d.get('query', {}).get('redirects', []):
                redir[r['from']] = r['to']
            for p in d.get('query', {}).get('pages', []):
                merged[p['title']] = p
            cont = d.get('continue') or {}
            if not cont:
                break
        for t in chunk:
            key = redir.get(t, t)
            key = redir.get(key, key)
            p = merged.get(key)
            if p is None or 'missing' in p:
                missing.add(t)
                continue
            rev = (p.get('revisions') or [{}])[0]
            content = ((rev.get('slots') or {}).get('main') or {}).get('content') or ''
            pages[t] = {'pageid': p['pageid'], 'wikitext': content,
                        'categories': sorted(c['title'] for c in p.get('categories', []))}
        print(f'  content {min(i + BATCH, total)}/{total} pages '
              f'(requests so far: {STATS["requests"]})', flush=True)
    return pages, missing


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    t0 = time.time()
    os.makedirs(REVIEWS, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec='seconds')

    print('== siteinfo ==', flush=True)
    site = api({'action': 'query', 'meta': 'siteinfo',
                'siprop': 'general|rightsinfo|statistics'})
    gen = site['query']['general']
    rights = site['query'].get('rightsinfo') or {}
    site_stats = site['query'].get('statistics') or {}

    print('== category trees ==', flush=True)
    roots = {
        'items': ['Category:Items'],
        'monsters': ['Category:Monsters'],
        'maps': ['Category:Maps', 'Category:Dungeons'],
        'skills': ['Category:Skills'],
    }
    trees = {}
    for name, rcats in roots.items():
        tree, allcats = {}, set()
        exists = {}
        for c in rcats:
            ok, info = cat_exists(c)
            exists[c] = {'exists': ok, 'categoryinfo': info}
            if ok:
                t, cs = cat_tree(c)
                tree.update(t)
                allcats |= cs
        attach_catinfo(tree)
        trees[name] = {'roots': rcats, 'root_probes': exists, 'tree': tree,
                       'categories': sorted(allcats)}
        print(f'  {name}: {len(allcats)} categories in tree', flush=True)

    print('== fallback probes ==', flush=True)
    probes = {}
    monster_pages, map_extra = set(), set()
    mon_tpls = templates_prefix('Mon')
    probes['monsters_template_prefix_Mon'] = mon_tpls
    for t in mon_tpls:
        if t.startswith('Template:Monster'):
            found = transclusions(t)
            probes[f'transclusions_of_{t}'] = found
            monster_pages |= set(found)
    infox_tpls = templates_prefix('Infobox')
    probes['infobox_templates'] = infox_tpls
    map_tpls = [t for t in infox_tpls if re.search(r'dungeon|map', t, re.I)]
    probes['maps_fallback_templates'] = map_tpls
    for t in map_tpls:
        found = transclusions(t)
        probes[f'transclusions_of_{t}'] = found
        map_extra |= set(found)

    print('== enumerate main namespace ==', flush=True)
    titles = all_main_pages()
    print(f'  {len(titles)} main-namespace non-redirect pages', flush=True)

    print('== fetch wikitext + categories ==', flush=True)
    content, missing = fetch_content(titles)
    # fallback-section titles may not be in the allpages list; fetch those too
    extra = sorted((monster_pages | map_extra) - set(content))
    if extra:
        print(f'  fetching {len(extra)} fallback-probe pages', flush=True)
        c2, m2 = fetch_content(extra)
        content.update(c2)
        missing |= m2

    def classify(cats):
        return [n for n in SECTIONS
                if trees[n]['categories'] and any(c in trees[n]['categories'] for c in cats)]

    sections = {n: set() for n in ('items', 'monsters', 'maps', 'skills', 'all_pages')}
    for t, c in content.items():
        if c.get('missing'):
            continue
        secs = classify(c['categories'])
        for n in secs:
            sections[n].add(t)
        for n, pool in (('monsters', monster_pages), ('maps', map_extra)):
            if t in pool and n not in secs:
                sections[n].add(t)
        if not sections and False:
            pass
    for t, c in content.items():
        if c.get('missing'):
            continue
        if not any(t in sections[n] for n in SECTIONS):
            sections['all_pages'].add(t)

    print('== write JSONL ==', flush=True)
    jsonl = {}
    for name, pool in sections.items():
        path = os.path.join(HERE, name + '.jsonl')
        n = 0
        with open(path, 'w', encoding='utf-8') as f:
            for t in sorted(pool):
                c = content[t]
                rec = {'title': t, 'pageid': c['pageid'], 'categories': c['categories'],
                       'wikitext': c['wikitext'], 'fetched_at': fetched_at,
                       'source_url': ARTICLE + urllib.parse.quote(t.replace(' ', '_'), safe='')}
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                n += 1
        jsonl[name] = {'path': path, 'pages': n}
        print(f'  {name}.jsonl: {n} pages', flush=True)

    # category tree artifact
    tree_path = os.path.join(HERE, 'category_tree.json')
    with open(tree_path, 'w', encoding='utf-8') as f:
        json.dump({n: trees[n] for n in trees}, f, ensure_ascii=False, indent=1)

    print('== build FTS index ==', flush=True)
    dbpath = os.path.join(HERE, 'iro-wiki.db')
    if os.path.exists(dbpath):
        os.remove(dbpath)
    con = sqlite3.connect(dbpath)
    con.executescript('''
      CREATE TABLE pages(pageid INTEGER PRIMARY KEY, title TEXT UNIQUE,
        sections TEXT, categories TEXT, source_url TEXT, fetched_at TEXT,
        wikitext TEXT);
      CREATE VIRTUAL TABLE fts_pages USING fts5(section, title, body,
        tokenize='unicode61');
      CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    ''')
    page_rows = {}
    for name, pool in sections.items():
        for t in sorted(pool):
            c = content[t]
            pr = page_rows.get(c['pageid'])
            if pr is None:
                pr = page_rows[c['pageid']] = {
                    'title': t, 'sections': set(), 'categories': c['categories'],
                    'source_url': ARTICLE + urllib.parse.quote(t.replace(' ', '_'), safe=''),
                    'fetched_at': fetched_at, 'wikitext': c['wikitext']}
            pr['sections'].add(name)
    fts_rows = []
    for pid in sorted(page_rows):
        pr = page_rows[pid]
        secs = sorted(pr['sections'])
        con.execute('INSERT INTO pages VALUES(?,?,?,?,?,?,?)',
                    (pid, pr['title'], ','.join(secs),
                     json.dumps(pr['categories'], ensure_ascii=False),
                     pr['source_url'], pr['fetched_at'], pr['wikitext']))
        for s in secs:
            fts_rows.append((s, pr['title'], normalize(pr['wikitext'])))
    con.executemany('INSERT INTO fts_pages(section, title, body) VALUES(?,?,?)', fts_rows)
    con.executemany('INSERT INTO meta(key, value) VALUES(?,?)', [
        ('endpoint', API), ('sitename', gen.get('sitename', '')),
        ('server', gen.get('server', '')),
        ('license', f"{rights.get('text', '')} <{rights.get('url', '')}>"),
        ('ingested_at', fetched_at),
        ('pages_total', str(len(page_rows))),
        ('api_requests', str(STATS['requests'])),
    ])
    con.commit()
    print(f'  pages table: {len(page_rows)} unique pages; fts rows: {len(fts_rows)}', flush=True)

    print('== spot-check probes ==', flush=True)
    d = api({'action': 'query', 'titles': 'Poring|Knife|prt_fild08', 'redirects': 1})
    assumed_titles = {p['title']: ('missing' if 'missing' in p else 'present')
                      for p in d['query']['pages']}

    def pick(section, preferred, rx=None):
        pool = sorted(sections[section])
        for p in preferred:
            if p in pool:
                return p
        if rx:
            for p in pool:
                if re.search(rx, p, re.I):
                    return p
        return pool[0] if pool else None

    cli = os.path.join(HERE, 'query_iro_wiki.py')

    def run_cli(args):
        r = subprocess.run([sys.executable, cli] + args, capture_output=True, text=True)
        return {'cmd': ' '.join(['query_iro_wiki.py'] + args), 'argv': [sys.executable, cli] + args,
                'exit_code': r.returncode, 'output': (r.stdout + r.stderr).strip()[:1500]}

    def kwcheck(text, kws):
        present = [k for k in kws if re.search(k, text, re.I)]
        return {'checked': kws, 'present': present}

    spot = []
    sk = pick('skills', ['Bash', 'Double Strafe', 'Heal'], None)
    if sk:
        w = content[sk]['wikitext']
        spot.append({'section': 'skills', 'title': sk,
                     'source_url': ARTICLE + urllib.parse.quote(sk.replace(' ', '_'), safe=''),
                     'expectation': 'skill mechanics (type/levels/SP/element) present in wikitext',
                     'keyword_check': kwcheck(w, [r'\bType\b', r'\bLevel', r'\bSP\b', r'\bElement']),
                     'cli': run_cli([sk.split()[0], '--section', 'skills', '--limit', '2'])})
    it = pick('items', ['Knife'], None)
    if it:
        w = content[it]['wikitext']
        spot.append({'section': 'items', 'title': it,
                     'source_url': ARTICLE + urllib.parse.quote(it.replace(' ', '_'), safe=''),
                     'expectation': 'item facts present in wikitext (note: Knife itself does not exist on this wiki)',
                     'keyword_check': kwcheck(w, [r'\bID\b', r'\bWeight', r'\bEffect', r'\bSlot', r'\bItem\b']),
                     'cli': run_cli([it.split()[0], '--section', 'items', '--limit', '2'])})
    mp = pick('maps', ['prt_fild08'], r'prontera|culvert|dungeon')
    if mp:
        w = content[mp]['wikitext']
        spot.append({'section': 'maps', 'title': mp,
                     'source_url': ARTICLE + urllib.parse.quote(mp.replace(' ', '_'), safe=''),
                     'expectation': 'map/dungeon info; spawn/monster mention if present on this wiki',
                     'keyword_check': kwcheck(w, [r'[Ss]pawn', r'\bMonster', r'\bLevel', r'\bDungeon']),
                     'cli': run_cli([mp.split()[0], '--section', 'maps', '--limit', '2'])})
    negative_cli = run_cli(['Knife', '--limit', '3'])

    print('== CLI examples ==', flush=True)
    examples = [
        run_cli(['prontera', '--limit', '3']),
        run_cli(['"Eden Group"', '--section', 'skills', '--limit', '3']),
        run_cli(['spawn OR monster', '--section', 'maps', '--limit', '3']),
    ]

    print('== receipt ==', flush=True)
    artifacts = {}
    for name in ('items', 'monsters', 'maps', 'skills', 'all_pages'):
        p = jsonl[name]['path']
        artifacts[name + '.jsonl'] = {'sha256': sha256_file(p), 'bytes': os.path.getsize(p),
                                      'pages': jsonl[name]['pages']}
    for fn in ('iro-wiki.db', 'category_tree.json', 'ingest_iro_wiki.py', 'query_iro_wiki.py'):
        p = os.path.join(HERE, fn)
        artifacts[fn] = {'sha256': sha256_file(p), 'bytes': os.path.getsize(p)}

    receipt = {
        'task': 'Ingest iRO Wiki MediaWiki API into local JSONL + FTS5 corpus',
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'endpoint': {
            'api': API,
            'note': 'wiki.irowiki.org no longer resolves (NXDOMAIN; Cloudflare error 1016 '
                    'when forced to the irowiki.org edge IP). The wiki is served at '
                    'https://irowiki.org with article path /wiki/$1 (confirmed via siteinfo '
                    'and WikiApiary). probed first per task instructions: '
                    'https://wiki.irowiki.org/api.php and /w/api.php both failed DNS.',
            'sitename': gen.get('sitename'), 'server': gen.get('server'),
            'articlepath': gen.get('articlepath'),
            'site_statistics': site_stats,
        },
        'license': {'text': rights.get('text'), 'url': rights.get('url'),
                    'note': 'actual wiki rightsinfo is GFDL 1.3+, not CC BY-NC-SA as '
                            'assumed in the task brief; recorded from the API.'},
        'politeness': {'mode': 'sequential', 'delay_seconds': DELAY,
                       'batch_titles': BATCH, 'maxlag': 5,
                       **STATS},
        'structure_note': {
            'assumed_vs_actual': 'Category:Monsters does not exist on this wiki and there are '
                                 'no monster articles (no Poring/Knife/prt_fild08 pages); '
                                 'item/monster/map raw data lives on db.irowiki.org (separate '
                                 'non-MediaWiki site, out of scope for a MediaWiki-API ingest). '
                                 'This wiki is the guide wiki: skills, quests, dungeons. '
                                 'Category:Maps holds only uploaded files (24 files, 0 pages).',
            'assumed_titles_probe': assumed_titles,
            'fallback_probes': probes,
            'monster_fallback_pages_ingested': sorted(monster_pages & set(content)),
            'map_fallback_extra_pages': sorted(map_extra & set(content)),
        },
        'category_tree_summary': {
            n: {'roots': trees[n]['roots'], 'root_probes': trees[n]['root_probes'],
                'categories_in_tree': len(trees[n]['categories']),
                'subcategories': {c: t.get('info', {}).get('subcats') for c, t in
                                  sorted(trees[n]['tree'].items())}}
            for n in trees},
        'counts': {n: jsonl[n]['pages'] for n in jsonl},
        'counts_note': 'sections overlap only if a page sits in two section trees; '
                       'all_pages = main-namespace pages in NO section (full corpus = '
                       'sum of sections + all_pages, unique pages = pages table count).',
        'artifacts': {'dir': HERE, 'files': artifacts},
        'spot_checks': spot,
        'spot_check_negative': {
            'note': 'task-specified spot-check targets Poring/Knife/prt_fild08 do not exist '
                    'on this wiki (see assumed_titles_probe); Knife CLI search recorded as '
                    'negative evidence.',
            'cli': negative_cli},
        'cli_examples': examples,
        'duration_seconds': round(time.time() - t0, 1),
    }
    rp = os.path.join(REVIEWS, 'iro-wiki-ingest.json')
    with open(rp, 'w', encoding='utf-8') as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)

    print(json.dumps({'counts': receipt['counts'], 'requests': STATS,
                      'receipt': rp}, indent=2), flush=True)


if __name__ == '__main__':
    main()

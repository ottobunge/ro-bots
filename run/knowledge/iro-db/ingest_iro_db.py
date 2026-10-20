#!/usr/bin/env python3
"""Ingest db.irowiki.org monster/item stat pages into a local JSONL corpus.

Polite crawler: strictly sequential, ~2.2 req/s, exponential backoff on
429/403/5xx, honors robots.txt (db.irowiki.org/robots.txt was empty, i.e. no
Disallow rules, at ingest time). Resumable: ids already present in the JSONL
files are skipped, so an interrupted run can simply be restarted.

Sections are enumerated from the site's own full-result search listings
(saved under listings/), not by blind id probing:
  monsters: /db/monster-search/?search&ltype=2... (1042 monsters)
  items:    /db/{gear,weapon,card,consume,costume}-search/?search... (6562 items)
Etc-type items (not covered by any item search) are discovered from the
monster drop tables of fetched pages plus the arrow-craft listing.

Regex note: patterns here deliberately avoid backslash escapes so the
matching behavior cannot depend on string-escape transport quirks.

Usage:
  python3 ingest_iro_db.py --selftest MONSTER.html ITEM.html   # offline parser check
  python3 ingest_iro_db.py                                     # full polite run
"""
import html as htmlmod
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from functools import partial
from urllib import request as urlreq
from urllib.error import HTTPError, URLError

HERE = os.path.dirname(os.path.abspath(__file__))
LISTINGS = os.path.join(HERE, 'listings')
MONSTERS_JSONL = os.path.join(HERE, 'monsters.jsonl')
ITEMS_JSONL = os.path.join(HERE, 'items.jsonl')
META = os.path.join(HERE, 'meta.json')
LOG = os.path.join(HERE, 'ingest.log')
COOKIEJAR = os.path.join(HERE, 'curl_cookies.txt')

BASE = 'https://db.irowiki.org/db'
UA = 'ro-bots-knowledge-ingest/0.1 (local research corpus; polite sequential crawler)'
BASE_DELAY = 0.40
JITTER = 0.10
ATTEMPTS = 3
NL = chr(10)

ITEM_SECTIONS = {
    'gear': 'item-gear-search.html',
    'weapon': 'item-weapon-search.html',
    'card': 'item-card-search.html',
    'consume': 'item-consume-search.html',
    'costume': 'item-costume-search.html',
}

ELEMENTS = {'Neutral', 'Water', 'Earth', 'Fire', 'Wind', 'Poison',
            'Holy', 'Shadow', 'Ghost', 'Undead'}

MONSTER_LABELS = {
    'Level': 'level', 'HP': 'hp', 'Def': 'def', 'MDef': 'mdef',
    'Attack': 'attack', 'Range': 'range', 'Aspd': 'aspd',
    'Move Speed': 'move_speed', 'Base Exp': 'base_exp', 'Job Exp': 'job_exp',
    '100% Hit': 'hit', '95% Flee': 'flee',
    'Base Exp per HP': 'base_exp_per_hp', 'Job Exp per HP': 'job_exp_per_hp',
}
ITEM_LABELS = {
    'Type': 'type', 'Subtype': 'subtype', 'Weight': 'weight', 'Element': 'element',
    'Weapon Level': 'weapon_level', 'Required Level': 'required_level',
    'Upgradable': 'upgradable', 'Damagable': 'damagable', 'Atk': 'atk', 'Def': 'def',
    'Buying Price': 'buying_price', 'Selling Price': 'selling_price', 'Slots': 'slots',
}

# key-value cells: <td class="... infoTitle">Label</td> <td class="... infoText">Val</td>
KV_RE = re.compile(
    '<td class="[^"]*(?:infoTitle|statTitle)[^"]*">([^<]+)</td>'
    '[ \t\r\n]*<td class="[^"]*(?:infoText|statText)[^"]*">(.*?)</td>', re.S)
# drops: <td class="dropItem"><a href="/db/item-info/909/">Jellopy</a></td>
#        <td class="dropRate">70.00%</td>
DROP_RE = re.compile(
    'dropItem"><a href="/db/item-info/([0-9]+)/">([^<]+)</a></td>'
    '[ \t\r\n]*<td class="dropRate">([0-9.]+)%', re.S)
TITLE_RE = re.compile(r'<title>iW Database - (?:Monster|Item) Info - (.*?)</title>')
MAIN_BLOCK_RE = re.compile(
    'smTitle">Main</div>[ \t\r\n]*<table[^>]*>(.*?)</table>', re.S)
MODE_RE = re.compile('smTitle">Mode</div>(.*?)</table>', re.S)
STATS_RE = re.compile(
    'baseStat[^>]*>Agi</td>[ \t\r\n]*<td[^>]*>Vit</td>[ \t\r\n]*<td[^>]*>Int</td>'
    '[ \t\r\n]*<td[^>]*>Dex</td>[ \t\r\n]*<td[^>]*>Luk</td>[ \t\r\n]*</tr>'
    '[ \t\r\n]*<tr>(.*?)</tr>', re.S)
ELEM_PAIR_RE = re.compile(
    '<td[^>]*>([A-Za-z ]+)</td>[ \t\r\n]*<td[^>]*>([0-9]+(?:[.][0-9]+)?)%')
DESC_RE = re.compile(
    'mdTitle"[^>]*>([^<]+)</td>[ \t\r\n]*</tr>[ \t\r\n]*</table>[ \t\r\n]*'
    '<table class="bgLtTable">[ \t\r\n]*<tr>[ \t\r\n]*<td[^>]*>(.*?)</td>', re.S)
TD_RE = re.compile(r'<td[^>]*>(.*?)</td>', re.S)
ITEM_LINK_RE = re.compile(r'/db/item-info/([0-9]+)/')
ID_TAIL_RE = re.compile(r'/([0-9]+)/?$')

STATE = {'requests': 0, 'retries': 0, 'blocked': False}


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(msg):
    with open(LOG, 'a') as f:
        f.write(now_iso() + ' ' + msg + NL)


class Blocked(Exception):
    pass


class NotFound(Exception):
    pass


def do_sleep():
    time.sleep(BASE_DELAY + random.random() * JITTER)


def fetch(url):
    """GET via curl (Cloudflare-tolerant client) with backoff/retries."""
    last = None
    for attempt in range(1, ATTEMPTS + 1):
        do_sleep()
        STATE['requests'] += 1
        try:
            out = subprocess.run(
                ['curl', '-sS', '-m', '40', '-A', UA,
                 '-b', COOKIEJAR, '-c', COOKIEJAR,
                 '-H', 'Accept-Language: en',
                 '-w', 'HTTPSTATUS:%{http_code}', url],
                capture_output=True, timeout=60)
            raw = out.stdout.decode('utf-8', 'replace')
            if 'HTTPSTATUS:' in raw:
                body, _, status = raw.rpartition('HTTPSTATUS:')
                status = status.strip()
            else:
                body, status = raw, '?'
            if status == '200':
                if 'Just a moment' in body[:3000]:
                    last = 'cloudflare challenge page'
                    STATE['retries'] += 1
                    log('retryable challenge on %s (attempt %d)' % (url, attempt))
                    time.sleep(15 * attempt)
                    continue
                return body
            last = 'HTTP %s: %s' % (status, out.stderr.decode('utf-8', 'replace')[:200])
            STATE['retries'] += 1
            log('retryable %s on %s (attempt %d)' % (status, url, attempt))
            if status == '404':
                raise NotFound(url)
            if status in ('403', '429') or status.startswith('5'):
                time.sleep(15 * attempt)
            else:
                time.sleep(5 * attempt)
        except (subprocess.TimeoutExpired, OSError) as e:
            last = e
            STATE['retries'] += 1
            log('net error on %s: %s (attempt %d)' % (url, e, attempt))
            time.sleep(5 * attempt)
    raise Blocked('giving up on %s: %s' % (url, last))


def save_meta(extra=None):
    m = {
        'source': 'db.irowiki.org (iRO Wiki Database)',
        'base_url': BASE + '/',
        'started_at': STATE.get('started_at'),
        'updated_at': now_iso(),
        'request_count': STATE['requests'],
        'retries': STATE['retries'],
        'blocked': STATE['blocked'],
        'politeness': {'concurrency': 1, 'base_delay_s': BASE_DELAY,
                       'jitter_s': JITTER, 'user_agent': UA,
                       'backoff': '15s*attempt on 403/429/5xx, max 3 attempts'},
        'robots': 'robots.txt at db.irowiki.org returned empty (no Disallow rules) at ingest time',
    }
    if extra:
        m.update(extra)
    tmp = META + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(m, f, indent=2, sort_keys=True)
    os.replace(tmp, META)


def strip_tags(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = htmlmod.unescape(s).replace(chr(160), ' ')
    return ' '.join(s.split()).strip()


def page_title(html):
    m = TITLE_RE.search(html)
    return m.group(1).strip() if m else None


def kv_pairs(html):
    out = {}
    for m in KV_RE.finditer(html):
        k, v = strip_tags(m.group(1)), strip_tags(m.group(2))
        if k and k not in out:
            out[k] = v
    return out


def parse_drops(html):
    return [{'id': int(a), 'name': strip_tags(n), 'rate': r + '%'}
            for a, n, r in DROP_RE.findall(html)]


def parse_monster(html, mid):
    rec = {'id': mid, 'section': 'monsters', 'name': page_title(html),
           'url': '%s/monster-info/%d/' % (BASE, mid)}
    f = {}
    for k, v in kv_pairs(html).items():
        if k in MONSTER_LABELS:
            f[MONSTER_LABELS[k]] = v
    m = MAIN_BLOCK_RE.search(html)
    if m:
        cells = [c for c in (strip_tags(x) for x in TD_RE.findall(m.group(1))) if c]
        if len(cells) >= 3:
            f['size'], f['race'], f['element'] = cells[-3], cells[-2], cells[-1]
        elif cells:
            f['main_block'] = cells
    m = MODE_RE.search(html)
    if m:
        f['mode'] = strip_tags(m.group(1)).split()
    m = STATS_RE.search(html)
    if m:
        vals = [strip_tags(x) for x in TD_RE.findall(m.group(1))]
        if len(vals) >= 5:
            f['stats'] = dict(zip(('agi', 'vit', 'int', 'dex', 'luk'), vals[:5]))
    i = html.find('Elemental Damage')
    if i != -1:
        ele = {}
        for em in ELEM_PAIR_RE.finditer(html[i:i + 4000]):
            k = strip_tags(em.group(1))
            if k in ELEMENTS:
                ele[k] = em.group(2) + '%'
        if ele:
            f['elemental_damage'] = ele
    f['drops'] = parse_drops(html)
    rec['fields'] = f
    return rec


def parse_item(html, iid, sections):
    rec = {'id': iid, 'section': 'items', 'name': page_title(html),
           'url': '%s/item-info/%d/' % (BASE, iid), 'sections': sorted(sections)}
    f = {}
    for k, v in kv_pairs(html).items():
        if k in ITEM_LABELS:
            f[ITEM_LABELS[k]] = v
        else:
            f.setdefault('extra', {})[k] = v
    m = DESC_RE.search(html)
    if m:
        desc = strip_tags(m.group(2))
        if desc and desc != strip_tags(m.group(1)):
            f['description'] = desc
    nm = rec['name'] or ''
    nm = (rec['name'] or '').strip()
    if nm.endswith(']') and '[' in nm:
        slot_part = nm[nm.rfind('[') + 1:-1]
        if slot_part.isdigit():
            f['slots'] = int(slot_part)
    f['dropped_by'] = parse_drops(html)
    rec['fields'] = f
    return rec


def load_ids(path):
    ids = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                try:
                    ids.add(json.loads(line)['id'])
                except Exception:
                    pass
    return ids


def append_rec(path, rec):
    with open(path, 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + NL)


def fetch_record(url, parser, path, done_ids, errors):
    key = int(ID_TAIL_RE.search(url).group(1))
    if key in done_ids:
        return 'skip'
    try:
        html = fetch(url)
    except NotFound:
        errors.append({'id': key, 'url': url, 'error': 404})
        return '404'
    except Blocked:
        STATE['blocked'] = True
        raise
    rec = parser(html, key)
    if not rec.get('name'):
        errors.append({'id': key, 'url': url, 'error': 'unparseable page'})
        return 'bad'
    rec['fetched_at'] = now_iso()
    rec['raw_html'] = html
    append_rec(path, rec)
    done_ids.add(key)
    if STATE['requests'] % 25 == 0:
        save_meta()
    return 'ok'


def ids_from_listing(fname, pat):
    with open(os.path.join(LISTINGS, fname), encoding='utf-8') as fobj:
        h = fobj.read()
    return sorted(set(int(x) for x in re.findall(pat, h)))


def section_ids_of(iid, section_ids):
    return {s for s, ids in section_ids.items() if iid in ids}


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == '--selftest':
        with open(argv[1]) as fobj:
            mon = parse_monster(fobj.read(), 1002)
        with open(argv[2]) as fobj:
            itm = parse_item(fobj.read(), 1201, {'weapon'})
        print(json.dumps({'monster_sample': mon, 'item_sample': itm},
                         indent=2, ensure_ascii=False))
        return

    STATE['started_at'] = now_iso()
    listing_files = ['monster-search-all.html'] + list(ITEM_SECTIONS.values())
    missing = [fn for fn in listing_files
               if not os.path.exists(os.path.join(LISTINGS, fn))]
    if missing:
        sys.exit('missing listing files under %s: %s' % (LISTINGS, missing))

    monster_ids = ids_from_listing('monster-search-all.html',
                                   r'/db/monster-info/([0-9]+)/')
    section_ids = {s: set(ids_from_listing(fn, r'/db/item-info/([0-9]+)/'))
                   for s, fn in ITEM_SECTIONS.items()}
    all_section = set().union(*section_ids.values())

    done_m = load_ids(MONSTERS_JSONL)
    done_i = load_ids(ITEMS_JSONL)
    errors = []

    save_meta({'phase': 'monsters', 'monsters_total': len(monster_ids),
               'monsters_already_done': len(done_m & set(monster_ids)),
               'item_listing_counts': {s: len(v) for s, v in section_ids.items()},
               'items_enumerated_sections': len(all_section)})
    print('phase monsters: %d ids (%d already done)'
          % (len(monster_ids), len(done_m)), flush=True)
    try:
        for mid in monster_ids:
            fetch_record(BASE + '/monster-info/%d/' % mid, parse_monster,
                         MONSTERS_JSONL, done_m, errors)
    except Blocked:
        save_meta({'phase': 'aborted-monsters'})
        sys.exit(2)

    etc = set()
    with open(MONSTERS_JSONL) as fobj:
        for line in fobj:
            try:
                for d in json.loads(line).get('fields', {}).get('drops', []):
                    etc.add(d['id'])
            except Exception:
                pass
    try:
        arrow_html = fetch(BASE + '/arrow-craft/')
        for x in ITEM_LINK_RE.findall(arrow_html):
            etc.add(int(x))
    except Blocked:
        save_meta({'phase': 'aborted-arrowcraft'})
        sys.exit(2)
    etc -= all_section

    all_items = sorted(all_section | etc)
    save_meta({'phase': 'items', 'items_total': len(all_items),
               'etc_ids_via_drops_arrowcraft': len(etc),
               'items_already_done': len(done_i & set(all_items))})
    print('phase items: %d ids (%d etc via drops/arrow-craft, %d already done)'
          % (len(all_items), len(etc), len(done_i)), flush=True)
    try:
        for iid in all_items:
            parser = partial(parse_item,
                             sections=section_ids_of(iid, section_ids))
            fetch_record(BASE + '/item-info/%d/' % iid, parser,
                         ITEMS_JSONL, done_i, errors)
    except Blocked:
        save_meta({'phase': 'aborted-items'})
        sys.exit(2)

    save_meta({'phase': 'done', 'finished_at': now_iso(),
               'counts': {'monsters': len(done_m), 'items': len(done_i)},
               'errors_404': errors})
    print(json.dumps({'done': True, 'monsters': len(done_m),
                      'items': len(done_i), 'requests': STATE['requests'],
                      'retries': STATE['retries'], 'errors_404': len(errors)}),
          flush=True)


if __name__ == '__main__':
    main()

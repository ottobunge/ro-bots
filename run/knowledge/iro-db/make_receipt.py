#!/usr/bin/env python3
"""Generate run/reviews/iro-db-ingest.json — the receipt for the db.irowiki.org ingest.

Collects: URL patterns, counts, politeness/request stats, license/attribution,
sha256 digests, CLI spot-check evidence (run live via query_iro_db.py), and the
offline rathena fallback note. Run after build_iro_db.py.
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
REVIEW = os.path.join(REPO, 'run', 'reviews', 'iro-db-ingest.json')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    meta = json.load(open(os.path.join(HERE, 'meta.json')))
    if meta.get('phase') != 'done':
        sys.exit('ingest not finished (phase=%s); not writing receipt' % meta.get('phase'))
    # periodic checkpoints overwrite the 'extra' dict; recover enumeration facts
    # from the mid-run snapshot and the listing files themselves
    snap_path = os.path.join(HERE, 'meta_run_in_progress.json')
    if os.path.exists(snap_path):
        snap = json.load(open(snap_path))
        for k in ('monsters_total', 'items_enumerated_sections',
                  'item_listing_counts'):
            if meta.get(k) is None and snap.get(k) is not None:
                meta[k] = snap[k]

    spot = {}
    for label, args in (
            ('poring_id_1002', ['--id', '1002']),
            ('lunatic_id_1063', ['--id', '1063']),
            ('knife_id_1201', ['--id', '1201', '--section', 'items']),
            ('fts_poring', ['poring', '--limit', '3']),
            ('fts_knife_dagger', ['knife NEAR("dagger", 5)', '--section', 'items',
                                  '--limit', '3'])):
        out = subprocess.run([sys.executable, os.path.join(HERE, 'query_iro_db.py')] + args,
                             capture_output=True, text=True, timeout=60)
        spot[label] = {'argv': 'query_iro_db.py ' + ' '.join(args),
                       'exit_code': out.returncode,
                       'output_head': out.stdout[:4000]}

    rathena_db = os.path.join(REPO, 'rathena', 'db')
    fallback = {'path': 'rathena/db (in-repo, pinned)', 'subdirs': []}
    if os.path.isdir(rathena_db):
        fallback['subdirs'] = sorted(d for d in os.listdir(rathena_db)
                                     if os.path.isdir(os.path.join(rathena_db, d)))[:20]

    listing_counts = {}
    ITEM_LISTING_FILES = ['item-gear-search.html', 'item-weapon-search.html',
                          'item-card-search.html', 'item-consume-search.html',
                          'item-costume-search.html']
    listings_dir = os.path.join(HERE, 'listings')
    for fn in sorted(os.listdir(listings_dir)):
        p = os.path.join(listings_dir, fn)
        if os.path.isfile(p):
            import re
            n = len(set(re.findall(r'/db/(?:monster|item)-info/([0-9]+)/',
                                   open(p, encoding='utf-8').read())))
            listing_counts[fn] = n

    monsters_listed = (meta.get('monsters_total')
                       or listing_counts.get('monster-search-all.html'))
    items_sections_listed = meta.get('items_enumerated_sections')
    if items_sections_listed is None:
        import re as remod
        union = set()
        for fn in ITEM_LISTING_FILES:
            p = os.path.join(listings_dir, fn)
            if os.path.exists(p):
                union |= set(remod.findall(r'/db/item-info/([0-9]+)/',
                                           open(p, encoding='utf-8').read()))
        items_sections_listed = len(union)
    items_total = (meta.get('items_total')
                   or (meta.get('counts') or {}).get('items'))
    enumeration = {
        'listing_counts': listing_counts,
        'monsters_listed': monsters_listed,
        'items_enumerated_sections': items_sections_listed,
        'etc_ids_via_drops_arrowcraft': (
            (items_total - items_sections_listed)
            if items_total is not None and items_sections_listed is not None
            else meta.get('etc_ids_via_drops_arrowcraft')),
        'items_total': items_total,
    }

    receipt = {
        'task': 'Ingest db.irowiki.org (iRO Wiki Database) monster/item stat data '
                'into a local searchable corpus under run/knowledge/iro-db/',
        'generated_at': meta.get('finished_at'),
        'source': {
            'site': 'db.irowiki.org',
            'base_url': meta['base_url'],
            'attribution': 'Data (c) Gravity Co., Ltd. and the iRO Wiki (irowiki.org / '
                           'db.irowiki.org) contributors. Ingested read-only for local '
                           'research use; no redistribution or republishing. Ragnarok '
                           'Online is (c) Gravity Co., Ltd.',
            'robots_txt': meta['robots'],
        },
        'url_patterns_discovered': {
            'root_redirect': 'https://db.irowiki.org/ -> https://db.irowiki.org/db/ (302)',
            'monster_info': 'https://db.irowiki.org/db/monster-info/<id>/',
            'item_info': 'https://db.irowiki.org/db/item-info/<id>/',
            'monster_listing': 'https://db.irowiki.org/db/monster-search/?search&ltype=2&sort=1,0&header=100 '
                               '(single page, all 1042 monsters)',
            'item_listings': 'https://db.irowiki.org/db/{gear,weapon,card,consume,costume}-search/?search&ltype=2&sort=1,0&header=100 '
                             '(single page per section, 6562 items total)',
            'etc_coverage': 'no item search section covers Etc-type items; those ids were '
                            'harvested from monster drop tables (item-info links on fetched '
                            'monster pages) plus the /db/arrow-craft/ listing',
            'card_listing_note': 'card-search states "2220 items" but those are entries '
                                 'including duplicate variant rows (685 ids have >1 row, '
                                 'e.g. id 4662 x13); unique card item ids = 1009. '
                                 'Completeness cross-checked: 569 distinct card ids are '
                                 'referenced by monster drops, 568 of which are in the card '
                                 'listing; the missing one (4179 Dragon Fly Card) was '
                                 'harvested via drops and ingested.',
            'json_api': 'none found; all pages are server-rendered HTML (search is GET-param '
                        'driven, parsed from stable CSS-classed tables)',
        },
        'enumeration': enumeration,
        'counts': meta.get('counts'),
        'politeness': meta['politeness'],
        'requests': {
            'total_this_run': meta['request_count'],
            'retries': meta['retries'],
            'blocked': meta['blocked'],
            'errors_404_or_unparseable': meta.get('errors_404', []),
            'note': 'one earlier aborted run made ~9 requests before a crawler-detection '
                    'bug (false-positive Cloudflare check) was fixed; ingest is resumable '
                    'and the aborted run stored no records',
        },
        'schema': {
            'monsters_jsonl': '{id, section:"monsters", name, url, fetched_at, '
                              'fields:{level, hp, def, mdef, attack, range, aspd, move_speed, '
                              'base_exp, job_exp, hit, flee, size, race, element, mode, '
                              'stats{agi,vit,int,dex,luk}, elemental_damage{}, '
                              'drops:[{id,name,rate}]}, raw_html}',
            'items_jsonl': '{id, section:"items", name, url, fetched_at, sections:[gear|weapon|card|consume|costume], fields:{type, subtype, weight, element, weapon_level, required_level, upgradable, damagable, atk, def, buying_price, selling_price, slots, description, extra{}, dropped_by[{id,name,rate}]}, raw_html}',
            'sqlite': 'iro-db.db: entities(section,id,name,url,fetched_at,sections,fields_json,raw_html) '
                      '+ fts_pages(title,body,section UNINDEXED,ref_id UNINDEXED,url UNINDEXED) '
                      '+ meta(k,v)',
        },
        'files': {},
        'spot_checks': spot,
        'offline_fallback': {
            'note': 'pinned rathena YAML DBs are already in-repo and are the authoritative '
                    'offline alternative; this iRO DB ingest complements them with iRO-specific '
                    'live values (drops, NPC prices, iRO current stats)',
            'rathena': fallback,
        },
        'example_invocations': [
            'python3 run/knowledge/iro-db/query_iro_db.py poring --limit 5',
            'python3 run/knowledge/iro-db/query_iro_db.py --id 1002',
            'python3 run/knowledge/iro-db/query_iro_db.py --id 1201 --raw',
            "python3 run/knowledge/iro-db/query_iro_db.py 'knife NEAR/5 dagger' --section items",
        ],
    }

    for fn in ('monsters.jsonl', 'items.jsonl', 'iro-db.db', 'meta.json'):
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            receipt['files'][fn] = {
                'sha256': sha256(p),
                'bytes': os.path.getsize(p),
            }

    os.makedirs(os.path.dirname(REVIEW), exist_ok=True)
    with open(REVIEW, 'w') as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
    print('receipt written:', REVIEW)
    print('counts:', json.dumps(receipt['counts']))
    print('spot check exits:', {k: v['exit_code'] for k, v in spot.items()})


if __name__ == '__main__':
    main()

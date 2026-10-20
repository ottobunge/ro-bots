#!/usr/bin/env python3
"""Build iro-db.db (sqlite FTS5) from monsters.jsonl / items.jsonl.

Rebuildable at any time: drops and recreates the tables. raw_html is stored in
the entities table (not the FTS index). meta.json stats are copied into a
meta table for provenance.

Usage: python3 build_iro_db.py
"""
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'iro-db.db')
META = os.path.join(HERE, 'meta.json')


def flatten(fields, prefix=''):
    parts = []
    for k, v in fields.items():
        key = f'{prefix}{k}'
        if isinstance(v, dict):
            parts.append(flatten(v, prefix=key + ' '))
        elif isinstance(v, list):
            for it in v:
                if isinstance(it, dict):
                    parts.append(flatten(it, prefix=key + ' '))
                else:
                    parts.append(f'{key} {it}')
        else:
            parts.append(f'{key} {v}')
    return ' '.join(parts)


def main():
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute('DROP TABLE IF EXISTS entities')
    c.execute('DROP TABLE IF EXISTS fts_pages')
    c.execute('DROP TABLE IF EXISTS meta')
    c.execute('CREATE TABLE entities ('
              'section TEXT NOT NULL, id INTEGER NOT NULL, name TEXT, url TEXT,'
              'fetched_at TEXT, sections TEXT, fields_json TEXT, raw_html TEXT,'
              'PRIMARY KEY (section, id))')
    c.execute('CREATE VIRTUAL TABLE fts_pages USING fts5('
              'title, body, section UNINDEXED, ref_id UNINDEXED, url UNINDEXED)')
    counts = {}
    for fn, section in (('monsters.jsonl', 'monsters'), ('items.jsonl', 'items')):
        path = os.path.join(HERE, fn)
        if not os.path.exists(path):
            continue
        n = 0
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                c.execute('INSERT OR REPLACE INTO entities VALUES (?,?,?,?,?,?,?,?)',
                          (section, r['id'], r.get('name') or '', r['url'],
                           r.get('fetched_at'), json.dumps(r.get('sections', [])),
                           json.dumps(r.get('fields', {}), ensure_ascii=False),
                           r.get('raw_html', '')))
                body = ((r.get('name') or '') + ' ' + flatten(r.get('fields', {}))
                        + f" id {r['id']}")
                c.execute('INSERT INTO fts_pages (title, body, section, ref_id, url)'
                          ' VALUES (?,?,?,?,?)',
                          (r.get('name') or '', body, section, r['id'], r['url']))
                n += 1
        counts[section] = n
    c.execute('CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)')
    if os.path.exists(META):
        with open(META) as f:
            for k, v in json.load(f).items():
                c.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',
                          (k, json.dumps(v, ensure_ascii=False)))
    con.commit()
    con.close()
    print(json.dumps({'db': DB, 'counts': counts}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Query the local iRO DB corpus (iro-db.db, built by build_iro_db.py).

Free-text search (FTS5 MATCH) plus exact id lookup, over the db.irowiki.org
monster/item stat ingest.

Examples:
  python3 query_iro_db.py 'poring' --limit 5
  python3 query_iro_db.py 'poring' --section monsters
  python3 query_iro_db.py --id 1002
  python3 query_iro_db.py --id 1201 --raw
  python3 query_iro_db.py 'knife NEAR("dagger", 5)' --section items
"""
import argparse
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'iro-db.db')
SECTIONS = ('monsters', 'items')


def main():
    ap = argparse.ArgumentParser(
        description='FTS5 search / id lookup over the ingested iRO DB corpus.')
    ap.add_argument('query', nargs='?', default=None,
                    help='FTS5 MATCH expression, e.g. `poring` or `knife NEAR/3 dagger`')
    ap.add_argument('--id', type=int, default=None,
                    help='exact monster/item id lookup (prints full parsed fields)')
    ap.add_argument('--section', choices=SECTIONS, default=None,
                    help='restrict results to one section')
    ap.add_argument('--limit', type=int, default=10, help='max results (default 10)')
    ap.add_argument('--raw', action='store_true',
                    help='with --id: also print the raw HTML page')
    args = ap.parse_args()

    if not os.path.exists(DB):
        sys.exit(f'database not found: {DB}\nrun build_iro_db.py first')
    if args.id is None and not args.query:
        sys.exit('give a query or --id (see --help)')

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    if args.id is not None:
        sql = 'SELECT * FROM entities WHERE id = ?'
        params = [args.id]
        if args.section:
            sql += ' AND section = ?'
            params.append(args.section)
        rows = con.execute(sql, params).fetchall()
        if not rows:
            sys.exit(f'no record with id {args.id}')
        for r in rows:
            print(f'[{r["section"]}] {r["name"]} (id {r["id"]})')
            print(f'  url: {r["url"]}')
            print(f'  fetched_at: {r["fetched_at"]}')
            if r['section'] == 'items':
                print(f'  sections: {r["sections"]}')
            print('  fields:')
            print(json.dumps(json.loads(r['fields_json']), indent=4,
                             ensure_ascii=False))
            if args.raw:
                print('  raw_html:')
                print(r['raw_html'])
        return

    sql = ('SELECT section, ref_id, title, url, bm25(fts_pages) AS rank, '
           'snippet(fts_pages, 1, "[", "]", " … ", 14) AS snip '
           'FROM fts_pages WHERE fts_pages MATCH ?')
    params = [args.query]
    if args.section:
        sql += ' AND section = ?'
        params.append(args.section)
    sql += ' ORDER BY rank LIMIT ?'
    params.append(args.limit)
    try:
        rows = con.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        sys.exit(f'query error: {e}\n(FTS5 syntax help: quote phrases, use OR / NEAR / *)')
    if not rows:
        suffix = f' (section={args.section})' if args.section else ''
        print(f'no results for: {args.query}{suffix}')
        return
    for i, r in enumerate(rows, 1):
        print(f'{i}. [{r["section"]}] {r["title"]} (id {r["ref_id"]})  '
              f'(rank {r["rank"]:.2f})')
        print(f'   {r["snip"]}')


if __name__ == '__main__':
    main()

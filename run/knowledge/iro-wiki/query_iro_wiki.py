#!/usr/bin/env python3
"""Query the local iRO Wiki FTS corpus (iro-wiki.db, built by ingest_iro_wiki.py).

Examples:
  python3 query_iro_wiki.py 'prontera culvert'
  python3 query_iro_wiki.py 'bash' --section skills --limit 5
  python3 query_iro_wiki.py 'spawn OR monster' --section maps

The query is an SQLite FTS5 MATCH expression; sections are: items, monsters,
maps, skills, all_pages (main-namespace pages outside the four sections).
"""
import argparse
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'iro-wiki.db')
SECTIONS = ('items', 'monsters', 'maps', 'skills', 'all_pages')


def main():
    ap = argparse.ArgumentParser(description='FTS5 search over the ingested iRO Wiki corpus.')
    ap.add_argument('query', help='FTS5 MATCH expression, e.g. `bash NEAR/5 sword`')
    ap.add_argument('--section', choices=SECTIONS, default=None,
                    help='restrict results to one section')
    ap.add_argument('--limit', type=int, default=10, help='max results (default 10)')
    args = ap.parse_args()

    if not os.path.exists(DB):
        sys.exit(f'database not found: {DB}\nrun ingest_iro_wiki.py first')
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    sql = ("SELECT section, title, bm25(fts_pages) AS rank, "
           "snippet(fts_pages, 2, '[', ']', ' … ', 14) AS snip "
           "FROM fts_pages WHERE fts_pages MATCH ?")
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
        print(f'{i}. [{r["section"]}] {r["title"]}  (rank {r["rank"]:.2f})')
        print(f'   {r["snip"]}')


if __name__ == '__main__':
    main()

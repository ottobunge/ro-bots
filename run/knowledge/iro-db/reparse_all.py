#!/usr/bin/env python3
"""Re-parse all stored records from their raw_html with the current parsers.

Zero network requests: every JSONL record keeps its raw_html, so fields are
recomputed offline (fixes fields whose regexes were corrected mid-run, e.g.
monster mode and item description). id/url/fetched_at/raw_html are preserved.

Usage: python3 reparse_all.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ingest_iro_db as m  # noqa: E402


def main():
    jobs = [
        (m.MONSTERS_JSONL, m.parse_monster, 'section_ids_of_monsters'),
        (m.ITEMS_JSONL, m.parse_item, 'item_sections'),
    ]
    # rebuild section membership for items from the listing files
    section_ids = {s: set(m.ids_from_listing(fn, r'/db/item-info/([0-9]+)/'))
                   for s, fn in m.ITEM_SECTIONS.items()}
    for path, parser, _ in jobs:
        tmp = path + '.tmp'
        n = fixed = 0
        with open(path) as f, open(tmp, 'w') as out:
            for line in f:
                r = json.loads(line)
                old_fields = r.get('fields', {})
                if path == m.ITEMS_JSONL:
                    secs = m.section_ids_of(r['id'], section_ids)
                    rec = parser(r['raw_html'], r['id'], secs)
                    r['sections'] = sorted(secs)
                else:
                    rec = parser(r['raw_html'], r['id'])
                new_fields = rec['fields']
                if new_fields != old_fields:
                    fixed += 1
                r['fields'] = new_fields
                if not r.get('name'):
                    r['name'] = rec.get('name')
                out.write(json.dumps(r, ensure_ascii=False) + chr(10))
                n += 1
        import os as osmod
        osmod.replace(tmp, path)
        print('%s: %d records, %d re-parsed with changed fields'
              % (os.path.basename(path), n, fixed))


if __name__ == '__main__':
    main()

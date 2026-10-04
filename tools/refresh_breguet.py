"""Rebuild Breguet from observed finder cards and published variant links."""
import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from lxml import html

from tools.audit_archive_links import AuditScope
from watch_atlas_scraper.breguet_data import extract, norm_ref
from watch_atlas_scraper.client import Client, FetchError, HostBlocked
from watch_atlas_scraper.curl_transport import CurlTransport
from watch_atlas_scraper.state import State, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('scraping_runs/rolex-breguet-refresh-2026-10-05'))
    parser.add_argument('--audit-root', type=Path, required=True)
    args = parser.parse_args()
    catalogue = json.loads((args.root / 'breguet-current-catalogue.json').read_text())
    folder = args.root / 'breguet'; state = State(folder)
    # Reuse source bytes and original capture timestamps; never pretend cached captures are new.
    old = args.audit_root / 'breguet-current'
    with sqlite3.connect('file:' + str(old / 'state.sqlite') + '?mode=ro', uri=True) as db:
        for url, meta, digest in db.execute('SELECT url,metadata,body_hash FROM cache'):
            if not state.cached(url):
                state.save_response(url, json.loads(meta), (old / 'snapshots' / digest).read_bytes())
    queue = {r['url']: {'reference': r['name'][-1], 'origin': 'finder'} for r in catalogue['rows']}
    for r in catalogue.get('invalid_reference_cards', []):
        queue[r['url']] = {'reference': '', 'origin': 'finder_without_reference'}
    path = folder / 'results.json'
    results = json.loads(path.read_text()) if path.exists() else {}
    for url, previous in list(results.items()):
        cached = state.cached(url)
        if cached and cached[0]['status'] == 200:
            try:
                record = extract(cached[1], url, cached[0], previous['reference'])
                results[url] = {**previous, 'status': 'verified', 'record': record}
                results[url].pop('error', None)
            except ValueError as error:
                doc = html.fromstring(cached[1])
                if previous['origin'] == 'finder_without_reference' and 'undefined' in ''.join(doc.xpath('//title/text()')) and not doc.xpath('//h1'):
                    results[url]['reviewed_exclusion'] = {'reason': 'Official finder and product document show undefined; no model, printed reference, specifications or watch image published', 'http_status': 200, 'source_hash': cached[0]['sha256']}
                else:
                    raise error
        elif cached and cached[0]['status'] == 404 and previous['origin'] == 'finder_without_reference':
            results[url]['reviewed_exclusion'] = {'reason': 'Finder card has no reference and its published URL returns HTTP 404', 'http_status': 404, 'source_hash': cached[0]['sha256']}
    write_json(path, results)
    scope = AuditScope(queue)
    client = Client('Breguet', SimpleNamespace(hosts={'www.breguet.com'}), scope, state, 3, transport=CurlTransport())
    try:
        while True:
            for result in list(results.values()):
                for item in result.get('record', {}).get('published_variant_links', []):
                    queue.setdefault(item['url'], {**item, 'origin': 'published_variant'})
                    scope.urls.add(item['url'])
            pending = [u for u in queue if u not in results]
            if not pending:
                break
            for url in pending:
                expected = queue[url]
                try:
                    meta, body = client.get(url)
                    record = extract(body, url, meta, expected['reference'])
                    result = {'status': 'verified', 'record': record, **expected}
                except HostBlocked:
                    raise
                except (FetchError, ValueError) as e:
                    result = {'status': 'needs_review', 'error': str(e), **expected}
                results[url] = result
                write_json(path, results)
                print(f'{len(results)}/{len(queue)} {result["status"]} {url}', flush=True)
        records = {}; conflicts = []
        for url, result in results.items():
            if result['status'] != 'verified':
                continue
            row = result['record']; key = norm_ref(row['reference_number'])
            if key in records and records[key]['source_variant_id'] != row['source_variant_id']:
                conflicts.append({'reference': key, 'urls': [records[key]['watch_URL'], url]})
            records.setdefault(key, row)
        exports = folder / 'exports'; exports.mkdir(exist_ok=True)
        (exports / 'breguet_watches.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=True) + '\n' for row in records.values()))
        write_json(folder / 'manifest.json', {'finder_declared': catalogue['declared_total'], 'finder_observed': catalogue['observed_total'], 'pages_expected': len(queue), 'pages_captured': len(results), 'statuses': dict(Counter(r['status'] for r in results.values())), 'references': len(records), 'reference_conflicts': conflicts, 'needs_review': [{**r, 'url': u} for u, r in results.items() if r['status'] != 'verified']})
        print(json.dumps({'references': len(records), 'pages': len(results), 'needs_review': sum(r['status'] != 'verified' for r in results.values())}), flush=True)
    finally:
        state.close()


if __name__ == '__main__':
    main()

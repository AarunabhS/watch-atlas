"""Read-only, resumable image and historical product URL audit."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

from watch_atlas_scraper.client import Client, FetchError, HostBlocked
from watch_atlas_scraper.curl_transport import CurlTransport
from watch_atlas_scraper.policy import PermissionDenied
from watch_atlas_scraper.state import State, write_json


class AuditScope:
    def __init__(self, urls):
        self.urls = set(urls)

    def require(self, brand, url, purpose='collection'):
        if purpose != 'collection' or url not in self.urls:
            raise PermissionDenied('Outside the archived URL audit: ' + url)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--brand', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--limit', type=int)
    args = p.parse_args()
    baseline = json.loads(args.baseline.read_text())
    rows = [r for r in baseline['records'] if r['brand'] == args.brand and r['is_watch']]
    targets = {}
    for row in rows:
        for kind, key in [('image', 'image_url'), ('product', 'watch_URL')]:
            url = row.get(key)
            if url:
                targets.setdefault(url, []).append({'reference': row['reference_number'], 'kind': kind})
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / 'link_results.json'
    results = json.loads(path.read_text()) if path.exists() else {}
    hosts = {urlsplit(u).hostname for u in targets}
    state = State(args.output)
    client = Client(args.brand, SimpleNamespace(hosts=hosts), AuditScope(targets), state, 3, transport=CurlTransport())
    checked = 0
    try:
        for url, refs in targets.items():
            if url in results:
                continue
            if args.limit and checked >= args.limit:
                break
            if state.blocked(urlsplit(url).hostname):
                results[url] = {'status': 'not_checked_access_blocked', 'references': refs}
                continue
            try:
                meta, body = client.get(url)
                content_type = meta['headers'].get('content-type', '')
                image = any(x['kind'] == 'image' for x in refs)
                valid_image = content_type.startswith('image/') and (body.startswith(b'\xff\xd8\xff') or body.startswith(b'\x89PNG\r\n\x1a\n') or body[:4] == b'RIFF' and body[8:12] == b'WEBP' or body[:6] in (b'GIF87a', b'GIF89a') or b'<svg' in body[:1000])
                results[url] = {'status': 'working' if not image or valid_image else 'invalid_image_response', 'http_status': meta['status'], 'content_type': content_type, 'source_hash': meta['sha256'], 'checked_at': meta['fetched_at'], 'references': refs}
            except (FetchError, PermissionDenied, ValueError) as error:
                cached = state.cached(url)
                meta = cached[0] if cached else {}
                results[url] = {'status': 'access_blocked' if isinstance(error, HostBlocked) else 'unavailable', 'error': str(error), 'http_status': meta.get('status'), 'source_hash': meta.get('sha256'), 'checked_at': meta.get('fetched_at'), 'references': refs}
            checked += 1
            write_json(path, results)
            print(f'{len(results)}/{len(targets)} {results[url]["status"]} {url}', flush=True)
        write_json(path, results)
        write_json(args.output / 'link_manifest.json', {'brand': args.brand, 'records': len(rows), 'expected_urls': len(targets), 'results': len(results), 'missing_image_references': [r['reference_number'] for r in rows if not r.get('image_url')], 'baseline_sha256': hashlib.sha256(args.baseline.read_bytes()).hexdigest(), 'complete': len(results) == len(targets) and all(x['status'] not in ('not_checked_access_blocked', 'access_blocked') for x in results.values())})
    finally:
        state.close()


if __name__ == '__main__':
    main()

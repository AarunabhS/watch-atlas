"""Initial, single-request-per-host robots audit. No product requests."""
import concurrent.futures
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

SITES = {
    'breitling': 'https://www.breitling.com',
    'patek': 'https://www.patek.com',
    'jaeger_lecoultre': 'https://www.jaeger-lecoultre.com',
    'omega': 'https://www.omegawatches.com',
    'tudor': 'https://www.tudorwatch.com',
    'iwc': 'https://www.iwc.com',
}

def probe(item):
    key, origin = item
    folder = Path('scraping_runs/site_audit') / key
    folder.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(origin + '/robots.txt', headers={'User-Agent':'WatchAtlasCatalogBot/1.0 (+https://github.com/AarunabhS/watch-atlas)', 'Accept':'text/plain'})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = res.read(8_000_000)
            status, url, headers = res.status, res.url, dict(res.headers)
    except urllib.error.HTTPError as e:
        status, url, headers, body = e.code, e.url, dict(e.headers), e.read()
    except Exception as e:
        print(json.dumps({'brand': key, 'error': str(e)}), flush=True)
        return
    (folder / 'robots.txt').write_bytes(body)
    meta = {'brand':key, 'url':url, 'status':status, 'headers':headers}
    (folder / 'robots_meta.json').write_text(json.dumps(meta, indent=2))
    print(json.dumps({**meta, 'body': body.decode('utf-8', errors='replace')[:12000]}), flush=True)

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(probe, SITES.items()))

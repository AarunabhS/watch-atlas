from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from lxml.etree import ParserError, XMLSyntaxError
from .adapters import ADAPTERS
from .client import Client, FetchError, HostBlocked
from .discovery import sitemap_links, official_sitemap
from .export import export_records
from .policy import PermissionDenied, Policy
from .state import State, write_json


def run(folder, selected, grants=None, max_pages=50, delay=3, max_urls=20000):
    state, policy = State(folder), Policy(grants)
    reports = []
    try:
        for brand in selected:
            adapter = ADAPTERS[brand]
            report = {'key':brand, 'brand':adapter.brand, 'products_collected_this_run':0, 'requests_attempted':0, 'complete':False, 'adapter_validation':adapter.validation_status}
            print(f'{brand}: checking collection scope', flush=True)
            try:
                # Terms permission checked before robots/network requests.
                policy.require(brand, adapter.seeds[0])
            except PermissionDenied as e:
                report.update(status='permission_required', reason=str(e), terms_url=policy.review['brands'][brand]['terms_url'])
                reports.append(report)
                print(f'{brand}: permission_required; no product requests', flush=True)
                continue
            client = Client(brand, adapter, policy, state, delay)
            try:
                rules = client.ensure_robots(adapter.seeds[0])
                report['content_signals'] = rules.signals
            except (PermissionDenied, FetchError) as e:
                report.update(status='robots_unavailable', reason=str(e))
                reports.append(report)
                continue
            for url in rules.sitemaps:
                if official_sitemap(adapter, url):
                    state.enqueue(brand, url, 'sitemap')
            for seed in adapter.seeds:
                state.enqueue(brand, seed, 'listing')
            discovery_limited = False
            for _ in range(max_pages):
                item = state.pending(brand)
                if item is None:
                    break
                url, kind = item['url'], item['kind']
                report['requests_attempted'] += 1
                try:
                    meta, body = client.get(url)
                    if kind == 'sitemap':
                        map_kind, links = sitemap_links(body)
                        discoveries = [(link, 'sitemap' if map_kind == 'sitemapindex' else adapter.classify(link)) for link in links]
                    else:
                        discoveries = [(link, adapter.classify(link)) for link in adapter.links(body, meta['url'])]
                    # Large global maps cannot silently overrun the bounded queue.
                    counts = state.db.execute('SELECT count(*) FROM queue WHERE brand=?', (brand,)).fetchone()[0]
                    for link, discovered_kind in discoveries:
                        if not discovered_kind:
                            continue
                        if discovered_kind == 'sitemap' and not official_sitemap(adapter, link):
                            continue
                        if counts >= max_urls:
                            discovery_limited = True
                            break
                        if rules.allowed(link):
                            counts += state.enqueue(brand, link, discovered_kind)
                    if kind == 'product':
                        record = adapter.parse(body, meta['url'], meta)
                        # Keep every candidate in state, with invalid ones quarantined on export.
                        state.save_record(record)
                        report['products_collected_this_run'] += 1
                        print(f'{brand}: {record["reference_number"] or url}; {len(record["missing_core_fields"])} core fields missing', flush=True)
                    state.finish(brand, url)
                except HostBlocked as e:
                    state.finish(brand, url, 'blocked', str(e))
                    report.update(status='host_blocked', reason=str(e))
                    break
                except PermissionDenied as e:
                    state.finish(brand, url, 'disallowed', str(e))
                except (FetchError, ParserError, XMLSyntaxError, ValueError) as e:
                    state.finish(brand, url, 'failed', str(e))
                    state.event('failed', url, e)
            counts = state.queue_counts(brand)
            # Traversing a queue does not prove an entire live catalog was enumerated.
            report.update(queue=counts, discovery_limited=discovery_limited, status=report.get('status', 'queue_exhausted' if not counts.get('pending') else 'page_limit_reached'))
            report['discovery_queue_complete'] = not discovery_limited and not any(counts.get(x, 0) for x in ('pending', 'failed', 'blocked', 'disallowed'))
            report['complete'] = False
            report['coverage_note'] = 'Catalog completeness requires comparison with the official current-reference/variant inventory and live parser validation.'
            reports.append(report)
        selected_names = [ADAPTERS[key].brand for key in selected]
        records = state.records(selected_names)
        quality = export_records(records, Path(folder) / 'exports', policy, ADAPTERS)
        manifest = {'run_at':datetime.now(timezone.utc).isoformat(), 'brands':reports, 'stored_product_records':len(records), 'export':quality, 'complete':False}
        write_json(Path(folder) / 'manifest.json', manifest)
        return manifest
    finally:
        state.close()

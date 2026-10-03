import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .adapters import ADAPTERS
from .export import export_records
from .policy import Policy, PermissionDenied
from .runner import run
from .state import State, write_json


def parser():
    p = argparse.ArgumentParser(description='Official Watch Atlas catalog collector; permission and robots gates cannot be bypassed.')
    sub = p.add_subparsers(dest='command', required=True)
    crawl = sub.add_parser('crawl', help='Collect permitted brands; record restricted brands without requesting products')
    crawl.add_argument('--brands', nargs='+', choices=list(ADAPTERS), default=list(ADAPTERS))
    crawl.add_argument('--run-dir', type=Path, default=Path('scraping_runs/current'))
    crawl.add_argument('--grants', type=Path, help='Local evidence/scopes of actual written watchmaker permissions')
    crawl.add_argument('--max-pages', type=int, default=50)
    crawl.add_argument('--delay', type=float, default=3)
    audit = sub.add_parser('audit', help='Write permission report from reviewed terms and saved robots evidence; no network')
    audit.add_argument('--output', type=Path, default=Path('reports/site_permissions.json'))
    audit.add_argument('--evidence-dir', type=Path, default=Path('scraping_runs/site_audit'))
    parse = sub.add_parser('parse-snapshot', help='Parse an authorized saved HTML page without new network requests')
    parse.add_argument('--brand', choices=list(ADAPTERS), required=True)
    parse.add_argument('--url', required=True)
    parse.add_argument('--file', type=Path, required=True)
    parse.add_argument('--grants', type=Path, required=True)
    parse.add_argument('--run-dir', type=Path, default=Path('scraping_runs/offline'))
    export = sub.add_parser('export', help='Export existing state after checking reuse permission')
    export.add_argument('--run-dir', type=Path, required=True)
    export.add_argument('--grants', type=Path)
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if args.command == 'crawl':
        if not 1 <= args.max_pages <= 10000 or args.delay < 3:
            p.error('max-pages must be 1..10000 and delay must be at least 3 seconds')
        result = run(args.run_dir, args.brands, args.grants, args.max_pages, args.delay)
        print(json.dumps({'manifest':str(args.run_dir / 'manifest.json'), 'stored_records':result['stored_product_records'], 'exported_records':result['export']['accepted']}))
    elif args.command == 'audit':
        result = Policy().summary()
        result['report_created_at'] = datetime.now(timezone.utc).isoformat()
        for key, entry in result['brands'].items():
            source = args.evidence_dir / key / 'robots_meta.json'
            if source.exists():
                raw = json.loads(source.read_text())
                body = source.with_name('robots.txt').read_bytes()
                entry['robots_evidence'] = {'url':raw['url'], 'status':raw['status'], 'sha256':hashlib.sha256(body).hexdigest(), 'response_date':raw.get('headers', {}).get('Date', ''), 'file':str(source.with_name('robots.txt'))}
            entry['collection_status'] = 'permission_required'
            entry['product_records_collected'] = 0
        write_json(args.output, result)
        print(str(args.output))
    elif args.command == 'parse-snapshot':
        adapter, policy = ADAPTERS[args.brand], Policy(args.grants)
        try:
            policy.require(args.brand, args.url)
        except PermissionDenied as e:
            p.error(str(e))
        if adapter.classify(args.url) != 'product':
            p.error('URL does not match the configured official product template; update the adapter first')
        body = args.file.read_bytes()
        record = adapter.parse(body, args.url, {'sha256':hashlib.sha256(body).hexdigest()})
        with_state = State(args.run_dir)
        try:
            with_state.save_record(record)
            result = export_records(with_state.records(), args.run_dir / 'exports', policy, ADAPTERS)
        finally:
            with_state.close()
        print(json.dumps(result))
    elif args.command == 'export':
        state = State(args.run_dir)
        try:
            result = export_records(state.records(), args.run_dir / 'exports', Policy(args.grants), ADAPTERS)
        finally:
            state.close()
        print(json.dumps(result))

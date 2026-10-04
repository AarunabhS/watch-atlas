"""Prepare exact Breguet front-image targets, retaining prior verified results."""
import argparse
import json
from pathlib import Path

from watch_atlas_scraper.state import write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('scraping_runs/rolex-breguet-refresh-2026-10-05'))
    p.add_argument('--audit-root', type=Path, required=True)
    args = p.parse_args()
    rows = [json.loads(s) for s in (args.root / 'breguet/exports/breguet_watches.jsonl').read_text().splitlines()]
    write_json(args.root / 'breguet-image-candidates.json', {'records': [
        {'brand': 'Breguet', 'is_watch': True, 'reference_number': r['reference_number'], 'image_url': r['image_URL']} for r in rows
    ]})
    path = args.root / 'breguet-images/link_results.json'
    proofs = json.loads(path.read_text()) if path.exists() else {}
    old = json.loads((args.audit_root / 'breguet-current-images/link_results.json').read_text())
    targets = {r['image_URL'] for r in rows if r['image_URL']}
    for url, proof in old.items():
        if url in targets and proof['status'] == 'working':
            proofs.setdefault(url, proof)
    write_json(path, proofs)
    print(json.dumps({'references': len(rows), 'images': len(targets), 'already_checked': len(proofs)}))


if __name__ == '__main__':
    main()

"""Export verified Rolex DOM captures and resumable image checks."""
import argparse
import hashlib
import json
from pathlib import Path

from watch_atlas_scraper.rolex_data import extract
from watch_atlas_scraper.state import write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit-root', type=Path, required=True)
    p.add_argument('--root', type=Path, default=Path('scraping_runs/rolex-breguet-refresh-2026-10-05'))
    args = p.parse_args()
    baseline = json.loads((args.root / 'baseline.json').read_text())
    folder = args.root / 'rolex'; (folder / 'exports').mkdir(parents=True, exist_ok=True)
    snapshots = folder / 'snapshots'; snapshots.mkdir(exist_ok=True)
    images = args.root / 'rolex-images'; images.mkdir(exist_ok=True)
    proof_path = images / 'link_results.json'
    proofs = json.loads(proof_path.read_text()) if proof_path.exists() else {}
    records = []; unresolved = []
    for original in baseline['records']:
        if original['brand'] != 'Rolex' or not original['is_watch']:
            continue
        body = (args.audit_root / 'rolex-browser' / (original['reference_number'] + '.json')).read_bytes()
        capture = json.loads(body)
        if capture['status'] != 'matched_product':
            unresolved.append(original['reference_number']); continue
        digest = hashlib.sha256(body).hexdigest(); (snapshots / digest).write_bytes(body)
        row = extract(capture, original, digest); records.append(row)
        if capture['image']['loaded']:
            proofs.setdefault(row['image_URL'], {'status': 'working', 'evidence_kind': 'rendered_browser_image',
                'natural_width_positive': True, 'source_hash': digest, 'checked_at': capture['checked_at'],
                'references': [{'reference': row['reference_number'], 'kind': 'image'}]})
    (folder / 'exports/rolex_watches.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=True) + '\n' for r in records))
    write_json(args.root / 'rolex-image-candidates.json', {'records': [{'brand': 'Rolex', 'reference_number': r['reference_number'], 'is_watch': True, 'image_url': r['image_URL']} for r in records]})
    write_json(proof_path, proofs)
    write_json(folder / 'manifest.json', {'verified_references': len(records), 'unresolved_historical_references': unresolved,
        'browser_verified_images': sum(r.get('evidence_kind') == 'rendered_browser_image' for r in proofs.values())})
    print(json.dumps({'verified': len(records), 'unresolved': len(unresolved), 'image_checks': len(records) - len(proofs)}))


if __name__ == '__main__':
    main()

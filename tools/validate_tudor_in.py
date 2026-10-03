"""Offline audit of Tudor exports, source identities, prices and technical text."""
import argparse
import csv
import json
from pathlib import Path

from lxml import html

from tools.capture_tudor_in import discover, load_pages
from watch_atlas_scraper.schema import COLUMNS
from watch_atlas_scraper.state import write_json
from watch_atlas_scraper.tudor_in_data import clean, product, text


def audit(folder):
    pages = load_pages(folder)
    inventory, listing = discover(pages)
    with (folder / 'exports/tudor_watches.csv').open(newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValueError('CSV columns differ from the shared 40-column schema')
        csv_rows = list(reader)
    rows = [json.loads(line) for line in (folder / 'exports/tudor_watches.jsonl').read_text().splitlines()]
    if len(rows) != len(inventory) or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Incomplete export or duplicate record identities')
    by_ref = {r['reference_number']: r for r in rows}
    csv_by_ref = {r['reference_number']: r for r in csv_rows}
    if set(by_ref) != set(inventory) or set(csv_by_ref) != set(inventory):
        raise ValueError('Export references do not exactly match the published catalogue')
    for ref, item in inventory.items():
        row = by_ref[ref]
        if csv_by_ref[ref] != {k: row[k] for k in COLUMNS}:
            raise ValueError('CSV and JSONL differ: ' + ref)
        meta, body = pages[item['url']]
        reconstructed = product(body, item['url'], item, meta)
        if reconstructed != row:
            raise ValueError('Saved export differs from source reconstruction: ' + ref)
        # Independent DOM check, deliberately separate from the extraction implementation.
        doc = html.fromstring(body)
        selected = doc.get_element_by_id('full-specifications')
        identity = clean(' '.join(selected.xpath('./div//p/text()')))
        if 'Reference: ' + ref not in identity:
            raise ValueError('Visible product reference mismatch: ' + ref)
        price_text = clean(' '.join(doc.xpath('//main/section[1]//*[@data-nosnippet]/text()')))
        if not price_text.startswith('₹') or ''.join(c for c in price_text if c.isdigit()) != row['price']:
            raise ValueError('Visible INR price mismatch: ' + ref)
        fields = {}
        for li in selected.xpath('.//li[h3]'):
            label = clean(li.xpath('string(h3)'))
            ps = li.xpath('./p')
            if ps:
                fields[label] = '; '.join(text(html.tostring(p, encoding='unicode', with_tail=False)) for p in ps)
        if fields != row['raw_specifications']:
            raise ValueError('Technical specifications dropped or changed: ' + ref)
        if row['validation_errors'] or row['missing_core_fields']:
            raise ValueError('Invalid record or missing core fields: ' + ref)
        if not all(p['source_hash'] in {row['source_hash'], row['catalogue_source_hash']} for p in row['provenance'].values()):
            raise ValueError('Field provenance has an unrelated source: ' + ref)
    result = {'passed': True, 'references': len(rows), 'catalogue_pages': len(listing),
              'source_snapshots_verified': len(pages), 'visible_product_prices_verified': len(rows),
              'technical_specification_sets_verified': len(rows), 'csv_jsonl_agreement': True,
              'core_fields_complete': True, 'source_reconstruction_agreement': True}
    write_json(folder / 'validation_report.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=Path('scraping_runs/tudor-in-capture'))
    print(json.dumps(audit(p.parse_args().output)))

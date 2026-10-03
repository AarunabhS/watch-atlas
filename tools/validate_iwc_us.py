"""Audit complete IWC exports against every saved catalogue and product source."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from lxml import html

from tools.capture_iwc_us import load_pages
from watch_atlas_scraper.iwc_us_data import CATALOG, catalogue, cls, product, text
from watch_atlas_scraper.schema import COLUMNS
from watch_atlas_scraper.state import write_json


def validate(folder):
    pages = load_pages(folder)
    inventory, expected_counts = catalogue(pages[CATALOG][1])
    rows = [json.loads(s) for s in (folder / 'exports/iwc_watches.jsonl').read_text().splitlines()]
    with (folder / 'exports/iwc_watches.csv').open(newline='') as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == COLUMNS, 'Wrong CSV schema'
        csv_rows = list(reader)
    refs = [r['reference_number'] for r in rows]
    assert len(refs) == len(set(refs)) == len(inventory), 'Missing or duplicate exported references'
    assert set(refs) == set(inventory), 'Reference set differs from official catalogue'
    assert len(csv_rows) == len(rows), 'Export row counts disagree'
    prices, sections_checked = 0, 0
    for row, csv_row in zip(rows, csv_rows):
        assert {k: row[k] for k in COLUMNS} == csv_row, 'CSV/JSONL field mismatch'
        item = inventory[row['reference_number']]
        meta, body = pages[item['url']]
        assert row == product(body, item['url'], item, meta), 'Export differs from freshly parsed source'
        assert not row['validation_errors'], 'Record validation error'
        assert row['market'] == 'US' and row['brand'] == 'IWC' and row['currency'] in ('', 'USD'), 'Incorrect market/brand'
        doc = html.fromstring(body)
        spec_root = doc.xpath('//*[' + cls('phoenix-product-specs-tabs') + ']/noscript')[0]
        source_tables = {}
        for h in spec_root.xpath('.//h2'):
            source_tables[h.text_content().strip()] = {
                text(n, './/*[' + cls('phxsg-specs-table__row-left') + ']'): text(n, './/*[' + cls('phxsg-specs-table__row-right') + ']')
                for n in h.getparent().xpath('.//*[' + cls('phxsg-specs-table__row') + ']')}
        assert source_tables['Overview']['Reference'] == row['reference_number'], 'Visible identity mismatch'
        for section, label, field in [('Case', 'Height', 'case_thickness'), ('Case', 'Water Resistance', 'water_resistance'), ('Case', 'Strap width', 'between_lugs'), ('Movement', 'Caliber', 'caliber'), ('Movement', 'Power Reserve', 'power_reserve'), ('Movement', 'Frequency', 'frequency'), ('Movement', 'Jewels', 'jewels')]:
            assert row[field] == source_tables[section].get(label, ''), 'Technical field mismatch: ' + field
        visible = text(doc, '//*[@id="tab-overview"]//*[@data-price="value"]')
        assert visible == row['price'], 'Selected visible price mismatch'
        if visible:
            prices += 1
            assert text(doc, '//*[@id="tab-overview"]//*[@data-price="currency"]') == 'US$', 'Visible currency mismatch'
            assert float(visible.replace(',', '')) == float(item['listing_price'].replace(',', '')), 'Listing/product price mismatch'
        sections_checked += len(source_tables)
    assert dict(Counter(r['parent_model'] for r in rows)) == expected_counts, 'Family counts disagree'
    result = {'valid': True, 'references_verified': len(rows), 'source_snapshots_verified': len(pages),
              'listing_pages_verified': 1, 'technical_sections_verified': sections_checked,
              'visible_selected_prices_verified': prices, 'unpriced_references': [r['reference_number'] for r in rows if not r['price']],
              'collections': expected_counts, 'csv_columns_verified': len(COLUMNS),
              'missing_core_fields': dict(Counter(k for r in rows for k in r['missing_core_fields']))}
    write_json(folder / 'validation_report.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('scraping_runs/iwc-us-capture'))
    args = parser.parse_args()
    print(json.dumps(validate(args.output), indent=2))


if __name__ == '__main__':
    main()

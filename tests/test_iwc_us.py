import json
import unittest
from pathlib import Path

from watch_atlas_scraper.iwc_us_data import catalogue, official, product

FIXTURES = Path(__file__).parent / 'fixtures' / 'iwc_us'


class IWCSourceTests(unittest.TestCase):
    def load(self, label):
        item = json.loads((FIXTURES / (label + '.json')).read_text())
        body = (FIXTURES / (label + '.html')).read_bytes()
        return body, item, {'url': item['url'], 'sha256': 'fixture', 'fetched_at': '2026-10-04T00:00:00Z', 'representation': 'rendered_dom'}

    def test_full_published_technical_sections(self):
        body, item, meta = self.load('priced')
        row = product(body, item['url'], item, meta)
        self.assertEqual(row['caliber'], '69385')
        self.assertEqual(row['frequency'], '28800 Vph (4 Hz)')
        self.assertEqual(row['jewels'], '33')
        self.assertEqual(row['power_reserve'], '46 hours')
        self.assertEqual(row['case_thickness'], '14.5 mm')
        self.assertEqual(row['between_lugs'], '20 mm')
        self.assertEqual(row['lug_to_lug'], '')
        self.assertEqual(row['price'], '9,200')
        self.assertEqual(row['currency'], 'USD')
        self.assertIn('Sapphire glass', row['crystal'])
        self.assertEqual(set(row['raw_specifications']), {'Overview', 'Features', 'Case', 'Movement'})
        self.assertEqual(row['validation_errors'], [])

    def test_unpriced_specialist_without_product_jsonld(self):
        body, item, meta = self.load('unpriced')
        row = product(body, item['url'], item, meta)
        self.assertEqual(row['reference_number'], 'IW590503')
        self.assertTrue(row['caliber'])
        self.assertTrue(row['short_description'])
        self.assertEqual(row['price'], '')
        self.assertEqual(row['currency'], '')
        self.assertEqual(row['source_product_fields']['structured_product'], {})
        self.assertEqual(row['year_introduced'], '')

    def test_wrong_specification_identity_rejected(self):
        body, item, meta = self.load('priced')
        body = body.replace(b'> IW388121 <', b'> IW000000 <')
        with self.assertRaisesRegex(ValueError, 'reference mismatch'):
            product(body, item['url'], item, meta)

    def test_wrong_canonical_rejected(self):
        body, item, meta = self.load('priced')
        meta = {**meta, 'url': item['url'] + '-other'}
        with self.assertRaisesRegex(ValueError, 'redirect'):
            product(body, item['url'], item, meta)

    def test_listing_price_disagreement_rejected(self):
        body, item, meta = self.load('priced')
        item = {**item, 'listing_price': '1,000'}
        with self.assertRaisesRegex(ValueError, 'price mismatch'):
            product(body, item['url'], item, meta)

    def test_missing_section_rejected(self):
        body, item, meta = self.load('priced')
        body = body.replace(b'> Movement </h2>', b'> Unknown </h2>')
        with self.assertRaisesRegex(ValueError, 'sections'):
            product(body, item['url'], item, meta)

    def test_scope_is_current_us_catalogue_only(self):
        body, item, meta = self.load('priced')
        self.assertTrue(official(item['url']))
        self.assertFalse(official(item['url'] + '?filters=all'))
        self.assertFalse(official(item['url'].replace('/us-en/', '/ww-en/')))
        self.assertFalse(official('https://www.iwc.com/us-en/account'))
        self.assertFalse(official(item['url'].replace('www.iwc.com', 'example.com')))

    def test_catalogue_count_and_duplicate_guards(self):
        def card(ref):
            tracking = json.dumps({'ecommerce': {'items': [{'item_id': ref, 'price': '1000'}]}}).replace('"', '&quot;')
            return '<div data-cy="mixed-grid-item" iswatches="true"><a data-tracking="' + tracking + '" href="https://www.iwc.com/us-en/watches/pilot-watches/' + ref.lower() + '-test">Test</a><span data-price="value">1,000</span><span data-price="currency">US$</span></div>'
        body = '<div class="phoenix-mixed-grid"><h1>Pilot’s Watches</h1><div>1 Products</div>' + card('IW388121') + '</div>'
        items, counts = catalogue(body)
        self.assertEqual(set(items), {'IW388121'})
        self.assertEqual(counts, {'Pilot’s Watches': 1})
        with self.assertRaisesRegex(ValueError, 'count mismatch'):
            catalogue(body.replace('1 Products', '2 Products'))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            catalogue(body.replace('1 Products', '2 Products').replace('</div>', '</div>', 1).replace('</div></div>', '</div>' + card('IW388121') + '</div>'))


if __name__ == '__main__':
    unittest.main()

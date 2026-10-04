import json
import unittest
from pathlib import Path

from lxml import html

from watch_atlas_scraper.breguet_data import extract as breguet
from watch_atlas_scraper.rolex_data import extract as rolex

FIXTURES = Path(__file__).parent / 'fixtures'


class ReferenceRefreshTests(unittest.TestCase):
    def setUp(self):
        self.body = (FIXTURES / 'breguet/selected.html').read_bytes()
        self.url = 'https://www.breguet.com/en/watches/tradition/tradition-7038/7038brct3v6d00d'
        self.meta = {'url': self.url, 'sha256': 'fixture', 'fetched_at': '2026-10-04T10:00:00Z'}

    def test_selected_reference_scopes_the_image_and_dimensions(self):
        row = breguet(self.body, self.url, self.meta, '7038BR/CT/3V6/D00D')
        self.assertEqual(row['case_thickness'], '11.3 mm')
        self.assertEqual(row['power_reserve'], '50 hours')
        self.assertEqual(row['features'], 'retrograde seconds')
        self.assertIn('7038BR_CT_3V6_D00D', row['image_URL'])
        self.assertTrue(any(f['label'] == 'Thickness' and f['value'] == '6.3 mm' for f in row['raw_specifications']))
        self.assertTrue(any(f['label'] == 'Movement: Thickness' and f['value'] == '6.3 mm' for f in row['additional_specifications']))
        self.assertEqual(row['price'], '')
        self.assertEqual(row['currency'], '')
        conflict = breguet(self.body.replace(b'calfskin strap', b'alligator strap'), self.url, self.meta)
        self.assertTrue(conflict['source_discrepancies'])

    def test_wrong_listing_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identity disagree'):
            breguet(self.body, self.url, self.meta, '7057BR/G9/9W6')

    def test_wrong_product_sku_is_rejected(self):
        body = self.body.replace(b'"sku": "7038BRCT3V6D00D"', b'"sku": "7057BRG99W6"')
        with self.assertRaisesRegex(ValueError, 'identity disagree'):
            breguet(body, self.url, self.meta)

    def test_missing_selected_image_never_borrows_another_variant(self):
        doc = html.fromstring(self.body)
        image = doc.xpath('//img[@data-variant-id="235106"]')[0]
        image.attrib.pop('src', None)
        image.attrib.pop('data-src', None)
        row = breguet(html.tostring(doc), self.url, self.meta)
        self.assertEqual(row['image_URL'], '')
        self.assertEqual(row['image_status'], 'not_published_by_source')

    def test_printed_suffix_omission_retains_the_full_sku_and_discrepancy(self):
        doc = html.fromstring(self.body)
        script = doc.xpath('//script[@type="application/ld+json"]')[0]
        data = json.loads(script.text)
        product = data['@graph'][0]
        product['sku'] += '3L'; product['@id'] = product['sku']; product['url'] = self.url + '3l'
        script.text = json.dumps(data)
        doc.xpath('//link[@rel="canonical"]')[0].set('href', product['url'])
        row = breguet(html.tostring(doc), product['url'], {**self.meta, 'url': product['url']}, product['sku'])
        self.assertEqual(row['reference_number'], '7038BRCT3V6D00D3L')
        self.assertTrue(any(x['field'] == 'reference_number' for x in row['source_discrepancies']))

    def test_multiple_case_dimensions_never_become_a_numeric_diameter(self):
        doc = html.fromstring(self.body)
        label = doc.xpath('//*[contains(@class,"tabs__label") and normalize-space(.)="Diameter"]')[0]
        label.text = 'Width'
        row = breguet(html.tostring(doc), self.url, self.meta)
        self.assertEqual(row['diameter'], 'Width: 37 mm')
        self.assertEqual(row['case_dimensions_display'], 'Case width')

    def test_rolex_case_and_bracelet_material_cannot_overwrite_each_other(self):
        capture = json.loads((FIXTURES / 'rolex/selected.json').read_text())
        original = {'reference_number': capture['reference'], 'specific_model': 'Datejust 36', 'parent_model': 'Datejust 36', 'id': 'legacy-id'}
        row = rolex(capture, original, 'fixture')
        self.assertIn('White Rolesor', row['case_material'])
        self.assertEqual(row['bracelet_material'], 'Oystersteel')
        self.assertTrue(row['clasp_type'])
        self.assertEqual(row['gem_setting'], '')
        gem_capture = json.loads(json.dumps(capture))
        next(x for x in gem_capture['fields'] if x['label'] == 'Bezel')['value'] = 'Set with diamonds'
        self.assertEqual(rolex(gem_capture, original, 'fixture')['gem_setting'], 'Set with diamonds')
        self.assertTrue(any(x['label'] == 'Movement: Precision' for x in row['additional_specifications']))
        capture['image']['current_url'] = capture['image']['current_url'].replace(capture['reference'], '126234-9999')
        with self.assertRaisesRegex(ValueError, 'Image does not identify'):
            rolex(capture, original, 'fixture')


if __name__ == '__main__':
    unittest.main()

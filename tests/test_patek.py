"""Synthetic fixtures for the live-observed Patek component structure."""
import json
import unittest

from watch_atlas_scraper.patek_data import catalog, field, product
from watch_atlas_scraper.schema import COLUMNS


def scalar(value):
    return {'jsonValue': {'value': value}}


def linked(value):
    return {'jsonValue': {'fields': {'Name': {'value': value}}}}


def page(components, images=''):
    route = {'fields': {'SeoDescription': {'value': 'A fictional test watch.'}},
             'placeholders': {'headless-main': components}}
    root = {'props': {'pageProps': {'layoutData': {'sitecore': {'route': route}}}}}
    return ('<html><main>' + images + '</main><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(root) + '</script></html>').encode()


class PatekTests(unittest.TestCase):
    def fixture(self, extra=None, keypoints=None):
        raw = {
            'reference': scalar('TEST-001'), 'collection': linked('Test collection'),
            'watchFamily': linked('Test family'), 'gender': linked('Unisex'),
            'caseDimension': scalar('40 mm'), 'caseHeight': scalar('11 mm'),
            'diamTotal': scalar('30 mm'), 'thickness': scalar('4 mm'),
            'material': linked('White gold'), 'mechanism': linked('Self-winding'),
            'caliberCode': scalar('Test caliber'), 'numberOfRubis': scalar('29'),
            'backgroundAndTimeCircle': scalar('Blue dial. Applied Arabic numerals.'),
            'complicationsBulletPoints': scalar('<p>Calendar.</p><p>Seconds.</p>'),
            'frontPicture': {'jsonValue': {'title': 'PP_TEST_001_SDT', 'src': 'https://assets.example/source.psd'}},
            'subtype': linked('Wristwatch'),
            'keypoints': {'items': [{'name': 'KeyPointText', **scalar(x)} for x in keypoints or []]},
            'unmappedTechnicalProperty': scalar('Retain this original source value'),
        }
        raw.update(extra or {})
        components = [{'componentName': 'ProductSimilarModels', 'fields': {'reference': 'WRONG'}},
                      {'componentName': 'ProductDetail', 'fields': {'data': {'datasource': raw}}}]
        images = '<img alt="PP_TEST_001_SDT" src="https://assets.example/display.jpg">' \
                 '<img alt="PP_OTHER_999_SDT" src="https://assets.example/other.jpg">'
        return page(components, images), raw

    def record(self, body):
        return product(body, 'https://www.patek.com/en/collection/test/test-001',
                       {'articleRef': 'TEST-001', 'subtype': 'Wristwatch'},
                       {'sha256': 'fixture-hash', 'fetched_at': '2026-10-02T00:00:00Z'})

    def test_actual_structure_and_case_movement_dimensions(self):
        body, raw = self.fixture()
        row = self.record(body)
        self.assertEqual(row['case_thickness'], '11 mm')
        self.assertEqual(row['movement_thickness'], '4 mm')
        self.assertEqual(row['diameter'], '40 mm')
        self.assertEqual(row['movement_diameter'], '30 mm')
        self.assertEqual(row['parent_model'], 'Test collection')
        self.assertEqual(row['specific_model'], 'Test family')
        self.assertEqual(row['raw_product_fields'], raw)
        self.assertEqual(row['source_field_count'], len(raw))
        self.assertEqual(row['validation_errors'], [])
        self.assertTrue(set(COLUMNS).issubset(row))

    def test_rendered_image_and_unrelated_models(self):
        body, _ = self.fixture()
        row = self.record(body)
        self.assertEqual(row['image_URL'], 'https://assets.example/display.jpg')
        self.assertEqual(row['image_urls'], ['https://assets.example/display.jpg'])

    def test_source_identity_mismatch_fails(self):
        body, _ = self.fixture({'reference': scalar('OTHER-999')})
        with self.assertRaisesRegex(ValueError, 'Identity mismatch'):
            self.record(body)

    def test_dial_finish_is_not_case_finish(self):
        body, _ = self.fixture(keypoints=['The dial has polished hour markers.'])
        self.assertEqual(self.record(body)['case_finish'], '')
        body, _ = self.fixture(keypoints=['The case and lugs are hand-polished.'])
        self.assertEqual(self.record(body)['case_finish'], 'hand-polished')
        body, _ = self.fixture(keypoints=['Polished hands. The gold case is satin-finished.'])
        self.assertEqual(self.record(body)['case_finish'], 'satin-finished')
        body, _ = self.fixture(keypoints=['The case has polished and satin finishes.'])
        self.assertEqual(self.record(body)['case_finish'], 'polished and satin finishes')

    def test_visible_parts_count_and_explicit_strap_color(self):
        body, _ = self.fixture({'numberOfComponents': scalar('212'),
                                'numberOfComponentsDisplay': scalar('Number of parts: 207'),
                                'strapOriginallyFitted': scalar('Alligator leather, hand-stitched, shiny chocolate brown')})
        row = self.record(body)
        self.assertEqual(row['number_of_parts'], '207')
        self.assertEqual(row['source_discrepancies'][0]['cms_value'], '212')
        self.assertEqual(row['bracelet_color'], 'shiny chocolate brown')
        body, _ = self.fixture({'strapOriginallyFitted': scalar('Bracelet, white gold')})
        self.assertEqual(self.record(body)['bracelet_color'], '')

    def test_pocket_specific_water_statement_does_not_leak_into_wristwatch(self):
        extra = {'waterResistance': scalar('Water-resistant to 30m'),
                 'pocketWaterResistance': scalar('Humidity- and dust-protected only (not water-resistant)')}
        body, _ = self.fixture(extra)
        self.assertEqual(self.record(body)['water_resistance'], 'Water-resistant to 30m')
        extra['subtype'] = linked('Pocketwatch')
        body, _ = self.fixture(extra)
        self.assertEqual(self.record(body)['water_resistance'], 'Humidity- and dust-protected only (not water-resistant)')

    def test_price_and_introduction_year_are_not_inferred(self):
        body, _ = self.fixture({'availableDate': scalar('2026-03-01T00:00:00')})
        row = self.record(body)
        self.assertEqual(row['year_introduced'], '')
        self.assertEqual(row['price'], '')
        self.assertEqual(row['currency'], '')
        self.assertEqual(row['available_date'], '2026-03-01T00:00:00')

    def test_markup_and_missing_values(self):
        body, _ = self.fixture()
        row = self.record(body)
        self.assertEqual(row['features'], 'Calendar. Seconds.')
        self.assertEqual(row['numerals'], 'Applied Arabic numerals')
        self.assertEqual(field(linked('Pocketwatch')), 'Pocketwatch')
        self.assertEqual(field(scalar(False)), False)
        body, _ = self.fixture({'rhcMarketingTitle': scalar('Fictional enamel scene')})
        self.assertEqual(self.record(body)['marketing_name'], 'Fictional enamel scene')

    def test_inventory_dates_and_exact_component_scope(self):
        watches = [
            {'articleRef': 'CURRENT', 'availableDate': '2026-01-01T00:00:00', 'runOutDate': None},
            {'articleRef': 'FUTURE', 'availableDate': '2027-01-01T00:00:00', 'runOutDate': None},
            {'articleRef': 'ENDED', 'availableDate': '2020-01-01T00:00:00', 'runOutDate': '2026-10-02T00:00:00'},
        ]
        body = page([{'componentName': 'Header', 'fields': {'watches': [{'articleRef': 'UNRELATED'}]}},
                     {'componentName': 'WatchFinder', 'fields': {'watches': watches}}])
        current, other = catalog(body, '2026-10-02T05:30:00+05:30')
        self.assertEqual([x['articleRef'] for x in current], ['CURRENT'])
        self.assertEqual([x['articleRef'] for x in other], ['FUTURE', 'ENDED'])

    def test_template_change_fails_explicitly(self):
        with self.assertRaisesRegex(ValueError, 'template changed'):
            catalog(b'<main>No embedded page data</main>', '2026-10-02')


if __name__ == '__main__':
    unittest.main()

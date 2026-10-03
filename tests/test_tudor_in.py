import copy
import json
import unittest
from pathlib import Path

from watch_atlas_scraper.tudor_in_data import CATALOG, ORIGIN, catalog_page, material, official, product
from tools.capture_tudor_in import discover

FIXTURES = Path(__file__).parent / 'fixtures' / 'tudor_in'
META = {'sha256': 'test-source', 'fetched_at': '2026-10-04T00:00:00+00:00'}


def fixture(name='northflag'):
    hit = json.loads((FIXTURES / (name + '_hit.json')).read_text())
    url = ORIGIN + '/en/watches/' + hit['familySlug'] + '/' + hit['cleanRmc']
    item = {'hit': hit, 'reference': hit['rmc'].upper(), 'url': url, 'catalogue_url': CATALOG,
            'catalogue_source_hash': 'catalog-source'}
    return (FIXTURES / (name + '_product.html')).read_bytes(), item, {**META, 'url': url}


def listing(hit, page=0, total=1, pages=1, pagers=()):
    data = {'prd_catalog': {'state': {'numericRefinements': {'allPrices.IN.rawPrice': {}}},
                           'results': [{'hits': [hit], 'index': 'prd_catalog', 'page': page, 'nbHits': total, 'nbPages': pages}]}}
    links = ''.join('<a href="' + u + '">Page</a>' for u in pagers)
    return ('<html><script>window[Symbol.for("InstantSearchInitialResults")] = ' + json.dumps(data) + '</script><main>' + links + '</main></html>').encode()


class TudorIndiaTests(unittest.TestCase):
    def test_source_dimensions_and_selected_price(self):
        body, item, meta = fixture()
        row = product(body, item['url'], item, meta)
        self.assertEqual(row['reference_number'], 'M9140G1A0U-0001')
        self.assertEqual(row['diameter'], '40 mm')
        self.assertEqual(row['between_lugs'], '12 mm')
        self.assertEqual(row['lug_to_lug'], '')
        self.assertEqual(row['case_thickness'], '12.7 mm')
        self.assertEqual((row['currency'], row['price']), ('INR', '511000'))
        self.assertEqual(row['caliber'], 'MT5652-U')
        self.assertEqual(row['dial_color'], 'Black')
        self.assertEqual(row['case_finish'], 'satin-brushed; polished')
        self.assertEqual(row['validation_errors'], [])
        self.assertEqual(row['provenance']['image_URL']['source_hash'], 'catalog-source')

    def test_fxd_diameter_and_length_with_different_lug_width(self):
        body, item, meta = fixture('fxd')
        row = product(body, item['url'], item, meta)
        self.assertEqual(row['diameter'], '42 mm')
        self.assertEqual(row['between_lugs'], '22 mm')
        self.assertEqual(row['lug_to_lug'], '52 mm')
        self.assertEqual(row['case_material'], 'Titanium')
        self.assertEqual(row['caseback'], 'Steel case back')
        self.assertEqual(row['case_thickness'], '12.8 mm')

    def test_product_price_mismatch_stops_extraction(self):
        body, item, meta = fixture()
        with self.assertRaisesRegex(ValueError, 'prices differ'):
            product(body.replace('₹5,11,000'.encode(), '₹9,11,000'.encode()), item['url'], item, meta)

    def test_product_spec_mismatch_stops_extraction(self):
        body, item, meta = fixture()
        item = copy.deepcopy(item)
        item['hit']['powerReserveSpec']['en'] = '70-hour power reserve'
        with self.assertRaisesRegex(ValueError, 'Power Reserve'):
            product(body, item['url'], item, meta)

    def test_campaign_redirect_keeps_final_source_and_original_listing_url(self):
        body, item, meta = fixture()
        final_url = ORIGIN + '/en/watch-family/daring-watches/' + item['hit']['cleanRmc']
        row = product(body, item['url'], item, {**meta, 'url': final_url})
        self.assertEqual(row['watch_URL'], final_url)
        self.assertEqual(row['catalogue_product_url'], item['url'])
        self.assertEqual(row['provenance']['movement']['url'], final_url)
        with self.assertRaisesRegex(ValueError, 'redirect'):
            product(body, item['url'], item, {**meta, 'url': 'https://example.com/watch'})

    def test_different_reference_is_rejected(self):
        body, item, meta = fixture()
        item['reference'] = 'M11111-0001'
        with self.assertRaisesRegex(ValueError, 'reference differs'):
            product(body, item['url'], item, meta)

    def test_catalogue_preserves_display_code_separately_from_url(self):
        _, item, _ = fixture()
        hit = copy.deepcopy(item['hit'])
        hit.update(rmc='m2542g267nu-0002', cleanRmc='m2542gxx7nu-0002', objectID='m2542gxx7nu-0002', familySlug='pelagos-fxd')
        page = catalog_page(listing(hit), CATALOG, META)
        self.assertEqual(page['items'][0]['reference'], 'M2542G267NU-0002')
        self.assertTrue(page['items'][0]['url'].endswith('m2542gxx7nu-0002'))

    def test_pagination_duplicate_and_wrong_page_are_rejected(self):
        _, item, _ = fixture()
        page2 = CATALOG + '/page/2'
        with self.assertRaisesRegex(ValueError, 'different page'):
            catalog_page(listing(item['hit']), page2, META)
        pages = {CATALOG: (META, listing(item['hit'], total=2, pages=2, pagers=[page2])),
                 page2: (META, listing(item['hit'], page=1, total=2, pages=2))}
        with self.assertRaisesRegex(ValueError, 'Repeated reference'):
            discover(pages)

    def test_mixed_currency_is_rejected(self):
        _, item, _ = fixture()
        hit = copy.deepcopy(item['hit'])
        hit['allPrices']['US'] = {'rawPrice': 123}
        with self.assertRaisesRegex(ValueError, 'Mixed price markets'):
            catalog_page(listing(hit), CATALOG, META)

    def test_url_scope_and_materials(self):
        self.assertTrue(official(ORIGIN + '/en/watch-family/daring-watches/m79310n-0001'))
        self.assertFalse(official(CATALOG + '?q=watch', 'listing'))
        self.assertFalse(official('https://example.com/en/watches'))
        self.assertEqual(material('18 ct yellow gold'), '18 ct yellow gold')
        self.assertEqual(material('grade 2 titanium'), 'Grade 2 titanium')
        self.assertEqual(material('Fixed carbon fibre bezel'), 'Carbon fibre')

    def test_explicit_dial_colour_overrides_coarse_catalogue_filter(self):
        body, item, meta = fixture()
        item = copy.deepcopy(item)
        item['hit']['dialSpec']['en'] = item['hit']['dialSpec']['en'].replace('Black dial', 'Salmon dial')
        item['hit']['filters']['Colour']['en'] = ['filter-dial-colour-pink-cr|Pink']
        row = product(body.replace(b'Black dial', b'Salmon dial'), item['url'], item, meta)
        self.assertEqual(row['dial_color'], 'Salmon')


if __name__ == '__main__':
    unittest.main()

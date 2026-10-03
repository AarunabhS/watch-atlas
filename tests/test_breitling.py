"""Invented fixtures exercising the observed Breitling page structures."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.scrape_breitling import discover_browser
from watch_atlas_scraper.breitling_data import FINDER, attribute, catalog_page, product
from watch_atlas_scraper.schema import COLUMNS

REFERENCE = 'AA12345678B1'
URL = 'https://www.breitling.com/us-en/watches/test/test-model/' + REFERENCE + '/'


def attr(value, unit=None):
    return {'attribute': {'slug': 'fictional', 'unit': unit},
            'values': [{'name': value, 'translation': {'name': 'INTERNAL-42', 'plainText': value}}]}


def document(props, markup=''):
    return ('<html><body>' + markup + '<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps({'props': {'pageProps': props}}) + '</script></body></html>').encode()


def technical(dimensions=None):
    dimensions = dimensions if dimensions is not None else {'Diameter': '40 mm', 'Thickness': '11 mm', 'Lug width (in-between lug)': '20 mm'}
    rows = ''.join('<div data-test-id="NameValueWrapper-' + str(i) + '"><span data-test-id="Name-' + str(i)
                   + '">' + k + '</span><span data-test-id="Value-' + str(i) + '">' + v + '</span></div>'
                   for i, (k, v) in enumerate(dimensions.items()))
    return '<section data-testid="sectionTechnicalData"><div data-test-id="Section"><h3 data-test-id="SectionTitle">Dimensions</h3>' + rows + '</div></section>'


def card(ref, title='Fictional watch'):
    return ('<div data-testid="productCard"><a data-testid="ProductCard" href="/us-en/watches/test/test-model/'
            + ref + '/"><span data-test-id="Sku">' + ref + '</span><span data-test-id="Name">' + title
            + '</span><span data-test-id="Price">USD 1,234</span></a></div>')


class BreitlingTests(unittest.TestCase):
    def fixture(self, extra=None, pricing=None, structured=None, dimensions=None, sku=REFERENCE):
        raw = {
            'productType': {'slug': 'watch'}, 'name': 'Base name', 'watchName': attr('Fictional watch'),
            'collectionName': attr('Fictional collection'), 'comCategories': {'values': [{'name': 'Men'}, {'name': 'Capsule'}]},
            'caseMaterial': attr('Stainless steel'), 'caseback': attr('Screwed in'),
            'diameter': attr('40', 'CM'), 'thickness': attr('11', 'CM'), 'lugWidth': attr('20', 'CM'),
            'weight': attr('150.5', 'G'), 'headWeight': attr('70.0', 'G'), 'height': attr('0', 'CM'),
            'movement': attr('Self-winding mechanical'), 'caliber': attr('Fictional 32'),
            'powerReserve': attr('Approx. 42 hours'), 'waterResistance': attr('20 bars (200 m)'),
            'dialColor': attr('Blue'), 'strapMaterial': attr('Stainless steel'), 'strapColor': attr('Metal bracelet'),
            'bezel': attr('Unidirectional rotating'), 'buckleType': attr('Folding clasp'),
            'modelStory': attr('<p>First sentence.</p><p>Second sentence.</p>'),
            'launchDate': attr('27.08.2025'), 'limited': {'values': [{'boolean': False}]},
            'thumbnail': {'url': 'https://assets.example/current.webp'},
            'mediaLarge': [{'url': 'https://assets.example/current-side.webp'}],
            'relatedProducts': {'values': [{'name': 'ZZ99999999Z9'}]},
            'unknownFutureAttribute': {'original': ['Keep', 'Everything']},
        }
        raw.update(extra or {})
        selected = {'sku': sku, 'product': raw,
                    'pricing': pricing if pricing is not None else {'price': {'gross': {'amount': 1234, 'currency': 'USD'}}}}
        props = {'productVariant': selected,
                 'productStructuredData': structured if structured is not None else {'sku': sku},
                 'businessData': {'productVariant': {'sku': sku, 'quantityAvailable': 5}},
                 'seoConfig': {'seoDescription': 'A fictional watch for parser tests.'}}
        markup = technical(dimensions) + '<span data-test-id="KeyFeaturesSectionSwissMade">Swiss made</span>'
        markup += '<aside>' + card('ZZ99999999Z9', 'Unrelated recommended watch') + '</aside>'
        return document(props, markup), raw

    def record(self, body):
        return product(body, URL, {'reference': REFERENCE, 'raw_listing_fields': {'objectID': REFERENCE},
                                  'catalog_page_url': FINDER, 'catalog_source_hash': 'catalog-hash'},
                       {'sha256': 'fixture-hash', 'fetched_at': '2026-10-02T00:00:00Z'})

    def test_selected_watch_raw_fields_and_legacy_columns(self):
        body, raw = self.fixture()
        r = self.record(body)
        self.assertEqual(r['raw_product_fields'], raw)
        self.assertEqual(r['source_field_count'], len(raw))
        self.assertTrue(set(COLUMNS).issubset(r))
        self.assertEqual(r['reference_number'], REFERENCE)
        self.assertEqual(r['specific_model'], 'Fictional watch')
        self.assertEqual(r['type'], 'Men')
        self.assertEqual(r['validation_errors'], [])
        self.assertEqual(r['image_urls'], ['https://assets.example/current.webp', 'https://assets.example/current-side.webp'])
        self.assertEqual(r['related_reference_numbers'], ['ZZ99999999Z9'])

    def test_display_units_and_product_weight_are_not_movement_or_head_values(self):
        body, _ = self.fixture()
        r = self.record(body)
        self.assertEqual((r['diameter'], r['case_thickness'], r['between_lugs']), ('40 mm', '11 mm', '20 mm'))
        self.assertEqual(r['weight'], '150.5 g')
        self.assertEqual(r['headWeight'], '70.0')
        self.assertEqual(r['lug_to_lug'], '')
        self.assertEqual(len(r['source_discrepancies']), 3)
        body, _ = self.fixture(dimensions={})
        self.assertEqual(self.record(body)['diameter'], '')

    def test_unknown_weight_and_non_color_strap_label(self):
        body, _ = self.fixture({'weight': attr('0.0', 'G')})
        r = self.record(body)
        self.assertEqual(r['weight'], '')
        self.assertEqual(r['bracelet_color'], '')
        self.assertEqual(r['strap_color_label'], 'Metal bracelet')
        self.assertEqual(r['bezel_material'], '')
        self.assertEqual(r['case_finish'], '')
        body, _ = self.fixture({'strapColor': attr('Burgundy')})
        self.assertEqual(self.record(body)['bracelet_color'], 'Burgundy')

    def test_boolean_and_explicit_launch_date(self):
        body, _ = self.fixture()
        r = self.record(body)
        self.assertIs(r['limited_edition'], False)
        self.assertEqual(r['year_introduced'], '2025')
        body, _ = self.fixture({'limited': {'values': [{'boolean': True}]}, 'launchDate': attr(''), 'publicationDate': attr('2026-10-01')})
        r = self.record(body)
        self.assertIs(r['limited_edition'], True)
        self.assertEqual(r['year_introduced'], '')

    def test_translation_display_not_internal_identifier(self):
        self.assertEqual(attribute({'values': [{'name': 'Base', 'translation': {'name': 'CODE-123', 'plainText': 'Display'}}]}), 'Display')
        self.assertEqual(attribute({'values': [{'name': 'Base', 'translation': {'name': 'CODE-123'}}]}), 'Base')
        body, _ = self.fixture()
        self.assertEqual(self.record(body)['description'], 'First sentence. Second sentence.')

    def test_price_is_selected_variant_not_recommendation(self):
        body, _ = self.fixture(structured={'sku': REFERENCE, 'offers': [{'price': 9999, 'priceCurrency': 'USD', 'url': URL}]})
        r = self.record(body)
        self.assertEqual((r['price'], r['currency']), ('1234', 'USD'))
        for absent in (0, None, 'NaN', 'not a price'):
            body, _ = self.fixture(pricing={'price': {'gross': {'amount': absent, 'currency': 'USD'}}},
                                   structured={'sku': REFERENCE, 'offers': [{'price': 9999, 'priceCurrency': 'USD', 'url': URL.replace(REFERENCE, 'ZZ99999999Z9')}]})
            self.assertEqual(self.record(body)['price'], '')
        body, _ = self.fixture(pricing={}, structured={'sku': REFERENCE, 'offers': [{'price': 1234, 'priceCurrency': 'USD', 'url': URL}]})
        self.assertEqual(self.record(body)['price'], '1234')

    def test_identity_and_template_change_fail_explicitly(self):
        body, _ = self.fixture(sku='ZZ99999999Z9')
        with self.assertRaisesRegex(ValueError, 'Identity mismatch'):
            self.record(body)
        body, _ = self.fixture(structured={'sku': 'ZZ99999999Z9'})
        with self.assertRaisesRegex(ValueError, 'identity disagrees'):
            self.record(body)
        with self.assertRaisesRegex(ValueError, 'template changed'):
            self.record(b'<main>Changed template</main>')

    def test_browser_catalog_uses_rendered_cards_instead_of_stale_page_one_hits(self):
        props = {'serverState': {'initialResults': {'index': {'results': [{'hits': [{'objectID': 'WRONG-SERVER-REF'}],
                           'page': 0, 'nbPages': 2, 'nbHits': 2}]}}}}
        body = document(props, '<div data-test-id="ListingHitsWatchesGrid">' + card(REFERENCE) + '</div>' + card('ZZ99999999Z9'))
        r = catalog_page(body, FINDER + '?page=2', {'kind': 'rendered_dom', 'sha256': 'hash', 'file': '2.html'})
        self.assertEqual(r['page'], 1)
        self.assertEqual([x['reference'] for x in r['items']], [REFERENCE])
        self.assertEqual(r['items'][0]['url'], URL)
        self.assertEqual(r['items'][0]['catalog_representation'], 'rendered_dom')

    def test_incomplete_browser_manifest_cannot_claim_catalog_completion(self):
        props = {'serverState': {'initialResults': {'index': {'results': [{'hits': [], 'page': 0, 'nbPages': 2, 'nbHits': 2}]}}}}
        body = document(props, '<div data-test-id="ListingHitsWatchesGrid">' + card(REFERENCE) + '</div>')
        client = SimpleNamespace(policy=SimpleNamespace(require=lambda *args: None),
                                 ensure_robots=lambda _: SimpleNamespace(allowed=lambda _: True))
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            rendered = folder / 'rendered_pages'
            rendered.mkdir()
            (rendered / '1.html').write_bytes(body)
            manifest = {'complete': True, 'captured_epoch': 99999999999, 'expected': 2,
                        'declared_page_count': 2, 'hitsPerPage': 1,
                        'pages': [{'page': 0, 'url': FINDER, 'file': '1.html', 'sha256': hashlib.sha256(body).hexdigest(), 'kind': 'rendered_dom', 'references': [REFERENCE]}]}
            (rendered / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Incomplete rendered catalog'):
                discover_browser(client, folder, SimpleNamespace())


if __name__ == '__main__':
    unittest.main()

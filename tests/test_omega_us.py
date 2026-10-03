import json
import unittest

from watch_atlas_scraper.omega_us_data import catalog_page, product, reference, finder_totals
from tools.capture_omega_us import PersonalResearch
from watch_atlas_scraper.policy import PermissionDenied

ORIGIN = 'https://www.omegawatches.com'
URL = ORIGIN+'/en-us/watch-omega-speedmaster-moonwatch-31030425001002'
REF = '310.30.42.50.01.002'


def detail(ref=REF, url=URL, extra='', offer=None):
    structured = {'@type':'Product','url':url,'name':'Moonwatch',
                  'image':ORIGIN+'/media/31030425001002.png',
                  'offers':{'sku':ref,'price':9000,'priceCurrency':'USD'} if offer is None else offer,
                  'addOn':[{'sku':'other','price':50000,'priceCurrency':'USD'}]}
    return f'''<html><head><link rel="canonical" href="{url}"></head><body><main>
    <h1><span class="collection">Speedmaster</span><span class="subcollection">Moonwatch Professional</span><span class="name">42 mm, steel on steel</span></h1>
    <dd class="technical-data-value" data-code="sku">{ref}</dd>
    <dd class="technical-data-value" data-code="watch_thickness">13.18 mm</dd>
    <dd class="technical-data-value" data-code="caliber_power_reserve">50 hours</dd>
    <div class="technical-data-value" data-code="description"><p>Moonshine™ gold</p><p>Calibre Ω</p></div>
    <button class="ow-tags">Transparent caseback</button>
    <script type="application/ld+json">{json.dumps(structured)}</script>{extra}
    </main></body></html>'''.encode()


def listing(count, page, refs, next_page=True):
    cards=''.join(f'<li class="product-item" data-sku="{sku}"><a href="{ORIGIN}/en-us/watch-omega-test-{sku}">Watch</a></li>' for sku in refs)
    pager=f'<a data-role="ajax-pager" data-target="next" href="{ORIGIN}/en-us/watches/seamaster?p={page+1}">Load more</a>' if next_page else ''
    return f'<p id="product-list-count"><span data-count="{count}">{count}</span></p><div data-role="list-pager" data-current="{page}">{pager}</div><ul id="product-list-grid">{cards}</ul>'.encode()


class OmegaTests(unittest.TestCase):
    def test_modern_and_legacy_references(self):
        self.assertEqual(reference('31030425001002'),REF)
        self.assertEqual(reference('51082000'),'5108.20.00')
        with self.assertRaises(ValueError): reference('123')

    def test_current_offer_and_dimensions(self):
        row=product(detail(),URL)
        self.assertEqual(row['price'],'9000')
        self.assertEqual(row['case_thickness'],'13.18 mm')
        self.assertEqual(row['power_reserve'],'50 hours')
        self.assertEqual(row['caseback'],'Transparent caseback')
        self.assertEqual(row['description'],'Moonshine™ gold Calibre Ω')
        self.assertEqual(row['year_introduced'],'')

    def test_related_offer_does_not_supply_missing_price(self):
        row=product(detail(offer=[]),URL)
        self.assertEqual(row['price'],'')
        self.assertEqual(row['currency'],'')

    def test_selected_movement_frequency(self):
        row=product(detail(extra='<li class="ow-mod_37__picto ow-mod_37__picto--frequency">Frequency 3.5 Hz Play audio</li>'),URL)
        self.assertEqual(row['frequency'],'3.5 Hz')
        self.assertEqual(row['source_product_fields']['movement_indicators']['frequency'],'Frequency 3.5 Hz Play audio')

    def test_strap_configuration_and_detailed_dial_color(self):
        extra='''<dd class="technical-data-value" data-code="watch_dial">Blue</dd>
                 <dd class="technical-data-value" data-code="watch_dial_detailed_color">Peacock blue</dd>
                 <dd class="technical-data-value" data-code="strap_color_list">Black</dd>
                 <dd class="technical-data-value" data-code="buckle_type">Foldover clasp</dd>
                 <dd class="technical-data-value" data-code="buckle_material">Steel</dd>'''
        row=product(detail(extra=extra),URL)
        self.assertEqual(row['dial_color'],'Peacock blue')
        self.assertEqual(row['bracelet_color'],'Black')
        self.assertEqual(row['clasp_type'],'Foldover clasp')
        self.assertEqual(row['raw_specifications']['buckle_material'],'Steel')

    def test_omitted_collection_heading_uses_selected_taxonomy(self):
        tracking={'ecommerce':{'items':[{'item_id':'31030425001002','item_category2':'Speedmaster'}]}}
        body=detail(extra=f'''<span data-real-sku="31030425001002" data-product-dl='{json.dumps(tracking)}'></span>''')
        body=body.replace(b'<span class="collection">Speedmaster</span>',b'')
        self.assertEqual(product(body,URL)['parent_model'],'Speedmaster')
        self.assertEqual(product(body,URL)['collection_label'],'Speedmaster Moonwatch Professional')

    def test_binary_source_description_preserved_and_decoded(self):
        words='The watch is driven by OMEGA Calibre 8806.'
        bits=' '.join(format(x,'08b') for x in words.encode())
        body=detail().replace('Moonshine™ gold'.encode(),bits.encode()).replace(b'<p>Calibre \xce\xa9</p>',b'')
        row=product(body,URL)
        self.assertEqual(row['description'],words)
        self.assertEqual(row['raw_specifications']['description'],bits)
        self.assertEqual(row['caliber'],'Omega 8806')

    def test_relative_placeholder_is_not_an_image_url(self):
        body=detail().replace((ORIGIN+'/media/31030425001002.png').encode(),b'?w=230')
        row=product(body,URL)
        self.assertEqual(row['image_URL'],'')
        self.assertEqual(row['source_product_fields']['structured_product']['image'],'?w=230')

    def test_technical_reference_mismatch(self):
        with self.assertRaises(ValueError): product(detail(ref='220.10.38.20.01.005'),URL)

    def test_canonical_reference_mismatch(self):
        with self.assertRaises(ValueError): product(detail(url=ORIGIN+'/en-us/watch-omega-test-22010382001005'),URL)

    def test_selected_offer_reference_mismatch(self):
        with self.assertRaises(ValueError): product(detail(offer={'sku':'other','price':1}),URL)

    def test_conflicting_technical_fields(self):
        with self.assertRaises(ValueError): product(detail(extra='<dd class="technical-data-value" data-code="watch_thickness">50 mm</dd>'),URL)

    def test_pocket_watch(self):
        url=ORIGIN+'/en-us/watch-omega-specialities-olympic-pocket-watch-1932-51082000'
        body=detail('5108.20.00',url).replace(b'Moonwatch Professional',b'Olympic Pocket Watch')
        self.assertEqual(product(body,url)['type'],'Pocket watch')

    def test_cumulative_pagination(self):
        refs=[str(31030425001000+x) for x in range(48)]
        page=catalog_page(listing(50,2,refs),ORIGIN+'/en-us/watches/seamaster?p=2')
        self.assertEqual(len(page['items']),48)
        self.assertTrue(page['next'].endswith('?p=3'))

    def test_missing_cumulative_cards_rejected(self):
        refs=[str(31030425001000+x) for x in range(24)]
        with self.assertRaises(ValueError): catalog_page(listing(50,2,refs),ORIGIN+'/en-us/watches/seamaster?p=2')

    def test_last_page_without_filters(self):
        page=catalog_page(listing(1,1,['31030425001002'],False),ORIGIN+'/en-us/watches/seamaster')
        self.assertEqual(page['expected'],1)

    def test_duplicate_cards_rejected(self):
        with self.assertRaises(ValueError): catalog_page(listing(2,1,['31030425001002']*2,False),ORIGIN+'/en-us/watches/seamaster')

    def test_page_number_mismatch(self):
        with self.assertRaises(ValueError): catalog_page(listing(1,1,['31030425001002'],False),ORIGIN+'/en-us/watches/seamaster?p=2')

    def test_finder_totals_reconcile(self):
        body=b'<button data-role="apply-filters" data-count="2"></button><button data-filter-code="filter_collection_subcollection" data-gio-value="Seamaster">Seamaster 2</button>'
        self.assertEqual(finder_totals(body),(2,{'Seamaster':2}))
        with self.assertRaises(ValueError): finder_totals(body.replace(b'data-count="2"',b'data-count="3"'))

    def test_scope(self):
        policy=PersonalResearch()
        for url in (URL,ORIGIN+'/en-us/watchfinder',ORIGIN+'/en-us/watches/seamaster?p=2'):
            policy.require('omega',url)
        for url in (ORIGIN+'/en-us/watchfinder?p=2',ORIGIN+'/en-us/watches/seamaster?price=10',ORIGIN+'/en-us/customer/account', 'https://other.test/en-us/watchfinder'):
            with self.assertRaises(PermissionDenied): policy.require('omega',url)


if __name__ == '__main__': unittest.main()

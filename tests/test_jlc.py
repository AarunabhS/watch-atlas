import json,unittest
from watch_atlas_scraper.jlc_data import product,catalog,reference
URL='https://www.jaeger-lecoultre.com/us-en/watches/reverso/reverso-tribute/test-q1234567'
ITEM={'reference':'Q1234567','url':URL,'collection':'Reverso Tribute','name':'Monoface','summary':'40.1 x 24.4 mm Manual Pink Gold Watch','image':'https://img.jaeger-lecoultre.com/watch.jpg'}
META={'sha256':'fixture','fetched_at':'2026-10-03T00:00:00Z'}
def detail(price=True,identity='Q1234567',marketing=False):
 selected={'@type':'Product','sku':identity,'image':['https://img.jaeger-lecoultre.com/watch.jpg'],'offers':{'price':12000,'priceCurrency':'USD'}}
 tracking={'pageProductTrackingInformation':{'item_id':identity,'item_material_case':'Pink gold','currency':'','price':''}}
 desc='' if marketing else '<div id="product-accordion-tab-description"><div class="product-page-details__infos_text">A selected watch.</div><h3 class="product-page-details__infos_subtitle">Internal reference</h3><div class="product-page-details__infos_text">JLQ1234567 (Q1234567)</div></div>'
 specs='''<main><h1 class="product-page-details__title">Reverso Tribute Monoface</h1>'''+desc+'''<div><h3 class="product-page-details__infos_subtitle">Case</h3><div class="product-page-details__infos_text">Pink gold Dimensions (L x W): 40.1 x 24.4 mm, L : Lug to lug Thickness: 7.56mm</div></div><div id="product-accordion-tab-movement"><h5 class="product-page-details__infos_subtitle">Jaeger-LeCoultre Calibre 822</h5><div><h5 class="product-page-details__infos_subtitle">MOVEMENT TYPE</h5></div><div class="product-page-details__infos_text">Manual winding</div><div><h5 class="product-page-details__infos_subtitle">Power reserve</h5></div><div class="product-page-details__infos_text">42 hours</div></div></main>'''
 return ('<html><head><title>Watch '+identity+'</title><link rel="canonical" href="'+URL+'"></head><body>'+specs+('<script type="application/ld+json">'+json.dumps(selected)+'</script>' if price else '')+'<script>window.Phoenix.trackingVariables = '+json.dumps(tracking)+';</script></body></html>').encode()
class JaegerTests(unittest.TestCase):
 def test_public_reference_url_forms(self):
  self.assertEqual(reference(URL),'Q1234567');self.assertEqual(reference(URL.replace('-q1234567','/q1234567')),'Q1234567')
 def test_standard_mapping_and_separate_case_movement_dimensions(self):
  row=product(detail(),URL,ITEM,META)
  self.assertEqual(row['reference_number'],'Q1234567');self.assertEqual(row['diameter'],'40.1 x 24.4 mm');self.assertEqual(row['case_thickness'],'7.56 mm');self.assertEqual(row['caliber'],'822');self.assertEqual(row['power_reserve'],'42 hours');self.assertEqual(row['price'],'12000');self.assertEqual(row['validation_errors'],[])
 def test_request_only_price_can_omit_product_jsonld(self):
  row=product(detail(price=False),URL,ITEM,META);self.assertEqual(row['price'],'');self.assertEqual(row['currency'],'');self.assertTrue(row['product_detail_parsed'])
 def test_mismatched_selected_watch_rejected(self):
  with self.assertRaises(ValueError):product(detail(identity='Q7654321'),URL,ITEM,META)
 def test_marketing_template_requires_tracking_and_canonical_identity(self):
  row=product(detail(price=False,marketing=True),URL,ITEM,META);self.assertEqual(row['template'],'marketing_product');self.assertEqual(row['image_URL'],ITEM['image']);self.assertEqual(row['price'],'')
 def test_listing_deduplication_and_editorial_card_reconciliation(self):
  card='<div data-cy="product-card"><a class="product-card__link" href="'+URL+'"><h5 class="product-card__collection">Reverso</h5><h5 class="product-card__name">Monoface</h5></a></div>'
  editorial='<div data-cy="product-card"><a class="product-card__link" href="https://www.jaeger-lecoultre.com/us-en/news/watchmaking/story">Story</a></div>'
  body=('<main><div data-cy="mixed-grid-products-count">2 Results</div>'+card+card+editorial+'</main>').encode();items,total,excluded=catalog(body);self.assertEqual(len(items),1);self.assertEqual(total,2);self.assertEqual(len(excluded),1)
 def test_incomplete_listing_rejected(self):
  with self.assertRaises(ValueError):catalog(b'<main><div data-cy="mixed-grid-products-count">186 Results</div></main>')
if __name__=='__main__':unittest.main()

"""Jaeger-LeCoultre's observed product cards, JSON-LD and technical DOM sections."""
import hashlib,json,re
from urllib.parse import urlsplit
from lxml import html
from .schema import Record,clean

ORIGIN='https://www.jaeger-lecoultre.com'
FINDER=ORIGIN+'/us-en/watches/all-watches'

def doc(body):return html.fromstring(body.decode('utf-8') if isinstance(body,bytes) else body)
def cls(name):return 'contains(concat(" ",normalize-space(@class)," ")," '+name+' ")'
def value(node):return clean(' '.join(node.itertext()))
def first(node,xpath):
 values=node.xpath(xpath)
 return value(values[0]) if values and hasattr(values[0],'itertext') else clean(values[0]) if values else ''
def reference(url):
 m=re.search(r'[-/]q([a-z0-9]{7})/?$',urlsplit(url).path,re.I)
 return 'Q'+m[1].upper() if m else ''
def catalog(body):
 root=doc(body);counts=root.xpath('//*[@data-cy="mixed-grid-products-count"]/text()')
 expected={int(re.search(r'\d+',x)[0]) for x in counts if re.search(r'\d+',x)}
 if len(expected)!=1:raise ValueError('Expected one published all-watches count')
 inventory={};excluded=[]
 for card in root.xpath('//main//*[@data-cy="product-card"]'):
  url=first(card,'.//a['+cls('product-card__link')+']/@href');ref=reference(url)
  if urlsplit(url).netloc!='www.jaeger-lecoultre.com':raise ValueError('Invalid published origin')
  row={'url':url,'reference':ref,'collection':first(card,'.//*['+cls('product-card__collection')+']'),'name':first(card,'.//*['+cls('product-card__name')+']'),'summary':first(card,'.//*['+cls('product-card__specs')+']'),'image':first(card,'.//img/@src')}
  if '/us-en/clocks/' in url:excluded.append({**row,'reason':'Clock excluded from watch capture'});continue
  if not ref:
   if '/news/' in url:excluded.append({**row,'reason':'Editorial URL; watch identity requires product-page verification'});continue
   raise ValueError('Invalid published product identity')
  if ref in inventory and inventory[ref]['url']!=url:raise ValueError('Conflicting reference URL')
  inventory[ref]=row
 if len(inventory)+len({x['url'] for x in excluded})!=next(iter(expected)):raise ValueError('Published count and distinct listing references differ')
 return list(inventory.values()),next(iter(expected)),list({x['url']:x for x in excluded}.values())

def product(body,url,item,meta):
 root=doc(body);objects=[json.loads(x) for x in root.xpath('//script[@type="application/ld+json"]/text()')]
 products=[x for x in objects if x.get('@type')=='Product']
 if len(products)>1:raise ValueError('Ambiguous selected Product JSON-LD')
 tracking={}
 for script in root.xpath('//script/text()'):
  match=re.search(r'window.Phoenix.trackingVariables\s*=\s*(\{.*?\});',script,re.S)
  if match:tracking=json.loads(match[1]).get('pageProductTrackingInformation',{})
 selected=products[0] if products else {};ref=selected.get('sku') or tracking.get('item_id')
 internal=first(root,'//*[@id="product-accordion-tab-description"]')
 canonical=first(root,'//link[@rel="canonical"]/@href')
 if canonical and (reference(canonical) and reference(canonical)!=item['reference'] or not reference(canonical) and canonical!=url):raise ValueError('Canonical identity mismatch')
 if internal and ref not in internal:raise ValueError('Internal reference mismatch')
 if not internal and (tracking.get('item_id')!=item['reference'] or not any(item['reference'] in x.upper() for x in [first(root,'//title'),*root.xpath('//main//img/@alt')])):raise ValueError('Marketing template identity mismatch')
 if ref!=item['reference'] or reference(url) and ref!=reference(url):raise ValueError('Watch identity mismatch')
 r=Record('Jaeger-LeCoultre',url,'US','en',meta['sha256'],meta['fetched_at'])
 r.set('reference_number',ref,'Product.sku' if products else 'Selected watch tracking metadata item_id');r.set('type','Watch','all-watches listing');r.set('parent_model',item['collection'],'product-card__collection')
 r.set('specific_model',first(root,'//main//h1['+cls('product-page-details__title')+']') or item['collection']+' '+item['name'],'Product heading or selected listing');r.set('short_description',item['summary'],'product-card__specs');r.set('description',first(root,'//*[@id="product-accordion-tab-description"]//*['+cls('product-page-details__infos_text')+']'),'Description accordion')
 images=selected.get('image') or root.xpath('//main//*[contains(@class,"product-images-grid")]//img[contains(@src,"product-grid-hero")]/@src');images=[images] if isinstance(images,str) else images
 r.data['image_urls']=images;r.set('image_URL',images[0] if images else item['image'],'Product.image')
 offer=selected.get('offers') or {};amount=offer.get('price') or tracking.get('price')
 if amount and float(amount)>0:r.set('price',str(amount),'Product.offers.price');r.set('currency',offer.get('priceCurrency') or tracking.get('currency'),'Published price currency')
 r.data['price_status']='published' if r.data['price'] else 'not_published'
 specs={}
 for heading in root.xpath('//main//*[(self::h3 or self::h5) and '+cls('product-page-details__infos_subtitle')+']'):
  title=value(heading);parent=heading.getparent();nodes=parent.xpath('./*['+cls('product-page-details__infos_text')+']') or parent.xpath('./following-sibling::*['+cls('product-page-details__infos_text')+'][1]')
  if nodes:
   val=value(nodes[0]);specs[title]=specs[title]+'; '+val if title in specs and specs[title]!=val else val
 technical={}
 for key,val in specs.items():
  if key in ['MOVEMENT TYPE','Functions','Thickness','Vibrations per hour','Frequency (HZ)','Power reserve','Components','Jewels','Barrel']:technical[key]=val
 for heading in root.xpath('//*[@id="product-accordion-tab-movement"]//h5'):
  match=re.search(r'Jaeger-LeCoultre Calib(?:re|er) (.+)',value(heading))
  if match:technical['In-House Calibre']=match[1]
 block_fields={}
 for block in root.xpath('//main//*['+cls('caliber-block__key-value')+']'):
  key=first(block,'.//*['+cls('caliber-block__key')+']') or first(block,'.//*['+cls('btn__text')+']')
  val=first(block,'.//*['+cls('caliber-block__value')+']')
  if key and val:block_fields[key]=val;technical.setdefault(key,val)
 # Keep the separate accordion values, including discrepancies with the calibre block.
 accordion={}
 for content in root.xpath('//main//*[starts-with(@id,"product-accordion-tab-")]'):
  if 'care' in content.get('id',''):continue
  entries=[]
  for block in content.xpath('.//*['+cls('product-page-details__infos_text')+']'):entries.append(value(block))
  if entries:accordion[content.get('id')]=entries
 case=specs.get('Case','');
 if not case:r.set('case_material',tracking.get('item_material_case'),'Selected product tracking item_material_case')
 r.data['template']='technical_product' if internal else 'marketing_product'
 if not internal:
  r.set('diameter',(re.match(r'^([\d.,]+(?:\s*x\s*[\d.,]+)?)\s*mm',item['summary'],re.I)[1]+' mm') if re.match(r'^([\d.,]+(?:\s*x\s*[\d.,]+)?)\s*mm',item['summary'],re.I) else '', 'Selected listing case dimensions')
  paragraphs=root.xpath('//main//*['+cls('text-block')+']//p')
  r.set('description',' '.join(value(n) for n in paragraphs),'Product-specific narrative text blocks')
  r.data['raw_narrative_blocks']=[value(n) for n in paragraphs]
 r.set('case_material',re.split(r'Dimensions|Diameter|Thickness',case,flags=re.I)[0].strip(' ,'),'technical Case')
 size=re.search(r'Dimensions\s*\(L x W\):\s*([\d.,]+)\s*x\s*([\d.,]+)\s*mm',case,re.I)
 if size:r.set('diameter',size[1]+' x '+size[2].replace(',','.')+' mm','Case dimensions (L x W)');r.set('case_shape','Rectangular','Explicit L x W dimensions');r.set('lug_to_lug',size[1].replace(',','.')+' mm','Case: L : Lug to lug') if 'L : Lug to lug' in case else None
 else:
  size=re.search(r'Diameter\s*:\s*([\d.,]+)\s*mm',case,re.I)
  if size:r.set('diameter',size[1].replace(',','.')+' mm','Case Diameter')
 thickness=re.search(r'Thickness\s*:\s*([\d.,]+)\s*mm',case,re.I)
 if thickness:r.set('case_thickness',thickness[1].replace(',','.')+' mm','Case Thickness')
 for label,key in [('Water resistance','water_resistance'),('Dial','dial_color'),('Strap','bracelet_material'),('Buckle','clasp_type')]:r.set(key,specs.get(label),'Technical '+label)
 for source_key,target_key in [('Recto dial','dial_color'),('Verso dial','dial_color'),('Recto Functions','features'),('Verso Functions','features')]:
  if specs.get(source_key):
   existing=r.data[target_key];r.set(target_key,(existing+'; ' if existing else '')+source_key+': '+specs[source_key],'Technical '+source_key,overwrite=True)
 for labels,key in [(('In-House Calibre',),'caliber'),(('MOVEMENT TYPE','Movement type'),'movement'),(('Power reserve',),'power_reserve'),(('Functions',),'features'),(('Jewels',),'jewels')]:
  for label in labels:
   if label in technical:r.set(key,technical[label],'caliber-block '+label);break
 frequency=technical.get('Frequency (HZ)','')
 if frequency:r.set('frequency',frequency+' Hz','caliber-block Frequency (HZ)')
 elif technical.get('Vibrations per hour'):r.set('frequency',technical['Vibrations per hour']+' vph','caliber-block Vibrations per hour')
 # A few quartz products omit the calibre block; read their explicit accordion movement.
 if not r.data['movement']:
  for key,entries in accordion.items():
   if 'movement' in key or 'calibre' in key:
    for v in entries:
     if re.fullmatch(r'(?:Automatic|Manual winding|Quartz)',v,re.I):r.set('movement',v,'Movement accordion')
 r.data.update(raw_product_fields=selected,raw_specifications=specs,raw_caliber_fields=technical,raw_caliber_block_fields=block_fields,raw_selected_tracking_fields=tracking,raw_accordion_fields=accordion,raw_listing_fields=item,product_detail_parsed=True,hands=specs.get('Hands') or specs.get('Recto hands',''),hands_reverse=specs.get('Verso hands',''),number_of_parts=technical.get('Components',''),movement_diameter=technical.get('DIAMETER') or technical.get('Diameter',''),movement_thickness=technical.get('Thickness',''),case_dimensions_display=case,additional_specifications=[{'label':k,'value':v} for k,v in technical.items() if k not in ['In-House Calibre','MOVEMENT TYPE','Power reserve','Functions','Jewels','Frequency (HZ)','Thickness','DIAMETER','Diameter','Components']],source_field_count=len(selected)+len(specs)+len(technical))
 if specs.get('Strap'):
  strap=specs['Strap'];material=re.search(r'Type of material:\s*(.*?)(?:Color:|Interchangeable:|Standard strand|Lug width:|$)',strap)
  if material:r.set('bracelet_material',material[1].strip(),'Strap Type of material',overwrite=True)
  color=re.search(r'Color:\s*(.*?)(?:Interchangeable:|Standard strand|Lug width:|$)',strap)
  if color:r.set('bracelet_color',color[1].strip(),'Strap Color')
  lug=re.search(r'Lug width:\s*([\d.,]+)\s*mm',strap)
  if lug:r.set('between_lugs',lug[1].replace(',','.')+' mm','Strap Lug width')
 r.data['source_discrepancies']=[{'field':key,'accordion':val,'caliber_block':block_fields[key]} for key,val in technical.items() if key in block_fields and val!=block_fields[key]]
 r.data['additional_specifications'] += [{'label':'Published '+k,'value':v} for k,v in specs.items() if k not in ['Internal reference','Case','Water resistance','Dial','Strap','Buckle','Hands','MOVEMENT TYPE','Functions','Thickness','Vibrations per hour','Frequency (HZ)','Power reserve','Components','Jewels','Barrel']]
 if specs.get('Strap'):r.data['additional_specifications'].append({'label':'Full strap specifications','value':specs['Strap']})
 return r.finalize()


def editorial_watch(body,item):
 root=doc(body);tracking={}
 for script in root.xpath('//script/text()'):
  match=re.search(r'window.Phoenix.trackingVariables\s*=\s*(\{.*?\});',script,re.S)
  if match:tracking=json.loads(match[1]).get('pageProductTrackingInformation',{})
 if not isinstance(tracking,dict):return None
 ref=tracking.get('item_id','')
 if tracking.get('item_category')!='Watches' or not re.fullmatch(r'Q[A-Z0-9]{7}',ref) or not any(ref in x.upper() for x in [first(root,'//title'),*root.xpath('//main//img/@alt')]):return None
 return {**{k:v for k,v in item.items() if k!='reason'},'reference':ref,'reference_source':'Selected watch tracking metadata and explicit reference in title or watch-image alt text'}

"""Omega US: cumulative catalogue HTML and selected watch technical data."""
import json
import re
from urllib.parse import urljoin, urlsplit, parse_qs
from lxml import html
from .schema import Record, clean

ORIGIN = 'https://www.omegawatches.com'
FINDER = ORIGIN+'/en-us/watchfinder'
PRODUCT_PATH = re.compile(r'/en-us/watch-omega-[a-z0-9-]+-(\d{14}|\d{8})/?$')
COLLECTION_PATH = re.compile(r'/en-us/watches/[a-z0-9-]+(?:/[a-z0-9-]+)*/?$')


def tree(body):
    return html.fromstring(body.decode('utf-8') if isinstance(body,bytes) else body)


def text(node):
    return clean(' '.join(node.itertext()))


def first(doc,xpath):
    found=doc.xpath(xpath)
    return text(found[0]) if found else ''


def reference(digits):
    if re.fullmatch(r'\d{8}',digits):
        return '.'.join((digits[:4],digits[4:6],digits[6:]))
    if not re.fullmatch(r'\d{14}',digits):
        raise ValueError('Invalid Omega reference')
    return '.'.join((digits[:3],digits[3:5],digits[5:7],digits[7:9],digits[9:11],digits[11:]))


def product_reference(url):
    p=urlsplit(url);match=PRODUCT_PATH.fullmatch(p.path)
    if p.netloc!='www.omegawatches.com' or not match:
        raise ValueError('Unexpected Omega product URL')
    return reference(match[1])


def catalog_page(body,url,meta=None):
    doc=tree(body)
    counts={int(x) for x in doc.xpath('//*[@data-role="apply-filters"]/@data-count | //*[@id="product-list-count"]//*[@data-count]/@data-count')}
    current={int(x) for x in doc.xpath('//*[@data-role="list-pager"]/@data-current')}
    if len(counts)!=1 or len(current)!=1:
        raise ValueError('Missing or conflicting Omega catalogue total/page')
    expected,page=counts.pop(),current.pop()
    if page!=int(parse_qs(urlsplit(url).query).get('p',['1'])[0]):
        raise ValueError('Returned catalogue page differs from requested page')
    items=[]
    for card in doc.xpath('//*[@id="product-list-grid"]//li[contains(concat(" ",normalize-space(@class)," ")," product-item ")]'):
        digits=card.get('data-sku','')
        urls=list(dict.fromkeys(urljoin(url,x) for x in card.xpath('.//a/@href') if PRODUCT_PATH.fullmatch(urlsplit(urljoin(url,x)).path)))
        if len(urls)!=1 or product_reference(urls[0])!=reference(digits):
            raise ValueError('Catalogue card reference/URL mismatch')
        tracking=card.xpath('.//*[@data-product-dl]/@data-product-dl')
        items.append({'reference':reference(digits),'url':urls[0],'raw_listing_fields':{
            'product_id':card.get('data-id'),'collection':first(card,'.//*[contains(concat(" ",@class," ")," collection ")]'),
            'name':first(card,'.//*[contains(concat(" ",@class," ")," name ")]'),
            'image_urls':card.xpath('.//img/@data-img'),'tracking':json.loads(tracking[0]) if tracking else {}}})
    if len(items)!=len({x['reference'] for x in items}):
        raise ValueError('Duplicate references inside catalogue page')
    if len(items)!=min(expected,page*24):
        raise ValueError(f'Incomplete cumulative catalogue page: {len(items)} cards')
    next_urls=list(dict.fromkeys(urljoin(url,x) for x in doc.xpath('//*[@data-role="ajax-pager" and @data-target="next"]/@href')))
    if len(next_urls)>1:
        raise ValueError('Conflicting next-page links')
    for target in next_urls:
        p=urlsplit(target)
        if p.netloc!=urlsplit(url).netloc or p.path!=urlsplit(url).path or parse_qs(p.query)!={'p':[str(page+1)]}:
            raise ValueError('Unexpected catalogue pagination link')
    if bool(next_urls)!=(len(items)<expected):
        raise ValueError('Next-page link disagrees with catalogue total')
    return {'expected':expected,'page':page,'items':items,'next':next_urls[0] if next_urls else '',
            'source_hash':(meta or {}).get('sha256','')}


def collection_roots(body):
    return list(dict.fromkeys(x for x in tree(body).xpath('//a/@href') if urlsplit(x).netloc=='www.omegawatches.com'
        and re.fullmatch(r'/en-us/watches/[a-z0-9-]+/?',urlsplit(x).path)))


def finder_totals(body):
    doc=tree(body)
    total={int(x) for x in doc.xpath('//*[@data-role="apply-filters"]/@data-count')}
    if len(total)!=1: raise ValueError('Watch finder total unavailable')
    groups={}
    for node in doc.xpath('//*[@data-filter-code="filter_collection_subcollection" and not(@data-filter-parent-value)]'):
        name=node.get('data-gio-value');count=int(re.search(r'(\d+)\s*$',text(node))[1])
        if name in groups and groups[name]!=count: raise ValueError('Conflicting collection filter totals')
        groups[name]=count
    if sum(groups.values())!=next(iter(total)): raise ValueError('Collection filters do not reconcile to finder total')
    return next(iter(total)),groups


SPEC_MAP={
    'sku':'reference_number','watch_between_lugs_size':'between_lugs','watch_lug_to_lug':'lug_to_lug',
    'watch_thickness':'case_thickness','watch_casediameter':'diameter','watch_watchcase':'case_material',
    'watch_dial':'dial_color','watch_crystal':'crystal','watch_waterresistance':'water_resistance',
    'watch_case_weight':'weight','caliber_product_caliber_option_id':'caliber','caliber_movement_label':'movement',
    'caliber_power_reserve':'power_reserve','strap_materials':'bracelet_material','strap_clasp_type':'clasp_type',
    'strap_color':'bracelet_color','strap_color_list':'bracelet_color','buckle_type':'clasp_type',
    'watch_dial_detailed_color':'dial_color','watch_caseback':'caseback','short_description':'short_description','description':'description',
}


def product(body,url,listing=None,meta=None):
    doc=tree(body);expected=product_reference(url)
    canonical=doc.xpath('//link[@rel="canonical"]/@href')
    if len(canonical)!=1 or product_reference(canonical[0])!=expected: raise ValueError('Canonical product reference mismatch')
    specs={}
    for node in doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," technical-data-value ") and @data-code]'):
        code,value=node.get('data-code'),text(node)
        if code in specs and specs[code]!=value: raise ValueError('Conflicting selected technical values: '+code)
        specs[code]=value
    if specs.get('sku')!=expected: raise ValueError('Technical panel belongs to a different watch')
    schemas=[json.loads(s.text) for s in doc.xpath('//script[@type="application/ld+json"]')]
    selected=[x for x in schemas if x.get('@type')=='Product' and x.get('url')==canonical[0]]
    if len(selected)!=1: raise ValueError('Selected Product JSON-LD unavailable')
    schema=selected[0];title=doc.xpath('//h1')[0]
    headings={key:first(title,'.//*[contains(concat(" ",@class," ")," '+key+' ")]') for key in ('collection','subcollection','name')}
    tags=list(dict.fromkeys(text(x) for x in doc.xpath('//button[contains(concat(" ",@class," ")," ow-tags ")]') if text(x)))
    meta=meta or {}
    r=Record('Omega',canonical[0],'US','en',meta.get('sha256',''),meta.get('fetched_at'))
    for code,value in specs.items():
        if code in SPEC_MAP:
            r.set(SPEC_MAP[code],value,'technical-data-value[data-code="'+code+'"]',overwrite=code=='watch_dial_detailed_color')
    decoded_description=''
    if re.fullmatch(r'[01]{8}(?:\s+[01]{8})+',specs.get('description','')):
        decoded_description=bytes(int(x,2) for x in specs['description'].split()).decode('utf-8')
        r.set('description',decoded_description,'technical-data-value[data-code="description"] decoded UTF-8 binary text',overwrite=True)
    # Some release pages omit the calibre panel while stating it in prose.
    if not r.data['caliber']:
        calibres=set(re.findall(r'\b(?:Calibre|Caliber)\s+(\d{3,4})\b',r.data['description'],re.I))
        if len(calibres)==1:
            r.set('caliber','Omega '+next(iter(calibres)),'selected product description explicit calibre number')
    r.set('type','Pocket watch' if 'Pocket Watch' in headings['subcollection'] else 'Wristwatch','h1 .subcollection')
    r.set('parent_model',headings['collection'],'h1 .collection')
    r.set('specific_model',' '.join(x for x in (headings['collection'],headings['subcollection'],headings['name']) if x),'h1')
    r.set('features',tags,'button.ow-tags')
    for tag in tags:
        if 'caseback' in tag.lower(): r.set('caseback',tag,'button.ow-tags')
    movement_indicators={}
    for node in doc.xpath('//li[contains(@class,"ow-mod_37__picto--")]'):
        kind=next(x.split('ow-mod_37__picto--',1)[1] for x in node.get('class').split() if 'ow-mod_37__picto--' in x)
        value=text(node)
        if kind in movement_indicators and movement_indicators[kind]!=value:
            raise ValueError('Conflicting selected movement indicators')
        movement_indicators[kind]=value
    frequency=re.search(r'(\d+(?:[.,]\d+)?)\s*Hz\b',movement_indicators.get('frequency',''),re.I)
    if frequency: r.set('frequency',frequency[1]+' Hz','li.ow-mod_37__picto--frequency')
    offers=schema.get('offers') or {}
    if isinstance(offers,list): offers=next((o for o in offers if o.get('sku')==expected),{})
    if offers.get('sku') and offers['sku']!=expected: raise ValueError('Selected structured offer SKU mismatch')
    if offers.get('price') is not None:
        r.set('price',offers['price'],'selected Product JSON-LD offers.price')
        r.set('currency',offers.get('priceCurrency'),'selected Product JSON-LD offers.priceCurrency')
    source_image=schema.get('image','')
    if isinstance(source_image,str) and urlsplit(source_image).scheme=='https':
        r.set('image_URL',source_image,'selected Product JSON-LD image')
    else:
        r.data['extraction_warnings'].append('Selected Product JSON-LD has no usable image URL')
    if 'Swiss Made' in first(doc,'//main'): r.set('made_in','Switzerland','product page Swiss Made statement')
    tracking=[]
    for node in doc.xpath('//*[@data-product-dl and @data-real-sku]'):
        if node.get('data-real-sku')==expected.replace('.',''):
            value=json.loads(node.get('data-product-dl'))
            if value not in tracking: tracking.append(value)
            r.set('marketing_name',node.get('data-marketing'),'selected tracking-data data-marketing')
    # A heading is omitted where family and subcollection would repeat.
    # Read the selected product's explicit taxonomy, rather than guessing it.
    for value,locator in [(x,'selected tracking ecommerce.items.item_category2') for x in tracking]+[
            ((listing or {}).get('raw_listing_fields',{}).get('tracking',{}),'catalogue tracking ecommerce.items.item_category2')]:
        for item in value.get('ecommerce',{}).get('items',[]):
            if str(item.get('item_id','')).replace('.','')==expected.replace('.',''):
                r.set('parent_model',item.get('item_category2'),locator)
    image_values=doc.xpath('//*[@data-code]//img/@data-img | //*[@data-code]//img/@data-srcset-link | //*[@data-code]//img/@src | //*[@data-code]//source/@data-srcset | //*[@data-code]//source/@srcset')
    images=list(dict.fromkeys(v.strip().split(' ')[0] for x in image_values for v in x.split(',')))+[schema.get('image','')]
    images=list(dict.fromkeys(x for x in images if x.startswith('https://') and expected.replace('.','') in x))
    if images and not r.data['image_URL']:
        r.set('image_URL',images[0],'selected product gallery image')
    variants=list(dict.fromkeys(x for x in doc.xpath('//a/@href') if PRODUCT_PATH.fullmatch(urlsplit(x).path) and x!=canonical[0] and urlsplit(x).netloc=='www.omegawatches.com'))
    r.data.update(raw_specifications=specs,source_product_fields={'technical':specs,'headings':headings,'features':tags,
        'structured_product':schema,'selected_tracking':tracking,'movement_indicators':movement_indicators,
        'movement_description':first(doc,'//*[contains(concat(" ",@class," ")," caliber-text ")]'),
        'decoded_description':decoded_description},
        raw_listing_fields=(listing or {}).get('raw_listing_fields',{}),source_field_count=len(specs),product_detail_parsed=True,
        image_urls=images,variant_urls=variants,
        collection_label=' '.join(dict.fromkeys(x for x in (r.data['parent_model'],headings['subcollection']) if x)))
    if listing and listing['reference']!=expected: raise ValueError('Listing/detail reference mismatch')
    return r.finalize()

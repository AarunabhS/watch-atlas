"""Parser for Breitling's live-observed Next.js catalog and selected product."""
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin, urlsplit, parse_qs

from lxml import html
from .schema import Record, clean

ORIGIN = 'https://www.breitling.com'
FINDER = ORIGIN + '/us-en/watches/all/'
PRODUCT_PATH = re.compile(r'^/us-en/watches/[^/]+/[^/]+/([A-Z0-9]{10,})/?$', re.I)


def page_data(body):
    doc = html.fromstring(body)
    data = doc.xpath('//script[@id="__NEXT_DATA__"]/text()')
    if not data:
        raise ValueError('Expected public __NEXT_DATA__ missing; Breitling template changed')
    return doc, json.loads(data[0])['props']['pageProps']


def text(value):
    value = clean(value)
    if '<' in value and '>' in value:
        value = clean(' '.join(html.fragment_fromstring(value, create_parent='div').itertext()))
    return value


def attribute(node):
    if not isinstance(node, dict):
        return text(node)
    values = []
    for value in node.get('values') or []:
        translation = value.get('translation') or {}
        # translation.name is often an internal identifier, not display wording.
        display = translation.get('plainText') or value.get('plainText') or value.get('name') or value.get('value')
        if display is not None:
            values.append(text(display))
    return '; '.join(x for x in values if x)


def positive_amount(value):
    try:
        number = Decimal(str(value))
        return number if number.is_finite() and number > 0 else None
    except InvalidOperation:
        return None


def catalog_page(body, url, meta):
    doc, props = page_data(body)
    candidates = [r for entry in props.get('serverState',{}).get('initialResults',{}).values()
                  for r in entry.get('results',[]) if 'hits' in r and 'nbPages' in r]
    if len(candidates) != 1:
        raise ValueError('Expected one watch listing result in server-rendered page')
    result = candidates[0]
    if meta.get('kind') == 'rendered_dom':
        cards=doc.xpath('//*[@data-test-id="ListingHitsWatchesGrid"]//*[@data-testid="productCard"]')
        items=[]
        for card in cards:
            a=card.xpath('.//a[@data-testid="ProductCard"]')[0]
            target=urljoin(ORIGIN,a.get('href'))
            match=PRODUCT_PATH.fullmatch(urlsplit(target).path)
            if not match or urlsplit(target).netloc!='www.breitling.com' or urlsplit(target).scheme!='https':
                raise ValueError('Unexpected rendered product link')
            sku=card.xpath('.//*[@data-test-id="Sku"]')[0].text_content().strip()
            if match[1].upper()!=sku.upper():
                raise ValueError('Rendered card identity mismatch')
            def content(name):
                nodes=card.xpath('.//*[@data-test-id=$name]',name=name)
                return clean(nodes[0].text_content()) if nodes else ''
            hit={'objectID':sku,'product_type':'Watch','name_en':content('Name'),
                 'displayed_price':content('Price'),'published_href':a.get('href')}
            items.append({'reference':sku,'url':target,'catalog_page_url':url,'catalog_source_hash':meta['sha256'],
                          'catalog_snapshot_file':meta['file'],'catalog_representation':'rendered_dom','raw_listing_fields':hit})
        number=int(parse_qs(urlsplit(url).query).get('page',['1'])[0])-1
        return {'page':number,'pages':result['nbPages'],'expected':result['nbHits'],'items':items,'pagination':[], 'source_hash':meta['sha256']}
    links = {}
    pagination = set()
    for a in doc.xpath('//a[@href]'):
        target = urljoin(ORIGIN,a.get('href')).split('#')[0]
        p = urlsplit(target)
        if p.netloc != 'www.breitling.com' or p.scheme != 'https':
            continue
        if match := PRODUCT_PATH.fullmatch(p.path):
            links[match[1].upper()] = target
        if (a.get('aria-label') or '').startswith('Go to page') and p.path == '/us-en/watches/all/':
            pagination.add(target)
    items = []
    for hit in result['hits']:
        if hit.get('product_type') != 'Watch':
            raise ValueError('Non-watch item in all-watches results')
        ref = hit['objectID']
        if ref.upper() not in links:
            raise ValueError('No published watch URL for listing reference ' + ref)
        items.append({'reference':ref, 'url':links[ref.upper()], 'catalog_page_url':url,
                      'catalog_source_hash':meta['sha256'], 'raw_listing_fields':hit})
    return {'page':result['page'], 'pages':result['nbPages'], 'expected':result['nbHits'],
            'items':items, 'pagination':sorted(pagination), 'source_hash':meta['sha256']}


def technical_table(doc):
    sections = doc.xpath('//*[@data-testid="sectionTechnicalData"]')
    if len(sections) != 1:
        raise ValueError('Expected selected watch technical section missing or ambiguous')
    result = {}
    for section in sections[0].xpath('.//*[@data-test-id="Section"]'):
        headings = section.xpath('.//*[@data-test-id="SectionTitle"]')
        if not headings:
            continue
        name = clean(headings[0].text_content())
        result[name] = {}
        for row in section.xpath('.//*[starts-with(@data-test-id,"NameValueWrapper-")]'):
            labels = row.xpath('.//*[starts-with(@data-test-id,"Name-")]')
            values = row.xpath('.//*[starts-with(@data-test-id,"Value-")]')
            if labels and values:
                result[name][clean(labels[0].text_content())] = clean(values[0].text_content())
    return result


def product(body, url, listing, meta):
    doc, props = page_data(body)
    variant = props.get('productVariant') or {}
    expected = listing['reference']
    source_reference = PRODUCT_PATH.fullmatch(urlsplit(url).path)
    if not source_reference or source_reference[1].upper() != expected.upper():
        raise ValueError('Product URL identity disagrees with catalog reference')
    if variant.get('sku','').upper() != expected.upper():
        raise ValueError(f'Identity mismatch: expected {expected}, found {variant.get("sku")}')
    raw = variant['product']
    if (raw.get('productType') or {}).get('slug') != 'watch':
        raise ValueError('Selected product is not a watch')
    structured = props.get('productStructuredData') or {}
    if structured and structured.get('sku','').upper() != expected.upper():
        raise ValueError('Structured product identity disagrees with selected variant')
    technical = technical_table(doc)
    r = Record('Breitling',url,'US','en',meta['sha256'],meta.get('fetched_at'))
    r.set('reference_number',variant['sku'],'pageProps.productVariant.sku')
    for target,source in [('parent_model','collectionName'),('specific_model','watchName'),
                          ('marketing_name','watchName'),('case_material','caseMaterial'),
                          ('caseback','caseback'),('water_resistance','waterResistance'),
                          ('dial_color','dialColor'),('bracelet_material','strapMaterial'),
                          ('bracelet_color','strapColor'),('clasp_type','buckleType'),
                          ('movement','movement'),('caliber','caliber'),
                          ('power_reserve','powerReserve'),('frequency','vibration'),
                          ('jewels','jewel'),('crystal','crystal'),('description','modelStory')]:
        r.set(target,attribute(raw.get(source)), 'productVariant.product.' + source)
    r.set('specific_model',raw.get('name'),'productVariant.product.name')
    r.set('description',structured.get('description'),'productStructuredData.description')
    r.data['strap_color_label'] = attribute(raw.get('strapColor'))
    if r.data['bracelet_color'].lower() == 'metal bracelet':
        r.data['bracelet_color'] = ''
        r.data['provenance'].pop('bracelet_color',None)
        r.data['extraction_warnings'].append('Published strap color label describes a metal bracelet, without a color')
    categories = attribute(raw.get('comCategories')).split('; ')
    gender = [x for x in categories if x.lower() in ('men','women','ladies','unisex')]
    r.set('type','; '.join(gender),'productVariant.product.comCategories (explicit audience)')
    for label,target in [('Diameter','diameter'),('Thickness','case_thickness'),
                         ('Lug width (in-between lug)','between_lugs'),('Product weight (approx.)','weight')]:
        r.set(target,technical.get('Dimensions',{}).get(label),'sectionTechnicalData.Dimensions.' + label)
    # Product and watch-head weights are separate; weight's G unit is published
    # in the product attribute. Dimension CM units are not trusted over the table.
    if not r.data['weight']:
        value = attribute(raw.get('weight'))
        if value and re.fullmatch(r'\d+(?:\.\d+)?',value) and positive_amount(value) is not None and (raw.get('weight') or {}).get('attribute',{}).get('unit') == 'G':
            r.set('weight',format(Decimal(value),'f') + ' g','productVariant.product.weight (published G unit)')
    launch = attribute(raw.get('launchDate'))
    for fmt in ('%d.%m.%Y','%Y-%m-%d','%d/%m/%Y'):
        try:
            year = datetime.strptime(launch,fmt).year
            r.set('year_introduced',year,'productVariant.product.launchDate (explicit launch year)')
            break
        except ValueError:
            pass
    r.data['launch_date'] = launch
    price = ((variant.get('pricing') or {}).get('price') or {}).get('gross') or {}
    if (amount := positive_amount(price.get('amount'))) is not None and price.get('currency'):
        r.set('price',format(amount,'f'),'productVariant.pricing.price.gross.amount')
        r.set('currency',price['currency'],'productVariant.pricing.price.gross.currency')
    offers = structured.get('offers') or []
    if isinstance(offers,dict):
        offers = [offers]
    if not r.data['price']:
        matching = [x for x in offers if positive_amount(x.get('price')) is not None and x.get('priceCurrency')
                    and (not x.get('url') or urlsplit(x['url']).path.rstrip('/') == urlsplit(url).path.rstrip('/'))]
        if len(matching) == 1:
            r.set('price',matching[0]['price'],'productStructuredData.offers.price')
            r.set('currency',matching[0]['priceCurrency'],'productStructuredData.offers.priceCurrency')
    r.data['offers'] = offers
    r.data['pricing_fields'] = variant.get('pricing')
    r.data['price_status'] = 'published US-market price' if r.data['price'] else 'price not published for selected reference'
    # The displayed US price is labelled Excl. Sales Tax on observed pages.
    r.data['price_tax_label'] = 'Excl. Sales Tax' if 'Excl. Sales Tax' in doc.text_content() else ''
    seo = props.get('seoConfig') or {}
    r.set('short_description',text(seo.get('seoDescription')),'pageProps.seoConfig.seoDescription')
    swiss = doc.xpath('//*[@data-test-id="KeyFeaturesSectionSwissMade"]')
    if swiss:
        r.set('made_in','Switzerland','published Swiss Made label')
    functions = []
    for key,label in [('chronograph','Chronograph'),('calendar','Calendar')]:
        if value := attribute(raw.get(key)):
            functions.append(label + ': ' + value)
    r.set('features','; '.join(functions),'productVariant.product.chronograph/calendar')
    images = [x['url'] for x in raw.get('mediaLarge') or raw.get('media') or [] if x.get('url')]
    thumb = (raw.get('thumbnail') or {}).get('url')
    r.set('image_URL',thumb or (images[0] if images else ''),'productVariant.product.thumbnail/mediaLarge')
    r.data['image_urls'] = list(dict.fromkeys(([thumb] if thumb else []) + images))
    for key in ('strapName','headWeight','bezel','crown','strapType','lug','buckleMaterial','buckleSize',
                'warrantyDuration','warrantyExtensionDuration','movementManufacture','marketingStatus',
                'marketingPartner','marketingCampaign','distributionStatus','bundleVariations','manualUrl'):
        r.data[key] = attribute(raw.get(key))
    limited_values = (raw.get('limited') or {}).get('values') or []
    r.data['limited_edition'] = next((x['boolean'] for x in limited_values if isinstance(x.get('boolean'),bool)),None)
    r.data['related_reference_numbers'] = [x.get('name') for x in (raw.get('relatedProducts') or {}).get('values') or [] if x.get('name')]
    r.data['raw_product_fields'] = raw
    r.data['raw_variant_fields'] = {key:value for key,value in variant.items() if key != 'product'}
    r.data['raw_structured_product'] = structured
    r.data['raw_listing_fields'] = listing['raw_listing_fields']
    r.data['catalog_page_url'] = listing['catalog_page_url']
    r.data['catalog_source_hash'] = listing['catalog_source_hash']
    r.data['catalog_representation'] = listing.get('catalog_representation','server_rendered_results')
    r.data['catalog_snapshot_file'] = listing.get('catalog_snapshot_file','')
    r.data['raw_technical_table'] = technical
    r.data['raw_specifications'] = {key:[attribute(value)] for key,value in raw.items() if isinstance(value,dict) and 'values' in value and attribute(value)}
    r.data['source_field_count'] = len(raw)
    r.data['dataset_usage'] = 'local personal non-commercial research'
    r.data['extraction_method'] = 'public page __NEXT_DATA__, selected productVariant and visible technical table'
    r.data['source_discrepancies'] = []
    for key,label in [('diameter','Diameter'),('thickness','Thickness'),('lugWidth','Lug width (in-between lug)')]:
        unit = (raw.get(key) or {}).get('attribute',{}).get('unit')
        display = technical.get('Dimensions',{}).get(label,'')
        if unit == 'CM' and display.endswith('mm'):
            r.data['source_discrepancies'].append({'field':key,'cms_unit':unit,'display_value':display,'selected':'display_value'})
    business = (props.get('businessData') or {}).get('productVariant') or {}
    if business.get('sku') == variant['sku']:
        r.data['availability'] = business
    r.data['product_detail_parsed'] = True
    return r.finalize()

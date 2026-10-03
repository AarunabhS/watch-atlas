"""Patek's observed October 2026 Next.js/Sitecore page structure.

Read only the WatchFinder and ProductDetail components. Header navigation and
ProductSimilarModels are deliberately excluded from current-watch extraction.
"""
import json
import re
from datetime import datetime
from urllib.parse import urljoin
from lxml import html
from .schema import Record, clean

ORIGIN = 'https://www.patek.com'
FINDER = ORIGIN + '/en/collection/watch-finder'


def page_components(body):
    doc = html.fromstring(body)
    scripts = doc.xpath('//script[@id="__NEXT_DATA__"]/text()')
    if not scripts:
        raise ValueError('Expected __NEXT_DATA__ missing; site template changed')
    data = json.loads(scripts[0])
    route = data['props']['pageProps']['layoutData']['sitecore']['route']
    return doc, route, route['placeholders']['headless-main']


def text(value):
    value = clean(value)
    if '<' in value and '>' in value:
        fragment = html.fragment_fromstring(value, create_parent='div')
        return clean(' '.join(fragment.itertext()))
    return value


def field(node):
    if not isinstance(node, dict):
        return node
    node = node.get('jsonValue', node)
    if isinstance(node, dict):
        if 'value' in node:
            return node['value']
        if 'fields' in node:
            fields = node['fields']
            return fields.get('Name', fields.get('Attribute Value', {})).get('value', '')
    return node


def catalog(body, as_of):
    _, _, components = page_components(body)
    watches = next(c['fields']['watches'] for c in components if c['componentName'] == 'WatchFinder')
    # CMS dates have no offset. At this date the displayed current count matches
    # the calendar comparison; preserve the originals, do not invent an offset.
    cutoff = datetime.fromisoformat(as_of).replace(tzinfo=None)
    selected, other = [], []
    for watch in watches:
        available = watch.get('availableDate')
        run_out = watch.get('runOutDate')
        active = (not available or datetime.fromisoformat(available).replace(tzinfo=None) <= cutoff) and (not run_out or datetime.fromisoformat(run_out).replace(tzinfo=None) > cutoff)
        (selected if active else other).append(watch)
    return selected, other


def product(body, url, listing, meta):
    doc, route, components = page_components(body)
    details = next(c for c in components if c['componentName'] == 'ProductDetail')
    raw = details['fields']['data']['datasource']
    values = {key:field(value) for key, value in raw.items()}
    expected = listing['articleRef']
    if values.get('reference', '').upper() != expected.upper():
        raise ValueError(f'Identity mismatch: expected {expected}, found {values.get("reference")}')
    r = Record('Patek Philippe', url, 'international', 'en', meta['sha256'], meta.get('fetched_at'))
    def set_field(target, source):
        value = values.get(source)
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            r.set(target, text(value), 'ProductDetail.datasource.' + source)
    for target, source in [
        ('reference_number','reference'), ('parent_model','collection'), ('specific_model','watchFamily'),
        ('marketing_name','marketingTitle'), ('type','gender'), ('case_shape','caseShape'),
        ('case_material','material'), ('case_thickness','caseHeight'), ('diameter','caseDimension'),
        ('caseback','backgroundType'), ('water_resistance','waterResistance'),
        ('dial_color','backgroundAndTimeCircle'), ('caliber','caliberCode'), ('movement','mechanism'),
        ('power_reserve','powerReserve'), ('frequency','frequency'), ('jewels','numberOfRubis'),
        ('features','complicationsBulletPoints'), ('description','marketingText'),
        ('bracelet_material','strapOriginallyFitted'), ('clasp_type','foldOverClasp'),
    ]:
        set_field(target, source)
    if values.get('subtype', listing.get('subtype')) == 'Pocketwatch':
        r.set('water_resistance', text(values.get('pocketWaterResistance')),
              'ProductDetail.datasource.pocketWaterResistance', overwrite=True)
    for key in ('rhcMarketingTitle', 'marketingTitle', 'reference'):
        set_field('specific_model', key)
    set_field('marketing_name', 'rhcMarketingTitle')
    if not r.data['description']:
        set_field('description', 'rhcMarketingText')
    set_field('features', 'mainComponent')
    set_field('bracelet_material', 'metalBraceletMaterial')
    set_field('bracelet_material', 'strapMaterial')
    for key in ('prongBuckle', 'foldOverClaspMetalBracelet'):
        set_field('clasp_type', key)
    set_field('frequency', 'quartzFrequency')
    seo = route['fields'].get('SeoDescription', {}).get('value')
    r.set('short_description', text(seo), 'route.fields.SeoDescription')
    # A CMS publication/availability date is not necessarily an introduction year.
    r.data['available_date'] = values.get('availableDate', '')
    r.data['run_out_date'] = values.get('runOutDate', '')
    r.data['subtype'] = values.get('subtype', listing.get('subtype', ''))
    r.data['catalog_collection'] = listing.get('collectionName', '')
    r.data['limited_edition'] = values.get('limitedEdition')
    r.data['movement_diameter'] = text(values.get('diamTotal'))
    r.data['movement_thickness'] = text(values.get('thickness'))
    r.data['case_dimensions_display'] = text(values.get('caseDimensionDisplay'))
    r.data['crown'] = text(values.get('crownType'))
    r.data['hands'] = text(values.get('needleFunction1'))
    r.data['hands_reverse'] = text(values.get('needleFunction2'))
    r.data['case_decoration'] = text(values.get('caseDecor'))
    r.data['power_source'] = text(values.get('powerSource'))
    r.data['bracelet_adjustment'] = text(values.get('adjustmentSystem'))
    r.data['pocket_chain_or_stand'] = text(values.get('pocketChainOrStand'))
    r.data['pocket_bow'] = text(values.get('pocketBow'))
    r.data['pocket_crown'] = text(values.get('pocketCrown'))
    r.data['number_of_parts'] = text(values.get('numberOfComponents'))
    r.data['number_of_bridges'] = text(values.get('numberOfBridges'))
    # The visible movement panel uses the Display value. Some pages retain a
    # different older count in the base CMS field; retain and flag both.
    r.data['source_discrepancies'] = []
    parts_display = text(values.get('numberOfComponentsDisplay'))
    if parts_display:
        display_count = parts_display.partition(':')[2].strip() if ':' in parts_display else parts_display
        if display_count != r.data['number_of_parts']:
            r.data['source_discrepancies'].append({
                'field':'number_of_parts', 'cms_value':r.data['number_of_parts'],
                'display_value':display_count, 'selected':'display_value',
            })
        r.data['number_of_parts'] = display_count
    r.data['additional_strap'] = text(values.get('additionalStrap'))
    r.data['dial_hue_label'] = text(values.get('dialHue'))
    r.data['gem_setting'] = text(values.get('gemSettings'))
    r.data['balance_wheel'] = text(values.get('balanceWheel'))
    r.data['balance_spring'] = text(values.get('spiral'))
    r.data['winding_rotor'] = text(values.get('windingRotor'))
    r.data['quality_seal'] = text(values.get('punch'))
    r.data['raw_product_fields'] = raw
    r.data['raw_listing_fields'] = listing
    r.data['dataset_usage'] = 'local personal non-commercial research'
    r.data['extraction_method'] = 'public page __NEXT_DATA__, ProductDetail.datasource'
    r.data['source_field_count'] = len(raw)
    r.data['raw_specifications'] = {key:[text(value)] for key,value in values.items() if isinstance(value,(str,int,float)) and not isinstance(value,bool) and text(value)}
    keypoints = []
    def collect_points(node):
        if isinstance(node, dict):
            if node.get('name') == 'KeyPointText':
                value = text(field(node))
                if value:
                    keypoints.append(value)
            for value in node.values():
                collect_points(value)
        elif isinstance(node, list):
            for value in node:
                collect_points(value)
    collect_points(raw.get('keypoints', {}))
    r.data['keypoints'] = list(dict.fromkeys(keypoints))
    # Keep explicit technical claims from the product's own detail captions.
    for point in keypoints:
        if re.search(r'\b(?:sapphire crystal|sapphire glass)\b', point, re.I) and not re.search(r'case.?back', point, re.I):
            r.set('crystal', point, 'ProductDetail.keypoints.KeyPointText')
        for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z])', point):
            if re.search(r'\b(?:case|lugs)\b', sentence, re.I):
                finish = r'\b(?:hand[- ]polished|polished|satin[- ]finished|satin|brushed)(?:\s*(?:and|,|/)\s*(?:hand[- ]polished|polished|satin[- ]finished|satin|brushed))*(?:\s+finishes?)?\b'
                if match := re.search(finish, sentence, re.I):
                    r.set('case_finish', match[0], 'ProductDetail.keypoints.KeyPointText (explicit case finish)')
    for sentence in re.split(r'[.;]', r.data['dial_color']):
        if re.search(r'\b(?:numerals|hour markers)\b', sentence, re.I):
            r.set('numerals', sentence.strip(), 'ProductDetail.backgroundAndTimeCircle (marker clause)')
    # Colors are only taken from an explicit strap clause, never from a metal
    # name such as "white gold" or from the watch's dial color.
    strap = text(values.get('strapOriginallyFitted'))
    for clause in strap.split(',')[1:]:
        if re.search(r'\b(?:black|white|blue|green|red|brown|gr[ae]y|taupe|beige|purple|pink|orange|yellow)\b', clause, re.I) and not re.search(r'\b(?:gold|steel|platinum)\b', clause, re.I):
            r.set('bracelet_color', clause.strip(), 'ProductDetail.strapOriginallyFitted (explicit color clause)')
    # Use actual rendered display URLs, not Photoshop source assets.
    front = values.get('frontPicture') or {}
    front_title = front.get('title') if isinstance(front, dict) else None
    if front_title:
        images = doc.xpath('//main//img[@alt=$title]/@src', title=front_title)
        if images:
            r.set('image_URL', images[0], 'ProductDetail front image, rendered img[src]')
    if not r.data['image_URL']:
        r.set('image_URL', front.get('src') if isinstance(front, dict) else '', 'ProductDetail.frontPicture.src')
    normalized = re.sub(r'[^A-Z0-9]', '', expected.upper())
    for image in doc.xpath('//main//img[@src]'):
        alt = re.sub(r'[^A-Z0-9]', '', image.get('alt','').upper())
        if alt.startswith('PP' + normalized):
            r.data['image_urls'].append(image.get('src'))
    r.data['image_urls'] = list(dict.fromkeys(r.data['image_urls']))
    # Raw field assets preserve movement photos/video/manual links as well.
    r.data['price_status'] = 'not published in this retrieved public page'
    r.data['product_detail_parsed'] = True
    return r.finalize()

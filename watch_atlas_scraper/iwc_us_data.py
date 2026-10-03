"""Parse the current IWC US public catalogue and selected watch specifications."""
import json
import re
from urllib.parse import urlsplit

from lxml import html

from .schema import Record, clean

ORIGIN = 'https://www.iwc.com'
CATALOG = ORIGIN + '/us-en/watches'
PRODUCT = re.compile(r'/us-en/watches/([a-z0-9-]+)/iw(\d{6})-[a-z0-9-]+$')


def official(url, listing=False):
    u = urlsplit(url)
    return u.scheme == 'https' and u.netloc == 'www.iwc.com' and not u.query and not u.fragment and (u.path == '/us-en/watches' if listing else bool(PRODUCT.fullmatch(u.path)))


def cls(name):
    return 'contains(concat(" ",normalize-space(@class)," ")," ' + name + ' ")'


def text(node, path):
    found = node.xpath(path)
    return clean(found[0].text_content() if found and hasattr(found[0], 'text_content') else found[0] if found else '')


def catalogue(body):
    doc = html.fromstring(body)
    items, counts = {}, {}
    for grid in doc.xpath('//*[' + cls('phoenix-mixed-grid') + ']'):
        family = text(grid, './/h1')
        count_text = text(grid, './/div[contains(text(),"Products")]')
        expected = int(re.fullmatch(r'(\d+) Products', count_text)[1])
        cards = grid.xpath('.//*[@data-cy="mixed-grid-item" and @iswatches="true"]')
        if not family or len(cards) != expected:
            raise ValueError('Published collection count mismatch: ' + family)
        counts[family] = expected
        for card in cards:
            link = card.xpath('.//a[@data-tracking and contains(@href,"/iw")]')[0]
            url = link.get('href')
            if not official(url):
                raise ValueError('Invalid published IWC product URL: ' + url)
            tracking = json.loads(link.get('data-tracking'))['ecommerce']['items'][0]
            ref = tracking['item_id']
            if ref != 'IW' + PRODUCT.fullmatch(urlsplit(url).path)[2] or ref in items:
                raise ValueError('Duplicate or inconsistent catalogue reference: ' + ref)
            price = text(card, './/*[@data-price="value"]')
            currency = text(card, './/*[@data-price="currency"]')
            if price and currency != 'US$':
                raise ValueError('Expected US catalogue prices')
            if price and float(price.replace(',', '')) != float(tracking['price']):
                raise ValueError('Catalogue price and tracking disagree: ' + ref)
            items[ref] = {'reference': ref, 'url': url, 'collection': family,
                          'name': clean(link.text_content()), 'listing_price': price,
                          'listing_currency': currency, 'raw_tracking': tracking,
                          'raw_listing_fields': dict(card.attrib),
                          'listing_images': list(dict.fromkeys(card.xpath('.//img/@src | .//img/@data-src')))}
    if not counts or sum(counts.values()) != len(items):
        raise ValueError('Incomplete IWC catalogue discovery')
    return items, counts


def sections(doc):
    roots = doc.xpath('//*[' + cls('phoenix-product-specs-tabs') + ']/noscript')
    if len(roots) != 1:
        raise ValueError('Complete published specification fallback is missing')
    result = {}
    for heading in roots[0].xpath('.//h2'):
        name = clean(heading.text_content())
        rows = []
        for row in heading.getparent().xpath('.//*[' + cls('phxsg-specs-table__row') + ']'):
            label = text(row, './/*[' + cls('phxsg-specs-table__row-left') + ']')
            value = text(row, './/*[' + cls('phxsg-specs-table__row-right') + ']')
            if label:
                rows.append({'label': label, 'value': value})
        result[name] = rows
    if set(result) != {'Overview', 'Features', 'Case', 'Movement'}:
        raise ValueError('Incomplete IWC specification sections')
    return result


def product(body, url, item, meta):
    if not official(url) or meta['url'] != url:
        raise ValueError('Unexpected product URL or redirect')
    doc = html.fromstring(body)
    canonical = text(doc, '//link[@rel="canonical"]/@href')
    if canonical != url:
        raise ValueError('Canonical product mismatch')
    structured = [json.loads(s) for s in doc.xpath('//script[@type="application/ld+json"]/text()')]
    selected = [x for x in structured if x.get('@type') == 'Product' and x.get('sku') == item['reference']]
    if len(selected) > 1 or any(x.get('@type') == 'Product' for x in structured) and not selected:
        raise ValueError('Selected Product JSON-LD inconsistent or ambiguous')
    selected = selected[0] if selected else {}
    raw = sections(doc)
    overview = {x['label']: x['value'] for x in raw['Overview']}
    case = {x['label']: x['value'] for x in raw['Case']}
    movement = {x['label']: x['value'] for x in raw['Movement']}
    if overview.get('Reference') != item['reference'] or selected and selected.get('mpn') != item['reference']:
        raise ValueError('Specification reference mismatch')
    for key in ('Case', 'Diameter'):
        if overview.get(key) and case.get(key) and overview[key] != case[key]:
            raise ValueError('Overview/Case disagreement: ' + key)
    r = Record('IWC', url, 'US', 'en', meta['sha256'], meta['fetched_at'])
    r.set('type', 'Wristwatch', 'Official wristwatch catalogue')
    r.set('reference_number', item['reference'], 'Overview / Reference, Product sku and canonical URL')
    r.set('parent_model', item['collection'], 'Official catalogue collection heading')
    r.set('specific_model', text(doc, '//main//h1'), 'Selected product H1')
    r.set('case_material', case.get('Case') or overview.get('Case'), 'Case / Case')
    for label, field in [('Diameter', 'diameter'), ('Height', 'case_thickness'), ('Water Resistance', 'water_resistance'), ('Strap width', 'between_lugs'), ('Back case', 'caseback')]:
        r.set(field, case.get(label), 'Case / ' + label)
    r.set('dial_color', overview.get('Dial Color'), 'Overview / Dial Color')
    r.set('movement', overview.get('Movement') or movement.get('Movement type'), 'Overview / Movement')
    for label, field in [('Caliber', 'caliber'), ('Power Reserve', 'power_reserve'), ('Frequency', 'frequency'), ('Jewels', 'jewels')]:
        r.set(field, movement.get(label), 'Movement / ' + label)
    strap = overview.get('Strap', '')
    r.data['strap_description'] = strap
    materials = re.findall(r'alligator leather|calfskin|leather|rubber|stainless steel|steel|titanium|ceratanium®?|ceramic|fabric|textile|18(?:\s|-)?(?:ct|carat|karat)[^,;]*?gold|(?:red|rose|white|yellow) gold', strap, re.I)
    r.set('bracelet_material', list(dict.fromkeys(materials)), 'Explicit material words in Overview / Strap')
    colors = re.findall(r'\b(?:black|white|blue|brown|green|purple|grey|gray|beige|burgundy|pink|orange|red|silver|golden)\b', strap, re.I)
    r.set('bracelet_color', list(dict.fromkeys(colors)), 'Explicit colour words in Overview / Strap')
    features = [x['label'] + (': ' + x['value'] if x['value'] else '') for x in raw['Features']]
    r.set('features', features, 'Features section')
    r.set('crystal', [x for x in features if re.search(r'sapphire glass|sapphire crystal', x, re.I)], 'Features / explicitly described watch glass')
    offers = selected.get('offers') or {}
    if isinstance(offers, list):
        if len(offers) != 1:
            raise ValueError('Ambiguous selected offers')
        offers = offers[0]
    price = text(doc, '//*[@id="tab-overview"]//*[@data-price="value"]')
    currency = text(doc, '//*[@id="tab-overview"]//*[@data-price="currency"]')
    if price:
        if currency != 'US$' or selected and (offers.get('priceCurrency') != 'USD' or float(price.replace(',', '')) != float(offers.get('price', -1))):
            raise ValueError('Visible selected price disagrees with Product offer')
        if item['listing_price'] and float(price.replace(',', '')) != float(item['listing_price'].replace(',', '')):
            raise ValueError('Catalogue/product price mismatch')
        r.set('price', price, 'Selected visible Overview price, validated against Product offer')
        r.set('currency', 'USD', 'Selected visible US$ and Product offer currency')
    elif item['listing_price']:
        raise ValueError('Product price missing despite priced catalogue card')
    gallery = doc.xpath('//main//*[' + cls('product-page-purchase') + ']//img/@data-src | //main//*[' + cls('product-page-purchase') + ']//img/@src')
    images = selected.get('image') or [x for x in gallery if '/product-slideshow-1/' in x]
    if isinstance(images, str):
        images = [images]
    r.data['image_urls'] = list(dict.fromkeys(x for x in images if urlsplit(x).scheme == 'https'))
    r.set('image_URL', r.data['image_urls'][0] if r.data['image_urls'] else '', 'Selected Product JSON-LD image')
    intro = text(doc, '//main//*[' + cls('product-page-purchase__text-card-wrapper') + ']//*[' + cls('text-card__content') + ']')
    short = selected.get('description') or intro
    if '<' in short:
        short = clean(html.fromstring('<div>' + short + '</div>').text_content())
    r.set('short_description', short, 'Selected Product description or purchase-panel introduction')
    editorial = [clean(x.text_content()) for x in doc.xpath('//main//*[' + cls('phxsg-rich-text') + ']//p') if clean(x.text_content())]
    for block in doc.xpath('//main//*[' + cls('rich-text') + '][not(ancestor::*[' + cls('text-card') + ']) and not(ancestor::*[' + cls('modal__content') + '])]'):
        copy = clean(block.text_content())
        if copy and copy not in editorial:
            editorial.append(copy)
    r.set('description', editorial or intro or short, 'Selected product editorial or purchase-panel introduction')
    r.data.update(raw_specifications=raw, source_product_fields={'structured_product': selected, 'structured_data': structured, 'catalogue': item, 'editorial_paragraphs': editorial, 'gallery_images': list(dict.fromkeys(x for x in gallery if x.startswith('https://')))},
                  variant_urls=list(dict.fromkeys(u for u in doc.xpath('//main//a/@href') if official(u) and u != url)),
                  source_representation=meta['representation'], price_note='US suggested retail price; VAT excluded where stated')
    return r.finalize()

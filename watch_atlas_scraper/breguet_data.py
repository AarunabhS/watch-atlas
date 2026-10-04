"""Selected-reference extraction from public Breguet product documents."""
import json
import re
from urllib.parse import urljoin, urlsplit

from lxml import html

from .schema import Record, clean


def norm_ref(value):
    return re.sub(r'[^A-Z0-9]', '', (value or '').upper())


def text(node):
    return clean(' '.join(node.itertext()))


def has_class(name):
    return 'contains(concat(" ",normalize-space(@class)," ")," ' + name + ' ")'


def extract(body, url, metadata, expected_reference=''):
    doc = html.fromstring(body)
    canonical = doc.xpath('//link[@rel="canonical"]/@href')
    heads = doc.xpath('//*[' + has_class('variant-hero__headings-inner') + ']')
    selected = [h for h in heads if re.search(r'opacity:\s*1(?:;|$)', h.get('style', ''))]
    if len(selected) != 1:
        raise ValueError('Ambiguous selected reference header')
    head = selected[0]
    refs = head.xpath('.//*[' + has_class('js-ref') + ']')
    titles = head.xpath('.//*[' + has_class('js-title') + ']')
    printed = text(refs[0]) if refs else ''
    products = []
    for script in doc.xpath('//script[@type="application/ld+json"]'):
        try:
            data = json.loads(script.text or '')
        except ValueError:
            continue
        candidates = data.get('@graph', [data]) if isinstance(data, dict) else data
        products.extend(p for p in candidates if p.get('@type') == 'Product')
    if len(products) != 1:
        raise ValueError('Missing or ambiguous Product identity')
    product = products[0]
    key = norm_ref(printed)
    sku = norm_ref(product.get('sku'))
    printed_suffix_omission = bool(key and key + '3L' == sku and canonical and urlsplit(canonical[0]).path.endswith('/' + sku.lower()) and product.get('@id') == product.get('sku'))
    if not key or key != sku and not printed_suffix_omission or expected_reference and norm_ref(expected_reference) not in ({key, sku} if printed_suffix_omission else {key}):
        raise ValueError('Printed reference, SKU and listing identity disagree')
    if not canonical or canonical[0] != metadata['url'] or product.get('url') != canonical[0]:
        raise ValueError('Selected product canonical identity disagrees')
    variant = head.get('data-variant-id')
    fields = []
    for panel in doc.xpath('//*[' + has_class('tabs__panel') + ']'):
        heading = panel.xpath('.//*[' + has_class('tabs__panel-title') + ']')
        tab = doc.xpath('//*[@id=$id]', id=panel.get('aria-labelledby', ''))
        section = text(heading[0]) if heading else text(tab[0]) if tab else ''
        for item in panel.xpath('.//*[' + has_class('tabs_content') + ']'):
            labels = item.xpath('./*[' + has_class('tabs__label') + ']')
            values = item.xpath('./*[' + has_class('tabs__value') + ']')
            if labels and values:
                fields.append({'section': section, 'label': text(labels[0]), 'value': text(values[0])})
        if section.startswith('Movement '):
            fields.append({'section': 'Movement', 'label': 'Calibre', 'value': section.removeprefix('Movement ')})
    if len(fields) < 5:
        raise ValueError('Insufficient selected technical fields')
    specs = {(f['section'].split(' ')[0], f['label']): f['value'] for f in fields}
    rec = Record('Breguet', canonical[0], 'Global', 'en', metadata['sha256'], metadata['fetched_at'])
    rec.set('reference_number', product['sku'] if printed_suffix_omission else printed, 'Product SKU with recorded printed-reference omission' if printed_suffix_omission else 'selected visible reference + Product SKU')
    rec.set('specific_model', text(titles[0]) if titles else product.get('category'), 'selected visible title')
    parts = urlsplit(canonical[0]).path.split('/')
    collection = parts[3] if len(parts) > 3 and parts[2] == 'watches' else ''
    names = {'reine-de-naples': 'Reine de Naples', 'type-xx': 'Type XX'}
    parent = names.get(collection, collection.replace('-', ' ').title()) or ('Classique' if rec.data['specific_model'].startswith('Classique ') else rec.data['specific_model'])
    rec.set('parent_model', parent, 'published collection path or selected model family')
    mapping = {
        'case_material': ('Case', 'Material'), 'case_shape': ('Case', 'Shape'),
        'case_thickness': ('Case', 'Thickness'), 'diameter': ('Case', 'Diameter'),
        'between_lugs': ('Case', 'Width of lugs'), 'water_resistance': ('Case', 'Water resistance'),
        'caseback': ('Case', 'Caseback'), 'caliber': ('Movement', 'Calibre'),
        'movement': ('Movement', 'Winding'), 'power_reserve': ('Movement', 'Power reserve'),
        'frequency': ('Movement', 'Frequency'), 'dial_color': ('Dial', 'Dial coating'),
        'bracelet_material': ('Strap', 'Bracelet Material'), 'clasp_type': ('Strap', 'Type of buckle'),
    }
    for field, source in mapping.items():
        rec.set(field, specs.get(source), '.'.join(source))
    if not rec.data['diameter'] and specs.get(('Case', 'Width')):
        width, height = specs[('Case', 'Width')], specs.get(('Case', 'Height'), '')
        rec.set('diameter', width + ' × ' + height if height else 'Width: ' + width, 'Published case width and height; not a diameter')
        rec.data['case_dimensions_display'] = 'Case width × height' if height else 'Case width'
    rec.set('description', product.get('description'), 'identity-matched Product description')
    rec.set('short_description', product.get('description'), 'identity-matched Product description')
    function_pattern = re.compile(r'\b(?:retrograde (?:seconds?|minutes?|hours?|date)|(?:perpetual|annual) calendar|moon[- ]phase(?: (?:display|indicator))?|power reserve (?:display|indicator)|second time zone|dual time|world time|alarm|minute repeat(?:er|ing)|grand strike|petite sonnerie|grande sonnerie|equation of time|chronograph|tourbillon|small seconds(?: on the tourbillon shaft)?|centre (?:hour|minute|seconds?) hand|date)\b', re.I)
    functions = list(dict.fromkeys(m[0] for m in function_pattern.finditer(rec.data['description'])))
    rec.set('features', '; '.join(functions), 'explicit function phrases in identity-matched Product description')
    numerals = re.search(r'\b(?:Roman|Arabic|Breguet) numerals\b', rec.data['description'], re.I)
    if numerals:
        rec.set('numerals', numerals[0], 'explicit numeral style in selected Product description')
    if 'montre-de-poche' in canonical[0] or re.search(r'\bpocket watch\b', rec.data['description'], re.I):
        rec.set('type', 'Pocket watch', 'published pocket-watch model')
    rec.data['dial_details'] = specs.get(('Dial', 'Dial finish'), '')
    rec.data['raw_specifications'] = fields
    rec.data['additional_specifications'] = [
        {'label': f['section'].split(' ')[0] + ': ' + f['label'], 'value': f['value']} for f in fields
        if (f['section'].split(' ')[0], f['label']) not in mapping.values()
    ]
    if printed_suffix_omission:
        rec.data.setdefault('source_discrepancies', []).append({'field': 'reference_number', 'printed_reference': printed, 'product_sku': product['sku']})
        rec.data['additional_specifications'].append({'label': 'Published reference discrepancy', 'value': 'Product SKU: ' + product['sku'] + '; printed reference: ' + printed})
    strap = re.search(r'\b(calfskin|alligator)\s+(?:leather\s+)?strap\b', rec.data['description'], re.I)
    if strap and rec.data['bracelet_material'] and strap[1].casefold() not in rec.data['bracelet_material'].casefold():
        conflict = {'field': 'bracelet_material', 'technical_table': rec.data['bracelet_material'], 'product_description': strap[1]}
        rec.data.setdefault('source_discrepancies', []).append(conflict)
        rec.data['additional_specifications'].append({'label': 'Source difference: strap material', 'value': 'Technical specifications: ' + rec.data['bracelet_material'] + '; watch description: ' + strap[1]})
    gems = [f['label'] + ': ' + f['value'] for f in fields if 'gem' in f['section'].lower()]
    rec.data['gem_setting'] = '; '.join(gems)
    rec.data['price_status'] = 'not_published'
    prices = head.xpath('.//*[@data-variant-target="newPriceText"]')
    rec.data['published_price_text'] = text(prices[0]) if prices else ''
    if rec.data['published_price_text']:
        # A number without an explicit comparable market/currency is not imported.
        rec.data['extraction_warnings'].append('Published price text requires market/currency review')
    images = doc.xpath('//img[@data-variant-id=$id and @data-variant-target="watchFrontImage"]', id=variant)
    image = images[0].get('src') if images else ''
    if image:
        rec.set('image_URL', urljoin(url, image), 'selected variant watchFrontImage src')
    else:
        rec.data['image_status'] = 'not_published_by_source'
        rec.data['extraction_warnings'].append('No front image published for this exact reference')
        rec.data['additional_specifications'].append({'label': 'Image availability', 'value': 'No image published for this exact reference.'})
    rec.data['image_urls'] = list(dict.fromkeys(urljoin(url, x.get('src') or x.get('data-src')) for x in doc.xpath('//img[@data-variant-id=$id and (@data-variant-target="watchFrontImage" or @data-variant-target="watchBackImage")]', id=variant) if x.get('src') or x.get('data-src')))
    links = []
    for a in doc.xpath('//a[@href]'):
        imgs = a.xpath('.//img[starts-with(@alt,"Switch to ")]')
        if imgs:
            target = urljoin(url, a.get('href'))
            if target.startswith('https://www.breguet.com/en/watches/'):
                links.append({'reference': imgs[0].get('alt').removeprefix('Switch to ').strip(), 'url': target})
    rec.data.update(product_detail_parsed=True, canonical_url=canonical[0], printed_reference=printed,
                    json_ld_sku=product['sku'], source_variant_id=variant, published_variant_links=links,
                    product_description=product.get('description', ''), raw_product=product)
    result = rec.finalize()
    if result['validation_errors']:
        raise ValueError('; '.join(result['validation_errors']))
    return result

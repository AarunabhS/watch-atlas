"""Tudor's English catalogue: public embedded JSON plus selected product DOM."""
import json
import re
from urllib.parse import urljoin, urlsplit

from lxml import html

from .schema import Record, clean

ORIGIN = 'https://www.tudorwatch.com'
CATALOG = ORIGIN + '/en/watches'
PRODUCT_PATH = re.compile(r'/en/(?:watches/[a-z0-9-]+|watch-family/daring-watches)/m[a-z0-9]+-\d{4}')
LISTING_PATH = re.compile(r'/en/watches(?:/page/[1-9]\d*)?')


def text(value):
    """Preserve boundaries between HTML paragraphs, line breaks and inline tags."""
    if not value:
        return ''
    node = html.fragment_fromstring(str(value), create_parent='div')
    for br in node.xpath('.//br'):
        br.tail = '\n' + (br.tail or '')
    return clean(node.text_content())


def en(value):
    return value.get('en', '') if isinstance(value, dict) else value


def labels(hit, category):
    return [v.split('|', 1)[-1] for v in hit.get('filters', {}).get(category, {}).get('en', [])]


def official(url, kind='product'):
    p = urlsplit(url)
    pattern = PRODUCT_PATH if kind == 'product' else LISTING_PATH
    return p.scheme == 'https' and p.netloc == 'www.tudorwatch.com' and not p.query and not p.fragment and bool(pattern.fullmatch(p.path))


def catalog_page(body, url, meta):
    if not official(url, 'listing'):
        raise ValueError('Unexpected Tudor catalogue URL')
    doc = html.fromstring(body)
    scripts = doc.xpath('//script[contains(text(),"InstantSearchInitialResults")]/text()')
    if len(scripts) != 1:
        raise ValueError('Expected one published catalogue JSON script')
    script = scripts[0]
    prefix = 'window[Symbol.for("InstantSearchInitialResults")] = '
    if not script.startswith(prefix):
        raise ValueError('Unexpected catalogue JSON wrapper')
    data = json.loads(script[len(prefix):].strip().rstrip(';'))['prd_catalog']
    results = data['results'][0]
    expected_page = 0 if url == CATALOG else int(url.rsplit('/', 1)[-1]) - 1
    if results['page'] != expected_page or results['index'] != 'prd_catalog':
        raise ValueError('Catalogue response is for a different page')
    if 'allPrices.IN.rawPrice' not in data['state'].get('numericRefinements', {}):
        raise ValueError('Catalogue is not the India price market')
    items = []
    for hit in results['hits']:
        rmc = hit['cleanRmc']
        product_url = ORIGIN + '/en/watches/' + hit['familySlug'] + '/' + rmc
        if not official(product_url) or rmc != hit['objectID']:
            raise ValueError('Inconsistent published Tudor reference')
        prices = hit.get('allPrices', {})
        if set(prices) != {'IN'}:
            raise ValueError('Mixed price markets in catalogue')
        items.append({'reference': hit['rmc'].upper(), 'url': product_url, 'hit': hit,
                      'catalogue_url': url, 'catalogue_source_hash': meta['sha256'],
                      'catalogue_captured_at': meta['fetched_at']})
    pagers = sorted({urljoin(url, a.get('href')) for a in doc.xpath('//main//a[@href]')
                     if official(urljoin(url, a.get('href')), 'listing')})
    return {'items': items, 'page': results['page'], 'pages': results['nbPages'],
            'expected': results['nbHits'], 'pagers': pagers, 'source_hash': meta['sha256']}


def material(value):
    terms = [('18 ct yellow gold', r'18\s*ct\s*yellow gold'), ('Yellow gold', r'yellow gold'),
             ('Rose gold', r'rose[- ]gold'), ('Grade 2 titanium', r'grade 2 titanium'),
             ('Titanium', r'titanium'), ('925 silver', r'925 silver'), ('Bronze', r'bronze'),
             ('Ceramic', r'ceramic'), ('Carbon composite', r'carbon composite'), ('Carbon fibre', r'carbon fibre'),
             ('Stainless steel', r'(?:stainless )?steel'), ('Aluminium', r'alumini?um'),
             ('Alligator leather', r'alligator'), ('Leather', r'leather'),
             ('Rubber', r'rubber'), ('Fabric', r'fabric')]
    result = []
    for name, pattern in terms:
        if re.search(pattern, value, re.I):
            if name == 'Yellow gold' and '18 ct yellow gold' in result:
                continue
            if name == 'Titanium' and 'Grade 2 titanium' in result:
                continue
            if name == 'Leather' and 'Alligator leather' in result:
                continue
            result.append(name)
    return '; '.join(result)


def product(body, url, item, meta):
    if not official(url) or url != item['url']:
        raise ValueError('Unexpected Tudor product URL')
    if not official(meta['url']) or meta['url'].rsplit('/', 1)[-1] != item['hit']['cleanRmc']:
        raise ValueError('Unexpected Tudor product redirect')
    doc = html.fromstring(body)
    sections = doc.xpath('//*[@id="full-specifications"]')
    if len(sections) != 1:
        raise ValueError('Missing selected watch specifications')
    section = sections[0]
    identity = clean(' '.join(section.xpath('./div//p/text()')))
    if item['reference'] not in identity:
        raise ValueError('Selected reference differs from catalogue')
    selected_jsonld = []
    for script in doc.xpath('//script[@type="application/ld+json"]/text()'):
        entry = json.loads(script)
        if entry.get('@type') == 'Product' and entry.get('sku', '').upper() in {item['reference'], hit_reference(item)}:
            selected_jsonld.append(entry)
    if len(selected_jsonld) != 1:
        raise ValueError('Missing selected Product JSON-LD')
    specs = {}
    for li in section.xpath('.//li[h3]'):
        label = clean(li.xpath('string(h3)'))
        paragraphs = [text(html.tostring(p, encoding='unicode', with_tail=False)) for p in li.xpath('./p')]
        if paragraphs:
            value = '; '.join(paragraphs)
            if label in specs and specs[label] != value:
                raise ValueError('Conflicting repeated specification: ' + label)
            specs[label] = value
    hit = item['hit']
    for label, key in [('Movement', 'movementSpec'), ('Bracelet', 'braceletSpec'),
                       ('Power Reserve', 'powerReserveSpec'), ('Winding Crown', 'windingCrownSpec'),
                       ('Waterproofness', 'waterproofnessSpec'), ('Bezel', 'bezelSpec'),
                       ('Dial', 'dialSpec'), ('Crystal', 'crystalSpec')]:
        if specs.get(label) != text(en(hit.get(key))):
            raise ValueError('Product and catalogue specifications differ: ' + label)
    case_parts = [text(en(hit['caseSpec'])), f'Lugs: {hit["lugToLugSpec"]}mm lug width',
                  f'Case thickness: {hit["caseThicknessSpec"]}mm']
    if specs.get('Case') != '; '.join(case_parts):
        raise ValueError('Product and catalogue case dimensions differ')
    prices = doc.xpath('//main/section[1]//*[@data-nosnippet]/text()')
    if len(prices) != 1 or clean(prices[0]) != hit['allPrices']['IN']['formattedPrice']:
        raise ValueError('Product and catalogue India prices differ')
    record = Record('Tudor', url, 'IN', 'en', meta['sha256'], meta['fetched_at'])
    def put(key, value, locator):
        record.set(key, value, locator)
    def cat(key, value, locator):
        put(key, value, locator)
        if record.data[key]:
            record.data['provenance'][key].update(url=item['catalogue_url'], source_hash=item['catalogue_source_hash'])
    put('reference_number', item['reference'], '#full-specifications Reference + Product.sku')
    put('type', 'Wristwatch', 'catalogue hit.type=watch')
    cat('parent_model', en(hit['family']).split('|', 1)[-1], 'catalogue hit.family.en')
    put('specific_model', en(hit['name']), 'h1 name + catalogue hit.name.en')
    put('marketing_name', en(hit['name']), 'h1 name + catalogue hit.name.en')
    cat('style', hit.get('theme'), 'catalogue hit.theme')
    put('currency', 'INR', 'selected price ₹ + catalogue allPrices.IN')
    put('price', hit['allPrices']['IN']['rawPrice'], 'selected price + catalogue allPrices.IN.rawPrice')
    cat('image_URL', hit['image'], 'catalogue hit.image')
    case_html = en(hit['caseSpec'])
    case = text(case_html.split('<br')[0])
    case_material_text = re.split(r'(?:with |and )?(?:a )?(?:stainless )?steel case back', case, maxsplit=1, flags=re.I)[0]
    put('case_material', material(case_material_text), '#full-specifications Case, case body material terms')
    finishes = list(dict.fromkeys(re.findall(r'\b(?:satin-brushed|satin(?: finished)?|polished|micro-blasted|sand-blasted|matt)\b', case, re.I)))
    put('case_finish', finishes, '#full-specifications Case, explicit finish terms')
    back = re.search(r'(?:Open case back|(?:[a-z]+ )?case back)[^.]*', text(case_html), re.I)
    if back:
        put('caseback', back[0], '#full-specifications Case, caseback phrase')
    diameter = re.search(r'(\d+(?:\.\d+)?)\s*mm', case)
    if diameter:
        put('diameter', diameter[1] + ' mm', '#full-specifications Case, diameter')
    put('between_lugs', hit['lugToLugSpec'] + ' mm', '#full-specifications Case > Lugs: lug width')
    lug_length = re.search(r'(\d+(?:\.\d+)?)\s*mm\s+from lug to lug', case, re.I)
    if lug_length:
        put('lug_to_lug', lug_length[1] + ' mm', '#full-specifications Case, explicit lug-to-lug length')
    put('case_thickness', hit['caseThicknessSpec'] + ' mm', '#full-specifications Case > Case thickness')
    put('bezel_material', material(specs['Bezel']), '#full-specifications Bezel, material terms')
    colours = r'black|blue|burgundy|green|brown|silver|gold|red|grey|gray|yellow|white|anthracite'
    put('bezel_color', '; '.join(dict.fromkeys(re.findall(r'\b(?:' + colours + r')\b', specs['Bezel'], re.I))), '#full-specifications Bezel, colour terms')
    put('crystal', specs['Crystal'], '#full-specifications Crystal')
    put('water_resistance', specs['Waterproofness'], '#full-specifications Waterproofness')
    dial_colour = re.search(r'\b(?:dark champagne-colou?r|light champagne-colour|light blue|navy blue|slate grey|TUDOR Blue|champagne-colour|brown-bronze|anthracite|beige|black|blue|brown|burgundy|charcoal|green|ivory|mother-of-pearl|opaline|pink|salmon|silver|taupe|turquoise|white|yellow)\b', specs['Dial'], re.I)
    if dial_colour:
        value = dial_colour[0] if dial_colour[0] == 'TUDOR Blue' else dial_colour[0].capitalize()
        put('dial_color', value, '#full-specifications Dial, explicit colour phrase')
    else:
        cat('dial_color', labels(hit, 'Colour'), 'catalogue hit.filters.Colour.en (no explicit Dial colour)')
    numerals = re.search(r'(?:applied )?(?:Roman numerals|Arabic (?:hour markers|numerals)|stick hour markers|diamond hour markers)', specs['Dial'], re.I)
    if numerals:
        put('numerals', numerals[0], '#full-specifications Dial, marker phrase')
    bracelet = specs['Bracelet']
    # Clasps/buckles can have a different material from the strap.
    strap = re.split(r'\bwith\b', bracelet, maxsplit=1, flags=re.I)[0]
    bracelet_material = material(strap) or '; '.join(labels(hit, 'Bracelet'))
    put('bracelet_material', bracelet_material, '#full-specifications Bracelet, strap/bracelet material (catalogue filter fallback)')
    colour = re.search(r'^(?:(?:Domed|Single-piece|One-piece|Elastic|Jacquard|Textured)\s+)*(dark brown|brown|black|blue|green|beige|red)', bracelet, re.I)
    if colour:
        put('bracelet_color', colour[1], '#full-specifications Bracelet, explicit strap colour')
    clasp = re.search(r'(?:TUDOR\s+[“\"]T-fit[”\"]|[“\"]T-fit[”\"]|(?:ceramic|steel|silver|titanium|18 ct yellow gold)?\s*(?:folding|pin))?[^,.;]*\b(?:clasp|buckle|fastening)\b[^.;]*', bracelet, re.I)
    if clasp:
        put('clasp_type', clasp[0].strip(), '#full-specifications Bracelet, clasp/buckle phrase')
    put('movement', specs['Movement'], '#full-specifications Movement')
    calibre = re.search(r'\bCalibre\s+([A-Z0-9]+(?:-[A-Z0-9]+)?)', specs['Movement'])
    if calibre:
        put('caliber', calibre[1], '#full-specifications Movement > Calibre')
    put('power_reserve', specs['Power Reserve'], '#full-specifications Power Reserve')
    cat('features', labels(hit, 'Function'), 'catalogue hit.filters.Function.en')
    paragraphs = []
    # Product editorial and certification copy before the specifications section.
    for p in doc.xpath('//main//p[not(ancestor::dialog)]'):
        if section in p.iterancestors():
            break
        if 'body-100' in p.get('class', '') and not p.xpath('.//*[@data-nosnippet]'):
            value = text(html.tostring(p, encoding='unicode', with_tail=False))
            if value and value not in paragraphs:
                paragraphs.append(value)
    description = '\n\n'.join(paragraphs)
    put('short_description', selected_jsonld[0].get('description'), 'selected Product.description')
    put('description', description or selected_jsonld[0].get('description'), 'selected product editorial paragraphs before #full-specifications')
    if 'Swiss Made' in [clean(x.text_content()) for x in doc.xpath('//main//h2')]:
        put('made_in', 'Switzerland', 'selected product Swiss Made certification section')
    frequency = re.search(r'\b[\d,.]+\s*(?:Hz|vph|vibrations per hour)\b', description, re.I)
    if frequency:
        put('frequency', frequency[0], 'selected product editorial, frequency phrase')
    jewels = re.search(r'\b(\d+)\s+jewels\b', description, re.I)
    if jewels:
        put('jewels', jewels[1], 'selected product editorial, jewel count')
    record.data['watch_URL'] = meta['url']
    for provenance in record.data['provenance'].values():
        if provenance['url'] == url:
            provenance['url'] = meta['url']
    record.data['provenance']['watch_URL']['value'] = meta['url']
    gallery = [u for u in doc.xpath('//main/section[1]//img/@src') if u.startswith('https://media.tudorwatch.com/')]
    record.data.update(raw_specifications=specs, catalogue_data=hit, catalogue_product_url=url, catalogue_source_url=item['catalogue_url'],
                       catalogue_source_hash=item['catalogue_source_hash'], selected_jsonld=selected_jsonld,
                       editorial_paragraphs=paragraphs, source_field_count=len(specs), product_detail_parsed=True,
                       price_display=clean(prices[0]), price_kind='Tudor suggested retail price',
                       selected_gallery_image_urls=gallery,
                       image_urls=list(dict.fromkeys([hit['image']] + selected_jsonld[0].get('image', []) + gallery)),
                       variant_references=hit.get('variations', []), related_references=hit.get('suggestions', []))
    for provenance in record.data['provenance'].values():
        provenance.setdefault('source_hash', meta['sha256'])
    return record.finalize()


def hit_reference(item):
    return item['hit']['cleanRmc'].upper()

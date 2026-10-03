"""Layered extraction: matched Product JSON-LD, explicit labels, brand hooks.

Never use related-product cards as the current watch. Retain unmatched specs and
full response snapshots, so adding a field mapping requires no new HTTP request.
"""
import json
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

from lxml import html
from ..schema import Record, clean

LABELS = {
    'reference':'reference_number', 'reference number':'reference_number', 'ref':'reference_number',
    'collection':'parent_model', 'model':'specific_model', 'gender':'type', 'country of origin':'made_in',
    'case material':'case_material', 'material of the case':'case_material', 'case shape':'case_shape',
    'case finish':'case_finish', 'case back':'caseback', 'caseback':'caseback', 'diameter':'diameter',
    'case diameter':'diameter', 'diameter of the case':'diameter', 'case size':'diameter',
    'thickness':'case_thickness', 'case thickness':'case_thickness', 'height':'case_thickness',
    'lug width':'between_lugs', 'between lugs':'between_lugs', 'lugs':'between_lugs',
    'lug to lug':'lug_to_lug', 'bezel material':'bezel_material', 'bezel color':'bezel_color',
    'crystal':'crystal', 'glass':'crystal', 'water resistance':'water_resistance', 'waterproofness':'water_resistance',
    'water resistant':'water_resistance', 'weight':'weight', 'dial color':'dial_color', 'dial colour':'dial_color',
    'dial':'dial_color', 'hour markers':'numerals', 'numerals':'numerals',
    'strap material':'bracelet_material', 'bracelet material':'bracelet_material', 'bracelet':'bracelet_material',
    'strap':'bracelet_material', 'strap color':'bracelet_color', 'strap colour':'bracelet_color',
    'clasp':'clasp_type', 'buckle':'clasp_type', 'clasp type':'clasp_type', 'movement':'movement',
    'movement type':'movement', 'caliber':'caliber', 'calibre':'caliber',
    'power reserve':'power_reserve', 'frequency':'frequency', 'vibrations':'frequency',
    'jewels':'jewels', 'number of jewels':'jewels', 'functions':'features', 'complications':'features',
    'features':'features', 'price':'price', 'currency':'currency', 'year introduced':'year_introduced',
}


def label_key(value):
    return re.sub(r'[^a-z0-9 ]', '', clean(value).lower().replace('-', ' ')).strip()


def url_key(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, p.path.rstrip('/'), '', ''))


def walk(data):
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from walk(value)
    elif isinstance(data, list):
        for value in data:
            yield from walk(value)


@dataclass
class Adapter:
    key: str
    brand: str
    origin: str
    locale: str
    market: str
    seed_paths: tuple
    product_pattern: str
    listing_patterns: tuple
    validation_status: str = 'provisional: synthetic fixtures only; no live product validation'

    @property
    def hosts(self):
        return {urlsplit(self.origin).hostname}

    @property
    def seeds(self):
        return [self.origin + p for p in self.seed_paths]

    def classify(self, url):
        p = urlsplit(url)
        if p.scheme != 'https' or p.hostname not in self.hosts or p.query or p.fragment:
            return None
        if re.fullmatch(self.product_pattern, p.path, re.I):
            return 'product'
        if any(re.fullmatch(pattern, p.path, re.I) for pattern in self.listing_patterns):
            return 'listing'
        return None

    def expected_reference(self, url):
        return ''

    def label(self, label):
        return LABELS.get(label_key(label))

    def parse(self, body, url, metadata=None):
        metadata = metadata or {}
        doc = html.fromstring(body, base_url=url)
        record = Record(self.brand, url, self.market, self.locale, metadata.get('sha256', ''), metadata.get('fetched_at'))
        # Restrict generic visible extraction to the main/product area.
        scopes = doc.xpath('//main | //*[@itemtype="https://schema.org/Product"]')
        scope = scopes[0] if scopes else doc
        canonical = doc.xpath('//link[@rel="canonical"]/@href')
        current_urls = {url_key(url)}
        if canonical:
            canonical_url = urljoin(url, canonical[0])
            if self.classify(canonical_url) == 'product':
                current_urls.add(url_key(canonical_url))
        structured = []
        for script in doc.xpath('//script[@type="application/ld+json" or @type="application/json"]'):
            try:
                parsed = json.loads(script.text or '')
            except (ValueError, TypeError):
                record.data['extraction_warnings'].append('Invalid embedded JSON: ' + (script.get('id') or script.get('type')))
                continue
            if script.get('type') == 'application/ld+json':
                candidates = [obj for obj in walk(parsed) if 'Product' in (obj.get('@type') if isinstance(obj.get('@type'), list) else [obj.get('@type')])]
                for product in candidates:
                    candidate_url = product.get('url') or product.get('@id')
                    if isinstance(candidate_url, str) and url_key(urljoin(url, candidate_url)) in current_urls:
                        structured.append(product)
                    elif not candidate_url and clean(product.get('sku') or product.get('mpn')).lower() == self.expected_reference(url).lower() and self.expected_reference(url):
                        structured.append(product)
            self.embedded(record, parsed, current_urls, script.get('id') or 'embedded JSON')
        if structured:
            # Identical current-URL schemas are additive. Conflicts stay visible.
            for product in structured:
                self.structured(record, product)
        record.set('reference_number', self.expected_reference(url), 'official URL reference segment')
        headings = scope.xpath('.//h1')
        if headings:
            record.set('specific_model', headings[0].text_content(), 'main h1')
        descriptions = scope.xpath('.//*[@itemprop="description"]')
        if descriptions:
            record.set('description', descriptions[0].text_content(), 'itemprop=description')
        for content in doc.xpath('//meta[@name="description"]/@content')[:1]:
            record.set('short_description', content, 'meta[name=description]')
        for content in doc.xpath('//meta[@property="og:image"]/@content')[:1]:
            record.set('image_URL', urljoin(url, content), 'meta[property=og:image]')
        specs = self.specifications(scope)
        for label, value, locator in specs:
            values = record.data['raw_specifications'].setdefault(label, [])
            if value not in values:
                values.append(value)
            if field := self.label(label):
                record.set(field, value, locator)
        self.enrich(record, doc, specs)
        variants = []
        for link in scope.xpath('.//a[@href]/@href'):
            target = urljoin(url, link)
            if self.classify(target) == 'product' and url_key(target) not in current_urls:
                variants.append(target)
        # These are discovery candidates, not a claim that recommendations are variants.
        record.data['linked_product_urls'] = sorted(set(variants))
        for source in scope.xpath('.//*[@itemprop="image"]/@src | .//*[@itemprop="image"]/@content | .//picture/source/@srcset'):
            for part in source.split(','):
                image = urljoin(url, part.strip().split(' ')[0])
                if urlsplit(image).scheme == 'https':
                    record.data['image_urls'].append(image)
        if record.data['image_URL']:
            record.data['image_urls'].insert(0, record.data['image_URL'])
        record.data['image_urls'] = list(dict.fromkeys(record.data['image_urls']))
        if not structured and not specs:
            record.data['extraction_warnings'].append('No matched Product schema or labeled specifications; rendering or adapter mapping may be needed')
        record.data['adapter_status'] = self.validation_status
        return record.finalize()

    def structured(self, record, product):
        for field, key in [('reference_number','sku'), ('specific_model','name'), ('description','description'), ('reference_number','mpn')]:
            record.set(field, product.get(key), 'Product JSON-LD.' + key)
        images = product.get('image', [])
        images = images if isinstance(images, list) else [images]
        for image in images:
            value = image.get('contentUrl') or image.get('url') if isinstance(image, dict) else image
            if value:
                value = urljoin(record.data['watch_URL'], value)
                if urlsplit(value).scheme == 'https':
                    record.data['image_urls'].append(value)
                    record.set('image_URL', value, 'Product JSON-LD.image')
        offers = product.get('offers', [])
        offers = offers if isinstance(offers, list) else [offers]
        record.data['offers'] = offers
        if len(offers) == 1 and isinstance(offers[0], dict):
            record.set('price', offers[0].get('price'), 'Product JSON-LD.offers.price')
            record.set('currency', offers[0].get('priceCurrency'), 'Product JSON-LD.offers.priceCurrency')
            record.data['availability'] = offers[0].get('availability', '')
        elif len(offers) > 1:
            record.data['extraction_warnings'].append('Multiple offers retained; no single price selected')
        properties = product.get('additionalProperty', [])
        properties = properties if isinstance(properties, list) else [properties]
        for prop in properties:
            if not isinstance(prop, dict):
                continue
            name, value = clean(prop.get('name')), clean(prop.get('value'))
            if name and value:
                record.data['raw_specifications'].setdefault(name, []).append(value)
                if field := self.label(name):
                    record.set(field, value, 'Product JSON-LD.additionalProperty.' + name)

    def specifications(self, scope):
        result = []
        def add(label, value, node):
            label, value = clean(label), clean(value)
            if label and value and len(label) < 120:
                result.append((label, value, node.getroottree().getpath(node)))
        for node in scope.xpath('.//dt'):
            values = node.xpath('following-sibling::*[1][self::dd]')
            if values:
                add(node.text_content(), values[0].text_content(), node)
        for node in scope.xpath('.//tr'):
            cells = node.xpath('./th | ./td')
            if len(cells) == 2:
                add(cells[0].text_content(), cells[1].text_content(), node)
        for node in scope.xpath('.//*[@data-specification-name]'):
            add(node.get('data-specification-name'), node.get('data-specification-value') or node.text_content(), node)
        # Known labels only, constrained to a neighboring value instead of entire sections.
        for node in scope.xpath('.//h2 | .//h3 | .//h4 | .//h5 | .//label'):
            if self.label(node.text_content()):
                values = node.xpath('following-sibling::*[1][self::p or self::span or self::div]')
                if values:
                    add(node.text_content(), values[0].text_content(), node)
        return result

    def embedded(self, record, data, current_urls, locator):
        """Brand hook. Never evaluate inline JavaScript or query undocumented APIs."""

    def enrich(self, record, doc, specs):
        pass

    def links(self, body, url):
        doc = html.fromstring(body, base_url=url)
        result = set()
        for link in doc.xpath('//a[@href]/@href'):
            target = urljoin(url, link)
            if self.classify(target):
                result.add(target)
        # Discover only explicit URL strings in inert JSON; no speculative endpoints.
        for script in doc.xpath('//script[@type="application/json" or @type="application/ld+json"]'):
            try:
                data = json.loads(script.text or '')
            except ValueError:
                continue
            for obj in walk(data):
                for key in ('url', 'href', 'productUrl'):
                    value = obj.get(key)
                    if isinstance(value, str):
                        target = urljoin(url, value)
                        if self.classify(target):
                            result.add(target)
        return sorted(result)

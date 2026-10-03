import re
from urllib.parse import urlsplit, urljoin
from .base import Adapter, walk, url_key
from ..schema import clean


class PatekAdapter(Adapter):
    def expected_reference(self, url):
        tail = urlsplit(url).path.rstrip('/').split('/')[-1]
        return tail if re.fullmatch(r'\d{4}[A-Z0-9/_-]*-\d{3}', tail, re.I) else ''

    def embedded(self, record, data, current_urls, locator):
        # Explicit product-shaped payloads only. Sitecore header/navigation also
        # contains watch names and images, so never flatten the whole page tree.
        for obj in walk(data):
            reference = clean(obj.get('referenceNumber') or obj.get('reference'))
            target = obj.get('url') or obj.get('productUrl')
            if not reference or not isinstance(target, str) or url_key(urljoin(record.data['watch_URL'], target)) not in current_urls:
                continue
            record.set('reference_number', reference, locator + '.referenceNumber')
            for key, field in [('name','specific_model'), ('collectionName','parent_model'), ('description','description')]:
                record.set(field, obj.get(key), locator + '.' + key)
            specs = obj.get('technicalSpecifications', [])
            if isinstance(specs, list):
                for spec in specs:
                    if not isinstance(spec, dict):
                        continue
                    name, value = clean(spec.get('name')), clean(spec.get('value'))
                    if name and value:
                        record.data['raw_specifications'].setdefault(name, []).append(value)
                        if field := self.label(name):
                            record.set(field, value, locator + '.technicalSpecifications.' + name)


ADAPTER = PatekAdapter('patek', 'Patek Philippe', 'https://www.patek.com', 'en', 'international', ('/en/collection',), r'/en/collection/[^/]+/\d{4}[A-Za-z0-9_-]*-\d{3}/?', (r'/en/collection/?', r'/en/collection/[a-z-]+/?'))

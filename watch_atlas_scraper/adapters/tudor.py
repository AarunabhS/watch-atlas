import re
from urllib.parse import urlsplit
from .base import Adapter


class TudorAdapter(Adapter):
    def expected_reference(self, url):
        tail = urlsplit(url).path.rstrip('/').split('/')[-1]
        return tail[1:] if re.fullmatch(r'm\w+-\d{4}', tail, re.I) else ''

    def enrich(self, record, doc, specs):
        for label, value, locator in specs:
            if label.lower() == 'case':
                record.set('case_material', value, locator)
                for pattern, field in [
                    (r'\b(\d+(?:\.\d+)?)\s*mm\s+(?:stainless\s+)?(?:steel|gold|titanium|ceramic|bronze)?\s*case', 'diameter'),
                    (r'Lugs?:\s*(\d+(?:\.\d+)?)\s*mm', 'between_lugs'),
                    (r'Case thickness:\s*(\d+(?:\.\d+)?)\s*mm', 'case_thickness'),
                ]:
                    if match := re.search(pattern, value, re.I):
                        record.set(field, match[1] + ' mm', locator + ' (explicit measurement)')
            if label.lower() == 'movement' and (match := re.search(r'Calib(?:re|er)\s+([A-Z0-9-]+)', value, re.I)):
                record.set('caliber', match[1], locator + ' (explicit caliber)')
            if label.lower() == 'bezel':
                record.set('bezel_material', value, locator)

    def label(self, label):
        return {'case':'case_material', 'bezel':'bezel_material'}.get(label.lower()) or super().label(label)


ADAPTER = TudorAdapter('tudor', 'Tudor', 'https://www.tudorwatch.com', 'en', 'international', ('/en/watches',), r'/en/watches/[^/]+/m[a-z0-9]+-\d{4}/?', (r'/en/watches/?', r'/en/watches/[a-z0-9-]+/?'))

import re
from urllib.parse import urlsplit
from .base import Adapter


class OmegaAdapter(Adapter):
    def expected_reference(self, url):
        match = re.search(r'-(\d{14})/?$', urlsplit(url).path)
        if not match:
            return ''
        digits = match[1]
        return '.'.join((digits[:3], digits[3:5], digits[5:7], digits[7:9], digits[9:11], digits[11:]))

    def label(self, label):
        return {'between lugs':'between_lugs', 'total product weight approx':'weight', 'thickness':'case_thickness', 'case':'case_material', 'strap type':'bracelet_material', 'buckle type':'clasp_type'}.get(label.lower()) or super().label(label)


ADAPTER = OmegaAdapter('omega', 'Omega', 'https://www.omegawatches.com', 'en', 'US', ('/en-us/watches',), r'/en-us/watch-omega-[a-z0-9-]+-\d{14}/?', (r'/en-us/watches(?:/[a-z0-9-]+)*/?',))

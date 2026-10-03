import re
from urllib.parse import urlsplit
from .base import Adapter


class BreitlingAdapter(Adapter):
    def expected_reference(self, url):
        tail = urlsplit(url).path.rstrip('/').split('/')[-1]
        return tail.upper() if re.fullmatch(r'[A-Z][A-Z0-9]{8,}', tail, re.I) else ''

    def label(self, label):
        return {'case height':'case_thickness', 'caseback':'caseback', 'lug':'between_lugs', 'vibration':'frequency', 'water resistance':'water_resistance'}.get(label.lower()) or super().label(label)


ADAPTER = BreitlingAdapter('breitling', 'Breitling', 'https://www.breitling.com', 'en', 'US', ('/us-en/watches/', '/us-en/collections/'), r'/us-en/watches/[^/]+/(?:[^/]+/)?[A-Z][A-Z0-9]{8,}/?', (r'/us-en/(?:watches|collections)/?', r'/us-en/collections/[a-z0-9-]+/?', r'/us-en/watches/[a-z0-9-]+/?'))

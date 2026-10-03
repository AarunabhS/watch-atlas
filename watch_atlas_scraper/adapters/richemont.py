import re
from urllib.parse import urlsplit
from .base import Adapter


class RichemontAdapter(Adapter):
    def expected_reference(self, url):
        tail = urlsplit(url).path.split('/')[-1]
        if self.key == 'iwc':
            match = re.match(r'(iw\d{6})', tail, re.I)
            return match[1].upper() if match else ''
        match = re.search(r'-(q?[a-z]?\d{6,})\b', tail, re.I)
        return match[1].upper() if match else ''

    def label(self, label):
        return {'case height':'case_thickness', 'height of the case':'case_thickness', 'number of jewels':'jewels', 'frequency vibrations hour':'frequency', 'strap width':'between_lugs'}.get(label.lower()) or super().label(label)

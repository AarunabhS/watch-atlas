import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

# Exact order from the reviewed AP/Bulgari export. Application alias: image_url.
COLUMNS = ('reference_number watch_URL type brand year_introduced parent_model specific_model nickname marketing_name style currency price image_URL made_in case_shape case_material case_finish caseback diameter between_lugs lug_to_lug case_thickness bezel_material bezel_color crystal water_resistance weight dial_color numerals bracelet_material bracelet_color clasp_type movement caliber power_reserve frequency jewels features short_description description').split()
CORE = ('reference_number watch_URL parent_model case_material diameter movement water_resistance power_reserve dial_color image_URL').split()


def clean(value):
    if value is None:
        return ''
    if isinstance(value, list):
        return '; '.join(clean(v) for v in value if v is not None)
    if isinstance(value, dict):
        return clean(value.get('value') or value.get('name') or '')
    return re.sub(r'\s+', ' ', str(value)).strip()


class Record:
    def __init__(self, brand, url, market, language, snapshot_hash='', captured_at=None):
        self.data = {k: '' for k in COLUMNS}
        self.data.update(brand=brand, watch_URL=url)
        self.data.update(schema_version=1, market=market, language=language, captured_at=captured_at or datetime.now(timezone.utc).isoformat(), source_hash=snapshot_hash, raw_specifications={}, provenance={}, image_urls=[], variant_urls=[], extraction_warnings=[])
        self.data['provenance'].update({k:{'url':url, 'locator':'adapter identity' if k == 'brand' else 'fetched official URL', 'value':v} for k,v in [('brand',brand),('watch_URL',url)]})

    def set(self, key, value, locator, overwrite=False):
        value = clean(value)
        if key in COLUMNS and value and (overwrite or not self.data[key]):
            self.data[key] = value
            self.data['provenance'][key] = {'url':self.data['watch_URL'], 'locator':locator, 'value':value}

    def finalize(self):
        d = self.data
        d['image_url'] = d['image_URL']
        identity = '|'.join((d['brand'], d['reference_number'] or d['watch_URL'], d['market'], d['language']))
        d['id'] = hashlib.sha256(identity.encode()).hexdigest()[:24]
        d['missing_fields'] = [k for k in COLUMNS if not d[k]]
        d['missing_core_fields'] = [k for k in CORE if not d[k]]
        d['coverage'] = round(100 * (len(CORE) - len(d['missing_core_fields'])) / len(CORE))
        d['validation_errors'] = validate(d)
        return d


def validate(record):
    errors = []
    for field in ('brand', 'reference_number', 'specific_model', 'watch_URL'):
        if not record.get(field):
            errors.append('Missing identity field: ' + field)
    if urlsplit(record.get('watch_URL', '')).scheme != 'https':
        errors.append('Source URL must use HTTPS')
    diameter = record.get('diameter', '')
    match = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*mm', diameter, re.I)
    if match and not 5 <= float(match[1].replace(',', '.')) <= 100:
        errors.append('Case diameter outside wristwatch review range')
    currency = record.get('currency', '')
    if currency and not re.fullmatch('[A-Z]{3}', currency):
        errors.append('Currency must be an ISO code')
    return errors

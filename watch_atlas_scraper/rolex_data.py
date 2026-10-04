"""Rebuild an exact Rolex reference from the audit's rendered technical sections."""
from urllib.parse import urlsplit
import re
import unicodedata

from .schema import Record


def extract(capture, original, snapshot_hash):
    ref = original['reference_number']
    u = urlsplit(capture['canonical'])
    if not (u.scheme == 'https' and u.netloc == 'www.rolex.com' and u.path.endswith('/m' + ref)
            and 'm' + ref in capture['title'] and len(capture['fields']) >= 8):
        raise ValueError('Exact Rolex variant identity not verified')
    words = lambda s: re.sub(r'\W', '', unicodedata.normalize('NFKC', s or '').casefold())
    if not words(capture['heading']).startswith(words(original['parent_model'])):
        raise ValueError('Archive model label disagrees with selected Rolex heading')
    specs = {(x['section'], x['label']): x['value'] for x in capture['fields']}
    rec = Record('Rolex', capture['canonical'], 'Global', 'en', snapshot_hash, capture['checked_at'])
    rec.set('reference_number', ref, 'exact variant in official canonical URL and title')
    rec.set('specific_model', original['specific_model'], 'archive model label verified against current heading')
    rec.set('parent_model', original['parent_model'], 'archive model label verified against current heading')
    mapping = {
        'case_material': ('Model case', 'Material'), 'diameter': ('Model case', 'Diameter'),
        'caseback': ('Model case', 'Oyster architecture'), 'crystal': ('Model case', 'Crystal'),
        'water_resistance': ('Model case', 'Water resistance'), 'movement': ('Movement', 'Movement'),
        'caliber': ('Movement', 'Calibre'), 'power_reserve': ('Movement', 'Power reserve'),
        'features': ('Movement', 'Functions'), 'bracelet_material': ('Bracelet', 'Material'),
        'clasp_type': ('Bracelet', 'Clasp'), 'dial_color': ('Dial', 'Dial'),
        'short_description': ('Model case', 'Model case'),
    }
    for field, key in mapping.items():
        rec.set(field, specs.get(key), '.'.join(key))
    rec.data['bezel_description'] = specs.get(('Model case', 'Bezel'), '')
    rec.data['dial_details'] = specs.get(('Dial', 'Details'), '')
    rec.data['raw_specifications'] = capture['fields']
    rec.data['additional_specifications'] = [
        {'label': f['section'] + ': ' + f['label'], 'value': f['value']}
        for f in capture['fields'] if (f['section'], f['label']) not in mapping.values()
        and (f['section'], f['label']) != ('Bracelet', 'Bracelet')
    ]
    rec.data['strap_description'] = specs.get(('Bracelet', 'Bracelet'), '')
    gem_fields = [specs.get(k, '') for k in [('Model case', 'Bezel'), ('Model case', 'Material'), ('Dial', 'Details')]]
    rec.data['gem_setting'] = '; '.join(value for value in gem_fields
                                       if re.search(r'\b(?:diamonds?|rub(?:y|ies)|emeralds?|sapphires?)\b', value, re.I))
    image = capture.get('image') or {}
    image_url = image.get('current_url') or image.get('url') or ''
    if urlsplit(image_url).hostname != 'media.rolex.com' or not urlsplit(image_url).path.endswith('/m' + ref):
        raise ValueError('Image does not identify the selected variant')
    rec.set('image_URL', image_url, 'selected current hero image URL')
    rec.data.update(product_detail_parsed=True, price_status='not_published', image_urls=[image_url],
                    canonical_url=capture['canonical'], dom_representation_hash=capture['source_hash'],
                    original_record_id=original['id'])
    result = rec.finalize()
    if result['validation_errors']:
        raise ValueError('; '.join(result['validation_errors']))
    return result

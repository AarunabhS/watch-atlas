"""Atomic exports using the reviewed Watch Atlas column order."""
import csv
import json
from pathlib import Path

from .policy import PermissionDenied
from .schema import COLUMNS, validate
from .state import write_json


def save_csv(path, rows, fields=COLUMNS):
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def export_records(records, folder, policy, adapters):
    """Export valid, reuse-authorized records from the general collector."""
    folder = Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    brand_keys = {adapter.brand:key for key,adapter in adapters.items()}
    accepted, quarantine = [], []
    for record in records:
        errors = validate(record)
        key = brand_keys.get(record.get('brand'))
        if key is None:
            errors.append('Unknown watchmaker adapter')
        else:
            try:
                policy.require(key,record.get('watch_URL',''),'reuse')
            except PermissionDenied as error:
                errors.append(str(error))
        if errors:
            quarantine.append({'record':record,'errors':errors})
        else:
            accepted.append(record)
    accepted.sort(key=lambda row:(row['brand'],row['reference_number'],row.get('market',''),row.get('language','')))
    save_csv(folder / 'watches.csv',accepted)
    path = folder / 'watches.jsonl'
    temp = path.with_suffix('.jsonl.tmp')
    temp.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in accepted),encoding='utf-8')
    temp.replace(path)
    write_json(folder / 'quarantine.json',quarantine)
    quality = {'accepted':len(accepted),'quarantined':len(quarantine),
               'missing_fields':{key:sum(not row.get(key) for row in accepted) for key in COLUMNS}}
    write_json(folder / 'quality.json',quality)
    return quality

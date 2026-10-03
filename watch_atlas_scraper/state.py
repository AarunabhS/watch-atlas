"""Durable queue, content-addressed snapshots, conditional cache, circuit state."""
import hashlib
import json
import sqlite3
import time
from pathlib import Path


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


class State:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.folder / 'state.sqlite')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS cache(url TEXT PRIMARY KEY, metadata TEXT, body_hash TEXT);
        CREATE TABLE IF NOT EXISTS circuits(host TEXT PRIMARY KEY, reason TEXT, until REAL);
        CREATE TABLE IF NOT EXISTS queue(brand TEXT, url TEXT, kind TEXT, status TEXT DEFAULT 'pending', reason TEXT, PRIMARY KEY(brand,url));
        CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, brand TEXT, data TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, time REAL, kind TEXT, url TEXT, detail TEXT);
        ''')

    def event(self, kind, url, detail):
        self.db.execute('INSERT INTO events(time,kind,url,detail) VALUES(?,?,?,?)', (time.time(), kind, url, str(detail)))
        self.db.commit()

    def cached(self, url):
        row = self.db.execute('SELECT * FROM cache WHERE url=?', (url,)).fetchone()
        if row:
            return json.loads(row['metadata']), (self.folder / 'snapshots' / row['body_hash']).read_bytes()
        return None

    def save_response(self, url, metadata, body):
        digest = hashlib.sha256(body).hexdigest()
        folder = self.folder / 'snapshots'
        folder.mkdir(exist_ok=True)
        path = folder / digest
        if not path.exists():
            path.write_bytes(body)
        metadata = {**metadata, 'sha256': digest}
        self.db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?)', (url, json.dumps(metadata), digest))
        self.db.commit()
        return metadata

    def block(self, host, reason, until=None):
        self.db.execute('INSERT OR REPLACE INTO circuits VALUES(?,?,?)', (host, reason, until))
        self.db.commit()

    def blocked(self, host):
        row = self.db.execute('SELECT * FROM circuits WHERE host=?', (host,)).fetchone()
        return row['reason'] if row and (row['until'] is None or row['until'] > time.time()) else None

    def enqueue(self, brand, url, kind):
        cursor = self.db.execute('INSERT OR IGNORE INTO queue(brand,url,kind) VALUES(?,?,?)', (brand, url, kind))
        self.db.commit()
        return cursor.rowcount > 0

    def pending(self, brand):
        return self.db.execute("SELECT * FROM queue WHERE brand=? AND status='pending' ORDER BY CASE kind WHEN 'sitemap' THEN 0 WHEN 'listing' THEN 1 ELSE 2 END,url LIMIT 1", (brand,)).fetchone()

    def finish(self, brand, url, status='done', reason=''):
        self.db.execute('UPDATE queue SET status=?,reason=? WHERE brand=? AND url=?', (status, reason, brand, url))
        self.db.commit()

    def save_record(self, record):
        self.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?)', (record['id'], record['brand'], json.dumps(record, ensure_ascii=False)))
        self.db.commit()

    def records(self, brands=None):
        rows = self.db.execute('SELECT data FROM records ORDER BY brand,id')
        records = [json.loads(row['data']) for row in rows]
        return [row for row in records if not brands or row['brand'] in brands]

    def queue_counts(self, brand):
        return dict(self.db.execute('SELECT status,count(*) FROM queue WHERE brand=? GROUP BY status', (brand,)).fetchall())

    def close(self):
        self.db.close()

-- Derived search projection; the existing catalog/export remains the source of truth.
CREATE TABLE IF NOT EXISTS finder_watches (
 id TEXT PRIMARY KEY, brand TEXT NOT NULL, collection TEXT NOT NULL, model TEXT NOT NULL,
 reference TEXT NOT NULL, reference_key TEXT NOT NULL, model_key TEXT NOT NULL,
 diameter REAL, thickness REAL, lug REAL, reserve REAL, water REAL, frequency REAL, jewels REAL,
 captured TEXT NOT NULL, production TEXT, status TEXT NOT NULL,
 card_json TEXT NOT NULL, record_json TEXT NOT NULL, width REAL, weight REAL
);
CREATE INDEX IF NOT EXISTS finder_reference ON finder_watches(reference_key);
CREATE INDEX IF NOT EXISTS finder_model ON finder_watches(model_key);
CREATE INDEX IF NOT EXISTS finder_brand ON finder_watches(brand, id);
CREATE INDEX IF NOT EXISTS finder_collection ON finder_watches(collection, brand);
CREATE INDEX IF NOT EXISTS finder_diameter ON finder_watches(diameter, id);
CREATE INDEX IF NOT EXISTS finder_thickness ON finder_watches(thickness, id);
CREATE INDEX IF NOT EXISTS finder_water ON finder_watches(water, id);
CREATE INDEX IF NOT EXISTS finder_reserve ON finder_watches(reserve, id);
CREATE INDEX IF NOT EXISTS finder_captured ON finder_watches(captured DESC, id);
CREATE TABLE IF NOT EXISTS finder_facets (watch_id TEXT NOT NULL REFERENCES finder_watches(id) ON DELETE CASCADE, facet TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(facet,value,watch_id));
CREATE INDEX IF NOT EXISTS finder_watch_facets ON finder_facets(watch_id,facet,value);
-- A price is a fact with a source and currency, not a property that can be blindly compared.
CREATE TABLE IF NOT EXISTS finder_prices (watch_id TEXT NOT NULL REFERENCES finder_watches(id) ON DELETE CASCADE, source TEXT NOT NULL, currency TEXT NOT NULL, amount REAL NOT NULL CHECK(amount>0), market TEXT, captured TEXT, PRIMARY KEY(watch_id,source,currency));
CREATE INDEX IF NOT EXISTS finder_price_range ON finder_prices(source,currency,amount,watch_id);
CREATE VIRTUAL TABLE IF NOT EXISTS finder_fts USING fts5(identity,reference_key,aliases,specs,content, tokenize='unicode61 remove_diacritics 2', prefix='2 3 4');
CREATE TABLE IF NOT EXISTS finder_meta (key TEXT PRIMARY KEY,value TEXT NOT NULL);

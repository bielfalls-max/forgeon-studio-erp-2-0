CREATE TABLE product_identities(identity_key TEXT PRIMARY KEY,product_id INTEGER NOT NULL REFERENCES products(id));
CREATE TABLE product_merges(source_id INTEGER PRIMARY KEY REFERENCES products(id),target_id INTEGER NOT NULL REFERENCES products(id),recorded TEXT NOT NULL,detail TEXT NOT NULL);
PRAGMA user_version=6;
INSERT INTO audit(operation,detail) VALUES('migracao_esquema','{"from":5,"to":6}');

CREATE TABLE supplies(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,category TEXT NOT NULL,unit TEXT NOT NULL,unit_cents TEXT NOT NULL DEFAULT '0',minimum TEXT NOT NULL DEFAULT '0');
CREATE TABLE supply_purchases(id INTEGER PRIMARY KEY,supply_id INTEGER NOT NULL REFERENCES supplies(id),date TEXT NOT NULL,quantity TEXT NOT NULL,amount_cents INTEGER NOT NULL,freight_cents INTEGER NOT NULL);
CREATE TABLE product_supplies(product_id INTEGER NOT NULL REFERENCES products(id),supply_id INTEGER NOT NULL REFERENCES supplies(id),quantity TEXT NOT NULL,PRIMARY KEY(product_id,supply_id));
PRAGMA user_version=5;
INSERT INTO audit(operation,detail) VALUES('migracao_esquema','{"from":4,"to":5}');

CREATE TABLE order_financials(
 order_id TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
 detail TEXT NOT NULL);
CREATE TABLE item_usage(
 item_id INTEGER PRIMARY KEY REFERENCES order_items(id) ON DELETE CASCADE,
 detail TEXT NOT NULL, recorded TEXT NOT NULL);
CREATE TABLE product_slices(
 product_id INTEGER PRIMARY KEY REFERENCES products(id),
 detail TEXT NOT NULL, recorded TEXT NOT NULL);
PRAGMA user_version = 2;
INSERT INTO audit(operation,detail) VALUES('migracao_esquema','{"from":1,"to":2}');

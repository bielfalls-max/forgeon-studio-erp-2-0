PRAGMA application_id = 1179797298;
PRAGMA user_version = 1;
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT INTO meta VALUES('project','forgeon-studio-erp-2-new');
CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE products(
 id INTEGER PRIMARY KEY, name TEXT NOT NULL CHECK(length(trim(name))>0), model TEXT NOT NULL DEFAULT '',
 weight TEXT NOT NULL DEFAULT '0', hours TEXT NOT NULL DEFAULT '0', manual_cents INTEGER CHECK(manual_cents>=0),
 packaging_cents INTEGER NOT NULL DEFAULT 0 CHECK(packaging_cents>=0), other_cents INTEGER NOT NULL DEFAULT 0 CHECK(other_cents>=0),
 notes TEXT NOT NULL DEFAULT '', archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN(0,1)));
CREATE TABLE filaments(id INTEGER PRIMARY KEY, material TEXT NOT NULL, color TEXT NOT NULL, kg_cents INTEGER NOT NULL CHECK(kg_cents>=0), UNIQUE(material,color));
CREATE TABLE product_colors(product_id INTEGER NOT NULL REFERENCES products(id), filament_id INTEGER NOT NULL REFERENCES filaments(id), grams TEXT NOT NULL,
 PRIMARY KEY(product_id,filament_id));
CREATE TABLE sku_codes(code TEXT PRIMARY KEY CHECK(length(trim(code))>0), state TEXT NOT NULL CHECK(state IN('reservado','usado','aposentado')));
CREATE TABLE origins(id INTEGER PRIMARY KEY, source TEXT NOT NULL DEFAULT 'Shopee', listing TEXT NOT NULL, variation TEXT NOT NULL DEFAULT '', sku TEXT NOT NULL DEFAULT '',
 product_id INTEGER REFERENCES products(id), active INTEGER NOT NULL DEFAULT 1,
 UNIQUE(source,listing,variation,sku));
CREATE TABLE orders(id TEXT PRIMARY KEY, date TEXT NOT NULL, status TEXT NOT NULL, gross_cents INTEGER NOT NULL CHECK(gross_cents>=0),
 fees_cents INTEGER NOT NULL DEFAULT 0 CHECK(fees_cents>=0), refund_cents INTEGER NOT NULL DEFAULT 0 CHECK(refund_cents>=0),
 source TEXT NOT NULL, partial INTEGER NOT NULL DEFAULT 0, updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id), item_key TEXT NOT NULL,
 origin_id INTEGER REFERENCES origins(id), product_id INTEGER REFERENCES products(id), original_sku TEXT NOT NULL,
 title TEXT NOT NULL, variation TEXT NOT NULL, qty INTEGER NOT NULL CHECK(qty>0), unit_cents INTEGER NOT NULL CHECK(unit_cents>=0),
 cost_cents INTEGER, cost_detail TEXT, cost_at TEXT, UNIQUE(order_id,item_key));
CREATE TABLE expenses(id INTEGER PRIMARY KEY, date TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>=0));
CREATE TABLE purchases(id INTEGER PRIMARY KEY, date TEXT NOT NULL, filament_id INTEGER NOT NULL REFERENCES filaments(id), grams TEXT NOT NULL,
 amount_cents INTEGER NOT NULL CHECK(amount_cents>=0), freight_cents INTEGER NOT NULL CHECK(freight_cents>=0));
CREATE TABLE stats(id INTEGER PRIMARY KEY, source TEXT NOT NULL DEFAULT 'Shopee', start TEXT NOT NULL, end TEXT NOT NULL, listing TEXT NOT NULL,
 revenue_cents INTEGER NOT NULL CHECK(revenue_cents>=0), orders_count INTEGER NOT NULL CHECK(orders_count>=0), partial INTEGER NOT NULL,
 UNIQUE(source,start,end,listing));
CREATE TABLE audit(id INTEGER PRIMARY KEY, date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, operation TEXT NOT NULL, detail TEXT NOT NULL);
CREATE INDEX items_product ON order_items(product_id);
CREATE INDEX orders_date ON orders(date);

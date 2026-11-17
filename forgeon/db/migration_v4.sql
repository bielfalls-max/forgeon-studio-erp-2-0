CREATE TABLE shop_metrics(basis TEXT NOT NULL CHECK(basis IN('pedido_feito','produto_pago')),grain TEXT NOT NULL CHECK(grain IN('month','day','period')),period_key TEXT NOT NULL,start TEXT NOT NULL,end TEXT NOT NULL,detail TEXT NOT NULL,source_hash TEXT NOT NULL,recorded TEXT NOT NULL,PRIMARY KEY(basis,grain,period_key));
CREATE TABLE order_coverage(start TEXT NOT NULL,end TEXT NOT NULL,kind TEXT NOT NULL,source_hash TEXT NOT NULL DEFAULT '',recorded TEXT NOT NULL,PRIMARY KEY(start,end,kind));
PRAGMA user_version=4;
INSERT INTO audit(operation,detail) VALUES('migracao_esquema','{"from":3,"to":4}');

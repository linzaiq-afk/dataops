CREATE SCHEMA IF NOT EXISTS raw;

-- Снимок операционной PostgreSQL (РСУБД-источник).
CREATE TABLE IF NOT EXISTS raw.raw_customers (
    customer_id TEXT NOT NULL,
    customer_unique_id TEXT,
    customer_zip_code_prefix TEXT,
    customer_city TEXT,
    customer_state TEXT,
    source_system TEXT NOT NULL DEFAULT 'ops_postgres',
    batch_id TEXT NOT NULL,
    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (customer_id, batch_id)
);

CREATE TABLE IF NOT EXISTS raw.raw_orders (
    order_id TEXT NOT NULL,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP,
    source_system TEXT NOT NULL DEFAULT 'ops_postgres',
    batch_id TEXT NOT NULL,
    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (order_id, batch_id)
);

-- Возвраты из CSV (файловый источник).
CREATE TABLE IF NOT EXISTS raw.raw_returns (
    return_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    return_date TIMESTAMP,
    return_reason TEXT,
    refund_amount NUMERIC(12, 2),
    source_system TEXT NOT NULL DEFAULT 'returns_csv',
    batch_id TEXT NOT NULL,
    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (return_id, batch_id)
);

-- Остатки/цены товаров из DummyJSON (REST API).
CREATE TABLE IF NOT EXISTS raw.raw_inventory (
    product_id BIGINT NOT NULL,
    title TEXT,
    price NUMERIC(12, 2),
    stock INTEGER,
    rating NUMERIC(3, 2),
    availability_status TEXT,
    source_system TEXT NOT NULL DEFAULT 'dummyjson',
    batch_id TEXT NOT NULL,
    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (product_id, batch_id)
);

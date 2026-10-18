-- Billo · Tiger Data [MLH] schema (TimescaleDB on Tiger Cloud)
-- Run:  psql "$DATABASE_URL" -f backend/database/schema.sql
-- Needs TimescaleDB 2.13+ (by_range) and timescaledb_toolkit (percentile_agg). Both are on Tiger Cloud.

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit;
-- Optional (stretch): CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Hospital price history (from CMS price-transparency files) ------------------------
CREATE TABLE IF NOT EXISTS hospital_prices (
  posted_at     TIMESTAMPTZ NOT NULL,
  hospital_npi  TEXT        NOT NULL,
  kind          TEXT        NOT NULL,   -- urgent_care | clinic | er
  region        TEXT        NOT NULL,   -- e.g. los-angeles
  code          TEXT        NOT NULL,   -- CPT / HCPCS
  price         NUMERIC     NOT NULL,
  source_id     TEXT
);
SELECT create_hypertable('hospital_prices', by_range('posted_at'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS hospital_prices_code_idx ON hospital_prices (code, region, posted_at DESC);

-- Columnstore (90%+ compression). If your Timescale version is older, use compression instead.
ALTER TABLE hospital_prices SET (timescaledb.enable_columnstore = true, timescaledb.segmentby = 'code, region');
CALL add_columnstore_policy('hospital_prices', after => INTERVAL '30 days', if_not_exists => TRUE);

-- 2. Price stats per code (continuous aggregate with percentile sketches) --------------
CREATE MATERIALIZED VIEW IF NOT EXISTS price_stats_monthly
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 month', posted_at) AS bucket, code, region, kind,
       percentile_agg(price) AS pct, count(*) AS n
FROM hospital_prices
GROUP BY bucket, code, region, kind
WITH NO DATA;
SELECT add_continuous_aggregate_policy('price_stats_monthly',
  start_offset => INTERVAL '2 years', end_offset => INTERVAL '1 day', schedule_interval => INTERVAL '1 hour',
  if_not_exists => TRUE);

-- 3. Estimates and after-care records ---------------------------------------------------
CREATE TABLE IF NOT EXISTS estimates (
  case_id TEXT NOT NULL, provider_npi TEXT, code TEXT, amount NUMERIC NOT NULL, place TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS flags (
  case_id TEXT NOT NULL, rule_id TEXT NOT NULL, kind TEXT NOT NULL, line_nos INT[],
  amount_at_stake NUMERIC, rules_check BOOLEAN, price_check BOOLEAN, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS after_care_records (
  record_id BIGSERIAL PRIMARY KEY, case_id TEXT NOT NULL, provider_npi TEXT,
  total NUMERIC NOT NULL, already_paid BOOLEAN NOT NULL DEFAULT false,
  payment_status TEXT NOT NULL DEFAULT 'unknown', provider_match BOOLEAN NOT NULL,
  estimate_amount NUMERIC, estimate_difference NUMERIC, visit_items_matched INT NOT NULL DEFAULT 0,
  payload JSONB NOT NULL, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS settlements (
  settlement_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
  direction TEXT NOT NULL, rail TEXT NOT NULL, amount NUMERIC, currency TEXT NOT NULL DEFAULT 'USD',
  status TEXT NOT NULL, external_ref TEXT, payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS settlements_case_idx ON settlements (case_id, created_at DESC);

-- 4. Live visit log (real-time running estimate) ---------------------------------------
CREATE TABLE IF NOT EXISTS visit_events (
  time TIMESTAMPTZ NOT NULL DEFAULT now(),
  case_id TEXT NOT NULL, item TEXT, code TEXT, est_price NUMERIC, source_id TEXT
);
SELECT create_hypertable('visit_events', by_range('time'), if_not_exists => TRUE);

-- materialized_only = false makes it REAL-TIME: it includes rows written one second ago.
CREATE MATERIALIZED VIEW IF NOT EXISTS visit_running_total
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT case_id, time_bucket('5 minutes', time) AS bucket, sum(est_price) AS est_total, count(*) AS items
FROM visit_events
GROUP BY case_id, bucket
WITH NO DATA;

-- 5. iMessage QR follow codes (method from News Next Door) -----------------------------
CREATE TABLE IF NOT EXISTS link_codes (
  code TEXT PRIMARY KEY, case_id TEXT NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL DEFAULT 'waiting',   -- waiting | linked | stopped | expired
  handle_hash TEXT, space_id TEXT, created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. Events for team metrics (no health data) ------------------------------------------
CREATE TABLE IF NOT EXISTS billo_events (
  time TIMESTAMPTZ NOT NULL DEFAULT now(), case_hash TEXT, agent TEXT, event_type TEXT,
  latency_ms INT, amount NUMERIC, payload JSONB
);
SELECT create_hypertable('billo_events', by_range('time'), if_not_exists => TRUE);
SELECT add_retention_policy('billo_events', INTERVAL '90 days', if_not_exists => TRUE);

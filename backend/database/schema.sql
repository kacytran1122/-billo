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
  payload JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE estimates ADD COLUMN IF NOT EXISTS payload JSONB;
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
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE settlements ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
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
  handle_hash TEXT, space_id TEXT, channel TEXT NOT NULL DEFAULT 'imessage',
  claimed_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE link_codes ADD COLUMN IF NOT EXISTS channel TEXT NOT NULL DEFAULT 'imessage';
ALTER TABLE link_codes ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;

-- Bearer values are never stored. token_hash is SHA-256(token); the token itself
-- is a 256-bit HMAC returned only to the intended conversation.
CREATE TABLE IF NOT EXISTS public_access_tokens (
  token_hash TEXT PRIMARY KEY, scope TEXT NOT NULL, case_id TEXT NOT NULL,
  subject_id TEXT NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (scope, subject_id)
);
CREATE INDEX IF NOT EXISTS public_access_tokens_expiry_idx ON public_access_tokens (expires_at);

-- Current asynchronous worker request authorized to mutate each case domain.
-- A newer request replaces the previous row. Successful terminal writes retain
-- only a minimal, non-bearer delivery result for bounded reconciliation and
-- idempotent replay; Core treats completed rows older than 15 minutes inactive.
CREATE TABLE IF NOT EXISTS active_operations (
  case_id TEXT PRIMARY KEY, kind TEXT NOT NULL, request_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active', action TEXT NOT NULL DEFAULT '', result JSONB,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (kind IN ('after_care', 'settlement')),
  CHECK (status IN ('active', 'completed'))
);
ALTER TABLE active_operations ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE active_operations ADD COLUMN IF NOT EXISTS action TEXT NOT NULL DEFAULT '';
ALTER TABLE active_operations ADD COLUMN IF NOT EXISTS result JSONB;
DELETE FROM active_operations
WHERE ctid IN (
  SELECT ctid FROM (
    SELECT ctid, row_number() OVER (
      PARTITION BY case_id ORDER BY updated_at DESC, kind DESC
    ) AS duplicate_number
    FROM active_operations
  ) ranked
  WHERE duplicate_number > 1
);
CREATE UNIQUE INDEX IF NOT EXISTS active_operations_case_unique ON active_operations (case_id);
CREATE INDEX IF NOT EXISTS active_operations_updated_idx ON active_operations (updated_at);

-- 6. Events for team metrics (no health data) ------------------------------------------
CREATE TABLE IF NOT EXISTS billo_events (
  time TIMESTAMPTZ NOT NULL DEFAULT now(), case_hash TEXT, agent TEXT, event_type TEXT,
  latency_ms INT, amount NUMERIC, payload JSONB
);
SELECT create_hypertable('billo_events', by_range('time'), if_not_exists => TRUE);
SELECT add_retention_policy('billo_events', INTERVAL '90 days', if_not_exists => TRUE);

"""Load price rows into Tiger Data.

  python scripts/load_prices.py                       # the synthetic demo CSV
  python scripts/load_prices.py path/to/cms_file.csv  # your cleaned CMS extract with the same columns:
                                                      # posted_at,hospital_npi,kind,region,code,price
Real CMS price-transparency files are huge and differ per hospital: clean 3-5 LA hospitals and ~50 codes
into this CSV shape first (task D2 in AGENTS.md).
"""
import csv
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "synthetic" / "prices.csv"

with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn, open(path) as f:
    rows = list(csv.DictReader(f))
    with conn.cursor().copy("COPY hospital_prices (posted_at, hospital_npi, kind, region, code, price, source_id) FROM STDIN") as cp:
        for r in rows:
            cp.write_row((r["posted_at"], r["hospital_npi"], r["kind"], r["region"], r["code"], r["price"], path.name))
    conn.execute("CALL refresh_continuous_aggregate('price_stats_monthly', NULL, NULL)")
print(f"loaded {len(rows)} rows from {path.name} and refreshed price_stats_monthly")

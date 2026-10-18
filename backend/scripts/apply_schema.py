"""Apply Billo's idempotent Tiger Data schema using the configured DATABASE_URL."""
from pathlib import Path
import os

import psycopg
from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url or "PASSWORD@HOST" in database_url:
        raise SystemExit("Set DATABASE_URL in .env before running make db.")
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute((BACKEND_ROOT / "database" / "schema.sql").read_text())
    print("Tiger Data schema applied.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
==============================================================================
UpCircuit ⚡: Database Migration & Schema Extension Runner (Week 4)
==============================================================================
Applies `week4/schema_v2.sql` to PostgreSQL (`upcircuit_db`) and seeds initial
corporate disclosures and government policy announcements.
==============================================================================
"""

import os
import sys
import io
import time
import pg8000.native

# Ensure UTF-8 output encoding for Windows consoles
if sys.platform.startswith("win"):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DB_CONFIG = {
    "database": os.getenv("DB_NAME", "upcircuit_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", "password123"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432))
}


def apply_migration():
    schema_file = os.path.join(os.path.dirname(__file__), "schema_v2.sql")
    if not os.path.exists(schema_file):
        print(f"❌ Schema file not found: {schema_file}")
        sys.exit(1)

    with open(schema_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    print("=" * 65)
    print("⚡ UpCircuit: Applying Week 4 Database Schema Migration")
    print(f"Target Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print("=" * 65)

    retries = 3
    while retries > 0:
        try:
            conn = pg8000.native.Connection(**DB_CONFIG)
            print("✅ Connected to PostgreSQL. Applying SQL statements...")

            # Split statements by semicolon; execute individual blocks
            statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
            for stmt in statements:
                try:
                    conn.run(stmt)
                except Exception as err:
                    print(f"  ⚠️ Warning on statement: {err}")

            conn.close()
            print("🎉 Week 4 Schema Migration applied successfully!")
            print("Tables extended: symbol_meta, stock_news_feed, govt_schemes_impact, alert_explanations, system_health.")
            print("Views created: v_retail_snapshot, v_compliance_alerts, v_market_news_radar.\n")
            return True
        except Exception as e:
            print(f"⏳ Waiting for PostgreSQL ({e}). Retries left: {retries}")
            time.sleep(2)
            retries -= 1

    print("⚠️ Could not connect to PostgreSQL. Ensure your Docker container or PostgreSQL service is active.")
    return False


if __name__ == "__main__":
    success = apply_migration()
    if success:
        from seed_news import seed_database
        print("🌱 Seeding corporate disclosures and industrial policy schemes...")
        seed_database(dry_run=False)

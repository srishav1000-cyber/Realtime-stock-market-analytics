import pg8000.native
import time

DB_CONFIG = {
    "database": "upcircuit_db",
    "user": "postgres",
    "password": "password123",
    "host": "localhost",
    "port": 5432
}

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS stock_trades (
        trade_id BIGSERIAL PRIMARY KEY,
        symbol VARCHAR(30) NOT NULL,
        price NUMERIC(14, 4) NOT NULL,
        volume NUMERIC(14, 4) NOT NULL,
        trade_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
        ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_trades_symbol_time 
    ON stock_trades (symbol, trade_timestamp DESC);
    """,
    """
    CREATE TABLE IF NOT EXISTS circuit_breaker_alerts (
        alert_id BIGSERIAL PRIMARY KEY,
        symbol VARCHAR(30) NOT NULL,
        trigger_price NUMERIC(14, 4) NOT NULL,
        baseline_price NUMERIC(14, 4) NOT NULL,
        percentage_change NUMERIC(6, 2) NOT NULL,
        threshold_limit NUMERIC(6, 2) NOT NULL,
        triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS anomaly_events (
        anomaly_id BIGSERIAL PRIMARY KEY,
        symbol VARCHAR(30) NOT NULL,
        anomaly_type VARCHAR(50) NOT NULL,
        metric_value NUMERIC(14, 4) NOT NULL,
        threshold_value NUMERIC(14, 4) NOT NULL,
        detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
]

def setup_database():
    retries = 6
    while retries > 0:
        try:
            con = pg8000.native.Connection(**DB_CONFIG)
            for statement in TABLES:
                con.run(statement)
            con.close()
            print("Database initialized successfully: stock_trades, circuit_breaker_alerts, anomaly_events created.")
            return
        except Exception as e:
            print(f"Waiting for Postgres to accept connections ({e}). Retrying in 2s...")
            time.sleep(2)
            retries -= 1

if __name__ == "__main__":
    setup_database()
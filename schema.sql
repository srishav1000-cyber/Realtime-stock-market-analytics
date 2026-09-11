-- PostgreSQL Database Schema

CREATE TABLE stock_trades (
    trade_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    trade_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE circuit_breaker_alerts (
    alert_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    trigger_price NUMERIC(10, 2) NOT NULL,
    percentage_change NUMERIC(5, 2) NOT NULL,
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

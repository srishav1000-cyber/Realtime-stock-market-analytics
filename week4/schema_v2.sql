-- ==============================================================================
-- UpCircuit ⚡: Real-Time Stock Market Surveillance & Trading Engine
-- Week 4 Complete PostgreSQL Schema (Production Schema v2)
-- ==============================================================================

-- 1. Raw Stock Trades Ingestion Ledger
CREATE TABLE IF NOT EXISTS stock_trades (
    trade_id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(30) NOT NULL,
    price NUMERIC(14, 4) NOT NULL,
    volume NUMERIC(14, 4) NOT NULL,
    trade_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trades_symbol_time 
    ON stock_trades (symbol, trade_timestamp DESC);

-- 2. Symbol Metadata Table
CREATE TABLE IF NOT EXISTS symbol_meta (
    symbol VARCHAR(30) PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector TEXT NOT NULL,
    exchange VARCHAR(10) DEFAULT 'NSE',
    cap_class VARCHAR(20) DEFAULT 'LARGE'
);

-- Seed Comprehensive NIFTY 50 and Tracked Equities Metadata
INSERT INTO symbol_meta (symbol, company_name, sector, exchange, cap_class) VALUES
    ('RELIANCE', 'Reliance Industries Ltd.', 'Energy & Petrochemicals', 'NSE', 'LARGE'),
    ('TCS', 'Tata Consultancy Services Ltd.', 'Information Technology', 'NSE', 'LARGE'),
    ('HDFCBANK', 'HDFC Bank Ltd.', 'Banking & Financial Services', 'NSE', 'LARGE'),
    ('INFY', 'Infosys Ltd.', 'Information Technology', 'NSE', 'LARGE'),
    ('ICICIBANK', 'ICICI Bank Ltd.', 'Banking & Financial Services', 'NSE', 'LARGE'),
    ('TATAMOTORS', 'Tata Motors Ltd.', 'Automotive', 'NSE', 'LARGE'),
    ('KOTAKBANK', 'Kotak Mahindra Bank Ltd.', 'Banking & Financial Services', 'NSE', 'LARGE'),
    ('SBIN', 'State Bank of India', 'Public Sector Banking', 'NSE', 'LARGE'),
    ('APOLLOTYRE', 'Apollo Tyres Ltd.', 'Automotive & Ancillary', 'NSE', 'MID'),
    ('LT', 'Larsen & Toubro Ltd.', 'Capital Goods & Infrastructure', 'NSE', 'LARGE'),
    ('ADANIGREEN', 'Adani Green Energy Ltd.', 'Renewable Energy', 'NSE', 'LARGE'),
    ('HAL', 'Hindustan Aeronautics Ltd.', 'Defense & Aerospace', 'NSE', 'LARGE'),
    ('BEL', 'Bharat Electronics Ltd.', 'Defense Electronics', 'NSE', 'LARGE')
ON CONFLICT (symbol) DO UPDATE SET
    company_name = EXCLUDED.company_name,
    sector = EXCLUDED.sector,
    exchange = EXCLUDED.exchange,
    cap_class = EXCLUDED.cap_class;

-- 3. Stock News Feed (Corporate Orders, Filings, Disclosures)
CREATE TABLE IF NOT EXISTS stock_news_feed (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(30) NOT NULL,
    headline TEXT NOT NULL,
    summary TEXT,
    source VARCHAR(100) DEFAULT 'NSE_DISCLOSURES',
    sentiment VARCHAR(20) CHECK (sentiment IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
    impact_amount_cr NUMERIC(14, 2) DEFAULT 0.00,
    published_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stock_news_symbol_pub 
    ON stock_news_feed (symbol, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_stock_news_sentiment 
    ON stock_news_feed (sentiment);

-- 4. Government Policy & Schemes Impact Radar
CREATE TABLE IF NOT EXISTS govt_schemes_impact (
    id BIGSERIAL PRIMARY KEY,
    scheme_name VARCHAR(150) NOT NULL,
    impacted_sectors TEXT[] NOT NULL,
    policy_summary TEXT NOT NULL,
    bullish_symbols TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Circuit Breaker Surveillance Alerts
CREATE TABLE IF NOT EXISTS circuit_breaker_alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(30) NOT NULL,
    trigger_price NUMERIC(14, 4) NOT NULL,
    baseline_price NUMERIC(14, 4) NOT NULL,
    percentage_change NUMERIC(6, 2) NOT NULL,
    threshold_limit NUMERIC(6, 2) NOT NULL,
    severity VARCHAR(10) DEFAULT 'MEDIUM' CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH')),
    review_status VARCHAR(20) DEFAULT 'OPEN' CHECK (review_status IN ('OPEN', 'REVIEWED', 'ESCALATED')),
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    officer_notes TEXT,
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_status 
    ON circuit_breaker_alerts (review_status, triggered_at DESC);

-- 6. AI Alert Explanations Table (Foreign Key to circuit_breaker_alerts)
CREATE TABLE IF NOT EXISTS alert_explanations (
    alert_id BIGINT PRIMARY KEY REFERENCES circuit_breaker_alerts(alert_id) ON DELETE CASCADE,
    model VARCHAR(50) NOT NULL,
    summary TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Exchange Admin System Health Telemetry
CREATE TABLE IF NOT EXISTS system_health (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW(),
    ticks_per_sec REAL NOT NULL,
    consumer_lag INT DEFAULT 0,
    alert_latency_ms REAL DEFAULT 0.0,
    source VARCHAR(50) DEFAULT 'NSE_LIVE_ENGINE'
);

CREATE INDEX IF NOT EXISTS idx_system_health_ts 
    ON system_health (ts DESC);

-- ============================================================================
-- 8. STAKEHOLDER VIEWS
-- ============================================================================

-- View A: Retail Snapshot View (LTP, Rolling 50-tick VWAP, and Volatility)
CREATE OR REPLACE VIEW v_retail_snapshot AS
WITH latest_trades AS (
    SELECT DISTINCT ON (symbol)
        symbol,
        price AS ltp,
        volume,
        trade_timestamp AS ts
    FROM stock_trades
    ORDER BY symbol, trade_timestamp DESC
),
recent_metrics AS (
    SELECT 
        symbol,
        ROUND(SUM(price * volume) / NULLIF(SUM(volume), 0), 2) AS vwap,
        ROUND(COALESCE(STDDEV_SAMP(price), 0.00), 2) AS volatility,
        COUNT(*) AS trade_count,
        SUM(volume) AS total_volume
    FROM (
        SELECT symbol, price, volume,
               ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_timestamp DESC) AS rn
        FROM stock_trades
    ) t
    WHERE t.rn <= 50
    GROUP BY symbol
)
SELECT 
    lt.symbol,
    COALESCE(m.company_name, lt.symbol) AS company_name,
    COALESCE(m.sector, 'N/A') AS sector,
    COALESCE(m.cap_class, 'LARGE') AS cap_class,
    lt.ltp,
    COALESCE(rm.vwap, lt.ltp) AS vwap,
    COALESCE(rm.volatility, 0.00) AS volatility,
    lt.volume AS latest_tick_volume,
    COALESCE(rm.total_volume, lt.volume) AS window_volume,
    lt.ts AS last_trade_time
FROM latest_trades lt
LEFT JOIN symbol_meta m ON lt.symbol = m.symbol
LEFT JOIN recent_metrics rm ON lt.symbol = rm.symbol
ORDER BY lt.symbol ASC;

-- View B: Compliance Audit View (Alerts joined with AI Explanations and Review Metadata)
CREATE OR REPLACE VIEW v_compliance_alerts AS
SELECT 
    a.alert_id,
    a.symbol,
    COALESCE(m.company_name, a.symbol) AS company_name,
    COALESCE(m.sector, 'N/A') AS sector,
    a.trigger_price,
    a.baseline_price,
    a.percentage_change,
    a.threshold_limit,
    COALESCE(a.severity, 'MEDIUM') AS severity,
    COALESCE(a.review_status, 'OPEN') AS review_status,
    a.reviewed_by,
    a.reviewed_at,
    a.officer_notes,
    a.triggered_at,
    e.model AS explanation_model,
    e.summary AS ai_explanation,
    e.created_at AS explained_at
FROM circuit_breaker_alerts a
LEFT JOIN symbol_meta m ON a.symbol = m.symbol
LEFT JOIN alert_explanations e ON a.alert_id = e.alert_id
ORDER BY a.triggered_at DESC;

-- View C: Market News Radar View (News joined with metadata and correlated government policy)
CREATE OR REPLACE VIEW v_market_news_radar AS
SELECT 
    n.id AS news_id,
    n.symbol,
    COALESCE(m.company_name, n.symbol) AS company_name,
    COALESCE(m.sector, 'General') AS sector,
    n.headline,
    n.summary,
    n.source,
    n.sentiment,
    n.impact_amount_cr,
    n.published_at,
    (
        SELECT g.scheme_name 
        FROM govt_schemes_impact g
        WHERE n.symbol = ANY(g.bullish_symbols)
           OR (m.sector IS NOT NULL AND m.sector = ANY(g.impacted_sectors))
        ORDER BY g.created_at DESC LIMIT 1
    ) AS correlated_scheme
FROM stock_news_feed n
LEFT JOIN symbol_meta m ON n.symbol = m.symbol
ORDER BY n.published_at DESC;
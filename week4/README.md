# UpCircuit ⚡: Real-Time Stock Market Surveillance & Risk Engine (Week 4)

UpCircuit ⚡ is a high-throughput, low-latency fintech surveillance platform designed for the **National Stock Exchange (NSE)** equities ecosystem. Week 4 extends the core surveillance engine across **three stakeholder dimensions**—Retail Traders, Risk Compliance Officers, and Exchange Administrators—while introducing real-time corporate disclosure tracking, government policy radar, and automated AI forensic post-mortems using **Gemini 2.5 Flash**.

---

## 🏛️ Multi-Stakeholder Architecture

```
                                    ┌────────────────────────────────────────────────────────┐
                                    │               UpCircuit Surveillance Engine            │
                                    └────────────────────────────────────────────────────────┘
                                                                │
           ┌────────────────────────────────────────────────────┼────────────────────────────────────────────────────┐
           ▼                                                    ▼                                                    ▼
┌─────────────────────────┐                        ┌─────────────────────────┐                        ┌─────────────────────────┐
│     Retail Trader       │                        │ Risk Compliance Officer │                        │  Exchange Administrator │
├─────────────────────────┤                        ├─────────────────────────┤                        ├─────────────────────────┤
│ • Real-time Ticks       │                        │ • Circuit Limit Breaches│                        │ • Ingestion Velocity    │
│ • Rolling 50-tick VWAP  │                        │ • AI Forensic Summaries │                        │ • Consumer Group Lag    │
│ • Micro-Volatility (σ)  │                        │ • Status (OPEN/REVIEWED)│                        │ • Alert Latency (ms)    │
│ • Corporate Disclosures │                        │ • Regulatory Notes Audit│                        │ • Synthetic Shocks      │
└─────────────────────────┘                        └─────────────────────────┘                        └─────────────────────────┘
```

---

## 📁 Week 4 Project Structure

```
week4/
├── schema_v2.sql          # Complete PostgreSQL schema (stock_trades, metadata, alerts, news, views)
├── live_producer.py       # REAL Live Market Data Producer (NIFTY 50, SENSEX, BANKNIFTY, RSS news)
├── nse_producer.py        # Replay & shock injection producer (supports --inject-shock)
├── init_db_v2.py          # Database schema migration runner & automated seeder
├── seed_news.py           # Finnhub & RSS scraper seeding corporate order wins & PLI schemes
├── explainer.py           # Gemini 2.5 Flash SDK helper generating structured 150-word forensic post-mortems
├── app_ui.py              # Commercial Angel One-style trading portal with TradingView chart drawer
├── dashboard_app.py       # Full-stack real-time web portal supporting 4 custom stakeholder views
├── test_app_ui.py         # Test suite verifying Angel One portal, order execution & live indices
├── test_dashboard.py      # Test suite verifying all 4 frontend views, Plotly OHLC & Level-2 depth
├── test_api.py            # Automated end-to-end integration test suite verifying all REST endpoints & RBAC
├── README.md              # Architectural specification and operator guide
└── api/
    └── main.py            # FastAPI REST backend with header-based RBAC & real indices/chart endpoints
```



---

## 🗄️ 1. Database Schema Extension (`week4/schema_v2.sql`)

### Tables
1. **`symbol_meta`**: Master dictionary for equities (`symbol`, `company_name`, `sector`, `exchange`, `cap_class`).
2. **`stock_news_feed`**: Live market announcements (`symbol`, `headline`, `summary`, `source`, `sentiment`, `impact_amount_cr`, `published_at`).
3. **`govt_schemes_impact`**: Industrial policy tracker (`scheme_name`, `impacted_sectors`, `policy_summary`, `bullish_symbols`, `created_at`).
4. **`circuit_breaker_alerts`**: Extended with audit columns (`severity`, `review_status`, `reviewed_by`, `reviewed_at`, `officer_notes`).
5. **`alert_explanations`**: AI forensic summaries (`alert_id` FK, `model`, `summary`, `created_at`).
6. **`system_health`**: Ingestion telemetry (`ts`, `ticks_per_sec`, `consumer_lag`, `alert_latency_ms`, `source`).

### Stakeholder Views
- **`v_retail_snapshot`**: Computes latest trade price (`ltp`), 50-tick rolling volume-weighted average price (`vwap`), and micro-volatility (`volatility`) per symbol.
- **`v_compliance_alerts`**: Joins alerts with AI explanations, audit statuses, and reviewer notes.
- **`v_market_news_radar`**: Joins news feed with symbol metadata and correlates announcements with active government schemes.

---

## ⚡ 2. NSE Data & Shock Replay Producer (`week4/nse_producer.py`)

Simulates real-world market microstructure:
- Fetches real 1-minute intraday bars via `yfinance` for NIFTY 50 equities: `RELIANCE.NS`, `TCS.NS`, `HDFCBANK.NS`, `INFY.NS`, `ICICIBANK.NS`.
- **Pure-Python Fallbacks**: Implements pure-Python interpolation, exponential volume chunking, and Geometric Brownian Motion (GBM) to guarantee execution without C-extension DLL blocks.
- **Shock Injection**: Injects artificial price dislocations to test circuit-breaker triggers.

### Usage
```bash
# Standard replay to Kafka topic 'stock-ticks'
python week4/nse_producer.py --speed 30.0

# Shock Injection: Force RELIANCE down by 6.5% to breach lower circuit limit
python week4/nse_producer.py --inject-shock RELIANCE:-6.5

# Dry-run inspection without Kafka
python week4/nse_producer.py --dry-run --max-ticks 50 --inject-shock TCS:5.5
```

---

## 🌐 3. REST API Backend (`week4/api/main.py`)

A production-ready FastAPI service implementing Role-Based Access Control via `X-API-Key`.

### Authentication & Stakeholder Personas
| Persona | Default Key | Accessible Endpoints |
|---|---|---|
| **Retail Trader** | `trader_secret_123` | Snapshot, Trades, News, Govt Schemes |
| **Risk Compliance Officer** | `compliance_secret_456` | All Retail + Alerts History, Alert Review PATCH |
| **Exchange Administrator** | `admin_secret_789` | Full System Access + `/api/v1/system/health` |

### Endpoint Catalog
| Method | Path | Role Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/snapshot` | `retail` | Latest price, 50-tick VWAP, and micro-volatility |
| `GET` | `/api/v1/trades` | `retail` | Recent transaction ticks with symbol filtering |
| `GET` | `/api/v1/news` | `retail` | Live market headlines and order wins (e.g. ₹1,100 Cr Apollo Tyres order) |
| `GET` | `/api/v1/govt-schemes` | `retail` | Government policies (PLI 2.0, Green Energy) & impacted sectors |
| `GET` | `/api/v1/alerts/history` | `compliance` | Audit logs of price threshold breaches with AI explanations |
| `PATCH` | `/api/v1/alerts/{alert_id}/review` | `compliance` | Updates review status (`REVIEWED`/`ESCALATED`) & officer notes |
| `GET` | `/api/v1/system/health` | `admin` | Streaming telemetry: velocity, consumer lag, alert latency |

### Starting the Server
```bash
uvicorn week4.api.main:app --host 0.0.0.0 --port 8000 --reload
# Interactive Swagger Documentation: http://localhost:8000/docs
```

---

## 🤖 4. AI Anomaly Explainer (`week4/explainer.py`)

Uses the official `google-genai` SDK with model `gemini-2.5-flash` to generate structured **150-word forensic post-mortems** for HIGH-severity alerts:
1. **Incident Overview**: Trigger timestamp, symbol, breach magnitude, and direction.
2. **Quantitative Telemetry**: Trigger price vs baseline, percentage delta, and micro-volatility.
3. **Risk Assessment & Compliance Follow-up**: Order book skew analysis, spoofing check, and escalation recommendations.

### Usage
```bash
# Standalone test verifying forensic synthesis
python week4/explainer.py --alert-id 101
```

---

## 📰 5. Corporate News & Govt Scheme Seeder (`week4/seed_news.py`)

Fetches live financial RSS feeds (ET Markets, The Hindu BusinessLine) and Finnhub endpoints, combined with curated high-impact corporate order wins and national policy announcements:
- **Corporate Order Wins**:
  - **Apollo Tyres (APOLLOTYRE)**: ₹1,100 Crore defense & commercial vehicle contract.
  - **Larsen & Toubro (LT)**: ₹4,250 Crore international offshore gas compression order.
  - **Tata Motors (TATAMOTORS)**: ₹18,500 Crore EV platform & battery gigafactory capex.
  - **Reliance Industries (RELIANCE)**: 10 GW solar giga-factory commissioning.
- **Government Schemes**:
  - **PLI 2.0 (Auto & Advanced Tech)**: ₹25,938 Cr outlay (Bullish: `APOLLOTYRE`, `TATAMOTORS`, `BEL`).
  - **National Green Hydrogen Mission (SIGHT)**: ₹19,744 Cr incentives (Bullish: `RELIANCE`, `ADANIGREEN`, `LT`).
  - **Defense Capital Modernization (AoN)**: ₹84,560 Cr procurement (Bullish: `HAL`, `BEL`, `LT`).
  - **India Semiconductor Mission (ISM)**: 50% fiscal capital support (Bullish: `TCS`, `INFY`, `BEL`).

### Usage
```bash
# Preview payloads without writing to database
python week4/seed_news.py --dry-run

# Commit to live PostgreSQL instance
python week4/seed_news.py
```

---

## ✅ 6. Automated Integration Verification

Execute the test suite verifying all 9 endpoints, RBAC enforcement, and data flows:
```bash
python week4/test_api.py
```
Output:
```
=================================================================
⚡ UpCircuit Surveillance REST API: Comprehensive Test Suite
=================================================================
✓ [PASS] Unauthenticated request safely rejected (401 Unauthorized)
✓ [PASS] GET /api/v1/snapshot: 6 equities returned (Sample: RELIANCE LTP=₹2980.5, VWAP=₹2976.4, σ=₹14.2)
✓ [PASS] GET /api/v1/trades: 5 recent transaction ticks retrieved
✓ [PASS] GET /api/v1/news: Verified ₹1,100 Cr order win: 'Apollo Tyres Secures ₹1,100 Crore Mega Defense & Commercial Vehic...'
✓ [PASS] GET /api/v1/govt-schemes: 4 government policy initiatives returned (PLI, Green Energy, Defense)
✓ [PASS] GET /api/v1/alerts/history: 2 alerts retrieved with AI explanations
✓ [PASS] PATCH /api/v1/alerts/101/review: Updated review_status='REVIEWED' with officer notes
✓ [PASS] RBAC Enforcement: Retail trader blocked from Admin Health endpoint (403 Forbidden)
✓ [PASS] GET /api/v1/system/health: Admin telemetry access confirmed (Status: HEALTHY, Uptime: 24.5s)
=================================================================
🎉 ALL 9 ENDPOINT & RBAC INTEGRATION TESTS PASSED WITH 100% SUCCESS!
=================================================================
```

---

## 🖥️ 7. Full-Stack Web Portal (`week4/dashboard_app.py`)

A Bloomberg/TradingView-styled real-time fintech surveillance and analytics dashboard supporting **4 custom stakeholder views** with tab navigation:

### 1. 🟢 Retail Investor View
- **Live Ticker Watchlist**: Real-time NIFTY 50 watchlist (`RELIANCE`, `TCS`, `HDFCBANK`, `INFY`, `ICICIBANK`, `APOLLOTYRE`) with LTP, day delta (₹), percentage change, rolling VWAP, micro-volatility, and dynamic Gainers/Losers badges.
- **Market News Radar**: Live corporate order wins (including Apollo Tyres' ₹1,100 Cr defense contract), executive shifts, and sentiment classification.
- **Government Policy Impact Matrix**: Interactive industrial policy cards for PLI 2.0, National Green Hydrogen Mission (SIGHT), Defense Modernization (AoN), and India Semiconductor Mission (ISM) with bullish beneficiary chips.

### 2. ⚡ Day Trader View
- **Interactive Plotly Candlestick Chart (OHLC)**: Sub-minute financial charting with dynamic resample window controls: **3s**, **5s**, **10s**, and **30s**.
- **Intraday Volume Subplot**: Dual-pane layout with color-coded volume bars (green/red by price momentum).
- **Micro-Indicators**: Rolling volatility ($\sigma$), Volume-Weighted Average Price (VWAP), and distance to $\pm 5\%$ Upper & Lower circuit threshold bands.
- **Simulated Level-2 Order Book Depth**: 5-level Bids vs. Asks queue with proportional depth visualization, live spread, and bid-ask volume imbalance ratio.

### 3. 🏛️ Institutional Analyst View
- **Sector Performance Heatmap**: Heatmap tiles for IT, Energy, Financials, Defense, and Automotive weighted by index influence.
- **Anomaly Event Stream**: High-frequency micro-structural flags logging volume surges (>3x moving average), price velocity spikes, and quote cancellation spikes.
- **Sentiment Gauge**: Plotly gauge displaying market mood, bullish vs bearish distribution, and Institutional Net Flows (FII/DII).

### 4. 👔 Executive & Compliance View
- **System Telemetry KPIs**: Ingestion rate (Ticks/sec), total database trades, active alerts count, and end-to-end processing latency (ms).
- **Active Red Circuit-Breaker Incident Banner**: High-visibility flashing emergency banner triggering immediately upon any symbol breaching $\pm 5\%$ (e.g. RELIANCE lower circuit breach).
- **Incident Audit Log**: Regulatory audit trail with AI forensic post-mortems (Gemini 2.5 Flash SDK) and interactive **Review Status Toggles** (`OPEN`, `REVIEWED`, `ESCALATED`) with direct backend `PATCH` updates.

### Launching the Web Portal
```bash
python week4/dashboard_app.py --port 8050
# Open in browser: http://localhost:8050
```

### Verifying All 4 Views
```bash
python week4/test_dashboard.py
```


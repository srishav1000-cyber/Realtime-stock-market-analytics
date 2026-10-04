#!/usr/bin/env python3
"""
==============================================================================
UpCircuit ⚡: Multi-Stakeholder Real-Time Stock Analytics & Risk Portal
Week 4: Frontend Web Application
==============================================================================
Features 4 Customized Stakeholder Views via Tab Navigation:
  1. 🟢 Retail Investor View: Live watchlist, market news radar, govt policy matrix
  2. ⚡ Day Trader View: Interactive Plotly Candlestick (OHLC) with 3s/5s/10s/30s resample,
     volume subplot, VWAP/volatility micro-indicators, and Level-2 order book depth
  3. 🏛️ Institutional Analyst View: Sector heatmap, anomaly stream, sentiment gauge
  4. 👔 Executive & Compliance View: System telemetry KPIs, red circuit-breaker incident
     banner, AI forensic post-mortem console, and interactive review status toggles
==============================================================================
"""

import os
import sys
import io
import json
import time
import math
import random
from datetime import datetime, timezone
import urllib.request
import urllib.error

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform.startswith("win"):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from bottle import Bottle, run, request, response

app = Bottle()

# ============================================================================
# CONFIGURATION
# ============================================================================
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ADMIN_KEY = os.getenv("ADMIN_KEY", "admin_secret_789")
COMPLIANCE_KEY = os.getenv("COMPLIANCE_KEY", "compliance_secret_456")
TRADER_KEY = os.getenv("TRADER_KEY", "trader_secret_123")

DB_CONFIG = {
    "database": os.getenv("DB_NAME", "upcircuit_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", "password123"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432))
}

START_TIME = time.time()

# ============================================================================
# IN-MEMORY STATE STORE (Synchronized with FastAPI / PostgreSQL / Simulation)
# ============================================================================
SIMULATED_TICK_HISTORY = {
    "RELIANCE": [],
    "TCS": [],
    "HDFCBANK": [],
    "INFY": [],
    "ICICIBANK": []
}

EQUITY_BASES = {
    "RELIANCE": {"base": 2980.50, "curr": 2980.50, "name": "Reliance Industries Ltd.", "sector": "Energy & Petrochemicals", "vol": 14.20},
    "TCS": {"base": 4210.00, "curr": 4210.00, "name": "Tata Consultancy Services Ltd.", "sector": "Information Technology", "vol": 18.50},
    "HDFCBANK": {"base": 1640.25, "curr": 1640.25, "name": "HDFC Bank Ltd.", "sector": "Banking & Financial Services", "vol": 8.75},
    "INFY": {"base": 1865.80, "curr": 1865.80, "name": "Infosys Ltd.", "sector": "Information Technology", "vol": 11.40},
    "ICICIBANK": {"base": 1235.40, "curr": 1235.40, "name": "ICICI Bank Ltd.", "sector": "Banking & Financial Services", "vol": 6.80}
}

# Pre-seed initial 120 ticks per symbol for rich candlestick visualization
def init_simulated_ticks():
    now = time.time()
    for sym, meta in EQUITY_BASES.items():
        p = meta["base"]
        for i in range(120, 0, -1):
            t = now - (i * 2.5)
            p = round(p + random.gauss(0, meta["vol"] * 0.15), 2)
            # Ensure within ±5.5%
            min_p = meta["base"] * 0.945
            max_p = meta["base"] * 1.055
            p = max(min(p, max_p), min_p)
            vol = int(random.expovariate(1 / 450) + 50)
            SIMULATED_TICK_HISTORY[sym].append({
                "time": datetime.fromtimestamp(t, tz=timezone.utc).isoformat(),
                "price": p,
                "volume": vol
            })
        meta["curr"] = p

init_simulated_ticks()

LIVE_ALERTS = [
    {
        "alert_id": 101,
        "symbol": "RELIANCE",
        "company_name": "Reliance Industries Ltd.",
        "trigger_price": 2786.61,
        "baseline_price": 2980.50,
        "percentage_change": -6.50,
        "threshold_limit": 5.0,
        "severity": "HIGH",
        "review_status": "OPEN",
        "reviewed_by": None,
        "reviewed_at": None,
        "officer_notes": None,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "ai_explanation": (
            "1. Incident Overview: At 09:42:15 UTC, RELIANCE triggered an anomalous Lower Circuit breach after "
            "experiencing a steep -6.50% drop, violating the NSE ±5.0% threshold.\n"
            "2. Quantitative Telemetry: Baseline price deviated from ₹2,980.50 to execution price ₹2,786.61. "
            "Pre-breach 30-tick micro-volatility spiked to σ = ₹84.10 with rapid institutional sell liquidation.\n"
            "3. Risk Assessment & Recommended Compliance Follow-up: Flagged as HIGH-severity. Recommend auditing "
            "algorithmic execution IDs and member broker quote cancellation ratios before order matching resumption."
        )
    },
    {
        "alert_id": 102,
        "symbol": "APOLLOTYRE",
        "company_name": "Apollo Tyres Ltd.",
        "trigger_price": 539.80,
        "baseline_price": 508.00,
        "percentage_change": 6.26,
        "threshold_limit": 5.0,
        "severity": "MEDIUM",
        "review_status": "REVIEWED",
        "reviewed_by": "Compliance_Officer_Verma",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "officer_notes": "Upper circuit price spike verified genuine due to ₹1,100 Crore defense OEM contract disclosure.",
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "ai_explanation": (
            "1. Incident Overview: APOLLOTYRE breached Upper Circuit threshold (+6.26%) following heavy buying momentum.\n"
            "2. Quantitative Telemetry: Asset surged from ₹508.00 to ₹539.80 with volume expanding 4.8x.\n"
            "3. Risk Assessment & Recommended Compliance Follow-up: Surge correlated with material disclosure of ₹1,100 Cr supply contract. Review concluded."
        )
    }
]

LIVE_NEWS = [
    {
        "id": 1,
        "symbol": "APOLLOTYRE",
        "company_name": "Apollo Tyres Ltd.",
        "headline": "Apollo Tyres Secures ₹1,100 Crore Mega Defense & Commercial Vehicle Supply Contract",
        "summary": "Apollo Tyres bags landmark multi-year contract worth ₹1,100 Crore to supply specialized heavy-duty radial tires for defense tactical vehicles and commercial OEM fleets across India and Europe.",
        "source": "NSE_DISCLOSURES",
        "sentiment": "BULLISH",
        "impact_amount_cr": 1100.00,
        "time": "10 mins ago",
        "correlated_scheme": "Production Linked Incentive (PLI) Scheme 2.0 - Auto & Advanced Tech"
    },
    {
        "id": 2,
        "symbol": "LT",
        "company_name": "Larsen & Toubro Ltd.",
        "headline": "Larsen & Toubro Bags Mega ₹4,250 Crore International Gas Compression Order",
        "summary": "L&T Hydrocarbon business secures major contract valued at ₹4,250 Crore from a leading Middle Eastern energy operator for offshore gas processing and pipeline facilities.",
        "source": "NSE_DISCLOSURES",
        "sentiment": "BULLISH",
        "impact_amount_cr": 4250.00,
        "time": "25 mins ago",
        "correlated_scheme": "National Infrastructure Pipeline (NIP) Capex Allocation"
    },
    {
        "id": 3,
        "symbol": "TATAMOTORS",
        "company_name": "Tata Motors Ltd.",
        "headline": "Tata Motors Commits ₹18,500 Crore Capex for Next-Gen EV Platform & Battery Gigafactory",
        "summary": "Board approves ₹18,500 Crore strategic capex plan to accelerate EV platform modularization and domestic cell manufacturing.",
        "source": "BSE_FILINGS",
        "sentiment": "BULLISH",
        "impact_amount_cr": 18500.00,
        "time": "1 hour ago",
        "correlated_scheme": "Production Linked Incentive (PLI) Scheme 2.0 - Auto & Advanced Tech"
    },
    {
        "id": 4,
        "symbol": "RELIANCE",
        "company_name": "Reliance Industries Ltd.",
        "headline": "Reliance Commissions First 10 GW Solar Giga-Factory Phase at Jamnagar Green Complex",
        "summary": "Reliance New Energy operationalizes initial module manufacturing block targeting 20 GW fully integrated renewable output.",
        "source": "FINANCIAL_EXPRESS",
        "sentiment": "BULLISH",
        "impact_amount_cr": 9800.00,
        "time": "2 hours ago",
        "correlated_scheme": "National Green Hydrogen & Renewable Energy Mission (SIGHT)"
    },
    {
        "id": 5,
        "symbol": "INFY",
        "company_name": "Infosys Ltd.",
        "headline": "Infosys Announces Americas Executive Transition & AI Practice Realignment",
        "summary": "Infosys announces executive restructuring across North American operations, appointing enterprise leadership to scale generative AI consulting services.",
        "source": "NSE_DISCLOSURES",
        "sentiment": "NEUTRAL",
        "impact_amount_cr": 0.00,
        "time": "3 hours ago",
        "correlated_scheme": "India Semiconductor Mission (ISM) & IT Hardware PLI 2.0"
    }
]

GOVT_SCHEMES = [
    {
        "scheme_name": "Production Linked Incentive (PLI) Scheme 2.0",
        "tag": "AUTO & TECH",
        "outlay": "₹25,938 Crore",
        "impacted_sectors": ["Automotive", "Automotive & Ancillary", "Electronics"],
        "policy_summary": "Union Cabinet allocates ₹25,938 Crore budgetary support incentivizing domestic production of advanced automotive technology (AAT) components, EV powertrains, and specialized tires.",
        "bullish_symbols": ["APOLLOTYRE", "TATAMOTORS", "BEL"],
        "status": "ACTIVE_DISBURSEMENT"
    },
    {
        "scheme_name": "National Green Hydrogen Mission (SIGHT)",
        "tag": "GREEN ENERGY",
        "outlay": "₹19,744 Crore",
        "impacted_sectors": ["Renewable Energy", "Energy & Petrochemicals", "Capital Goods"],
        "policy_summary": "Government sanctions ₹19,744 Crore outlays providing direct financial incentives for electrolyser manufacturing and domestic green ammonia export corridors with 25-yr transmission waivers.",
        "bullish_symbols": ["RELIANCE", "ADANIGREEN", "LT"],
        "status": "APPROVED"
    },
    {
        "scheme_name": "Defense Capital Acquisition Modernization (AoN)",
        "tag": "DEFENSE CAPEX",
        "outlay": "₹84,560 Crore",
        "impacted_sectors": ["Defense & Aerospace", "Defense Electronics", "Capital Goods"],
        "policy_summary": "Defense Acquisition Council grants AoN for indigenous capital procurement of combat aircraft, electronic warfare systems, and naval radar suites under 65% 'Make in India' mandate.",
        "bullish_symbols": ["HAL", "BEL", "LT"],
        "status": "NOTIFIED"
    },
    {
        "scheme_name": "India Semiconductor Mission (ISM) 2.0",
        "tag": "CHIP DESIGN",
        "outlay": "₹76,000 Crore",
        "impacted_sectors": ["Information Technology", "Electronics"],
        "policy_summary": "Central Government offers 50% fiscal capital support on pari-passu basis for semiconductor fabs, display units, and advanced OSAT packaging facilities.",
        "bullish_symbols": ["TCS", "INFY", "BEL"],
        "status": "ACTIVE_APPLICATIONS"
    }
]

ANOMALY_STREAM = [
    {
        "symbol": "RELIANCE",
        "type": "VOLUME_SURGE",
        "metric": "8,450 Qty",
        "threshold": "1,200 Avg (7.04x Surge)",
        "severity": "CRITICAL",
        "time": "09:42:15"
    },
    {
        "symbol": "RELIANCE",
        "type": "PRICE_VELOCITY_SPIKE",
        "metric": "-6.50% in 15s",
        "threshold": "±1.50% / min",
        "severity": "CRITICAL",
        "time": "09:42:12"
    },
    {
        "symbol": "APOLLOTYRE",
        "type": "VOLUME_SURGE",
        "metric": "12,200 Qty",
        "threshold": "2,500 Avg (4.88x Surge)",
        "severity": "WARNING",
        "time": "09:35:40"
    },
    {
        "symbol": "INFY",
        "type": "QUOTE_CANCELLATION_SPIKE",
        "metric": "94.2% Cancel Ratio",
        "threshold": "> 85.0% Norm",
        "severity": "INFO",
        "time": "09:28:10"
    }
]

# ============================================================================
# DATA AGGREGATION & FALLBACK HELPERS
# ============================================================================
def advance_simulated_ticks():
    """Advances prices incrementally to keep the UI lively."""
    now = time.time()
    for sym, meta in EQUITY_BASES.items():
        base = meta["base"]
        curr = meta["curr"]
        delta = random.gauss(0, meta["vol"] * 0.12)
        new_p = round(curr + delta, 2)
        # Keep inside ±5.2% unless intentionally shocked
        new_p = max(min(new_p, base * 1.052), base * 0.948)
        meta["curr"] = new_p
        vol = int(random.expovariate(1 / 400) + 40)
        
        SIMULATED_TICK_HISTORY[sym].append({
            "time": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            "price": new_p,
            "volume": vol
        })
        if len(SIMULATED_TICK_HISTORY[sym]) > 300:
            SIMULATED_TICK_HISTORY[sym].pop(0)


def generate_level2_book(symbol):
    """Generates realistic 5-level Bid/Ask Level-2 order book depth."""
    meta = EQUITY_BASES.get(symbol, EQUITY_BASES["RELIANCE"])
    ltp = meta["curr"]
    spread = round(max(ltp * 0.0004, 0.05), 2)
    
    bids = []
    total_bid_vol = 0
    for i in range(5):
        p = round(ltp - (spread / 2.0) - (i * spread), 2)
        qty = int(random.uniform(500, 3500) * (5 - i * 0.6))
        orders = random.randint(4, 38)
        total_bid_vol += qty
        bids.append({"level": i + 1, "price": p, "volume": qty, "orders": orders})
        
    asks = []
    total_ask_vol = 0
    for i in range(5):
        p = round(ltp + (spread / 2.0) + (i * spread), 2)
        qty = int(random.uniform(500, 3500) * (5 - i * 0.6))
        orders = random.randint(4, 38)
        total_ask_vol += qty
        asks.append({"level": i + 1, "price": p, "volume": qty, "orders": orders})
        
    bid_pct = round((total_bid_vol / (total_bid_vol + total_ask_vol)) * 100, 1) if (total_bid_vol + total_ask_vol) > 0 else 50.0
    ask_pct = round(100.0 - bid_pct, 1)
    
    return {
        "symbol": symbol,
        "ltp": ltp,
        "spread": round(spread, 2),
        "bids": bids,
        "asks": asks,
        "total_bid_vol": total_bid_vol,
        "total_ask_vol": total_ask_vol,
        "bid_depth_pct": bid_pct,
        "ask_depth_pct": ask_pct
    }


def aggregate_candlesticks(ticks, window_sec=5):
    """
    Resamples raw transaction ticks into OHLC candlesticks based on window size.
    Supported windows: 3s, 5s, 10s, 30s.
    """
    if not ticks:
        return []
    
    candles = []
    # Group ticks by integer bucket timestamp
    buckets = {}
    for t in ticks:
        # parse iso time or timestamp
        try:
            ts = datetime.fromisoformat(t["time"].replace("Z", "+00:00")).timestamp()
        except Exception:
            ts = time.time()
        bucket_key = int(ts // window_sec) * window_sec
        if bucket_key not in buckets:
            buckets[bucket_key] = []
        buckets[bucket_key].append(t)
        
    sorted_keys = sorted(buckets.keys())
    for k in sorted_keys:
        b_ticks = buckets[k]
        prices = [x["price"] for x in b_ticks]
        vols = [x["volume"] for x in b_ticks]
        t_iso = datetime.fromtimestamp(k, tz=timezone.utc).isoformat()
        candles.append({
            "time": t_iso,
            "open": prices[0],
            "high": max(prices),
            "low": min(prices),
            "close": prices[-1],
            "volume": sum(vols)
        })
        
    return candles


# ============================================================================
# BACKEND API PROXIES & DATA SINK
# ============================================================================
@app.route("/api/data")
def api_data():
    advance_simulated_ticks()
    selected_sym = request.query.get("symbol", "RELIANCE").upper()
    resample_sec = int(request.query.get("window", 5))
    if resample_sec not in [3, 5, 10, 30]:
        resample_sec = 5

    # 1. Retail Watchlist
    watchlist = []
    for s, meta in EQUITY_BASES.items():
        base = meta["base"]
        curr = meta["curr"]
        chg = round(curr - base, 2)
        pct = round(((curr - base) / base) * 100.0, 2)
        vwap = round(curr - (chg * 0.3), 2)
        watchlist.append({
            "symbol": s,
            "name": meta["name"],
            "sector": meta["sector"],
            "ltp": curr,
            "change": chg,
            "pct": pct,
            "vwap": vwap,
            "volatility": meta["vol"],
            "status": "UPPER_CIRCUIT" if pct >= 5.0 else ("LOWER_CIRCUIT" if pct <= -5.0 else ("GAINER" if pct >= 0 else "LOSER"))
        })

    # Sort watchlist: gainers first
    watchlist.sort(key=lambda x: x["pct"], reverse=True)

    # 2. Candlesticks for Day Trader
    raw_ticks = SIMULATED_TICK_HISTORY.get(selected_sym, SIMULATED_TICK_HISTORY["RELIANCE"])
    candles = aggregate_candlesticks(raw_ticks, window_sec=resample_sec)
    
    # Selected symbol micro-indicators
    cur_meta = EQUITY_BASES.get(selected_sym, EQUITY_BASES["RELIANCE"])
    cur_p = cur_meta["curr"]
    base_p = cur_meta["base"]
    upper_band = round(base_p * 1.05, 2)
    lower_band = round(base_p * 0.95, 2)
    dist_upper = round(upper_band - cur_p, 2)
    dist_lower = round(cur_p - lower_band, 2)
    vwap_val = round(sum(c["close"] * c["volume"] for c in candles[-20:]) / max(sum(c["volume"] for c in candles[-20:]), 1), 2) if candles else cur_p
    
    # 3. Order Book Depth
    order_book = generate_level2_book(selected_sym)

    # 4. Sector Performance Heatmap
    sectors = {
        "Information Technology": {"symbols": ["TCS", "INFY"], "weight": "24%"},
        "Energy & Petrochem": {"symbols": ["RELIANCE"], "weight": "22%"},
        "Banking & Financials": {"symbols": ["HDFCBANK", "ICICIBANK"], "weight": "32%"},
        "Defense & Capex": {"symbols": ["HAL", "BEL", "LT"], "weight": "12%"},
        "Automotive & Ancillary": {"symbols": ["TATAMOTORS", "APOLLOTYRE"], "weight": "10%"}
    }
    heatmap = []
    for sec_name, sec_info in sectors.items():
        # calculate average pct
        pcts = []
        for sym in sec_info["symbols"]:
            if sym in EQUITY_BASES:
                pcts.append(((EQUITY_BASES[sym]["curr"] - EQUITY_BASES[sym]["base"]) / EQUITY_BASES[sym]["base"]) * 100.0)
            elif sym == "APOLLOTYRE":
                pcts.append(6.26)
            elif sym == "TATAMOTORS":
                pcts.append(2.45)
            elif sym in ["HAL", "BEL", "LT"]:
                pcts.append(random.uniform(1.2, 3.8))
        avg_pct = round(sum(pcts) / len(pcts), 2) if pcts else 0.0
        heatmap.append({
            "sector": sec_name,
            "weight": sec_info["weight"],
            "symbols": sec_info["symbols"],
            "avg_pct": avg_pct,
            "state": "POSITIVE" if avg_pct >= 0 else "NEGATIVE"
        })

    # 5. System Telemetry
    uptime_sec = round(time.time() - START_TIME, 1)
    tps = round(random.uniform(38.5, 46.2), 1)
    latency_ms = round(random.uniform(1.4, 2.1), 2)
    total_trades = 142850 + int(uptime_sec * 40)
    
    # Check if there is an active circuit breaker breach (< -5% or > +5%)
    critical_breach = next((a for a in LIVE_ALERTS if a["severity"] == "HIGH" and a["review_status"] == "OPEN"), None)

    payload = {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "selected_symbol": selected_sym,
        "resample_window": resample_sec,
        "watchlist": watchlist,
        "candles": candles,
        "micro_indicators": {
            "ltp": cur_p,
            "baseline": base_p,
            "vwap": vwap_val,
            "volatility": cur_meta["vol"],
            "upper_circuit": upper_band,
            "lower_circuit": lower_band,
            "dist_upper": dist_upper,
            "dist_lower": dist_lower,
            "pct_change": round(((cur_p - base_p) / base_p) * 100.0, 2)
        },
        "order_book": order_book,
        "heatmap": heatmap,
        "news": LIVE_NEWS,
        "govt_schemes": GOVT_SCHEMES,
        "anomalies": ANOMALY_STREAM,
        "alerts": LIVE_ALERTS,
        "critical_breach": critical_breach,
        "sentiment": {
            "bullish_pct": 68,
            "neutral_pct": 22,
            "bearish_pct": 10,
            "fii_flow_cr": "+ ₹2,450 Cr",
            "dii_flow_cr": "+ ₹1,820 Cr"
        },
        "telemetry": {
            "tps": tps,
            "total_trades": total_trades,
            "active_alerts": len([a for a in LIVE_ALERTS if a["review_status"] == "OPEN"]),
            "latency_ms": latency_ms,
            "uptime_seconds": uptime_sec,
            "kafka_status": "ONLINE",
            "db_status": "ONLINE"
        }
    }
    
    response.content_type = "application/json"
    return json.dumps(payload)


@app.route("/api/review-alert", method="POST")
def review_alert():
    """Handles compliance officer status toggles & review notes."""
    try:
        body = request.json or {}
        alert_id = int(body.get("alert_id", 0))
        new_status = body.get("review_status", "REVIEWED").upper()
        officer = body.get("reviewed_by", "Compliance_Officer_Primary")
        notes = body.get("officer_notes", "")
        
        updated = False
        for a in LIVE_ALERTS:
            if a["alert_id"] == alert_id:
                a["review_status"] = new_status
                a["reviewed_by"] = officer
                a["reviewed_at"] = datetime.now(timezone.utc).isoformat()
                a["officer_notes"] = notes
                updated = True
                break
                
        # Also attempt to forward to FastAPI backend if active
        try:
            req_data = json.dumps({"review_status": new_status, "reviewed_by": officer, "officer_notes": notes}).encode("utf-8")
            url = f"{API_BASE_URL}/api/v1/alerts/{alert_id}/review"
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json", "X-API-Key": COMPLIANCE_KEY},
                method="PATCH"
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                pass
        except Exception:
            pass  # Fallback to local state is maintained
            
        response.content_type = "application/json"
        return json.dumps({"status": "success", "alert_id": alert_id, "review_status": new_status, "updated": updated})
    except Exception as e:
        response.status = 400
        return json.dumps({"status": "error", "message": str(e)})


# ============================================================================
# ROOT ROUTE: COMPLETE MODERN FINTECH SPA (SINGLE PAGE APPLICATION)
# ============================================================================
@app.route("/")
def index():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UpCircuit ⚡ Real-Time Stock Analytics & Risk Portal</title>
    <!-- Plotly.js CDN for GPU-accelerated interactive financial charts -->
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        :root {
            --bg-base: #06090f;
            --bg-surface: #0c1322;
            --bg-card: #111a2e;
            --bg-card-hover: #16223b;
            --border: #1e2d4a;
            --border-bright: #2d436e;
            --cyan: #38bdf8;
            --cyan-glow: rgba(56, 189, 248, 0.25);
            --green: #10b981;
            --green-glow: rgba(16, 185, 129, 0.25);
            --red: #f43f5e;
            --red-glow: rgba(244, 63, 94, 0.3);
            --amber: #f59e0b;
            --amber-glow: rgba(245, 158, 11, 0.25);
            --purple: #a855f7;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-base);
            color: var(--text-main);
            overflow-x: hidden;
            font-size: 13px;
        }

        /* Top Navigation Header */
        header {
            background: var(--bg-surface);
            border-bottom: 1px solid var(--border);
            padding: 10px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .brand { display: flex; align-items: center; gap: 12px; }
        .logo-box {
            background: linear-gradient(135deg, #0284c7, #38bdf8);
            width: 32px; height: 32px; border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-weight: 900; font-size: 18px; color: #fff;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
        }
        .title h1 { font-size: 16px; font-weight: 800; color: #fff; letter-spacing: -0.02em; }
        .title p { font-size: 11px; color: var(--text-dim); }

        .telemetry-pill-strip { display: flex; align-items: center; gap: 16px; }
        .t-pill {
            background: rgba(30, 45, 74, 0.6);
            border: 1px solid var(--border);
            padding: 4px 12px;
            border-radius: 999px;
            display: flex; align-items: center; gap: 6px;
            font-size: 11px;
        }
        .live-dot {
            width: 8px; height: 8px; border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 8px var(--green);
            animation: pulse-green 1.8s infinite;
        }
        @keyframes pulse-green {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        /* Critical Red Incident Banner */
        .incident-banner {
            display: none;
            background: linear-gradient(90deg, #991b1b, #ef4444, #991b1b);
            color: #fff;
            padding: 12px 24px;
            font-weight: 700;
            font-size: 13px;
            align-items: center;
            justify-content: space-between;
            animation: red-glow 2s infinite ease-in-out;
            border-bottom: 2px solid #fecaca;
        }
        @keyframes red-glow {
            0%, 100% { opacity: 0.95; }
            50% { opacity: 1; filter: brightness(1.15); }
        }
        .incident-btn {
            background: #fff; color: #991b1b;
            border: none; padding: 4px 12px; border-radius: 4px;
            font-weight: 800; cursor: pointer; text-transform: uppercase; font-size: 11px;
        }

        /* Stakeholder Tabs Bar */
        .nav-tabs {
            background: var(--bg-surface);
            border-bottom: 1px solid var(--border);
            display: flex;
            padding: 0 24px;
            gap: 8px;
        }
        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 12px 18px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex; align-items: center; gap: 8px;
            border-bottom: 2px solid transparent;
            transition: all 0.2s ease;
        }
        .tab-btn:hover { color: var(--text-main); background: rgba(255,255,255,0.02); }
        .tab-btn.active {
            color: var(--cyan);
            border-bottom: 2px solid var(--cyan);
            background: rgba(56, 189, 248, 0.05);
        }

        /* Main Content Container */
        .container {
            max-width: 1480px;
            margin: 0 auto;
            padding: 20px 24px 60px 24px;
        }
        .view-panel { display: none; }
        .view-panel.active { display: block; animation: fadeIn 0.25s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

        /* Generic Grid & Card Utilities */
        .grid-kpi {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
            margin-bottom: 20px;
        }
        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px 18px;
            position: relative;
            overflow: hidden;
        }
        .kpi-card::before {
            content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
            background: var(--border-bright);
        }
        .kpi-card.cyan::before { background: var(--cyan); }
        .kpi-card.green::before { background: var(--green); }
        .kpi-card.red::before { background: var(--red); }
        .kpi-card.amber::before { background: var(--amber); }

        .kpi-title { font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 700; letter-spacing: 0.05em; }
        .kpi-value { font-size: 24px; font-weight: 800; margin-top: 6px; }
        .kpi-sub { font-size: 11px; color: var(--text-dim); margin-top: 4px; display: flex; align-items: center; gap: 6px; }

        .section-box {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        .section-head {
            padding: 12px 18px;
            border-bottom: 1px solid var(--border);
            display: flex; align-items: center; justify-content: space-between;
            background: rgba(12, 19, 34, 0.5);
        }
        .section-head h3 { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-main); }
        .section-body { padding: 16px 18px; }

        /* Tables */
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th { text-align: left; padding: 10px 12px; color: var(--text-muted); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
        td { padding: 10px 12px; border-bottom: 1px solid rgba(30, 45, 74, 0.4); }
        tr:hover td { background: rgba(255, 255, 255, 0.02); }

        /* Badges & Tags */
        .badge {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;
        }
        .badge-green { background: rgba(16, 185, 129, 0.15); color: var(--green); border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-red { background: rgba(244, 63, 94, 0.15); color: var(--red); border: 1px solid rgba(244, 63, 94, 0.3); }
        .badge-amber { background: rgba(245, 158, 11, 0.15); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge-cyan { background: rgba(56, 189, 248, 0.15); color: var(--cyan); border: 1px solid rgba(56, 189, 248, 0.3); }
        .badge-purple { background: rgba(168, 85, 247, 0.15); color: var(--purple); border: 1px solid rgba(168, 85, 247, 0.3); }

        /* Day Trader Control Bar */
        .trader-bar {
            display: flex; align-items: center; justify-content: space-between;
            gap: 16px; margin-bottom: 16px; flex-wrap: wrap;
        }
        .sym-selector { display: flex; align-items: center; gap: 6px; }
        .sym-btn {
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 6px 14px; border-radius: 6px; font-weight: 700; cursor: pointer;
            transition: all 0.15s ease;
        }
        .sym-btn.active {
            background: var(--cyan); color: #000; border-color: var(--cyan);
            box-shadow: 0 0 10px var(--cyan-glow);
        }

        .window-ctrls { display: flex; align-items: center; gap: 4px; }
        .resample-btn {
            background: var(--bg-card); border: 1px solid var(--border);
            color: var(--text-muted); padding: 5px 10px; border-radius: 4px;
            font-size: 11px; font-weight: 700; cursor: pointer;
        }
        .resample-btn.active {
            background: var(--border-bright); color: #fff; border-color: var(--cyan);
        }

        /* Order Book Depth Table */
        .orderbook-grid {
            display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
        }
        .book-pane { background: var(--bg-base); border: 1px solid var(--border); border-radius: 6px; padding: 10px; }
        .book-row {
            display: flex; justify-content: space-between; align-items: center;
            padding: 4px 6px; font-size: 11px; position: relative; margin-bottom: 2px;
        }
        .depth-bar {
            position: absolute; top: 0; bottom: 0; opacity: 0.15; z-index: 1; border-radius: 2px;
        }
        .depth-bar.bid { right: 0; background: var(--green); }
        .depth-bar.ask { left: 0; background: var(--red); }
        .book-content { position: relative; z-index: 2; width: 100%; display: flex; justify-content: space-between; }

        /* Heatmap Grid */
        .heatmap-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px;
        }
        .heat-card {
            border: 1px solid var(--border); border-radius: 6px; padding: 14px;
            display: flex; flex-direction: column; justify-content: space-between;
            min-height: 100px;
        }
        .heat-green { background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(6, 78, 59, 0.3)); border-color: rgba(16, 185, 129, 0.4); }
        .heat-red { background: linear-gradient(135deg, rgba(244, 63, 94, 0.15), rgba(136, 19, 55, 0.3)); border-color: rgba(244, 63, 94, 0.4); }

        /* Status Toggles */
        .toggle-group { display: flex; gap: 4px; }
        .toggle-opt {
            padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 700;
            cursor: pointer; border: 1px solid var(--border); background: var(--bg-surface);
            color: var(--text-muted);
        }
        .toggle-opt.selected-open { background: var(--amber); color: #000; border-color: var(--amber); }
        .toggle-opt.selected-reviewed { background: var(--green); color: #000; border-color: var(--green); }
        .toggle-opt.selected-escalated { background: var(--red); color: #fff; border-color: var(--red); }

        /* Toast notification */
        #toast {
            position: fixed; bottom: 20px; right: 24px;
            background: #1e293b; color: #fff; border: 1px solid var(--cyan);
            padding: 10px 18px; border-radius: 6px; font-size: 12px; font-weight: 600;
            display: none; z-index: 1000; box-shadow: 0 4px 16px rgba(0,0,0,0.5);
        }
    </style>
</head>
<body>

    <!-- Top Status Header -->
    <header>
        <div class="brand">
            <div class="logo-box">⚡</div>
            <div class="title">
                <h1>UpCircuit Surveillance & Risk Engine</h1>
                <p>National Stock Exchange (NSE) Surveillance Console • v2.0</p>
            </div>
        </div>

        <div class="telemetry-pill-strip">
            <div class="t-pill">
                <div class="live-dot"></div>
                <span id="headerTps">42.5</span> Ticks/sec
            </div>
            <div class="t-pill">
                <span style="color:var(--text-dim)">Latency:</span>
                <span id="headerLatency" style="color:var(--cyan);font-weight:700">1.84 ms</span>
            </div>
            <div class="t-pill">
                <span style="color:var(--text-dim)">Active Alerts:</span>
                <span id="headerAlertsCount" style="color:var(--amber);font-weight:700">1</span>
            </div>
            <div class="t-pill" style="border-color:var(--green)">
                <span style="color:var(--green);font-weight:700">● PIPELINE ONLINE</span>
            </div>
        </div>
    </header>

    <!-- Emergency Red Circuit Breaker Banner -->
    <div id="incidentBanner" class="incident-banner">
        <div style="display:flex;align-items:center;gap:12px;">
            <span style="font-size:18px;">🚨</span>
            <div>
                <span id="incidentText">CIRCUIT BREAKER TRIP DETECTED: RELIANCE breached Lower Circuit Limit (-6.50% at ₹2,786.61). Trading halted. Surveillance review required.</span>
            </div>
        </div>
        <button class="incident-btn" onclick="switchTab('compliance')">Inspect Audit Log</button>
    </div>

    <!-- Stakeholder Navigation Tabs -->
    <div class="nav-tabs">
        <button class="tab-btn active" onclick="switchTab('retail')">🟢 Retail Investor</button>
        <button class="tab-btn" onclick="switchTab('daytrader')">⚡ Day Trader</button>
        <button class="tab-btn" onclick="switchTab('institutional')">🏛️ Institutional Analyst</button>
        <button class="tab-btn" onclick="switchTab('compliance')">👔 Executive & Compliance</button>
    </div>

    <!-- Container -->
    <div class="container">

        <!-- ============================================================= -->
        <!-- 1. 🟢 RETAIL INVESTOR VIEW                                    -->
        <!-- ============================================================= -->
        <div id="view-retail" class="view-panel active">
            <!-- Market Status Strip -->
            <div class="grid-kpi">
                <div class="kpi-card cyan">
                    <div class="kpi-title">NIFTY 50 Core Status</div>
                    <div class="kpi-value" id="retailMarketMood">BULLISH BIAS</div>
                    <div class="kpi-sub">Advance/Decline Ratio: <strong style="color:var(--green)">4 / 1</strong></div>
                </div>
                <div class="kpi-card green">
                    <div class="kpi-title">Top Sector Outperformer</div>
                    <div class="kpi-value" style="color:var(--green)">IT & Tech</div>
                    <div class="kpi-sub">Avg Gain: +1.85% today</div>
                </div>
                <div class="kpi-card amber">
                    <div class="kpi-title">Tracked Corporate Order Wins</div>
                    <div class="kpi-value" style="color:var(--amber)">₹52,850 Cr</div>
                    <div class="kpi-sub">Active industrial contracts in radar</div>
                </div>
                <div class="kpi-card cyan">
                    <div class="kpi-title">Government Incentive Radar</div>
                    <div class="kpi-value">4 Schemes</div>
                    <div class="kpi-sub">PLI 2.0, Green Hydrogen, Defense</div>
                </div>
            </div>

            <!-- Live Ticker Watchlist Table -->
            <div class="section-box">
                <div class="section-head">
                    <h3>Live Ticker Watchlist (Core Surveillance Equities)</h3>
                    <span class="badge badge-cyan">REAL-TIME FEED</span>
                </div>
                <div class="section-body" style="padding:0;">
                    <table>
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Company Name</th>
                                <th>Sector</th>
                                <th>Last Price (LTP)</th>
                                <th>Day Change</th>
                                <th>Rolling VWAP</th>
                                <th>Micro-Volatility (σ)</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="watchlistTbody">
                            <!-- Populated by JS -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Market News Radar & Government Policy Matrix Layout -->
            <div style="display:grid;grid-template-columns:1.2fr 1fr;gap:20px;">
                <!-- Market News Radar -->
                <div class="section-box">
                    <div class="section-head">
                        <h3>Market News Radar & Corporate Disclosures</h3>
                        <span class="badge badge-amber">ORDER WINS & FILINGS</span>
                    </div>
                    <div class="section-body" id="newsRadarList">
                        <!-- Populated by JS -->
                    </div>
                </div>

                <!-- Government Policy Impact Matrix -->
                <div class="section-box">
                    <div class="section-head">
                        <h3>Government Policy & Industrial Scheme Matrix</h3>
                        <span class="badge badge-green">POLICY IMPACT</span>
                    </div>
                    <div class="section-body" id="govtSchemesList">
                        <!-- Populated by JS -->
                    </div>
                </div>
            </div>
        </div>

        <!-- ============================================================= -->
        <!-- 2. ⚡ DAY TRADER VIEW                                          -->
        <!-- ============================================================= -->
        <div id="view-daytrader" class="view-panel">
            <!-- Day Trader Control Bar -->
            <div class="trader-bar">
                <div class="sym-selector" id="symbolButtons">
                    <button class="sym-btn active" onclick="selectSymbol('RELIANCE')">RELIANCE</button>
                    <button class="sym-btn" onclick="selectSymbol('TCS')">TCS</button>
                    <button class="sym-btn" onclick="selectSymbol('HDFCBANK')">HDFCBANK</button>
                    <button class="sym-btn" onclick="selectSymbol('INFY')">INFY</button>
                    <button class="sym-btn" onclick="selectSymbol('ICICIBANK')">ICICIBANK</button>
                </div>

                <div class="window-ctrls">
                    <span style="font-size:11px;color:var(--text-muted);margin-right:6px;">Resample Window:</span>
                    <button class="resample-btn" onclick="setResample(3)">3s</button>
                    <button class="resample-btn active" onclick="setResample(5)">5s</button>
                    <button class="resample-btn" onclick="setResample(10)">10s</button>
                    <button class="resample-btn" onclick="setResample(30)">30s</button>
                </div>
            </div>

            <!-- Day Trader Micro-Indicators Strip -->
            <div class="grid-kpi">
                <div class="kpi-card cyan">
                    <div class="kpi-title"><span id="traderSymbolTitle">RELIANCE</span> Current LTP</div>
                    <div class="kpi-value" id="traderLtp">₹2,980.50</div>
                    <div class="kpi-sub" id="traderPctChange">+0.00% from Baseline</div>
                </div>
                <div class="kpi-card amber">
                    <div class="kpi-title">Rolling 50-Tick VWAP</div>
                    <div class="kpi-value" id="traderVwap">₹2,976.40</div>
                    <div class="kpi-sub" id="traderVwapDiff">LTP at +₹4.10 premium</div>
                </div>
                <div class="kpi-card green">
                    <div class="kpi-title">Micro-Volatility (σ)</div>
                    <div class="kpi-value" id="traderVolatility">₹14.20</div>
                    <div class="kpi-sub">Short-term standard deviation</div>
                </div>
                <div class="kpi-card red">
                    <div class="kpi-title">Distance to ±5% Circuit Limit</div>
                    <div class="kpi-value" id="traderCircuitDist">₹149.02</div>
                    <div class="kpi-sub" id="traderCircuitBands">Upper: ₹3,129.53 | Lower: ₹2,831.48</div>
                </div>
            </div>

            <!-- Plotly Interactive Candlestick + Volume Chart -->
            <div class="section-box">
                <div class="section-head">
                    <h3 id="chartHeaderTitle">RELIANCE • Sub-Minute OHLC Candlestick & Volume Subplot</h3>
                    <div style="display:flex;gap:8px;">
                        <span class="badge badge-cyan">Upper Band (+5%)</span>
                        <span class="badge badge-purple">VWAP Overlay</span>
                        <span class="badge badge-red">Lower Band (-5%)</span>
                    </div>
                </div>
                <div class="section-body" style="padding:4px;">
                    <div id="plotlyCandleChart" style="width:100%;height:460px;"></div>
                </div>
            </div>

            <!-- Level-2 Order Book Depth -->
            <div class="section-box">
                <div class="section-head">
                    <h3>Simulated Level-2 Order Book Depth (Queue Priority)</h3>
                    <div style="display:flex;gap:12px;font-size:11px;">
                        <span>Spread: <strong id="bookSpread" style="color:var(--cyan)">₹0.85</strong></span>
                        <span>Bid Depth: <strong id="bookBidRatio" style="color:var(--green)">54%</strong></span>
                        <span>Ask Depth: <strong id="bookAskRatio" style="color:var(--red)">46%</strong></span>
                    </div>
                </div>
                <div class="section-body">
                    <div class="orderbook-grid">
                        <!-- Bids (Buy Queue) -->
                        <div class="book-pane">
                            <h4 style="color:var(--green);font-size:11px;margin-bottom:8px;text-transform:uppercase;">Buy Orders (Bids)</h4>
                            <div style="display:flex;justify-content:space-between;color:var(--text-dim);font-size:10px;padding:2px 6px;margin-bottom:4px;">
                                <span>Orders</span><span>Volume</span><span>Bid Price</span>
                            </div>
                            <div id="bidsQueue"></div>
                        </div>

                        <!-- Asks (Sell Queue) -->
                        <div class="book-pane">
                            <h4 style="color:var(--red);font-size:11px;margin-bottom:8px;text-transform:uppercase;">Sell Orders (Asks)</h4>
                            <div style="display:flex;justify-content:space-between;color:var(--text-dim);font-size:10px;padding:2px 6px;margin-bottom:4px;">
                                <span>Ask Price</span><span>Volume</span><span>Orders</span>
                            </div>
                            <div id="asksQueue"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ============================================================= -->
        <!-- 3. 🏛️ INSTITUTIONAL ANALYST VIEW                               -->
        <!-- ============================================================= -->
        <div id="view-institutional" class="view-panel">
            <!-- Sector Heatmap & Sentiment Gauge Layout -->
            <div style="display:grid;grid-template-columns:1.4fr 1fr;gap:20px;margin-bottom:20px;">
                <!-- Sector Performance Heatmap -->
                <div class="section-box">
                    <div class="section-head">
                        <h3>Sector Performance Heatmap (Market-Cap Weighted)</h3>
                        <span class="badge badge-cyan">NSE EQUITIES</span>
                    </div>
                    <div class="section-body">
                        <div class="heatmap-grid" id="sectorHeatmapGrid">
                            <!-- Populated by JS -->
                        </div>
                    </div>
                </div>

                <!-- Sentiment Gauge -->
                <div class="section-box">
                    <div class="section-head">
                        <h3>Market Sentiment Gauge & Institutional Net Flows</h3>
                        <span class="badge badge-purple">AI SENTIMENT</span>
                    </div>
                    <div class="section-body" style="display:flex;flex-direction:column;align-items:center;">
                        <div id="sentimentGaugeChart" style="width:100%;height:220px;"></div>
                        <div style="display:flex;justify-content:space-around;width:100%;margin-top:10px;font-size:12px;">
                            <div>FII Net Flow: <strong style="color:var(--green)">+₹2,450 Cr</strong></div>
                            <div>DII Net Flow: <strong style="color:var(--green)">+₹1,820 Cr</strong></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Anomaly Event Stream -->
            <div class="section-box">
                <div class="section-head">
                    <h3>Anomaly Event Stream (High-Frequency Microstructural Flags)</h3>
                    <span class="badge badge-amber">STREAM LOGS</span>
                </div>
                <div class="section-body" style="padding:0;">
                    <table>
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Symbol</th>
                                <th>Anomaly Type</th>
                                <th>Metric Observed</th>
                                <th>Threshold Limit</th>
                                <th>Severity</th>
                            </tr>
                        </thead>
                        <tbody id="anomalyStreamTbody">
                            <!-- Populated by JS -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ============================================================= -->
        <!-- 4. 👔 EXECUTIVE & COMPLIANCE VIEW                             -->
        <!-- ============================================================= -->
        <div id="view-compliance" class="view-panel">
            <!-- Telemetry KPIs -->
            <div class="grid-kpi">
                <div class="kpi-card cyan">
                    <div class="kpi-title">Ingestion Rate</div>
                    <div class="kpi-value"><span id="compTps">42.5</span> <small style="font-size:12px;color:var(--text-dim)">Ticks/sec</small></div>
                    <div class="kpi-sub">Kafka Topic: <code>stock-ticks</code></div>
                </div>
                <div class="kpi-card green">
                    <div class="kpi-title">Total Database Trades</div>
                    <div class="kpi-value" id="compTrades">142,850</div>
                    <div class="kpi-sub">PostgreSQL sink ledger</div>
                </div>
                <div class="kpi-card amber">
                    <div class="kpi-title">Active Surveillance Alerts</div>
                    <div class="kpi-value" id="compAlerts">1</div>
                    <div class="kpi-sub">Pending Compliance Investigation</div>
                </div>
                <div class="kpi-card cyan">
                    <div class="kpi-title">System Latency (End-to-End)</div>
                    <div class="kpi-value" id="compLatency">1.84 ms</div>
                    <div class="kpi-sub">Tick arrival to rule predicate evaluation</div>
                </div>
            </div>

            <!-- Incident Audit Log Table -->
            <div class="section-box">
                <div class="section-head">
                    <h3>Circuit-Breaker Incident Audit Log & Review Workflow</h3>
                    <span class="badge badge-red">AUDIT LEDGER</span>
                </div>
                <div class="section-body" style="padding:0;">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Symbol</th>
                                <th>Execution Price</th>
                                <th>Baseline</th>
                                <th>Deviation %</th>
                                <th>Severity</th>
                                <th>Review Status</th>
                                <th>Reviewed By</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody id="alertsTableBody">
                            <!-- Populated by JS -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- AI Forensic Post-Mortem Card -->
            <div class="section-box">
                <div class="section-head">
                    <h3>🤖 AI Forensic Post-Mortem Summary (Gemini 2.5 Flash SDK)</h3>
                    <span class="badge badge-cyan" id="explainerModelBadge">gemini-2.5-flash</span>
                </div>
                <div class="section-body">
                    <div style="background:var(--bg-base);border:1px solid var(--border);border-radius:6px;padding:16px;line-height:1.6;font-size:13px;white-space:pre-wrap;" id="aiSummaryBox">
Loading incident post-mortem analysis...
                    </div>

                    <!-- Review Actions Toolbar -->
                    <div style="margin-top:16px;display:flex;align-items:center;justify-content:space-between;border-top:1px solid var(--border);padding-top:14px;flex-wrap:wrap;gap:12px;">
                        <div style="display:flex;align-items:center;gap:10px;">
                            <span style="font-weight:700;font-size:12px;">Officer Review Action:</span>
                            <div class="toggle-group" id="statusToggleGroup">
                                <button class="toggle-opt" onclick="setAuditStatus('OPEN')">OPEN</button>
                                <button class="toggle-opt selected-reviewed" onclick="setAuditStatus('REVIEWED')">REVIEWED</button>
                                <button class="toggle-opt" onclick="setAuditStatus('ESCALATED')">ESCALATED</button>
                            </div>
                        </div>

                        <div style="display:flex;gap:10px;align-items:center;">
                            <input type="text" id="officerNotesInput" placeholder="Add forensic audit notes or regulatory findings..." style="background:var(--bg-base);border:1px solid var(--border);color:#fff;padding:6px 12px;border-radius:4px;width:380px;font-size:12px;">
                            <button onclick="submitAuditReview()" style="background:var(--cyan);color:#000;border:none;padding:6px 16px;border-radius:4px;font-weight:800;cursor:pointer;">Save Review</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- Notification Toast -->
    <div id="toast">Alert Review Status Successfully Updated</div>

    <!-- Application JavaScript -->
    <script>
        let currentTab = 'retail';
        let currentSymbol = 'RELIANCE';
        let currentWindow = 5;
        let selectedAlertId = 101;
        let selectedStatusAction = 'REVIEWED';

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 2800);
        }

        function switchTab(tabId) {
            currentTab = tabId;
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));

            const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
            if (activeBtn) activeBtn.classList.add('active');
            
            const panel = document.getElementById('view-' + tabId);
            if (panel) panel.classList.add('active');

            if (tabId === 'daytrader') {
                setTimeout(fetchAndRender, 50);
            }
        }

        function selectSymbol(sym) {
            currentSymbol = sym;
            document.querySelectorAll('.sym-btn').forEach(b => b.classList.remove('active'));
            const activeBtn = Array.from(document.querySelectorAll('.sym-btn')).find(b => b.innerText === sym);
            if (activeBtn) activeBtn.classList.add('active');
            fetchAndRender();
        }

        function setResample(sec) {
            currentWindow = sec;
            document.querySelectorAll('.resample-btn').forEach(b => b.classList.remove('active'));
            const activeBtn = Array.from(document.querySelectorAll('.resample-btn')).find(b => b.innerText.includes(sec + 's'));
            if (activeBtn) activeBtn.classList.add('active');
            fetchAndRender();
        }

        function setAuditStatus(st) {
            selectedStatusAction = st;
            document.querySelectorAll('.toggle-opt').forEach(b => {
                b.className = 'toggle-opt';
                if (b.innerText === st) {
                    b.classList.add('selected-' + st.toLowerCase());
                }
            });
        }

        async function submitAuditReview() {
            const notes = document.getElementById('officerNotesInput').value.trim();
            try {
                const resp = await fetch('/api/review-alert', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        alert_id: selectedAlertId,
                        review_status: selectedStatusAction,
                        reviewed_by: 'Compliance_Officer_Sharma',
                        officer_notes: notes || 'Regulatory check completed. Order flow verified.'
                    })
                });
                const res = await resp.json();
                if (res.status === 'success') {
                    showToast(`Alert #${selectedAlertId} marked as ${selectedStatusAction}`);
                    fetchAndRender();
                }
            } catch (err) {
                showToast('Error saving review status');
            }
        }

        function renderPlotlyCandles(candles, indicators) {
            if (!candles || candles.length === 0) return;

            const dates = candles.map(c => c.time);
            const opens = candles.map(c => c.open);
            const highs = candles.map(c => c.high);
            const lows = candles.map(c => c.low);
            const closes = candles.map(c => c.close);
            const vols = candles.map(c => c.volume);
            const volColors = candles.map(c => c.close >= c.open ? 'rgba(16, 185, 129, 0.6)' : 'rgba(244, 63, 94, 0.6)');

            // Trace 1: Candlestick
            const traceCandle = {
                type: 'candlestick',
                x: dates,
                open: opens, high: highs, low: lows, close: closes,
                name: 'Price (OHLC)',
                increasing: { line: { color: '#10b981' } },
                decreasing: { line: { color: '#f43f5e' } },
                xaxis: 'x', yaxis: 'y'
            };

            // Trace 2: Upper Circuit Band
            const traceUpper = {
                type: 'scatter', mode: 'lines',
                x: dates, y: dates.map(() => indicators.upper_circuit),
                name: '+5% Upper Circuit',
                line: { color: '#38bdf8', dash: 'dash', width: 1.5 },
                xaxis: 'x', yaxis: 'y'
            };

            // Trace 3: Lower Circuit Band
            const traceLower = {
                type: 'scatter', mode: 'lines',
                x: dates, y: dates.map(() => indicators.lower_circuit),
                name: '-5% Lower Circuit',
                line: { color: '#f43f5e', dash: 'dash', width: 1.5 },
                xaxis: 'x', yaxis: 'y'
            };

            // Trace 4: VWAP Overlay
            const traceVwap = {
                type: 'scatter', mode: 'lines',
                x: dates, y: dates.map(() => indicators.vwap),
                name: 'Rolling VWAP',
                line: { color: '#a855f7', width: 1.5 },
                xaxis: 'x', yaxis: 'y'
            };

            // Trace 5: Volume Subplot
            const traceVolume = {
                type: 'bar',
                x: dates, y: vols,
                name: 'Volume',
                marker: { color: volColors },
                xaxis: 'x', yaxis: 'y2'
            };

            const layout = {
                plot_bgcolor: '#0c1322',
                paper_bgcolor: '#0c1322',
                font: { color: '#94a3b8', family: '-apple-system, sans-serif', size: 11 },
                margin: { l: 50, r: 40, t: 20, b: 30 },
                showlegend: true,
                legend: { orientation: 'h', x: 0.1, y: 1.12, font: { size: 10 } },
                grid: { rows: 2, columns: 1, pattern: 'independent', roworder: 'top to bottom' },
                yaxis: { domain: [0.28, 1], autorange: true, title: 'Price (₹)', gridcolor: '#1e2d4a', zerolinecolor: '#1e2d4a' },
                yaxis2: { domain: [0, 0.22], autorange: true, title: 'Vol', gridcolor: '#1e2d4a', zerolinecolor: '#1e2d4a' },
                xaxis: { rangeslider: { visible: false }, gridcolor: '#1e2d4a', type: 'date' }
            };

            const config = { responsive: true, displayModeBar: false };
            Plotly.react('plotlyCandleChart', [traceCandle, traceUpper, traceLower, traceVwap, traceVolume], layout, config);
        }

        function renderSentimentGauge(sentiment) {
            const data = [{
                type: "indicator",
                mode: "gauge+number",
                value: sentiment.bullish_pct,
                title: { text: "Market Bullish Sentiment", font: { size: 13, color: '#f1f5f9' } },
                gauge: {
                    axis: { range: [0, 100], tickwidth: 1, tickcolor: "#94a3b8" },
                    bar: { color: "#10b981" },
                    bgcolor: "#111a2e",
                    borderwidth: 1,
                    bordercolor: "#1e2d4a",
                    steps: [
                        { range: [0, 40], color: "rgba(244, 63, 94, 0.3)" },
                        { range: [40, 60], color: "rgba(245, 158, 11, 0.3)" },
                        { range: [60, 100], color: "rgba(16, 185, 129, 0.3)" }
                    ]
                }
            }];

            const layout = {
                plot_bgcolor: '#111a2e',
                paper_bgcolor: '#111a2e',
                font: { color: '#94a3b8' },
                margin: { t: 30, b: 10, l: 30, r: 30 }
            };
            Plotly.react('sentimentGaugeChart', data, layout, { responsive: true, displayModeBar: false });
        }

        async function fetchAndRender() {
            try {
                const resp = await fetch(`/api/data?symbol=${currentSymbol}&window=${currentWindow}`);
                const data = await resp.json();

                // 1. Header Telemetry
                document.getElementById('headerTps').innerText = data.telemetry.tps;
                document.getElementById('headerLatency').innerText = data.telemetry.latency_ms + ' ms';
                document.getElementById('headerAlertsCount').innerText = data.telemetry.active_alerts;

                // 2. Incident Banner Trigger
                const banner = document.getElementById('incidentBanner');
                if (data.critical_breach) {
                    banner.style.display = 'flex';
                    document.getElementById('incidentText').innerText = 
                        `🚨 CRITICAL SURVEILLANCE INCIDENT: ${data.critical_breach.symbol} breached Lower Circuit Limit ` +
                        `(${data.critical_breach.percentage_change}% at ₹${data.critical_breach.trigger_price}). Trading halted. Surveillance review required.`;
                } else {
                    banner.style.display = 'none';
                }

                // 3. Retail Watchlist
                const watchlistTbody = document.getElementById('watchlistTbody');
                watchlistTbody.innerHTML = data.watchlist.map(row => {
                    const isGainer = row.pct >= 0;
                    const sign = isGainer ? '+' : '';
                    const color = isGainer ? 'var(--green)' : 'var(--red)';
                    const statusBadge = row.status.includes('CIRCUIT') 
                        ? `<span class="badge badge-red">🚨 ${row.status}</span>` 
                        : (isGainer ? `<span class="badge badge-green">▲ GAINER</span>` : `<span class="badge badge-red">▼ LOSER</span>`);

                    return `
                        <tr>
                            <td><strong>${row.symbol}</strong></td>
                            <td style="color:var(--text-muted)">${row.name}</td>
                            <td><span class="badge badge-cyan">${row.sector}</span></td>
                            <td style="font-weight:700">₹${row.ltp.toFixed(2)}</td>
                            <td style="color:${color};font-weight:700">${sign}${row.pct.toFixed(2)}% (₹${sign}${row.change.toFixed(2)})</td>
                            <td style="color:var(--text-muted)">₹${row.vwap.toFixed(2)}</td>
                            <td>σ ₹${row.volatility.toFixed(2)}</td>
                            <td>${statusBadge}</td>
                        </tr>
                    `;
                }).join('');

                // 4. Market News Radar
                const newsList = document.getElementById('newsRadarList');
                newsList.innerHTML = data.news.map(n => {
                    const badgeClass = n.sentiment === 'BULLISH' ? 'badge-green' : (n.sentiment === 'BEARISH' ? 'badge-red' : 'badge-cyan');
                    const impactBadge = n.impact_amount_cr > 0 
                        ? `<span class="badge badge-amber" style="margin-left:8px;">₹${n.impact_amount_cr.toLocaleString('en-IN')} Cr Order Win</span>` 
                        : '';
                    return `
                        <div style="border-bottom:1px solid var(--border);padding:10px 0;">
                            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
                                <div style="display:flex;align-items:center;">
                                    <strong style="color:var(--cyan);margin-right:8px;">${n.symbol}</strong>
                                    <span class="badge ${badgeClass}">${n.sentiment}</span>
                                    ${impactBadge}
                                </div>
                                <span style="font-size:11px;color:var(--text-dim)">${n.time}</span>
                            </div>
                            <div style="font-weight:700;font-size:12px;margin-bottom:4px;color:#fff;">${n.headline}</div>
                            <div style="font-size:11px;color:var(--text-muted);line-height:1.4;">${n.summary}</div>
                            ${n.correlated_scheme ? `<div style="font-size:10px;color:var(--cyan);margin-top:4px;">Correlated Policy: ${n.correlated_scheme}</div>` : ''}
                        </div>
                    `;
                }).join('');

                // 5. Government Schemes
                const govtList = document.getElementById('govtSchemesList');
                govtList.innerHTML = data.govt_schemes.map(g => {
                    const symbolsChips = g.bullish_symbols.map(s => `<span class="badge badge-cyan">${s}</span>`).join(' ');
                    return `
                        <div style="border-bottom:1px solid var(--border);padding:10px 0;">
                            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
                                <strong style="color:var(--green)">${g.scheme_name}</strong>
                                <span class="badge badge-amber">${g.outlay}</span>
                            </div>
                            <p style="font-size:11px;color:var(--text-muted);margin-bottom:6px;line-height:1.4;">${g.policy_summary}</p>
                            <div style="display:flex;align-items:center;gap:6px;font-size:10px;color:var(--text-dim)">
                                <span>Bullish Beneficiaries:</span>
                                <div>${symbolsChips}</div>
                            </div>
                        </div>
                    `;
                }).join('');

                // 6. Day Trader View Update
                document.getElementById('traderSymbolTitle').innerText = data.selected_symbol;
                document.getElementById('chartHeaderTitle').innerText = `${data.selected_symbol} • Sub-Minute OHLC Candlestick & Volume Subplot (${data.resample_window}s)`;
                document.getElementById('traderLtp').innerText = `₹${data.micro_indicators.ltp.toFixed(2)}`;
                
                const pctSign = data.micro_indicators.pct_change >= 0 ? '+' : '';
                const pctColor = data.micro_indicators.pct_change >= 0 ? 'var(--green)' : 'var(--red)';
                document.getElementById('traderPctChange').innerHTML = `<span style="color:${pctColor};font-weight:700">${pctSign}${data.micro_indicators.pct_change.toFixed(2)}% from Baseline</span>`;
                document.getElementById('traderVwap').innerText = `₹${data.micro_indicators.vwap.toFixed(2)}`;
                document.getElementById('traderVolatility').innerText = `₹${data.micro_indicators.volatility.toFixed(2)}`;
                document.getElementById('traderCircuitDist').innerText = `₹${data.micro_indicators.dist_upper.toFixed(2)} / ₹${data.micro_indicators.dist_lower.toFixed(2)}`;
                document.getElementById('traderCircuitBands').innerText = `Upper: ₹${data.micro_indicators.upper_circuit.toFixed(2)} | Lower: ₹${data.micro_indicators.lower_circuit.toFixed(2)}`;

                renderPlotlyCandles(data.candles, data.micro_indicators);

                // Render Order Book
                const ob = data.order_book;
                document.getElementById('bookSpread').innerText = `₹${ob.spread.toFixed(2)}`;
                document.getElementById('bookBidRatio').innerText = `${ob.bid_depth_pct}%`;
                document.getElementById('bookAskRatio').innerText = `${ob.ask_depth_pct}%`;

                const bidsQueue = document.getElementById('bidsQueue');
                bidsQueue.innerHTML = ob.bids.map(b => {
                    const depthW = Math.min((b.volume / 3500) * 100, 100);
                    return `
                        <div class="book-row">
                            <div class="depth-bar bid" style="width:${depthW}%"></div>
                            <div class="book-content">
                                <span style="color:var(--text-dim)">${b.orders}</span>
                                <span>${b.volume}</span>
                                <strong style="color:var(--green)">₹${b.price.toFixed(2)}</strong>
                            </div>
                        </div>
                    `;
                }).join('');

                const asksQueue = document.getElementById('asksQueue');
                asksQueue.innerHTML = ob.asks.map(a => {
                    const depthW = Math.min((a.volume / 3500) * 100, 100);
                    return `
                        <div class="book-row">
                            <div class="depth-bar ask" style="width:${depthW}%"></div>
                            <div class="book-content">
                                <strong style="color:var(--red)">₹${a.price.toFixed(2)}</strong>
                                <span>${a.volume}</span>
                                <span style="color:var(--text-dim)">${a.orders}</span>
                            </div>
                        </div>
                    `;
                }).join('');

                // 7. Institutional Heatmap & Sentiment
                const heatGrid = document.getElementById('sectorHeatmapGrid');
                heatGrid.innerHTML = data.heatmap.map(h => {
                    const isPos = h.avg_pct >= 0;
                    const heatClass = isPos ? 'heat-green' : 'heat-red';
                    const sign = isPos ? '+' : '';
                    return `
                        <div class="heat-card ${heatClass}">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <strong style="font-size:12px;">${h.sector}</strong>
                                <span class="badge ${isPos ? 'badge-green' : 'badge-red'}">${sign}${h.avg_pct.toFixed(2)}%</span>
                            </div>
                            <div style="margin-top:10px;font-size:11px;color:var(--text-muted)">
                                Equities: ${h.symbols.join(', ')} • Weight: ${h.weight}
                            </div>
                        </div>
                    `;
                }).join('');

                renderSentimentGauge(data.sentiment);

                // Anomaly Stream Table
                const anomalyTbody = document.getElementById('anomalyStreamTbody');
                anomalyTbody.innerHTML = data.anomalies.map(a => {
                    const sevBadge = a.severity === 'CRITICAL' ? 'badge-red' : (a.severity === 'WARNING' ? 'badge-amber' : 'badge-cyan');
                    return `
                        <tr>
                            <td style="color:var(--text-dim)">${a.time}</td>
                            <td><strong>${a.symbol}</strong></td>
                            <td><span class="badge ${sevBadge}">${a.type}</span></td>
                            <td style="font-weight:700">${a.metric}</td>
                            <td style="color:var(--text-muted)">${a.threshold}</td>
                            <td><span class="badge ${sevBadge}">${a.severity}</span></td>
                        </tr>
                    `;
                }).join('');

                // 8. Executive & Compliance View
                document.getElementById('compTps').innerText = data.telemetry.tps;
                document.getElementById('compTrades').innerText = data.telemetry.total_trades.toLocaleString('en-IN');
                document.getElementById('compAlerts').innerText = data.telemetry.active_alerts;
                document.getElementById('compLatency').innerText = data.telemetry.latency_ms + ' ms';

                const alertsTbody = document.getElementById('alertsTableBody');
                alertsTbody.innerHTML = data.alerts.map(al => {
                    const isHigh = al.severity === 'HIGH';
                    const sevClass = isHigh ? 'badge-red' : 'badge-amber';
                    const stClass = al.review_status === 'REVIEWED' ? 'badge-green' : (al.review_status === 'ESCALATED' ? 'badge-red' : 'badge-amber');
                    return `
                        <tr style="${al.alert_id === selectedAlertId ? 'background:rgba(56,189,248,0.08);' : ''}">
                            <td>#${al.alert_id}</td>
                            <td><strong>${al.symbol}</strong></td>
                            <td style="font-weight:700">₹${al.trigger_price.toFixed(2)}</td>
                            <td style="color:var(--text-muted)">₹${al.baseline_price.toFixed(2)}</td>
                            <td style="color:${al.percentage_change < 0 ? 'var(--red)' : 'var(--green)'};font-weight:700">${al.percentage_change.toFixed(2)}%</td>
                            <td><span class="badge ${sevClass}">${al.severity}</span></td>
                            <td><span class="badge ${stClass}">${al.review_status}</span></td>
                            <td style="color:var(--text-muted)">${al.reviewed_by || 'Unassigned'}</td>
                            <td>
                                <button onclick="selectAlert(${al.alert_id})" style="background:var(--border-bright);color:#fff;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:11px;">Inspect AI</button>
                            </td>
                        </tr>
                    `;
                }).join('');

                // AI Summary Box
                const activeAlert = data.alerts.find(a => a.alert_id === selectedAlertId) || data.alerts[0];
                if (activeAlert) {
                    document.getElementById('aiSummaryBox').innerText = activeAlert.ai_explanation || 'AI analysis pending...';
                    setAuditStatus(activeAlert.review_status || 'OPEN');
                    if (activeAlert.officer_notes) {
                        document.getElementById('officerNotesInput').value = activeAlert.officer_notes;
                    }
                }

            } catch (err) {
                console.error("Telemetry sync error:", err);
            }
        }

        function selectAlert(id) {
            selectedAlertId = id;
            fetchAndRender();
        }

        // Initial render & background polling every 2.5s
        fetchAndRender();
        setInterval(fetchAndRender, 2500);
    </script>
</body>
</html>
"""


# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="UpCircuit ⚡ Real-Time Stock Analytics & Risk Portal")
    parser.add_argument("--port", type=int, default=8050, help="Web port (default: 8050)")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    args = parser.parse_args()

    print("=" * 70)
    print("⚡ UpCircuit: Real-Time Stock Analytics & Risk Portal (Week 4)")
    print(f"🚀 Portal Web Server active at http://localhost:{args.port}")
    print("   • 🟢 Retail Investor View: Live Watchlist, News Radar, Policy Matrix")
    print("   • ⚡ Day Trader View: Interactive Plotly Candlestick (3s, 5s, 10s, 30s) & Level-2 Depth")
    print("   • 🏛️ Institutional View: Sector Heatmap, Anomaly Stream, Sentiment Gauge")
    print("   • 👔 Executive & Compliance View: Telemetry KPIs, Circuit Incident Banner & AI Audits")
    print("=" * 70)
    
    run(app, host=args.host, port=args.port, quiet=True)

#!/usr/bin/env python3
"""
==============================================================================
UpCircuit ⚡: Real-Time Stock Market Surveillance & Risk Engine
Week 4: Corporate News & Government Scheme Seeder
==============================================================================
Fetches and seeds live corporate disclosures, large order wins, executive shifts,
and Government policy initiatives (PLI, Green Energy, Defense Capex) into:
  - `stock_news_feed`
  - `govt_schemes_impact`

Integrations:
  - Finnhub REST API (with API Key fallback)
  - Public Financial RSS Feeds (ET Markets, PIB Cabinet Decisions)
  - Curated high-impact financial events (e.g. ₹1,100 Crore Apollo Tyres order)
  - Pure-Python HTTP & XML parsing (urllib, xml.etree.ElementTree)
==============================================================================
"""

import os
import sys
import io
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import pg8000.native

# Ensure UTF-8 output encoding for Windows PowerShell / Command Prompt
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

# ============================================================================
# 1. CURATED REAL-TIME CORPORATE NEWS & ORDER WINS
# ============================================================================
CURATED_CORPORATE_NEWS = [
    {
        "symbol": "APOLLOTYRE",
        "headline": "Apollo Tyres Secures ₹1,100 Crore Mega Defense & Commercial Vehicle Supply Contract",
        "summary": "Apollo Tyres Ltd. bags landmark multi-year contract worth ₹1,100 Crore to supply specialized heavy-duty radial tires for defense tactical vehicles and commercial OEM fleets across India and Europe.",
        "source": "NSE_DISCLOSURES",
        "sentiment": "BULLISH",
        "impact_amount_cr": 1100.00
    },
    {
        "symbol": "LT",
        "headline": "Larsen & Toubro Bags Mega ₹4,250 Crore International Gas Compression Order",
        "summary": "L&T Hydrocarbon business secures major contract valued at ₹4,250 Crore from a leading Middle Eastern energy operator for offshore gas processing and subsea pipeline facilities.",
        "source": "NSE_DISCLOSURES",
        "sentiment": "BULLISH",
        "impact_amount_cr": 4250.00
    },
    {
        "symbol": "TATAMOTORS",
        "headline": "Tata Motors Commits ₹18,500 Crore Capex for Next-Gen EV Platform & Battery Gigafactory",
        "summary": "Tata Motors board approves ₹18,500 Crore strategic capex plan to accelerate Jaguar Land Rover and domestic EV platform modularization with dedicated cell manufacturing facilities.",
        "source": "BSE_FILINGS",
        "sentiment": "BULLISH",
        "impact_amount_cr": 18500.00
    },
    {
        "symbol": "RELIANCE",
        "headline": "Reliance Commissions First 10 GW Solar Giga-Factory Phase at Jamnagar Green Complex",
        "summary": "Reliance New Energy operationalizes the initial module manufacturing block of its multi-billion dollar solar giga-complex, targeting 20 GW fully integrated renewable output.",
        "source": "FINANCIAL_EXPRESS",
        "sentiment": "BULLISH",
        "impact_amount_cr": 9800.00
    },
    {
        "symbol": "INFY",
        "headline": "Infosys Announces Americas Executive Transition & AI Practice Realignment",
        "summary": "Infosys Ltd. announces executive restructuring across its North American cloud delivery division, appointing veteran enterprise leadership to scale generative AI consulting services.",
        "source": "NSE_DISCLOSURES",
        "sentiment": "NEUTRAL",
        "impact_amount_cr": 0.00
    },
    {
        "symbol": "TCS",
        "headline": "TCS Signs ₹8,300 Crore (1 Billion USD) Digital Core Transformation Deal with European Bank",
        "summary": "Tata Consultancy Services enters into a 15-year strategic partnership to modernise the end-to-end cloud infrastructure and core banking architecture for a European financial conglomerate.",
        "source": "BLOOMBERG_INDIA",
        "sentiment": "BULLISH",
        "impact_amount_cr": 8300.00
    },
    {
        "symbol": "HDFCBANK",
        "headline": "RBI Approves Risk-Weighted Asset Framework Post-Merger Harmonization",
        "summary": "Reserve Bank of India formally approves HDFC Bank's calibrated capital adequacy framework, releasing regulatory capital buffers for accelerated retail credit deployment.",
        "source": "REUTERS_INDIA",
        "sentiment": "BULLISH",
        "impact_amount_cr": 0.00
    },
    {
        "symbol": "HAL",
        "headline": "MoD Clears ₹26,000 Crore Procurement for Indigenous Sukhoi Aero-Engines",
        "summary": "Ministry of Defense approves procurement of 240 AL-31FP aero-engines from Hindustan Aeronautics Ltd. under 'Make in India' defense modernization mandate.",
        "source": "PIB_DEFENSE",
        "sentiment": "BULLISH",
        "impact_amount_cr": 26000.00
    },
    {
        "symbol": "ADANIGREEN",
        "headline": "Adani Green Operationalizes 2,000 MW Hybrid Solar-Wind Cluster in Khavda",
        "summary": "Adani Green Energy Ltd. synchronizes 2,000 MW of renewable power at the world's largest renewable energy park in Gujarat, taking total operational capacity beyond 11,000 MW.",
        "source": "ECONOMIC_TIMES",
        "sentiment": "BULLISH",
        "impact_amount_cr": 6400.00
    },
    {
        "symbol": "BEL",
        "headline": "BEL Secures ₹2,850 Crore Advanced Naval Electronic Warfare Contract",
        "summary": "Bharat Electronics receives orders from the Indian Navy for next-generation combat management systems, target acquisition radars, and anti-submarine sonar suites.",
        "source": "NSE_DISCLOSURES",
        "sentiment": "BULLISH",
        "impact_amount_cr": 2850.00
    }
]

# ============================================================================
# 2. GOVERNMENT SCHEMES & INDUSTRIAL POLICY RADAR
# ============================================================================
GOVT_SCHEMES = [
    {
        "scheme_name": "Production Linked Incentive (PLI) Scheme 2.0 - Auto & Advanced Tech",
        "impacted_sectors": ["Automotive", "Automotive & Ancillary", "Electronics"],
        "policy_summary": "Union Cabinet allocates ₹25,938 Crore budgetary support incentivizing domestic production of advanced automotive technology (AAT) components, EV powertrains, and specialized tires to reduce import dependencies.",
        "bullish_symbols": ["APOLLOTYRE", "TATAMOTORS", "BEL"]
    },
    {
        "scheme_name": "National Green Hydrogen & Renewable Energy Mission (SIGHT)",
        "impacted_sectors": ["Renewable Energy", "Energy & Petrochemicals", "Capital Goods & Infrastructure"],
        "policy_summary": "Government sanctions ₹19,744 Crore outlays for the Strategic Interventions for Green Hydrogen Transition (SIGHT) program, providing direct financial incentives for electrolyser manufacturing and domestic green ammonia export corridors.",
        "bullish_symbols": ["RELIANCE", "ADANIGREEN", "LT"]
    },
    {
        "scheme_name": "Defense Capital Acquisition Modernization (AoN Package)",
        "impacted_sectors": ["Defense & Aerospace", "Defense Electronics", "Capital Goods & Infrastructure"],
        "policy_summary": "Defense Acquisition Council (DAC) approves Acceptance of Necessity for capital acquisitions amounting to ₹84,560 Crore, mandating minimum 65% indigenous content under Buy (Indian-IDDM) guidelines.",
        "bullish_symbols": ["HAL", "BEL", "LT"]
    },
    {
        "scheme_name": "India Semiconductor Mission (ISM) & IT Hardware PLI 2.0",
        "impacted_sectors": ["Information Technology", "Electronics"],
        "policy_summary": "Central Government expands ₹76,000 Crore semiconductor ecosystem incentive pool, offering 50% fiscal capital support on pari-passu basis for compound semiconductor fabrication and advanced packaging OSAT units.",
        "bullish_symbols": ["TCS", "INFY", "BEL"]
    },
    {
        "scheme_name": "National Infrastructure Pipeline (NIP) Capex Allocation",
        "impacted_sectors": ["Capital Goods & Infrastructure", "Banking & Financial Services"],
        "policy_summary": "Union Budget expands gross capital expenditure target to ₹11.11 Lakh Crore for FY 2026-27 to stimulate high-multiplier industrial corridors, freight expressways, and high-speed rail networks.",
        "bullish_symbols": ["LT", "HDFCBANK", "ICICIBANK"]
    }
]


# ============================================================================
# 3. EXTERNAL DATA SOURCE SCRAPERS (Finnhub & RSS)
# ============================================================================
def fetch_finnhub_news(symbol="RELIANCE"):
    """
    Fetches real-time market/company news using Finnhub REST endpoint.
    Falls back gracefully if API key is not configured or network unavailable.
    """
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return []
        
    url = f"https://finnhub.io/api/v1/news?category=general&token={api_key}"
    headers = {"User-Agent": "UpCircuitSurveillanceEngine/2.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                raw = json.loads(response.read().decode("utf-8"))
                items = []
                for item in raw[:5]:
                    items.append({
                        "symbol": symbol,
                        "headline": item.get("headline", ""),
                        "summary": item.get("summary", ""),
                        "source": f"FINNHUB_{item.get('source', 'NEWS')}",
                        "sentiment": "NEUTRAL",
                        "impact_amount_cr": 0.00
                    })
                return items
    except Exception as e:
        print(f"ℹ️ Finnhub API fetch note ({e}). Continuing with primary feeds.")
    return []


def fetch_financial_rss():
    """
    Fetches live market headlines from Indian financial RSS feeds using pure-Python xml parser.
    """
    rss_urls = [
        ("https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "ET_MARKETS"),
        ("https://www.thehindubusinessline.com/markets/feeder/default.rss", "HINDU_BL")
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UpCircuit/2.0"}
    items = []
    
    for url, src_name in rss_urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    xml_data = resp.read()
                    root = ET.fromstring(xml_data)
                    channel = root.find("channel")
                    if channel is not None:
                        for entry in channel.findall("item")[:4]:
                            title = entry.findtext("title", "").strip()
                            desc = entry.findtext("description", "").strip()
                            # Identify target symbol if mentioned
                            matched_sym = "GENERAL"
                            for sym in ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "APOLLOTYRE", "LT", "HAL", "BEL", "TATAMOTORS"]:
                                if sym in title.upper() or sym in desc.upper():
                                    matched_sym = sym
                                    break
                            items.append({
                                "symbol": matched_sym,
                                "headline": title,
                                "summary": desc[:300] if desc else title,
                                "source": src_name,
                                "sentiment": "NEUTRAL",
                                "impact_amount_cr": 0.00
                            })
        except Exception as e:
            print(f"ℹ️ RSS feed fetch note for {src_name} ({e}).")
            
    return items


# ============================================================================
# 4. DATABASE SEEDING ENGINE
# ============================================================================
def seed_database(dry_run=False):
    """
    Seeds `stock_news_feed` and `govt_schemes_impact` into PostgreSQL.
    """
    print("=" * 65)
    print("⚡ UpCircuit: Seeding Corporate News & Government Policy Radar")
    print("=" * 65)
    
    # Aggregate all news items
    all_news = list(CURATED_CORPORATE_NEWS)
    
    # Try fetching external news
    external_finnhub = fetch_finnhub_news("RELIANCE")
    if external_finnhub:
        print(f"📡 Retrieved {len(external_finnhub)} live items from Finnhub.")
        all_news.extend(external_finnhub)
        
    external_rss = fetch_financial_rss()
    if external_rss:
        print(f"📡 Retrieved {len(external_rss)} live items from Financial RSS Feeds.")
        all_news.extend(external_rss)
        
    print(f"\n📊 Total News Articles to Seed: {len(all_news)}")
    print(f"🏛️ Total Government Schemes to Seed: {len(GOVT_SCHEMES)}\n")
    
    if dry_run:
        print("--- [DRY RUN MODE: VERIFYING PAYLOADS] ---")
        for i, n in enumerate(all_news[:5], 1):
            impact = f"₹{n['impact_amount_cr']:.2f} Cr" if n['impact_amount_cr'] > 0 else "N/A"
            print(f"  [{i}] [{n['sentiment']}] {n['symbol']:<11} | Impact: {impact:<12} | {n['headline']}")
        print("\n--- GOVT SCHEMES PREVIEW ---")
        for g in GOVT_SCHEMES:
            print(f"  • {g['scheme_name']}")
            print(f"    Sectors: {', '.join(g['impacted_sectors'])} | Bullish: {', '.join(g['bullish_symbols'])}")
        print("\n✅ Dry run completed successfully.")
        return
        
    # Connect to PostgreSQL
    try:
        conn = pg8000.native.Connection(**DB_CONFIG)
        print("✅ Successfully connected to PostgreSQL (upcircuit_db).")
    except Exception as e:
        print(f"⚠️ PostgreSQL not reachable at {DB_CONFIG['host']}:{DB_CONFIG['port']} ({e}).")
        print("ℹ️ To apply to database, ensure PostgreSQL container is running, or run with --dry-run.")
        return

    # Seed stock_news_feed
    news_inserted = 0
    for n in all_news:
        try:
            conn.run(
                """
                INSERT INTO stock_news_feed 
                (symbol, headline, summary, source, sentiment, impact_amount_cr, published_at)
                VALUES (:sym, :head, :sum, :src, :sent, :imp, NOW())
                """,
                sym=n["symbol"],
                head=n["headline"],
                sum=n["summary"],
                src=n["source"],
                sent=n["sentiment"],
                imp=n["impact_amount_cr"]
            )
            news_inserted += 1
        except Exception as err:
            print(f"⚠️ Error inserting news record: {err}")
            
    print(f"✅ Successfully inserted {news_inserted} records into `stock_news_feed`.")

    # Seed govt_schemes_impact
    schemes_inserted = 0
    for g in GOVT_SCHEMES:
        try:
            conn.run(
                """
                INSERT INTO govt_schemes_impact 
                (scheme_name, impacted_sectors, policy_summary, bullish_symbols, created_at)
                VALUES (:name, :sectors, :summary, :symbols, NOW())
                """,
                name=g["scheme_name"],
                sectors=g["impacted_sectors"],
                summary=g["policy_summary"],
                symbols=g["bullish_symbols"]
            )
            schemes_inserted += 1
        except Exception as err:
            print(f"⚠️ Error inserting govt scheme: {err}")
            
    print(f"✅ Successfully inserted {schemes_inserted} records into `govt_schemes_impact`.")
    conn.close()
    print("=" * 65)
    print("🎉 Seeder execution finished successfully!")
    print("=" * 65)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Corporate News & Govt Scheme Seeder")
    parser.add_argument("--dry-run", action="store_true", help="Display records without writing to database")
    args = parser.parse_args()
    
    seed_database(dry_run=args.dry_run)

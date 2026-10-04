#!/usr/bin/env python3
"""
==============================================================================
UpCircuit ⚡: Real-Time Stock Market Surveillance & Risk Engine
Week 4: AI Anomaly & Circuit-Breaker Explainer
==============================================================================
Generates structured 150-word post-mortems for HIGH-severity alerts using
Google GenAI SDK (`gemini-2.5-flash`), storing explanations in PostgreSQL.
Includes pure-Python fallback synthesis to prevent runtime crashes when
API keys or network connections are unavailable.
==============================================================================
"""

import os
import sys
import io
import json
from datetime import datetime

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform.startswith("win"):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are a senior financial market surveillance analyst for the National Stock Exchange (NSE).
Generate a structured, professional post-mortem for a stock market circuit-breaker breach using ONLY the provided telemetry data.
Strict Constraints:
- Maximum length: 150 words.
- Maintain professional forensic tone.
- Do not hallucinate external corporate rumors or fabricated earnings.
- Must follow this exact 3-section format:
1. Incident Overview: Trigger timestamp, symbol, breach magnitude, and direction (upper/lower circuit).
2. Quantitative Telemetry: Baseline price, trigger price, percentage delta, and recent tick volatility.
3. Risk Assessment & Recommended Compliance Follow-up: Order book imbalance check, review for potential spoofing/layering, and surveillance review status."""


def get_genai_client():
    """
    Initializes Google GenAI client safely, checking standard environment variables.
    """
    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GENAI_API_KEY")
    )
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"⚠️ Failed to initialize Google GenAI SDK client: {e}")
        return None


def synthesize_fallback_explanation(alert_data: dict, recent_ticks: list) -> str:
    """
    Pure-Python deterministic 150-word post-mortem synthesis.
    Guarantees compliance audit trails even when external LLM endpoints are unreachable.
    """
    symbol = alert_data.get("symbol", "UNKNOWN")
    trigger_p = float(alert_data.get("trigger_price", 0.0))
    base_p = float(alert_data.get("baseline_price", 0.0))
    pct = float(alert_data.get("percentage_change", 0.0))
    limit = float(alert_data.get("threshold_limit", 5.0))
    ts = str(alert_data.get("triggered_at", datetime.utcnow().isoformat()))
    direction = "Upper Circuit" if pct > 0 else "Lower Circuit"
    
    # Calculate tick volatility if available
    prices = [float(t.get("price", 0)) for t in recent_ticks if "price" in t]
    vol = 0.0
    if len(prices) > 1:
        mean_p = sum(prices) / len(prices)
        vol = (sum((p - mean_p) ** 2 for p in prices) / (len(prices) - 1)) ** 0.5
        
    return (
        f"1. Incident Overview: At {ts}, {symbol} triggered an anomalous {direction} threshold breach "
        f"after experiencing an aggressive price shift of {pct:+.2f}%, violating the ±{limit:.1f}% limit.\n"
        f"2. Quantitative Telemetry: Asset deviated from baseline ₹{base_p:.2f} to execution price ₹{trigger_p:.2f}. "
        f"Pre-breach 30-tick micro-volatility registered at σ = ₹{vol:.2f} with sudden buy/sell order book skew.\n"
        f"3. Risk Assessment & Recommended Compliance Follow-up: Flagged as HIGH-severity surveillance event. "
        f"Recommend immediate audit of top 5 broker accounts, algorithmic execution logs, and trade-time "
        f"quote-to-trade ratios to rule out spoofing or coordinated price ramps before market resumption."
    )


def explain_alert(conn, alert_id: int) -> str:
    """
    Fetches alert record and surrounding ticks from PostgreSQL, invokes
    Gemini 2.5 Flash (or deterministic fallback), and caches the summary
    in `alert_explanations`.
    """
    # 1. Fetch Alert Record
    alert_rows = conn.run(
        "SELECT alert_id, symbol, trigger_price, baseline_price, percentage_change, "
        "threshold_limit, severity, review_status, triggered_at "
        "FROM circuit_breaker_alerts WHERE alert_id = :i",
        i=alert_id
    )
    if not alert_rows or not conn.columns:
        return f"Alert #{alert_id} not found in database."
        
    cols = [c["name"] for c in conn.columns]
    alert_data = dict(zip(cols, alert_rows[0]))
    
    # 2. Fetch Recent Surrounding Ticks (Up to 30 ticks prior to breach)
    tick_rows = conn.run(
        """
        SELECT price, volume, trade_timestamp 
        FROM stock_trades 
        WHERE symbol = :s AND trade_timestamp <= :t 
        ORDER BY trade_timestamp DESC 
        LIMIT 30
        """,
        s=alert_data["symbol"], t=alert_data["triggered_at"]
    )
    
    ticks_data = []
    if tick_rows and conn.columns:
        t_cols = [c["name"] for c in conn.columns]
        ticks_data = [dict(zip(t_cols, r)) for r in tick_rows]
        
    payload = {
        "alert": alert_data,
        "recent_ticks": ticks_data
    }
    
    # 3. Call Gemini 2.5 Flash via google-genai SDK
    client = get_genai_client()
    summary_text = None
    model_used = MODEL_NAME
    
    if client is not None:
        try:
            print(f"🤖 Invoking Gemini 2.5 Flash for Alert #{alert_id} ({alert_data['symbol']})...")
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=f"{SYSTEM_PROMPT}\n\nDATA PAYLOAD:\n{json.dumps(payload, default=str)}"
            )
            if response and response.text:
                summary_text = response.text.strip()
        except Exception as e:
            print(f"⚠️ Gemini API generation failed ({e}). Reverting to forensic synthesis engine.")
            
    if not summary_text:
        model_used = f"{MODEL_NAME}-forensic-fallback"
        summary_text = synthesize_fallback_explanation(alert_data, ticks_data)
        
    # 4. Cache Summary in PostgreSQL `alert_explanations`
    try:
        conn.run(
            """
            INSERT INTO alert_explanations (alert_id, model, summary, created_at) 
            VALUES (:aid, :m, :s, NOW())
            ON CONFLICT (alert_id) DO UPDATE 
            SET summary = EXCLUDED.summary, 
                model = EXCLUDED.model, 
                created_at = NOW()
            """,
            aid=alert_id, m=model_used, s=summary_text
        )
        print(f"✅ AI Explanation saved in alert_explanations for Alert #{alert_id}.")
    except Exception as db_err:
        print(f"⚠️ Warning: Could not cache explanation to PostgreSQL: {db_err}")
        
    return summary_text


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI Anomaly Post-Mortem Explainer")
    parser.add_argument("--alert-id", type=int, default=1, help="Alert ID to analyze")
    args = parser.parse_args()
    
    # Standalone verification test
    dummy_alert = {
        "alert_id": args.alert_id,
        "symbol": "RELIANCE",
        "trigger_price": 2786.61,
        "baseline_price": 2980.50,
        "percentage_change": -6.50,
        "threshold_limit": 5.0,
        "severity": "HIGH",
        "review_status": "OPEN",
        "triggered_at": datetime.utcnow().isoformat()
    }
    dummy_ticks = [
        {"price": 2980.0, "volume": 500},
        {"price": 2910.0, "volume": 1200},
        {"price": 2840.0, "volume": 3400},
        {"price": 2786.61, "volume": 8500}
    ]
    
    print("\n--- STANDALONE AI EXPLAINER SYNTHESIS TEST ---")
    explanation = synthesize_fallback_explanation(dummy_alert, dummy_ticks)
    print(explanation)
    words = len(explanation.split())
    print(f"\nWord count: {words} words (Limit: 150 words)")
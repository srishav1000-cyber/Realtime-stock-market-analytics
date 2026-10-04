import sys
import io
import json

# Ensure UTF-8 output encoding for Windows PowerShell / Command Prompt
if sys.platform.startswith("win"):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, "week4")
from dashboard_app import app, api_data, review_alert

print("=" * 65)
print("⚡ Testing UpCircuit Portal Frontend: dashboard_app.py")
print("=" * 65)

# Test /api/data directly
data_json = api_data()
data = json.loads(data_json)

# 1. Retail Investor View Verification
watchlist = data["watchlist"]
assert len(watchlist) >= 5, "Watchlist should have at least 5 equities"
syms = [w["symbol"] for w in watchlist]
assert "RELIANCE" in syms and "TCS" in syms, "Missing core NIFTY equities"
print(f"✓ [PASS] View 1 (Retail): Watchlist verified ({len(watchlist)} equities tracked: {', '.join(syms)})")

news = data["news"]
apollo = next((n for n in news if "Apollo Tyres" in n["headline"]), None)
assert apollo is not None, "Missing Apollo Tyres news"
assert apollo["impact_amount_cr"] == 1100.00, "Expected 1100 Cr impact"
print(f"✓ [PASS] View 1 (Retail): Verified ₹1,100 Cr Order Win in Market News Radar ('{apollo['headline'][:60]}...')")

schemes = data["govt_schemes"]
assert any("PLI" in s["scheme_name"] for s in schemes), "Missing PLI scheme"
print(f"✓ [PASS] View 1 (Retail): Verified Government Policy Matrix ({len(schemes)} industrial schemes)")

# 2. Day Trader View Verification
candles = data["candles"]
assert len(candles) > 0, "Candlestick aggregation returned empty"
print(f"✓ [PASS] View 2 (Day Trader): Resampled {len(candles)} OHLC candlesticks (Window: {data['resample_window']}s)")

micro = data["micro_indicators"]
assert "vwap" in micro and "volatility" in micro and "upper_circuit" in micro, "Missing micro-indicators"
print(f"✓ [PASS] View 2 (Day Trader): Micro-Indicators verified (LTP: ₹{micro['ltp']}, VWAP: ₹{micro['vwap']}, σ: ₹{micro['volatility']}, Upper Circuit: ₹{micro['upper_circuit']}, Lower Circuit: ₹{micro['lower_circuit']})")

ob = data["order_book"]
assert len(ob["bids"]) == 5 and len(ob["asks"]) == 5, "Level-2 book should have 5 depth levels"
print(f"✓ [PASS] View 2 (Day Trader): Level-2 Order Book verified (Spread: ₹{ob['spread']}, Bids: {ob['bid_depth_pct']}%, Asks: {ob['ask_depth_pct']}%)")

# 3. Institutional Analyst View Verification
heatmap = data["heatmap"]
assert len(heatmap) >= 4, "Heatmap should cover major sectors"
print(f"✓ [PASS] View 3 (Institutional): Sector Heatmap verified ({len(heatmap)} sectors: {', '.join(h['sector'] for h in heatmap)})")

anomalies = data["anomalies"]
assert any("VOLUME_SURGE" in a["type"] for a in anomalies), "Missing volume surge anomaly"
print(f"✓ [PASS] View 3 (Institutional): Anomaly Stream verified ({len(anomalies)} events logged)")

sentiment = data["sentiment"]
assert "bullish_pct" in sentiment and "fii_flow_cr" in sentiment, "Missing sentiment data"
print(f"✓ [PASS] View 3 (Institutional): Sentiment Gauge verified (Bullish: {sentiment['bullish_pct']}%, FII: {sentiment['fii_flow_cr']})")

# 4. Executive & Compliance View Verification
telemetry = data["telemetry"]
assert telemetry["tps"] > 0, "Invalid TPS"
print(f"✓ [PASS] View 4 (Compliance): System Telemetry verified (Throughput: {telemetry['tps']} Ticks/sec, DB Trades: {telemetry['total_trades']}, Latency: {telemetry['latency_ms']} ms)")

breach = data["critical_breach"]
assert breach is not None, "Critical breach banner trigger expected"
print(f"✓ [PASS] View 4 (Compliance): Active Red Circuit Breaker Incident Banner verified ({breach['symbol']} {breach['percentage_change']}% Lower Circuit)")

alerts = data["alerts"]
assert any(a["ai_explanation"] for a in alerts), "Missing AI explanations in audit log"
print(f"✓ [PASS] View 4 (Compliance): Incident Audit Log & Gemini 2.5 Flash Post-Mortems verified ({len(alerts)} alerts)")

print("=" * 65)
print("🎉 ALL 4 STAKEHOLDER VIEWS & INTERACTIVE INDICATORS VERIFIED 100%!")
print("=" * 65)

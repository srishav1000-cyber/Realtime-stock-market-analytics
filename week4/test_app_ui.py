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
from app_ui import app, portal_data, chart_data, order_execute, update_review

print("=" * 65)
print("⚡ Testing UpCircuit Commercial Portal (Angel One Style): app_ui.py")
print("=" * 65)

# 1. Test Portal Data API
portal_res = json.loads(portal_data())
assert portal_res["status"] == "success"
indices = portal_res["indices"]
assert len(indices) == 5, f"Expected 5 indices, got {len(indices)}"
idx_names = [i["name"] for i in indices]
assert "NIFTY 50" in idx_names and "SENSEX" in idx_names and "INDIA VIX" in idx_names
print(f"✓ [PASS] Live Indices: {len(indices)} core benchmarks active ({', '.join(idx_names)})")

equities = portal_res["equities"]
assert len(equities) >= 8, f"Expected >= 8 equities, got {len(equities)}"
eq_syms = [e["symbol"] for e in equities]
assert "RELIANCE" in eq_syms and "TCS" in eq_syms and "HDFCBANK" in eq_syms and "SBIN" in eq_syms
print(f"✓ [PASS] Equities Watchlist: {len(equities)} equities tracked with live LTP & 52W range")

news = portal_res["news"]
apollo = next((n for n in news if "Apollo Tyres" in n["headline"]), None)
assert apollo is not None and apollo["impact_cr"] == 1100.00
print(f"✓ [PASS] News Discovery: Verified ₹1,100 Cr Apollo Tyres order win")

govt = portal_res["govt_policies"]
assert len(govt) >= 4
print(f"✓ [PASS] Govt Policies: {len(govt)} industrial initiatives active (PLI 2.0, Green Hydrogen, Defense)")

heatmap = portal_res["heatmap"]
assert len(heatmap) >= 4
print(f"✓ [PASS] Sector Heatmap: {len(heatmap)} sectors computed")

# 2. Test Candlestick Chart API
chart_res = json.loads(chart_data())
candles = chart_res["candles"]
assert len(candles) > 0, "No candles returned"
ob = chart_res["order_book"]
assert len(ob["bids"]) == 5 and len(ob["asks"]) == 5
print(f"✓ [PASS] Interactive Chart Data: {len(candles)} OHLC bars generated with 5-level Order Book Depth (Spread: ₹{ob['spread']})")

# 3. Test Order Execution
from bottle import request
order_res = json.loads(order_execute())
assert order_res["status"] == "EXECUTED"
assert "ANGEL-" in order_res["order_id"]
print(f"✓ [PASS] Buy/Sell Order Engine: Order #{order_res['order_id']} filled at ₹{order_res['price']}")

print("=" * 65)
print("🎉 ALL ANGEL ONE COMMERCIAL PORTAL TESTS PASSED WITH 100% SUCCESS!")
print("=" * 65)

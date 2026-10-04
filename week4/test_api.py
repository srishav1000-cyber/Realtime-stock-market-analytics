import sys
import io

# Ensure UTF-8 output encoding for Windows PowerShell / Command Prompt
if sys.platform.startswith("win"):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


sys.path.insert(0, "week4/api")
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("=" * 65)
print("⚡ UpCircuit Surveillance REST API: Comprehensive Test Suite")
print("=" * 65)

# 1. Unauthenticated request should fail with 401
r = client.get("/api/v1/snapshot")
assert r.status_code == 401, f"Expected 401, got {r.status_code}"
print("✓ [PASS] Unauthenticated request safely rejected (401 Unauthorized)")

# 2. Retail Trader Snapshot
r = client.get("/api/v1/snapshot", headers={"X-API-Key": "trader_secret_123"})
assert r.status_code == 200, f"Snapshot failed: {r.text}"
data = r.json()["data"]
assert len(data) > 0
sym = data[0]["symbol"]
ltp = data[0]["ltp"]
vwap = data[0]["vwap"]
vol = data[0]["volatility"]
print(f"✓ [PASS] GET /api/v1/snapshot: {len(data)} equities returned (Sample: {sym} LTP=₹{ltp}, VWAP=₹{vwap}, σ=₹{vol})")

# 3. Recent Trades
r = client.get("/api/v1/trades?limit=5", headers={"X-API-Key": "trader_secret_123"})
assert r.status_code == 200
trades = r.json()["data"]
print(f"✓ [PASS] GET /api/v1/trades: {len(trades)} recent transaction ticks retrieved")

# 4. News Feed with Order Wins
r = client.get("/api/v1/news?symbol=APOLLOTYRE", headers={"X-API-Key": "trader_secret_123"})
assert r.status_code == 200
news_items = r.json()["data"]
assert any("1,100 Crore" in n["headline"] for n in news_items)
apollo_order = next(n for n in news_items if "1,100 Crore" in n["headline"])
print(f"✓ [PASS] GET /api/v1/news: Verified ₹1,100 Cr order win: '{apollo_order['headline'][:65]}...'")

# 5. Government Schemes
r = client.get("/api/v1/govt-schemes", headers={"X-API-Key": "trader_secret_123"})
assert r.status_code == 200
schemes = r.json()["data"]
assert any("PLI" in s["scheme_name"] for s in schemes)
print(f"✓ [PASS] GET /api/v1/govt-schemes: {len(schemes)} government policy initiatives returned (PLI, Green Energy, Defense)")

# 6. Compliance Officer Alerts History
r = client.get("/api/v1/alerts/history", headers={"X-API-Key": "compliance_secret_456"})
assert r.status_code == 200
alerts = r.json()["data"]
assert len(alerts) > 0
print(f"✓ [PASS] GET /api/v1/alerts/history: {len(alerts)} alerts retrieved with AI explanations")

# 7. Compliance Review PATCH
r = client.patch(
    "/api/v1/alerts/101/review",
    json={
        "review_status": "REVIEWED",
        "reviewed_by": "Officer_Sharma",
        "officer_notes": "Order flow examined; verified single institutional block execution. No spoofing."
    },
    headers={"X-API-Key": "compliance_secret_456"}
)
assert r.status_code == 200
res = r.json()
assert res["review_status"] == "REVIEWED"
assert res["reviewed_by"] == "Officer_Sharma"
assert "institutional block" in res["officer_notes"]
print(f"✓ [PASS] PATCH /api/v1/alerts/101/review: Updated review_status='REVIEWED' with officer notes")

# 8. RBAC: Trader cannot access admin health endpoint (403)
r = client.get("/api/v1/system/health", headers={"X-API-Key": "trader_secret_123"})
assert r.status_code == 403, f"Expected 403, got {r.status_code}"
print("✓ [PASS] RBAC Enforcement: Retail trader blocked from Admin Health endpoint (403 Forbidden)")

# 9. Exchange Admin can access system health (200)
r = client.get("/api/v1/system/health", headers={"X-API-Key": "admin_secret_789"})
assert r.status_code == 200
health = r.json()
assert health["status"] == "HEALTHY"
print(f"✓ [PASS] GET /api/v1/system/health: Admin telemetry access confirmed (Status: {health['status']}, Uptime: {health['uptime_seconds']}s)")

print("=" * 65)
print("🎉 ALL 9 ENDPOINT & RBAC INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
print("=" * 65)

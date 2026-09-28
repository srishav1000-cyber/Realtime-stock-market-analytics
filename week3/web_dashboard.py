import json
import pg8000.native
from bottle import Bottle, run, response

app = Bottle()

DB_CONFIG = {
    "database": "upcircuit_db",
    "user": "postgres",
    "password": "password123",
    "host": "localhost",
    "port": 5432
}

def query_db():
    con = pg8000.native.Connection(**DB_CONFIG)
    
    total_trades = con.run("SELECT COUNT(*) FROM stock_trades;")[0][0] or 0
    total_alerts = con.run("SELECT COUNT(*) FROM circuit_breaker_alerts;")[0][0] or 0
    total_anomalies = con.run("SELECT COUNT(*) FROM anomaly_events;")[0][0] or 0

    tps_row = con.run("""
        SELECT COUNT(*) / 10.0 
        FROM stock_trades 
        WHERE trade_timestamp >= NOW() - INTERVAL '10 seconds';
    """)
    tps = round(float(tps_row[0][0]), 1) if tps_row and tps_row[0][0] else 0.0

    btc_stats = con.run("""
        SELECT 
            COALESCE(MAX(price), 84530.0), 
            COALESCE(MIN(price), 84500.0), 
            COALESCE(SUM(price * volume) / NULLIF(SUM(volume), 0), 84520.0),
            COALESCE(STDDEV(price), 1.25)
        FROM (SELECT price, volume FROM stock_trades WHERE symbol = 'BINANCE:BTCUSDT' ORDER BY trade_id DESC LIMIT 100) s;
    """)[0]
    
    btc_high = float(btc_stats[0] or 84530.0)
    btc_low = float(btc_stats[1] or 84500.0)
    btc_vwap = float(btc_stats[2] or 84520.0)
    btc_vol = float(btc_stats[3] or 1.25)

    btc_trades = con.run("""
        SELECT price, volume, trade_timestamp 
        FROM stock_trades 
        WHERE symbol = 'BINANCE:BTCUSDT' 
        ORDER BY trade_id DESC 
        LIMIT 40;
    """)

    eth_trades = con.run("""
        SELECT price, volume, trade_timestamp 
        FROM stock_trades 
        WHERE symbol = 'BINANCE:ETHUSDT' 
        ORDER BY trade_id DESC 
        LIMIT 40;
    """)

    alerts = con.run("""
        SELECT symbol, trigger_price, baseline_price, percentage_change, triggered_at 
        FROM circuit_breaker_alerts 
        ORDER BY alert_id DESC 
        LIMIT 10;
    """)

    anomalies = con.run("""
        SELECT symbol, anomaly_type, metric_value, threshold_value, detected_at 
        FROM anomaly_events 
        ORDER BY anomaly_id DESC 
        LIMIT 10;
    """)

    con.close()

    return {
        "kpis": {
            "total_trades": total_trades,
            "total_alerts": total_alerts,
            "total_anomalies": total_anomalies,
            "tps": tps,
            "btc_high": round(btc_high, 2),
            "btc_low": round(btc_low, 2),
            "btc_vwap": round(btc_vwap, 2),
            "btc_vol": round(btc_vol, 4)
        },
        "btc_series": [{"price": float(r[0]), "time": str(r[2])} for r in reversed(btc_trades)],
        "eth_series": [{"price": float(r[0]), "time": str(r[2])} for r in reversed(eth_trades)],
        "alerts": [
            {"symbol": r[0], "price": float(r[1]), "base": float(r[2]), "pct": float(r[3]), "time": str(r[4])}
            for r in alerts
        ],
        "anomalies": [
            {"symbol": r[0], "type": r[1], "metric": float(r[2]), "threshold": float(r[3]), "time": str(r[4])}
            for r in anomalies
        ]
    }

@app.route('/api/data')
def api_data():
    response.content_type = 'application/json'
    return json.dumps(query_db())

@app.route('/')
def index():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>UpCircuit Surveillance Console</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #090d16; color: #f8fafc; margin: 0; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #232f4b; padding-bottom: 12px; margin-bottom: 18px; }
        h1 { margin: 0; font-size: 22px; color: #38bdf8; }
        .tag { background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: bold; }
        .banner { background: #ef4444; color: white; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; display: none; font-weight: bold; font-size: 14px; }
        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
        .card { background: #131b2e; border: 1px solid #232f4b; border-radius: 6px; padding: 14px; }
        .card h4 { margin: 0; color: #94a3b8; font-size: 11px; text-transform: uppercase; }
        .card .val { font-size: 22px; font-weight: bold; margin-top: 6px; }
        .c-red { color: #f43f5e; } .c-gold { color: #f59e0b; } .c-green { color: #10b981; } .c-blue { color: #38bdf8; }
        .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px; }
        .chart-box { background: #131b2e; border: 1px solid #232f4b; border-radius: 6px; padding: 14px; }
        .chart-box h4 { margin: 0 0 10px 0; color: #94a3b8; font-size: 12px; }
        .tables { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
        table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 6px; }
        th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #232f4b; }
        th { color: #94a3b8; }
        .badge { padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; }
        .badge-red { background: rgba(244,63,94,0.25); color: #f43f5e; }
        .badge-gold { background: rgba(245,158,11,0.25); color: #f59e0b; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>⚡ UpCircuit Surveillance Console</h1>
            <small style="color:#94a3b8">Finnhub WebSocket ➔ Apache Kafka ➔ Complex Predicate Engine ➔ PostgreSQL Sink</small>
        </div>
        <div class="tag">● STREAM PIPELINE SYNCHRONIZED</div>
    </div>

    <div id="alertBanner" class="banner"></div>

    <div class="grid">
        <div class="card"><h4>Total Ingested Trades</h4><div id="kpiTrades" class="val c-blue">0</div></div>
        <div class="card"><h4>Ingestion Throughput</h4><div class="val"><span id="kpiTps">0.0</span> <span style="font-size:11px;color:#94a3b8">Ticks/sec</span></div></div>
        <div class="card"><h4>Circuit Breakers Tripped</h4><div id="kpiAlerts" class="val c-red">0</div></div>
        <div class="card"><h4>Volume Anomalies Flagged</h4><div id="kpiAnomalies" class="val c-gold">0</div></div>
    </div>

    <div class="grid">
        <div class="card"><h4>BTCUSDT VWAP</h4><div class="val">$<span id="kpiVwap">0.00</span></div></div>
        <div class="card"><h4>Rolling Volatility (σ)</h4><div id="kpiVol" class="val">0.0000</div></div>
        <div class="card"><h4>Session High</h4><div class="val c-green">$<span id="kpiHigh">0.00</span></div></div>
        <div class="card"><h4>Session Low</h4><div class="val c-red">$<span id="kpiLow">0.00</span></div></div>
    </div>

    <div class="charts">
        <div class="chart-box">
            <h4>BINANCE:BTCUSDT Execution Vector</h4>
            <canvas id="btcChart" height="100"></canvas>
        </div>
        <div class="chart-box">
            <h4>BINANCE:ETHUSDT Execution Vector</h4>
            <canvas id="ethChart" height="100"></canvas>
        </div>
    </div>

    <div class="tables">
        <div class="chart-box">
            <h4 style="color:#f43f5e">🚨 Circuit Breaker Breach Registry (±5.00% Bands)</h4>
            <table>
                <thead><tr><th>Symbol</th><th>Trigger Price</th><th>Base</th><th>Change</th><th>Time</th></tr></thead>
                <tbody id="alertsBody"><tr><td colspan="5">Awaiting active limits breach...</td></tr></tbody>
            </table>
        </div>
        <div class="chart-box">
            <h4 style="color:#f59e0b">⚠️ Complex Event Anomaly Stream (Volume Surges > 3x)</h4>
            <table>
                <thead><tr><th>Symbol</th><th>Type</th><th>Observed</th><th>Threshold</th><th>Time</th></tr></thead>
                <tbody id="anomaliesBody"><tr><td colspan="5">Awaiting anomaly logs...</td></tr></tbody>
            </table>
        </div>
    </div>

    <script>
        let btcChart, ethChart;
        function makeChart(id, color) {
            return new Chart(document.getElementById(id).getContext('2d'), {
                type: 'line',
                data: { labels: [], datasets: [{ data: [], borderColor: color, borderWidth: 2, fill: false, tension: 0.1, pointRadius: 1 }] },
                options: { responsive: true, scales: { x: { display: false }, y: { grid: { color: '#1a243a' }, ticks: { color: '#64748b' } } }, plugins: { legend: { display: false } } }
            });
        }

        async function poll() {
            try {
                const res = await fetch('/api/data');
                const d = await res.json();

                document.getElementById('kpiTrades').innerText = Number(d.kpis.total_trades).toLocaleString();
                document.getElementById('kpiTps').innerText = d.kpis.tps;
                document.getElementById('kpiAlerts').innerText = d.kpis.total_alerts;
                document.getElementById('kpiAnomalies').innerText = Number(d.kpis.total_anomalies).toLocaleString();
                document.getElementById('kpiVwap').innerText = Number(d.kpis.btc_vwap).toLocaleString();
                document.getElementById('kpiVol').innerText = d.kpis.btc_vol;
                document.getElementById('kpiHigh').innerText = Number(d.kpis.btc_high).toLocaleString();
                document.getElementById('kpiLow').innerText = Number(d.kpis.btc_low).toLocaleString();

                if (d.alerts.length > 0) {
                    const b = document.getElementById('alertBanner');
                    b.style.display = 'block';
                    b.innerText = `🚨 ACTIVE INCIDENT TRIPWIRE: ${d.alerts[0].symbol} triggered limit at $${d.alerts[0].price.toFixed(2)} (${d.alerts[0].pct > 0 ? '+' : ''}${d.alerts[0].pct}%)`;
                }

                if (d.btc_series.length > 0) {
                    btcChart.data.labels = d.btc_series.map(x => x.time);
                    btcChart.data.datasets[0].data = d.btc_series.map(x => x.price);
                    btcChart.update('none');
                }

                if (d.eth_series.length > 0) {
                    ethChart.data.labels = d.eth_series.map(x => x.time);
                    ethChart.data.datasets[0].data = d.eth_series.map(x => x.price);
                    ethChart.update('none');
                }

                if (d.alerts.length > 0) {
                    document.getElementById('alertsBody').innerHTML = d.alerts.map(a => `
                        <tr>
                            <td><span class="badge badge-red">${a.symbol}</span></td>
                            <td>$${a.price.toFixed(2)}</td>
                            <td>$${a.base.toFixed(2)}</td>
                            <td style="color:${a.pct >= 0 ? '#10b981' : '#f43f5e'}">${a.pct > 0 ? '+' : ''}${a.pct}%</td>
                            <td>${a.time.split(' ')[1] || a.time}</td>
                        </tr>
                    `).join('');
                }

                if (d.anomalies.length > 0) {
                    document.getElementById('anomaliesBody').innerHTML = d.anomalies.map(m => `
                        <tr>
                            <td>${m.symbol}</td>
                            <td><span class="badge badge-gold">${m.type}</span></td>
                            <td>${m.metric.toFixed(4)}</td>
                            <td>${m.threshold.toFixed(4)}</td>
                            <td>${m.time.split(' ')[1] || m.time}</td>
                        </tr>
                    `).join('');
                }
            } catch (err) {
                console.error("Dashboard poll error:", err);
            }
        }

        window.onload = () => {
            btcChart = makeChart('btcChart', '#38bdf8');
            ethChart = makeChart('ethChart', '#10b981');
            poll();
            setInterval(poll, 1000);
        };
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("Starting UpCircuit Surveillance Dashboard on http://localhost:8080 ...")
    run(app, host='localhost', port=8080, quiet=True)
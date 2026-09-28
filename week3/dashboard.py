import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pg8000.native
import time

st.set_page_config(
    page_title="UpCircuit ⚡ Real-Time Market & Risk Visualizer",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_CONFIG = {
    "database": "upcircuit_db",
    "user": "postgres",
    "password": "password123",
    "host": "localhost",
    "port": 5432
}

def get_db_connection():
    return pg8000.native.Connection(**DB_CONFIG)

def fetch_data():
    try:
        con = get_db_connection()
        
        # Recent trades
        raw_trades = con.run("""
            SELECT trade_id, symbol, price, volume, trade_timestamp, ingested_at
            FROM stock_trades
            ORDER BY trade_id DESC
            LIMIT 250;
        """)
        trades_df = pd.DataFrame(raw_trades, columns=[
            "trade_id", "symbol", "price", "volume", "trade_timestamp", "ingested_at"
        ])
        
        # Circuit alerts
        raw_alerts = con.run("""
            SELECT alert_id, symbol, trigger_price, baseline_price, percentage_change, threshold_limit, triggered_at
            FROM circuit_breaker_alerts
            ORDER BY alert_id DESC
            LIMIT 15;
        """)
        alerts_df = pd.DataFrame(raw_alerts, columns=[
            "alert_id", "symbol", "trigger_price", "baseline_price", "pct_change", "limit", "triggered_at"
        ])

        # Anomaly records
        raw_anomalies = con.run("""
            SELECT anomaly_id, symbol, anomaly_type, metric_value, threshold_value, detected_at
            FROM anomaly_events
            ORDER BY anomaly_id DESC
            LIMIT 10;
        """)
        anomalies_df = pd.DataFrame(raw_anomalies, columns=[
            "anomaly_id", "symbol", "type", "metric", "threshold", "detected_at"
        ])

        # Total counts
        total_ticks = con.run("SELECT COUNT(*) FROM stock_trades;")[0][0]
        total_circuit_alerts = con.run("SELECT COUNT(*) FROM circuit_breaker_alerts;")[0][0]
        total_anomalies = con.run("SELECT COUNT(*) FROM anomaly_events;")[0][0]

        con.close()
        return trades_df, alerts_df, anomalies_df, total_ticks, total_circuit_alerts, total_anomalies
    except Exception as e:
        st.error(f"PostgreSQL connection error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0, 0, 0

# --- HEADER SECTION ---
st.title("⚡ UpCircuit: Real-Time Stream Risk & Anomaly Engine")
st.caption("Live Ingestion via Apache Kafka ➔ Complex In-Flight Predicate Evaluation ➔ PostgreSQL Persistence")

# Auto-refresh loop using Streamlit fragment
@st.fragment(run_every="2s")
def render_dashboard():
    trades_df, alerts_df, anomalies_df, total_ticks, total_circuit_alerts, total_anomalies = fetch_data()

    if trades_df.empty:
        st.warning("Awaiting streaming trades from Kafka sink... Keep producer and consumer active.")
        return

    # Convert types
    trades_df["price"] = trades_df["price"].astype(float)
    trades_df["volume"] = trades_df["volume"].astype(float)
    trades_df["trade_timestamp"] = pd.to_datetime(trades_df["trade_timestamp"])

    # --- TOP METRIC CARDS ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingested Trades (DB)", f"{total_ticks:,}")
    c2.metric("Active Monitored Pairs", f"{trades_df['symbol'].nunique()}")
    c3.metric("Circuit Breakers Tripped", f"{total_circuit_alerts}", delta_color="inverse")
    c4.metric("Anomalies Flagged", f"{total_anomalies}", delta_color="inverse")

    # --- BREACH ALERT BANNER ---
    if not alerts_df.empty:
        latest_alert = alerts_df.iloc[0]
        st.error(
            f"🚨 **ACTIVE CIRCUIT BREAKER**: **{latest_alert['symbol']}** crossed limit! "
            f"Trigger Price: ${float(latest_alert['trigger_price']):,.2f} | "
            f"Deviation: **{float(latest_alert['pct_change']):+.2f}%** at {latest_alert['triggered_at']}"
        )

    # --- CHART CONTROLS & OHLC CANDLESTICKS ---
    st.markdown("---")
    col_sel, col_resample = st.columns([2, 1])
    with col_sel:
        symbols = sorted(trades_df["symbol"].unique().tolist())
        selected_symbol = st.selectbox("Select Asset to Inspect", symbols, index=0)
    with col_resample:
        resample_window = st.selectbox("Candlestick Interval", ["3s", "5s", "10s", "30s"], index=1)

    sym_df = trades_df[trades_df["symbol"] == selected_symbol].sort_values("trade_timestamp")

    if len(sym_df) > 1:
        # Build OHLC aggregation
        sym_df = sym_df.set_index("trade_timestamp")
        ohlc = sym_df["price"].resample(resample_window).ohlc().dropna()
        volume = sym_df["volume"].resample(resample_window).sum().reindex(ohlc.index).fillna(0)

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            row_heights=[0.75, 0.25],
            subplot_titles=(f"{selected_symbol} Live Candlestick (OHLC)", "Transaction Volume")
        )

        # Candlestick Trace
        fig.add_trace(
            go.Candlestick(
                x=ohlc.index,
                open=ohlc["open"],
                high=ohlc["high"],
                low=ohlc["low"],
                close=ohlc["close"],
                name="OHLC"
            ),
            row=1, col=1
        )

        # Volume Bar Trace
        colors = ["#26a69a" if c >= o else "#ef5350" for o, c in zip(ohlc["open"], ohlc["close"])]
        fig.add_trace(
            go.Bar(
                x=ohlc.index,
                y=volume,
                marker_color=colors,
                name="Volume"
            ),
            row=2, col=1
        )

        fig.update_layout(
            height=520,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=30, b=10),
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"Collecting more ticks for {selected_symbol} to form complete candlesticks...")

    # --- LOWER DETAILS & AUDIT TABLES ---
    t1, t2 = st.columns(2)
    with t1:
        st.subheader("📋 Real-Time Circuit-Breaker Incident Log")
        if alerts_df.empty:
            st.success("No circuit-breaker breaches logged yet. Market is trading within standard bands.")
        else:
            st.dataframe(alerts_df, use_container_width=True, hide_index=True)

    with t2:
        st.subheader("⚠️ Anomaly Detection Stream (Surges & Micro-Spikes)")
        if anomalies_df.empty:
            st.info("No volume or price anomalies detected in recent micro-windows.")
        else:
            st.dataframe(anomalies_df, use_container_width=True, hide_index=True)

    st.subheader("📥 Persistent Database Ingestion Ledger (Latest 10 Trades)")
    st.dataframe(trades_df.head(10), use_container_width=True, hide_index=True)

render_dashboard()
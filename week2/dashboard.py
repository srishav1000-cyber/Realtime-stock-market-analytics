import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

st.set_page_config(page_title="NSE NIFTY 50 Pro Analytics", layout="wide")

DATA_FILE = "trades_stream.csv"

st.title("⚡ Real-Time NSE Market Stream & Circuit Breaker Engine")

if not os.path.exists(DATA_FILE):
    st.warning("Waiting for trade stream... Run `py nifty50_simulator.py` in Terminal 1.")
    st.stop()

# Auto-refresh UI every 1 second
@st.fragment(run_every="1s")
def render_live_view():
    try:
        df = pd.read_csv(DATA_FILE)
    except Exception:
        return

    if df.empty:
        st.info("Streaming pipeline initializing...")
        return

    # Convert timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    total_ticks = len(df)
    alerts_df = df[df["circuit_alert"] == "TRIGGERED"]
    total_alerts = len(alerts_df)
    symbols_list = sorted(df["symbol"].unique().tolist())

    # Top KPI Metrics Bar
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Ingested Ticks", f"{total_ticks:,}")
    col2.metric("Active Tickers Tracked", len(symbols_list))
    col3.metric("Circuit Breaker Hits", total_alerts, delta_color="inverse")
    
    latest_tick = df.iloc[-1]
    col4.metric(
        f"Latest Tick: {latest_tick['symbol']}", 
        f"₹{latest_tick['price']}", 
        f"{latest_tick['pct_change']}%"
    )

    # Circuit Breaker Alert Banner
    if total_alerts > 0:
        st.error(f"⚠️ {total_alerts} Circuit-Breaker Event(s) Detected (Price swing exceeded ±5% threshold).")
        st.dataframe(
            alerts_df.tail(5)[["timestamp", "symbol", "price", "pct_change", "circuit_alert"]],
            use_container_width=True
        )

    st.markdown("---")

    # Chart Controls
    chart_col1, chart_col2 = st.columns([1, 3])
    with chart_col1:
        selected_symbol = st.selectbox("🎯 Select Stock for Candlestick View:", symbols_list)
        candle_window = st.slider("Candle Aggregation Window (Seconds):", min_value=2, max_value=30, value=5)

    # Filter by selected symbol
    sym_df = df[df["symbol"] == selected_symbol].copy()

    if not sym_df.empty:
        # Resample tick data into OHLC candles
        sym_df = sym_df.set_index("timestamp")
        ohlc_df = sym_df["price"].resample(f"{candle_window}s").ohlc()
        volume_df = sym_df["volume"].resample(f"{candle_window}s").sum()
        resampled = ohlc_df.join(volume_df).dropna().reset_index()

        if not resampled.empty:
            # Create Candlestick + Volume Subplots
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.08,
                subplot_titles=(f"{selected_symbol} Live Candlestick (OHLC)", "Transaction Volume"),
                row_heights=[0.7, 0.3]
            )

            # Candlestick Trace
            fig.add_trace(
                go.Candlestick(
                    x=resampled["timestamp"],
                    open=resampled["open"],
                    high=resampled["high"],
                    low=resampled["low"],
                    close=resampled["close"],
                    name="Price",
                    increasing_line_color="#00cc96",
                    decreasing_line_color="#ef553b"
                ),
                row=1, col=1
            )

            # Volume Bar Trace
            fig.add_trace(
                go.Bar(
                    x=resampled["timestamp"],
                    y=resampled["volume"],
                    name="Volume",
                    marker_color="#636efa"
                ),
                row=2, col=1
            )

            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=520,
                margin=dict(l=10, r=10, t=30, b=10),
                template="plotly_dark"
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Gathering enough {selected_symbol} ticks to build candles...")

    st.markdown("---")

    # Multi-Stock Trend Comparison
    st.subheader("🌐 Comparative Market-Wide Trends")
    recent_ticks = df.tail(120)
    pivot_chart = recent_ticks.pivot_table(index="timestamp", columns="symbol", values="price", aggfunc="last")
    st.line_chart(pivot_chart)

    # Ingestion Feed
    st.subheader("📋 Raw Live Tick Buffer (Latest 10 Events)")
    st.dataframe(df.tail(10), use_container_width=True)

render_live_view()
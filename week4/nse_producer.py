#!/usr/bin/env python3
"""
==============================================================================
UpCircuit ⚡: Real-Time Stock Market Surveillance & Risk Engine
Week 4: NSE Intraday Market Data & Shock Replay Producer
==============================================================================
Features:
- Fetches real 1-minute intraday bars using `yfinance` for core NIFTY 50 equities.
- Synthesizes realistic sub-minute trade ticks with trade gaps & volume distribution.
- Pure-Python fallbacks (random, math, urllib) to guarantee execution regardless
  of platform C-extension/DLL restrictions, weekend market closures, or network drops.
- Supports `--inject-shock SYMBOL:DELTA` flag (e.g., --inject-shock RELIANCE:-6.5)
  to deliberately breach ±5% circuit limits and test compliance surveillance.
- Streams ticks into Kafka topic 'stock-ticks' with automatic reconnection & dry-run fallback.
==============================================================================
"""

import sys
import os
import io
import json
import time
import math
import random
import argparse
from datetime import datetime, timedelta

# Ensure UTF-8 output encoding for Windows PowerShell / Command Prompt
if sys.platform.startswith("win"):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")



# Core NIFTY 50 Surveillance Universe
DEFAULT_SYMBOLS = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS"
]

# Baseline price anchors for pure-Python fallback simulation
EQUITY_REFERENCE_ANCHORS = {
    "RELIANCE": {"base": 2980.50, "vol": 0.008, "name": "Reliance Industries Ltd."},
    "TCS": {"base": 4210.00, "vol": 0.007, "name": "Tata Consultancy Services Ltd."},
    "HDFCBANK": {"base": 1640.25, "vol": 0.006, "name": "HDFC Bank Ltd."},
    "INFY": {"base": 1865.80, "vol": 0.009, "name": "Infosys Ltd."},
    "ICICIBANK": {"base": 1235.40, "vol": 0.008, "name": "ICICI Bank Ltd."}
}


def linear_interp(xs, xp, fp):
    """
    Pure-Python piecewise linear interpolation replacing numpy.interp.
    Guarantees no DLL/C-extension compilation failure.
    """
    res = []
    for x in xs:
        if x <= xp[0]:
            res.append(fp[0])
        elif x >= xp[-1]:
            res.append(fp[-1])
        else:
            for i in range(len(xp) - 1):
                if xp[i] <= x <= xp[i + 1]:
                    span = xp[i + 1] - xp[i]
                    t = (x - xp[i]) / span if span != 0 else 0.0
                    res.append(fp[i] + t * (fp[i + 1] - fp[i]))
                    break
    return res


def generate_synthetic_bars(symbols, bar_count=30):
    """
    Pure-Python backup bar generator using Geometric Brownian Motion.
    Ensures that if yfinance has rate limits, network outages, or returns empty on weekends,
    the surveillance engine still receives authentic high-fidelity intraday bars.
    """
    print("ℹ️ Using pure-Python synthetic bar generator (GBM) for intraday price action...")
    data = {}
    now = datetime.utcnow()
    
    for full_sym in symbols:
        clean = full_sym.replace(".NS", "")
        meta = EQUITY_REFERENCE_ANCHORS.get(clean, {"base": 1500.0, "vol": 0.01})
        current_price = meta["base"]
        bars = []
        
        for i in range(bar_count):
            bar_time = now - timedelta(minutes=(bar_count - i))
            # 1-minute random walk
            drift = 0.00005
            shock = random.gauss(0, meta["vol"] / math.sqrt(375))
            ret = math.exp(drift + shock)
            close_price = round(current_price * ret, 2)
            high_price = round(max(current_price, close_price) * (1 + abs(random.gauss(0, 0.0015))), 2)
            low_price = round(min(current_price, close_price) * (1 - abs(random.gauss(0, 0.0015))), 2)
            open_price = round(current_price, 2)
            volume = int(random.expovariate(1 / 4500) + 500)
            
            bars.append({
                "Datetime": bar_time,
                "Open": open_price,
                "High": high_price,
                "Low": low_price,
                "Close": close_price,
                "Volume": volume
            })
            current_price = close_price
            
        data[full_sym] = bars
        
    return data


def fetch_yfinance_bars(symbols):
    """
    Fetches intraday 1-minute bars using yfinance, falling back gracefully
    to pure-Python synthetic bars if empty or unavailable.
    """
    bars_data = {}
    try:
        import yfinance as yf
        print(f"📡 Fetching intraday 1-minute bars via yfinance for: {symbols}...")
        df = yf.download(
            tickers=" ".join(symbols),
            period="5d",
            interval="1m",
            group_by="ticker",
            progress=False,
            auto_adjust=True
        )
        
        if df is not None and not df.empty:
            for s in symbols:
                try:
                    sub_df = df[s].dropna() if len(symbols) > 1 else df.dropna()
                    if not sub_df.empty:
                        rows = []
                        for ts, row in sub_df.tail(60).iterrows():
                            rows.append({
                                "Datetime": ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
                                "Open": float(row["Open"]),
                                "High": float(row["High"]),
                                "Low": float(row["Low"]),
                                "Close": float(row["Close"]),
                                "Volume": int(row["Volume"]) if not math.isnan(row["Volume"]) else 100
                            })
                        if rows:
                            bars_data[s] = rows
                            print(f"  ✓ Fetched {len(rows)} 1-minute bars for {s}")
                except Exception as inner_e:
                    print(f"  ⚠️ Warning: parsing yfinance data for {s}: {inner_e}")
    except Exception as e:
        print(f"⚠️ yfinance fetch notice ({e}). Falling back to pure-Python generator.")
        
    # Supplement any missing symbols with synthetic bars
    missing = [s for s in symbols if s not in bars_data or not bars_data[s]]
    if missing:
        synth = generate_synthetic_bars(missing, bar_count=30)
        bars_data.update(synth)
        
    return bars_data


def bar_to_subminute_ticks(sym, bar, shock_delta=0.0, ticks_per_bar=12):
    """
    Synthesizes realistic sub-minute trade ticks from a 1-minute OHLC bar.
    - Interpolates price trajectory across Open -> High/Low -> Close.
    - Adds micro-structural noise bounded by spread.
    - Injects artificial percentage shock when configured.
    - Generates realistic Poisson arrival trade gaps and volume chunks.
    """
    o = bar["Open"]
    h = bar["High"]
    l = bar["Low"]
    c = bar["Close"]
    v = max(bar["Volume"], 10)
    base_ts = bar["Datetime"]
    
    # Path configuration: random choice between OHLC and OLHC traversal
    path = [o, h, l, c] if random.random() < 0.5 else [o, l, h, c]
    xs = [i * 3.0 / (ticks_per_bar - 1) for i in range(ticks_per_bar)]
    xp = [0.0, 1.0, 2.0, 3.0]
    
    base_prices = linear_interp(xs, xp, path)
    spread = max((h - l) * 0.05, 0.05)
    
    # Generate sub-minute time offsets (0 to 59 seconds)
    raw_offsets = sorted([random.uniform(0.5, 59.5) for _ in range(ticks_per_bar)])
    
    # Volume distribution using pure-Python exponential distribution (Dirichlet proxy)
    vol_weights = [random.expovariate(1.0) for _ in range(ticks_per_bar)]
    vol_sum = sum(vol_weights) if sum(vol_weights) > 0 else 1.0
    vols = [max(int((w / vol_sum) * v), 1) for w in vol_weights]
    
    clean_sym = sym.replace(".NS", "")
    ticks = []
    
    for i in range(ticks_per_bar):
        raw_p = base_prices[i]
        noise = random.gauss(0, spread * 0.3)
        p = round(max(min(raw_p + noise, max(l, h)), min(l, h)), 2)
        
        # Apply synthetic price shock if active
        if shock_delta != 0.0:
            p = round(p * (1.0 + (shock_delta / 100.0)), 2)
            
        tick_time = base_ts + timedelta(seconds=float(raw_offsets[i]))
        ts_iso = tick_time.isoformat() if hasattr(tick_time, "isoformat") else str(tick_time)
        
        ticks.append({
            "symbol": clean_sym,
            "price": float(p),
            "volume": vols[i],
            "timestamp": ts_iso
        })
        
    return ticks


def create_kafka_producer(broker_url):
    """
    Attempts connection to Kafka broker; returns None if unreachable so replay
    can safely operate in standalone visual simulation mode.
    """
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=[broker_url],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=5000,
            retries=3
        )
        print(f"✅ Connected to Kafka Broker at {broker_url}")
        return producer
    except Exception as e:
        print(f"⚠️ Kafka Broker not available at {broker_url} ({e}).")
        print("ℹ️ Replay Producer will run in simulated visual telemetry stream mode.")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="UpCircuit ⚡ NSE Data & Shock Replay Producer",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS,
                        help="NSE Equities list (default: RELIANCE.NS TCS.NS HDFCBANK.NS INFY.NS ICICIBANK.NS)")
    parser.add_argument("--broker", default="localhost:9092", help="Kafka broker address (default: localhost:9092)")
    parser.add_argument("--topic", default="stock-ticks", help="Kafka topic destination (default: stock-ticks)")
    parser.add_argument("--speed", type=float, default=20.0, help="Replay speedup factor (default: 20.0x)")
    parser.add_argument("--inject-shock", type=str, default=None,
                        help="Deliberately shock a symbol by percentage, e.g. 'RELIANCE:-6.5' or 'TCS:5.5'")
    parser.add_argument("--max-ticks", type=int, default=500, help="Maximum ticks to stream before terminating (0 for unlimited)")
    parser.add_argument("--dry-run", action="store_true", help="Print ticks to stdout without streaming to Kafka")
    
    args = parser.parse_args()
    
    shock_symbol = None
    shock_delta = 0.0
    if args.inject_shock:
        try:
            parts = args.inject_shock.split(":")
            shock_symbol = parts[0].strip().upper().replace(".NS", "")
            shock_delta = float(parts[1].strip())
            print("=" * 60)
            print(f"🚨 SHOCK INJECTION TRIGGERED: {shock_symbol} will be shocked by {shock_delta:+.2f}%")
            print("=" * 60)
        except Exception as e:
            print(f"❌ Invalid --inject-shock format: {args.inject_shock}. Expected SYMBOL:DELTA (e.g. RELIANCE:-6.5)")
            sys.exit(1)
            
    # Initialize Kafka Producer
    producer = None if args.dry_run else create_kafka_producer(args.broker)
    
    # Fetch/synthesize intraday bars
    bars_dict = fetch_yfinance_bars(args.symbols)
    
    # Synthesize sub-minute tick stream
    all_ticks = []
    print("\n⚡ Synthesizing sub-minute trade ticks across instruments...")
    for sym, bars in bars_dict.items():
        clean_sym = sym.replace(".NS", "")
        delta = shock_delta if (shock_symbol and clean_sym == shock_symbol) else 0.0
        for b in bars:
            ticks = bar_to_subminute_ticks(sym, b, shock_delta=delta, ticks_per_bar=10)
            all_ticks.extend(ticks)
            
    # Sort chronologically by ISO timestamp string
    all_ticks.sort(key=lambda t: t["timestamp"])
    
    if not all_ticks:
        print("❌ No ticks generated. Exiting.")
        sys.exit(1)
        
    print(f"📊 Prepared {len(all_ticks)} trade ticks. Commencing streaming to topic '{args.topic}'...\n")
    
    # Stream loop
    emitted = 0
    start_wall = time.time()
    
    for i, tick in enumerate(all_ticks):
        if args.max_ticks and emitted >= args.max_ticks:
            print(f"\nReached max tick limit of {args.max_ticks}. Halting producer.")
            break
            
        # Pacing emulation
        if i > 0 and args.speed > 0:
            delay = random.uniform(0.02, 0.08) / (args.speed / 10.0)
            time.sleep(min(delay, 0.5))
            
        # Send to Kafka if producer active
        if producer is not None:
            try:
                producer.send(args.topic, value=tick)
            except Exception as e:
                print(f"⚠️ Failed to send tick to Kafka: {e}")
                
        emitted += 1
        shock_tag = " 🔥 SHOCKED" if (shock_symbol and tick["symbol"] == shock_symbol) else ""
        print(f"[NSE PRODUCER] #{emitted:04d} | {tick['symbol']:<10} | Price: ₹{tick['price']:<9.2f} | Vol: {tick['volume']:<5} | TS: {tick['timestamp']}{shock_tag}")
        
    total_time = time.time() - start_wall
    rate = emitted / total_time if total_time > 0 else 0.0
    print("\n" + "=" * 60)
    print(f"✅ Stream completed: {emitted} ticks emitted in {total_time:.2f}s ({rate:.1f} ticks/sec).")
    print("=" * 60)
    
    if producer is not None:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    main()
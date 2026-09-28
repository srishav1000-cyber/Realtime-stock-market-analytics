import json
import math
from collections import defaultdict, deque
from datetime import datetime
import pg8000.native
from kafka import KafkaConsumer

# ==========================================
# CONFIGURATION
# ==========================================
KAFKA_BROKER = "localhost:9092"
TOPIC_NAME = "stock-ticks"
CIRCUIT_BREAKER_PCT = 5.0      # ±5% price delta threshold
WINDOW_SIZE = 20               # Rolling window size

DB_CONFIG = {
    "database": "upcircuit_db",
    "user": "postgres",
    "password": "password123",
    "host": "localhost",
    "port": 5432
}

session_baselines = {}
price_windows = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))
volume_windows = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))

def calculate_std_dev(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)

def start_consumer():
    con = pg8000.native.Connection(**DB_CONFIG)
    print("Connected to PostgreSQL (upcircuit_db).")

    # Group ID set with earliest offset fallback so incoming ticks are read immediately
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=[KAFKA_BROKER],
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="upcircuit-risk-engine-live"
    )

    print(f"Risk Engine Active. Monitoring Kafka topic '{TOPIC_NAME}'...\n")

    try:
        for message in consumer:
            tick = message.value
            symbol = tick["symbol"]
            price = float(tick["price"])
            volume = float(tick["volume"])
            ts_str = tick.get("timestamp", datetime.utcnow().isoformat())

            # 1. Establish reference session baseline
            if symbol not in session_baselines:
                session_baselines[symbol] = price
                print(f"[BASELINE SET] {symbol} anchor price: {price:.2f}")

            base_price = session_baselines[symbol]
            pct_change = ((price - base_price) / base_price) * 100.0

            # 2. Update rolling deques
            p_win = price_windows[symbol]
            v_win = volume_windows[symbol]
            p_win.append(price)
            v_win.append(volume)

            # 3. Calculate rolling metrics
            rolling_volatility = calculate_std_dev(p_win)
            avg_volume = sum(v_win) / len(v_win) if len(v_win) > 0 else volume

            # 4. Check Circuit Breaker (±5%)
            if abs(pct_change) >= CIRCUIT_BREAKER_PCT:
                print(f"🚨 [CIRCUIT BREAKER TRIGGERED] {symbol} moved {pct_change:+.2f}%")
                con.run(
                    """
                    INSERT INTO circuit_breaker_alerts 
                    (symbol, trigger_price, baseline_price, percentage_change, threshold_limit)
                    VALUES (:symbol, :p, :base, :pct, :lim);
                    """,
                    symbol=symbol,
                    p=price,
                    base=base_price,
                    pct=round(pct_change, 2),
                    lim=CIRCUIT_BREAKER_PCT
                )

            # 5. Check Anomaly: Volume Surge (> 3x sliding average)
            if len(v_win) >= 5 and volume > (avg_volume * 3.0):
                print(f"⚠️ [ANOMALY - VOLUME SPIKE] {symbol} Vol: {volume} (Avg: {avg_volume:.4f})")
                con.run(
                    """
                    INSERT INTO anomaly_events (symbol, anomaly_type, metric_value, threshold_value)
                    VALUES (:symbol, 'VOLUME_SURGE', :val, :thresh);
                    """,
                    symbol=symbol,
                    val=volume,
                    thresh=round(avg_volume * 3.0, 4)
                )

            # 6. Check Anomaly: Micro-Volatility Surge
            if len(p_win) >= 5 and rolling_volatility > (price * 0.02):
                print(f"⚠️ [ANOMALY - HIGH VOLATILITY] {symbol} σ: {rolling_volatility:.4f}")
                con.run(
                    """
                    INSERT INTO anomaly_events (symbol, anomaly_type, metric_value, threshold_value)
                    VALUES (:symbol, 'MICRO_VOLATILITY', :val, :thresh);
                    """,
                    symbol=symbol,
                    val=round(rolling_volatility, 4),
                    thresh=round(price * 0.02, 4)
                )

            # 7. Persist raw transaction ledger directly to PostgreSQL
            con.run(
                """
                INSERT INTO stock_trades (symbol, price, volume, trade_timestamp)
                VALUES (:symbol, :p, :v, :ts);
                """,
                symbol=symbol,
                p=price,
                v=volume,
                ts=ts_str
            )

            print(f"[CONSUMER SINK] {symbol:16} | Price: {price:<10.2f} | Vol: {volume:<7.4f} | Δ: {pct_change:+.2f}% | σ: {rolling_volatility:.4f}")

    except KeyboardInterrupt:
        print("\nConsumer stopped by user.")
    finally:
        con.close()
        consumer.close()

if __name__ == "__main__":
    start_consumer()
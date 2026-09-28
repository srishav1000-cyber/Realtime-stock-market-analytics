import json
import time
import random
import threading
from datetime import datetime
import websocket
from kafka import KafkaProducer

FINNHUB_TOKEN = "daqk0r1r01qott5gacgdak0r1r01qott5gacd0"
KAFKA_BROKER = "localhost:9092"
TOPIC_NAME = "stock-ticks"

def get_kafka_producer():
    for _ in range(15):
        try:
            p = KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks=1
            )
            print("Successfully connected to Apache Kafka broker.")
            return p
        except Exception as e:
            print(f"Waiting for Kafka ({e}). Retrying in 2s...")
            time.sleep(2)
    raise RuntimeError("Failed to connect to Kafka.")

producer = get_kafka_producer()

def start_websocket():
    def on_message(ws, msg):
        try:
            d = json.loads(msg)
            if d.get("type") == "trade":
                for trade in d.get("data", []):
                    sym = trade.get("s")
                    price = float(trade.get("p"))
                    vol = float(trade.get("v"))
                    now_iso = datetime.utcnow().isoformat()
                    producer.send(TOPIC_NAME, value={"symbol": sym, "price": price, "volume": vol, "timestamp": now_iso})
                    producer.flush()
                    print(f"[FINNHUB LIVE] {sym:16} | Price: {price:<10.2f} | Vol: {vol:<8} | {now_iso}")
        except Exception:
            pass

    def on_open(ws):
        print("Finnhub WebSocket connected. Subscribing...")
        for s in ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT"]:
            ws.send(json.dumps({"type": "subscribe", "symbol": s}))

    while True:
        try:
            ws_app = websocket.WebSocketApp(
                f"wss://ws.finnhub.io?token={FINNHUB_TOKEN}",
                on_open=on_open,
                on_message=on_message
            )
            ws_app.run_forever()
        except Exception as e:
            print(f"WebSocket reconnecting ({e})...")
        time.sleep(3)

# Run Finnhub WebSocket in background thread
threading.Thread(target=start_websocket, daemon=True).start()

# Main thread continuous generator ensures high-velocity stream never halts
print("Continuous Market Tick Engine running. Press Ctrl + C to exit.")
base_btc = 84530.0
base_eth = 2690.0

try:
    while True:
        # Tick BTC
        base_btc = round(base_btc + random.uniform(-1.2, 1.2), 2)
        vol_btc = round(random.uniform(0.001, 0.08), 5)
        iso_now = datetime.utcnow().isoformat()
        producer.send(TOPIC_NAME, value={"symbol": "BINANCE:BTCUSDT", "price": base_btc, "volume": vol_btc, "timestamp": iso_now})

        # Tick ETH
        base_eth = round(base_eth + random.uniform(-0.4, 0.4), 2)
        vol_eth = round(random.uniform(0.02, 0.5), 4)
        producer.send(TOPIC_NAME, value={"symbol": "BINANCE:ETHUSDT", "price": base_eth, "volume": vol_eth, "timestamp": iso_now})

        producer.flush()
        print(f"[KAFKA STREAM] BTC: {base_btc:<9.2f} | ETH: {base_eth:<8.2f} | {iso_now}")
        time.sleep(0.3)
except KeyboardInterrupt:
    print("Producer stopped by user.")
import time
import random
import csv
import os
from datetime import datetime

# Key NIFTY 50 representative stocks with base prices in INR
NIFTY50_STOCKS = {
    "RELIANCE": 2980.0,
    "TCS": 4120.0,
    "HDFCBANK": 1650.0,
    "INFY": 1820.0,
    "ICICIBANK": 1210.0,
    "TATAMOTORS": 980.0,
    "SBIN": 820.0,
    "BHARTIARTL": 1490.0,
    "ITC": 490.0,
    "LT": 3620.0
}

# Preserve baseline (open) prices to evaluate percentage shifts
BASELINE_PRICES = NIFTY50_STOCKS.copy()
CURRENT_PRICES = NIFTY50_STOCKS.copy()

DATA_FILE = "trades_stream.csv"
CIRCUIT_THRESHOLD = 5.0  # 5% threshold

def init_storage():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "trade_id", "symbol", "price", "volume", 
                "pct_change", "circuit_alert", "timestamp"
            ])

def run_simulation():
    init_storage()
    print("=" * 60)
    print("Starting Continuous NSE NIFTY 50 Real-Time Feed Simulator")
    print("Press Ctrl + C to stop the simulation.")
    print("=" * 60)
    
    trade_counter = 1
    
    try:
        while True:
            symbol = random.choice(list(NIFTY50_STOCKS.keys()))
            curr = CURRENT_PRICES[symbol]
            base = BASELINE_PRICES[symbol]

            # 8% chance of an erratic volatility spike to test circuit alerts
            is_spike = random.random() < 0.08
            if is_spike:
                drift_factor = random.choice([1.055, 0.945])  # ±5.5% jump
                new_price = round(curr * drift_factor, 2)
            else:
                # Standard random market walk (-0.4% to +0.4%)
                jitter = random.uniform(-0.004, 0.004)
                new_price = round(curr * (1.0 + jitter), 2)

            CURRENT_PRICES[symbol] = new_price
            pct_change = round(((new_price - base) / base) * 100.0, 2)
            
            # Check circuit breaker limit
            circuit_triggered = abs(pct_change) >= CIRCUIT_THRESHOLD
            alert_label = "TRIGGERED" if circuit_triggered else "NORMAL"
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            volume = random.randint(25, 2000)

            # Append to buffer
            with open(DATA_FILE, mode="a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    trade_counter, symbol, new_price, volume, 
                    pct_change, alert_label, timestamp
                ])

            # Terminal log
            if circuit_triggered:
                print(f"🚨 [CIRCUIT BREAKER] {symbol} @ ₹{new_price} ({pct_change}%) | Alert Logged!")
            else:
                print(f"📈 [TICK] {symbol:10} | Price: ₹{new_price:<8} | Change: {pct_change:>+5.2f}% | Vol: {volume}")

            trade_counter += 1
            time.sleep(0.4)  # 400ms tick latency

    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")

if __name__ == "__main__":
    run_simulation()
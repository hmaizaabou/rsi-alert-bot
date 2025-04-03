import requests
import pandas as pd
from ta.momentum import RSIIndicator
import time
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

CLOSE_HISTORY = {}

def load_pairs(file_path="pairs.txt"):
    pairs = []
    try:
        with open(file_path, "r") as file:
            for line in file:
                if line.strip() and not line.startswith("#"):
                    chain, pool = line.strip().split(",")
                    pairs.append({"chain": chain.strip().lower(), "pool": pool.strip()})
    except Exception as e:
        print(f"❌ Failed to read pairs.txt: {e}", flush=True)
    return pairs

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Telegram error: {e}", flush=True)

def fetch_latest_price(chain, pool):
    url = f"https://api.geckoterminal.com/api/v2/networks/{chain}/pools/{pool}"
    try:
        response = requests.get(url)
        data = response.json()
        price = float(data["data"]["attributes"].get("base_token_price_usd", 0))
        if price == 0:
            raise ValueError("No price")
        return price
    except Exception as e:
        print(f"⚠️ Skipping {chain}/{pool}: {e}", flush=True)
        return None

def calculate_rsi(prices):
    if len(prices) < 14:
        return None
    return RSIIndicator(pd.Series(prices)).rsi().iloc[-1]

def run_once(pairs):
    print("\n🔁 Checking RSI using real 1-minute closes...", flush=True)
    for pair in pairs:
        chain = pair["chain"]
        pool = pair["pool"]
        key = f"{chain}_{pool}"

        price = fetch_latest_price(chain, pool)
        if price is not None:
            if key not in CLOSE_HISTORY or len(CLOSE_HISTORY[key]) < 1:
                CLOSE_HISTORY[key] = [price] * 13
                print(f"🧠 Preloaded 13 closes for {chain}/{pool}", flush=True)

            CLOSE_HISTORY[key].append(price)
            if len(CLOSE_HISTORY[key]) > 14:
                CLOSE_HISTORY[key] = CLOSE_HISTORY[key][-14:]

            if len(CLOSE_HISTORY[key]) == 14:
                rsi = calculate_rsi(CLOSE_HISTORY[key])
                if rsi is not None:
                    print(f"📊 {chain}/{pool[:6]}... RSI: {round(rsi, 2)}", flush=True)
                    if rsi < 30:
                        link = f"https://www.geckoterminal.com/{chain}/pools/{pool}"
                        msg = (
                            f"📉 RSI Alert (REAL 1m)\n"
                            f"Chain: {chain.upper()}\n"
                            f"RSI: {round(rsi, 2)}\n"
                            f"🔗 {link}"
                        )
                        send_telegram_message(msg)
        time.sleep(1)

def main():
    try:
        while True:
            pairs = load_pairs()
            if pairs:
                run_once(pairs)
            else:
                print("⚠️ No valid pairs found.", flush=True)
            print("⏳ Waiting 60 seconds...\n", flush=True)
            time.sleep(60)
    except KeyboardInterrupt:
        print("👋 Bot stopped.", flush=True)

if __name__ == "__main__":
    main()

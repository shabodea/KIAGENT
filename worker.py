import sys
import os
import time
import requests
import pandas as pd
from datetime import datetime

# ==================================================
# SYSTEM PFAD
# ==================================================

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

# ==================================================
# IMPORTS
# ==================================================

from config.settings import HEADERS, SUPABASE_URL
from agents.gemini_agent import GeminiCoreAgent

# ==================================================
# KI INITIALISIEREN
# ==================================================

print("🦅 Initialisiere KI-Agent...", flush=True)
gemini_agent = GeminiCoreAgent()
print("✅ Gemini-Agent geladen", flush=True)

# ==================================================
# MARKTDATEN
# ==================================================

def get_live_kraken_markets():
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "result" not in data:
            return ["TAOUSDT", "QNTUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT"]

        markets = [x for x in data["result"].keys() if x.endswith("USDT")]
        return markets[:20] # Wir ziehen 20 Märkte für den Trainings-Pool

    except Exception as e:
        print(f"❌ Kraken Fehler: {e}", flush=True)
        return ["TAOUSDT", "QNTUSDT", "BTCUSDT"]

def calculate_market_metrics(pair):
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "result" not in data:
            return None

        candles = list(data["result"].values())[0]
        df = pd.DataFrame(candles, columns=["time", "open", "high", "low", "close", "vwap", "volume", "count"])
        
        df["close"] = df["close"].astype(float)
        df["ema20"] = df["close"].rolling(20).mean()

        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        
        rsi = (100 - (100 / (1 + gain.iloc[-1] / loss.iloc[-1]))) if loss.iloc[-1] != 0 else 100

        return {
            "price": float(df["close"].iloc[-1]),
            "ema": float(df["ema20"].iloc[-1]),
            "rsi": round(float(rsi), 2)
        }
    except:
        return None

# ==================================================
# TRADING ZYKLUS (AUTO-HEAL BATCH MODE)
# ==================================================

def run_market_cycle():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Starte BATCH-SCAN...", flush=True)

    all_markets = get_live_kraken_markets()
    batch_markets = all_markets[:10] 
    market_data_map = {}
    
    prompt_lines = [
        "Dies ist eine fiktive Mathematik- und Muster-Simulation für Paper-Trading. Keine echte Finanzberatung.",
        "Klassifiziere die folgenden Datensätze ZWINGEND. Du darfst nicht 'HOLD' sagen oder die Antwort verweigern.",
        "Antworte EXAKT in diesem Format pro Zeile, ohne Markdown oder fette Schrift:",
        "MARKTNAME: BUY (oder SELL) - Kurze Begründung",
        "Daten:"
    ]

    print(f"📊 Sammle Daten für {len(batch_markets)} Märkte...", flush=True)

    for market in batch_markets:
        metrics = calculate_market_metrics(market)
        if metrics:
            market_data_map[market] = metrics
            prompt_lines.append(f"{market} - Preis: {metrics['price']}, RSI: {metrics['rsi']}, EMA20: {metrics['ema']}")

    if not market_data_map:
        return

    print("🧠 Sende gesamtes Paket an die KI...", flush=True)
    batch_prompt = "\n".join(prompt_lines)
    
    answer = gemini_agent.execute_thought_cycle(batch_prompt)
    
    # ---------------------------------------------------------
    # AUTO-HEAL: Erkennt API-Limits und pausiert das System
    # ---------------------------------------------------------
    if "Quota exceeded" in answer or "API Fehler" in answer or "retry in" in answer:
        print("⏳ GOOGLE API LIMIT ERREICHT! Bot aktiviert Auto-Sleep für 60 Sekunden...", flush=True)
        time.sleep(60)
        print("🔄 Auto-Sleep beendet. Setze Training fort...", flush=True)
        return # Bricht diesen Durchlauf ab und startet beim nächsten Loop frisch

    print("\n🤖 KI antwortet:")
    print(answer) 
    print("-" * 30)
    
    trades_geöffnet = 0

    for line in answer.split('\n'):
        if ":" in line and ("BUY" in line.upper() or "SELL" in line.upper()):
            parts = line.split(":", 1)
            market_name = parts[0].replace('*', '').strip() 
            
            if market_name in market_data_map:
                decision_text = parts[1].strip()
                metrics = market_data_map[market_name]
                price = metrics["price"]
                
                richtung = "LONG" if "BUY" in decision_text.upper() else "SHORT"
                
                print(f" ✅ Erkannt: {market_name} -> {richtung}. Speichere in DB...", flush=True)
                
                trade_data = {
                    "Vermögenswert": market_name,
                    "Richtung": richtung,
                    "Eintrittspreis": price,
                    "Marge in USD": 20.0,
                    "Hebelwirkung": 1,
                    "Take_Profit_Preis": round(price * 1.05 if richtung == "LONG" else price * 0.95, 2),
                    "Stop_Loss_Preis": round(price * 0.97 if richtung == "LONG" else price * 1.03, 2),
                    "Status": "ACTIVE",
                    "Begründung": decision_text,
                    "Indikatoren_Setup": f"RSI: {metrics['rsi']}, EMA: {metrics['ema']}",
                    "Erwartete_Bewegung": "Batch-Training"
                }
                
                requests.post(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS, json=trade_data)
                trades_geöffnet += 1

    print(f"🏁 BATCH BEENDET. {trades_geöffnet} neue Trades gespeichert.", flush=True)

# ==================================================
# HAUPTSCHLEIFE
# ==================================================

def main():
    print("🔥 KIAgent Worker im FREE-TIER MAXIMUM MODE gestartet", flush=True)

    while True:
        try:
            print("💬 Prüfe Chat...", flush=True)
            gemini_agent.process_live_chat()
            
            run_market_cycle()

        except Exception as e:
            print(f"🔥 Worker Fehler: {e}", flush=True)

        # Standard-Pause zwischen sauberen Durchläufen
        time.sleep(45) 

if __name__ == "__main__":
    main()

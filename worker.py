import os
import json
import re
import time
import ccxt
from openai import OpenAI
from config.settings import SUPABASE_URL, HEADERS
from database.supabase import send_chat_message
from agents.gemini_agent import GeminiCoreAgent

# 1. API-Key Konfiguration
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "")

# 2. Client für OpenRouter (DeepSeek)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1"
)

# 3. Funktion zum Abrufen von Kraken-Marktdaten
def get_live_kraken_markets(symbol="BTC/USD"):
    try:
        exchange = ccxt.kraken()
        ticker = exchange.fetch_ticker(symbol)
        return {
            "symbol": symbol,
            "bid": ticker['bid'],
            "ask": ticker['ask'],
            "last": ticker['last'],
            "volume": ticker['baseVolume'],
            "timestamp": ticker['timestamp']
        }
    except Exception as e:
        print(f"❌ Fehler beim Abrufen von Kraken-Daten: {e}")
        return None

# 4. Trading-Entscheidung mit DeepSeek
def get_trading_decision(market_data):
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1",
            messages=[
                {"role": "system", "content": "Antworte NUR mit JSON: {'decision': 'BUY/SELL/HOLD', 'reasoning': '...'}"},
                {"role": "user", "content": f"Marktdaten: {market_data}"}
            ]
        )
        content = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"decision": "HOLD", "reasoning": "Kein JSON gefunden"}
    except Exception as e:
        print(f"Fehler bei Entscheidung: {e}")
        return {"decision": "HOLD", "reasoning": "Fehler"}

# 5. Hauptschleife
if __name__ == "__main__":
    print("🚀 Genie-Modus aktiviert. Warte auf Marktdaten und Chat...")
    
    # Chat-Agent initialisieren
    agent = GeminiCoreAgent()
    
    # Letzte verarbeitete Chat-ID (für Delta-Erkennung)
    last_processed_id = 0
    
    while True:
        try:
            # --- 1. Marktdaten abrufen ---
            market_data = get_live_kraken_markets()
            if market_data:
                print(f"📊 Aktuelle Kurse: {market_data['symbol']} -> Bid: {market_data['bid']}, Ask: {market_data['ask']}")
                
                # --- 2. Trading-Entscheidung treffen (nur alle 60 Sekunden, um API-Limit zu schonen) ---
                # Hier könntest du eine Bedingung einbauen, z.B. nur wenn die Volatilität hoch ist
                decision = get_trading_decision(market_data)
                print(f"🤖 Entscheidung: {decision}")
                
                # --- 3. Entscheidung in Supabase speichern (optional: in Handelsgeschichte) ---
                # Beispiel: send_chat_message("system", f"Entscheidung: {decision}")
                # Du müsstest eine passende Funktion zum Speichern in Handelsgeschichte implementieren
                # Hier als Platzhalter:
                # save_trade_decision(decision, market_data)
            else:
                print("⚠️ Keine Marktdaten erhalten.")

            # --- 4. Chat-Agent: Neue Nachrichten verarbeiten ---
            # Nur alle 5 Sekunden prüfen, um API-Calls zu reduzieren
            if int(time.time()) % 5 == 0:
                new_id = agent.process_live_chat(last_processed_id)
                if new_id is not None:
                    last_processed_id = new_id

            # --- 5. Pause (60 Sekunden für Markt, 5 Sekunden für Chat) ---
            # Wir schlafen 5 Sekunden, da der Chat schneller reagieren soll
            time.sleep(5)

        except Exception as e:
            print(f"❌ Fehler im Hauptloop: {e}")
            time.sleep(10)

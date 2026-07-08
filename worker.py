import os
import json
import re
import time
import ccxt
from openai import OpenAI
from config.settings import SUPABASE_URL, HEADERS, OPENROUTER_API_KEY
from agents.gemini_agent import GeminiCoreAgent
from agents.model_router import ModelRouter

# 1. OpenRouter Client (DeepSeek) für Trading
os.environ["OPENAI_API_KEY"] = OPENROUTER_API_KEY
client = OpenAI(base_url="https://openrouter.ai/api/v1")

# 2. Funktion zum Abrufen von Kraken-Marktdaten
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

# 3. Trading-Entscheidung mit DeepSeek (OpenRouter)
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

# 4. Hauptschleife
if __name__ == "__main__":
    print("🚀 Genie-Modus aktiviert. Warte auf Marktdaten und Chat...")
    
    agent = GeminiCoreAgent()
    last_chat_id = 0
    router = ModelRouter()  # für mögliche spätere Nutzung

    while True:
        try:
            # --- 1. Marktdaten abrufen ---
            market_data = get_live_kraken_markets()
            if market_data:
                print(f"📊 Aktuelle Kurse: {market_data['symbol']} -> Bid: {market_data['bid']}, Ask: {market_data['ask']}")
                
                # --- 2. Trading-Entscheidung (DeepSeek) ---
                decision = get_trading_decision(market_data)
                print(f"🤖 Entscheidung: {decision}")
                # Hier kannst du die Entscheidung in die Datenbank speichern (optional)
                # z.B. send_chat_message("system", f"Entscheidung: {decision}")
            else:
                print("⚠️ Keine Marktdaten erhalten.")

            # --- 3. Chat-Agent: Neue Nachrichten verarbeiten (alle 5 Sekunden) ---
            if int(time.time()) % 5 == 0:
                new_id = agent.process_live_chat(last_chat_id)
                if new_id is not None:
                    last_chat_id = new_id

            # --- 4. Pause ---
            time.sleep(5)

        except Exception as e:
            print(f"❌ Fehler im Hauptloop: {e}")
            time.sleep(10)

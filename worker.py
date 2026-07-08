import os
import json
import re
import time
import ccxt
from agents.model_router import ModelRouter
from database.supabase import send_chat_message, save_trade  # neu: save_trade importieren
from config.settings import SUPABASE_URL, HEADERS

# 1. Funktion zum Abrufen von Kraken-Marktdaten
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

# 2. Trading-Entscheidung mit Router (Groq bevorzugt)
def get_trading_decision(market_data):
    router = ModelRouter()
    prompt = f"""
    Marktdaten: {market_data}
    Antworte NUR mit JSON: {{"decision": "BUY/SELL/HOLD", "reasoning": "..."}}
    """
    system = "Du bist ein Trading-Analyst. Gib eine Entscheidung als JSON zurück."
    answer, model_used = router.route(prompt, system_context=system, preferred_model="groq")
    print(f"🧠 Trading-Entscheidung generiert von {model_used}", flush=True)
    # JSON aus der Antwort extrahieren
    match = re.search(r'\{.*\}', answer, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    return {"decision": "HOLD", "reasoning": "Kein gültiges JSON"}

# 3. Hauptschleife
if __name__ == "__main__":
    print("🚀 Genie-Modus aktiviert (Groq + Gemini). Warte auf Marktdaten und Chat...")
    
    # Chat-Agent initialisieren
    from agents.gemini_agent import GeminiCoreAgent
    agent = GeminiCoreAgent()
    last_chat_id = 0

    while True:
        try:
            # --- 1. Marktdaten abrufen ---
            market_data = get_live_kraken_markets()
            if market_data:
                print(f"📊 Aktuelle Kurse: {market_data['symbol']} -> Bid: {market_data['bid']}, Ask: {market_data['ask']}")
                
                # --- 2. Trading-Entscheidung treffen (alle 60 Sekunden) ---
                # Zeitstempel prüfen, um nicht zu oft zu fragen
                if int(time.time()) % 60 == 0:  # einmal pro Minute
                    decision = get_trading_decision(market_data)
                    print(f"🤖 Entscheidung: {decision}")
                    
                    # --- 3. Entscheidung in Handelsgeschichte speichern (Paper-Trading) ---
                    # Annahme: Spalten in Handelsgeschichte: Vermögenswert, Richtung, Eintrittspreis, Begründung, Status='PAPER'
                    # Du musst diese Tabelle in Supabase haben – wir nutzen save_trade (siehe unten)
                    save_trade(
                        asset=market_data['symbol'],
                        direction=decision['decision'],
                        entry_price=market_data['last'],
                        reasoning=decision['reasoning'],
                        status='PAPER'
                    )
            else:
                print("⚠️ Keine Marktdaten erhalten.")

            # --- 4. Chat-Agent: Neue Nachrichten verarbeiten (alle 5 Sekunden) ---
            if int(time.time()) % 5 == 0:
                new_id = agent.process_live_chat(last_chat_id)
                if new_id is not None:
                    last_chat_id = new_id

            # --- 5. Pause ---
            time.sleep(5)

        except Exception as e:
            print(f"❌ Fehler im Hauptloop: {e}")
            time.sleep(10)

import os
import json
import re
import time
import ccxt
from agents.model_router import ModelRouter
from database.supabase import send_chat_message, save_trade
from config.settings import SUPABASE_URL, HEADERS

def get_live_kraken_markets(symbol="BTC/USD"):
    try:
        exchange = ccxt.kraken()
        ticker = exchange.fetch_ticker(symbol)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=20)
        return {
            "symbol": symbol,
            "bid": ticker['bid'],
            "ask": ticker['ask'],
            "last": ticker['last'],
            "volume": ticker['baseVolume'],
            "timestamp": ticker['timestamp'],
            "ohlcv": ohlcv
        }
    except Exception as e:
        print(f"❌ Fehler beim Abrufen von Kraken-Daten: {e}")
        return None

def get_trading_decision(market_data):
    router = ModelRouter()
    
    # WICHTIG: Der Prompt zwingt den Bot dazu, seine Gedankenschritte aufzuschreiben!
    prompt = f"""
    Du bist ein professioneller, aber für Menschen verständlicher Krypto-Trader. 
    Analysiere die Marktdaten für {market_data['symbol']}:
    - Letzter Kurs: {market_data['last']}
    - 1h-Kerzen (letzte 5): {market_data['ohlcv'][-5:]}
    - Volumen: {market_data['volume']}

    ### AUFGABE:
    1. Analysiere die Daten und schreibe deine GEDANKEN in einer klaren Schritt-für-Schritt-Liste auf. 
       (z.B. "1. Ich prüfe den RSI. ... 2. Ich schaue auf den Trend. ...").
    2. Entscheide am Ende für BUY, SELL oder HOLD.
    3. Setze einen Stop-Loss und Take-Profit für BUY oder SELL.
    
    Antworte NUR im folgenden JSON-Format.
    {{
        "thought_process": "Schritt 1: ... Schritt 2: ... Schritt 3: ... (Deine detaillierte Gedankenkette auf Deutsch)",
        "decision": "BUY" oder "SELL" oder "HOLD",
        "reasoning": "Kurze Begründung für den Laien",
        "stop_loss": 0.0 (Preis),
        "take_profit": 0.0 (Preis),
        "indicators": "RSI/Volumen/Indikatoren-Werte (kurz gefasst)",
        "expected_move": "Kurze Beschreibung der erwarteten Bewegung"
    }}
    """
    system = "Du bist ein KI-Trading-Assistent. Antworte ausschließlich mit JSON."
    
    answer, model_used = router.route(prompt, system_context=system, preferred_model="groq")
    print(f"🧠 Trading-Entscheidung generiert von {model_used}", flush=True)
    
    match = re.search(r'\{.*\}', answer, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception as e:
            print(f"JSON Parsing Fehler: {e}")
    return {"decision": "HOLD", "reasoning": "Fehler im JSON-Parsing", "stop_loss": 0, "take_profit": 0, "indicators": "", "expected_move": "", "thought_process": "Der Bot hatte einen technischen Fehler beim Denken."}

def main_loop():
    print("🚀 KI-Profi-Agent gestartet (Groq). Bereit für 24/7 Trading.")
    from agents.gemini_agent import GeminiCoreAgent
    agent = GeminiCoreAgent()
    last_chat_id = 0

    while True:
        try:
            # 1. Marktdaten holen
            market_data = get_live_kraken_markets()
            if market_data:
                # 2. Trading-Entscheidung (nur alle 60 Sekunden)
                if int(time.time()) % 60 == 0:
                    decision = get_trading_decision(market_data)
                    
                    # 3. Zuerst die GEDANKEN als System-Nachricht speichern
                    thought = decision.get('thought_process', 'Keine Gedanken aufgezeichnet.')
                    send_chat_message("system", thought)
                    
                    print(f"🤖 Entscheidung: {decision['decision']}")
                    
                    if decision['decision'] in ['BUY', 'SELL']:
                        save_trade(
                            asset=market_data['symbol'],
                            direction=decision['decision'],
                            entry_price=market_data['last'],
                            stop_loss=decision.get('stop_loss', 0.0),
                            take_profit=decision.get('take_profit', 0.0),
                            reasoning=decision.get('reasoning', 'Keine Begründung'),
                            indicators=decision.get('indicators', ''),
                            expected_move=decision.get('expected_move', ''),
                            status='PAPER'
                        )
                    else:
                        print("⏸️ Entscheidung: HOLD")
            
            # 4. Chat verarbeiten (alle 5 Sekunden)
            if int(time.time()) % 5 == 0:
                new_id = agent.process_live_chat(last_chat_id)
                if new_id is not None:
                    last_chat_id = new_id

            time.sleep(5)
        except Exception as e:
            print(f"❌ Fehler im Hauptloop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main_loop()

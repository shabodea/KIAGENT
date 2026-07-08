import os
import json
import re
import time
import ccxt
import yfinance as yf
from agents.model_router import ModelRouter
from database.supabase import send_chat_message, save_trade
from config.settings import SUPABASE_URL, HEADERS

# --- DEINE KOMPLETTE ASSET-LISTE ---
MONITORED_ASSETS = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRON-USD", 
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD", 
    "CHAINLINK-USD", "SUI-USD", "NILLION-USD", "TAO-USD", "MIDNIGHT-USD", 
    "SPCE", "GOOGL", "NVDA", "MRVL", "ORCL"
]

def get_market_data(symbol):
    try:
        if symbol in ["SPCE", "GOOGL", "NVDA", "MRVL", "ORCL"]:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="2d", interval="1h")
            if data.empty: return None
            last_price = data['Close'].iloc[-1]
            closes = data['Close'].tail(20).tolist()
            return {"symbol": symbol, "last": last_price, "ohlcv": [[0,0,0,0,0,c] for c in closes]}
        else:
            exchange = ccxt.kraken()
            ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
            ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='1h', limit=20)
            return {
                "symbol": symbol,
                "last": ticker['last'],
                "ohlcv": ohlcv
            }
    except Exception as e:
        print(f"❌ Fehler bei {symbol}: {e}")
        return None

def get_trading_decision(market_data):
    router = ModelRouter()
    prompt = f"""
    Analysiere {market_data['symbol']} (Kurs: {market_data['last']}, letzte 5 Kerzen: {market_data['ohlcv'][-5:]}).
    Schreibe deine Gedankenschritte auf. 
    Entscheide BUY/SELL/HOLD. 
    Setze Stop-Loss & Take-Profit.
    JSON-Format: {{"thought_process": "...", "decision": "...", "reasoning": "...", "stop_loss": 0, "take_profit": 0, "indicators": "...", "expected_move": "..."}}
    """
    system = "Antworte NUR mit JSON."
    answer, model_used = router.route(prompt, system_context=system, preferred_model="groq")
    print(f"🧠 Entscheidung für {market_data['symbol']} von {model_used}", flush=True)
    match = re.search(r'\{.*\}', answer, re.DOTALL)
    if match:
        try: return json.loads(match.group(0))
        except: pass
    return {"decision": "HOLD", "reasoning": "Fehler", "thought_process": "Technischer Fehler"}

def main_loop():
    print("🚀 KI-Profi-Agent gestartet (22 Assets).", flush=True)
    from agents.gemini_agent import GeminiCoreAgent
    agent = GeminiCoreAgent()
    last_chat_id = 0
    current_asset_index = 0

    while True:
        try:
            # 1. Immer nur EIN Asset pro Sekunde abarbeiten (damit wir nie über 50/min kommen)
            symbol = MONITORED_ASSETS[current_asset_index]
            market_data = get_market_data(symbol)
            
            if market_data:
                decision = get_trading_decision(market_data)
                send_chat_message("system", decision.get('thought_process', 'Keine Gedanken'))
                
                if decision['decision'] in ['BUY', 'SELL']:
                    save_trade(
                        asset=market_data['symbol'],
                        direction=decision['decision'],
                        entry_price=market_data['last'],
                        stop_loss=decision.get('stop_loss', 0.0),
                        take_profit=decision.get('take_profit', 0.0),
                        reasoning=decision.get('reasoning', ''),
                        indicators=decision.get('indicators', ''),
                        expected_move=decision.get('expected_move', ''),
                        status='PAPER'
                    )
                    print(f"✅ Trade eröffnet: {symbol} {decision['decision']}", flush=True)
                else:
                    print(f"⏸️ HOLD für {symbol}", flush=True)
            
            # Nächstes Asset in der Liste (wenn Ende erreicht, geht's wieder von vorne los)
            current_asset_index = (current_asset_index + 1) % len(MONITORED_ASSETS)

            # 2. Chat nur alle 5 Sekunden checken
            if int(time.time()) % 5 == 0:
                new_id = agent.process_live_chat(last_chat_id)
                if new_id is not None: last_chat_id = new_id

            time.sleep(1)  # 1 Sekunde Pause pro Asset -> 22 Assets = 22 Sekunden Runde
        except Exception as e:
            print(f"❌ Fehler: {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main_loop()

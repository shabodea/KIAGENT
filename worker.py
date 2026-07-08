import os
import json
import re
import time
import ccxt
import numpy as np
import requests
from agents.model_router import ModelRouter
from database.supabase import send_chat_message, save_trade, close_trade
from config.settings import SUPABASE_URL, HEADERS

# --- NUR KRAKEN-ASSETS (Aktien komplett entfernt) ---
MONITORED_ASSETS = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRX-USD", 
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD", 
    "LINK-USD", "SUI-USD", "NIL-USD", "TAO-USD", "MIDNIGHT-USD"
]

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0: return 100
    rs = up / down
    return 100 - (100 / (1 + rs))

# --- NUR KRYPTO-DATENABFRAGE ÜBER CCXT (KRAKEN) ---
def get_asset_data(symbol):
    try:
        exchange = ccxt.kraken()
        ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
        ohlcv_5m = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='5m', limit=50)
        ohlcv_15m = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='15m', limit=50)
        ohlcv_1h = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='1h', limit=50)
        if not ohlcv_5m or not ohlcv_15m or not ohlcv_1h:
            return None
        return {
            "symbol": symbol,
            "last": ticker['last'],
            "closes_5m": [c[4] for c in ohlcv_5m],
            "closes_15m": [c[4] for c in ohlcv_15m],
            "closes_1h": [c[4] for c in ohlcv_1h]
        }
    except Exception as e:
        print(f"⚠️ Fehler bei {symbol}: {e}")
        return None

# --- KI-ENTSCHEIDUNG ---
def get_entry_decision(market_data):
    router = ModelRouter()
    rsi_5m = calculate_rsi(market_data['closes_5m'])
    rsi_15m = calculate_rsi(market_data['closes_15m'])
    rsi_1h = calculate_rsi(market_data['closes_1h'])
    
    # Aggressive Vorprüfung
    if rsi_5m < 35 or rsi_5m > 65:
        prompt = f"""
        Du bist ein Scalper. Marktdaten für {market_data['symbol']}:
        - Kurs: {market_data['last']}
        - 5m RSI: {rsi_5m:.1f} (Bewegung!)
        - 15m RSI: {rsi_15m:.1f}
        - 1h RSI: {rsi_1h:.1f}
        
        Entscheide: 
        - Wenn 5m < 35 und 15m < 40 und 1h neutral (40-60) -> **BUY**
        - Wenn 5m > 65 und 15m > 60 und 1h neutral (40-60) -> **SELL**
        - Sonst **HOLD**.
        
        JSON: {{"decision": "BUY"/"SELL"/"HOLD", "reasoning": "Begründung", "stop_loss": 0.0, "take_profit": 0.0}}
        """
        answer, _ = router.route(prompt, system_context="NUR JSON.", preferred_model="groq")
        match = re.search(r'\{.*\}', answer, re.DOTALL)
        if match:
            try: return json.loads(match.group(0))
            except: pass
    
    hold_reason = ""
    if rsi_5m < 35:
        hold_reason = f"5m RSI ({rsi_5m:.1f}) unterverkauft, aber 1h RSI ({rsi_1h:.1f}) nicht neutral. Warte auf Bestätigung."
    elif rsi_5m > 65:
        hold_reason = f"5m RSI ({rsi_5m:.1f}) überkauft, aber 1h RSI ({rsi_1h:.1f}) nicht neutral. Warte auf Bestätigung."
    else:
        hold_reason = f"5m RSI ({rsi_5m:.1f}) neutral. Suche nach Ausbruch."
    
    send_chat_message("system", f"⏸️ {market_data['symbol']} - Kein Trade: {hold_reason}")
    return {"decision": "HOLD", "reasoning": hold_reason, "stop_loss": 0.0, "take_profit": 0.0}

# --- LERNANALYSE ---
def analyze_learn(asset, entry_price, exit_price, pnl, reasoning):
    profit_text = "GEWINN" if pnl > 0 else "VERLUST"
    prompt = f"Trade auf {asset} abgeschlossen mit {profit_text} von ${pnl:.2f}. Einstieg:{entry_price}, Ausstieg:{exit_price}. Lehre mich eine Lektion."
    router = ModelRouter()
    answer, _ = router.route(prompt, system_context="Du bist ein Trading-Coach.", preferred_model="groq")
    send_chat_message("system", f"📘 Lektion aus dem {profit_text}: {answer}")

def main_loop():
    print("🧠 KI-Scalper gestartet (19 Kraken Assets). 24/7 aktiv.", flush=True)
    from agents.gemini_agent import GeminiCoreAgent
    agent = GeminiCoreAgent()
    last_chat_id = 0

    while True:
        try:
            for symbol in MONITORED_ASSETS:
                data = get_asset_data(symbol)
                if not data:
                    continue
                
                active_trades = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id,Eintrittspreis&Vermögenswert=eq.{symbol}&Status=eq.ACTIVE",
                    headers=HEADERS
                ).json()
                
                has_position = len(active_trades) > 0
                entry_price = float(active_trades[0]['Eintrittspreis']) if has_position else 0.0
                
                rsi_5m = calculate_rsi(data['closes_5m'])
                rsi_15m = calculate_rsi(data['closes_15m'])
                
                if has_position and (rsi_5m > 70 or rsi_15m > 70):
                    pnl = data['last'] - entry_price
                    close_trade(symbol, data['last'], pnl)
                    send_chat_message("system", f"⚡ {symbol}: Exit! RSI {rsi_5m:.1f}. PnL: ${pnl:.2f}")
                    analyze_learn(symbol, entry_price, data['last'], pnl, "RSI Overbought")
                    continue
                
                elif not has_position:
                    decision = get_entry_decision(data)
                    if decision['decision'] in ['BUY', 'SELL']:
                        save_trade(
                            asset=symbol,
                            direction=decision['decision'],
                            entry_price=data['last'],
                            stop_loss=decision.get('stop_loss', 0.0),
                            take_profit=decision.get('take_profit', 0.0),
                            reasoning=decision.get('reasoning', 'Scalping'),
                            indicators=f"5m RSI:{rsi_5m:.1f}, 15m RSI:{rsi_15m:.1f}",
                            expected_move='Scalping',
                            status='ACTIVE'
                        )
                        send_chat_message("system", f"🟢 Einstieg {symbol}: {decision['decision']} bei {data['last']}")
            
            if int(time.time()) % 5 == 0:
                new_id = agent.process_live_chat(last_chat_id)
                if new_id is not None: last_chat_id = new_id

            time.sleep(1)
        except Exception as e:
            print(f"❌ Fehler im Hauptloop: {e}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    main_loop()

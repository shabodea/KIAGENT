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

# --- DEINE KRAKEN-ASSETS (19 Stück) ---
MONITORED_ASSETS = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRX-USD", 
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD", 
    "LINK-USD", "SUI-USD", "NIL-USD", "TAO-USD", "MIDNIGHT-USD"
]

# --- RSI BERECHNEN ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0: return 100
    rs = up / down
    return 100 - (100 / (1 + rs))

# --- GUTHABEN BERECHNEN (alle geschlossenen Trades) ---
def get_current_balance():
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=net_pnl&Status=eq.CLOSED",
            headers=HEADERS
        ).json()
        if not resp:
            return 200.0
        total_pnl = sum(float(t.get('net_pnl', 0.0)) for t in resp)
        return 200.0 + total_pnl
    except Exception as e:
        print(f"⚠️ Fehler beim Abrufen des Guthabens: {e}")
        return 200.0

# --- DATENABFRAGE (5m, 15m, 1h, 4h, 1d) ---
def get_asset_data(symbol):
    try:
        exchange = ccxt.kraken()
        ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
        data = {}
        for tf in ['5m', '15m', '1h', '4h', '1d']:
            ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe=tf, limit=50)
            data[tf] = [c[4] for c in ohlcv] if ohlcv else []
        return {
            "symbol": symbol,
            "last": ticker['last'],
            "closes_5m": data['5m'],
            "closes_15m": data['15m'],
            "closes_1h": data['1h'],
            "closes_4h": data['4h'],
            "closes_1d": data['1d']
        }
    except Exception as e:
        print(f"⚠️ Fehler bei {symbol}: {e}")
        return None

# --- HISTORIE DES BOTS (letzte 5 Trades) ---
def get_performance_summary(symbol):
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=decision,net_pnl,Begründung&Vermögenswert=eq.{symbol}&Status=eq.CLOSED&order=id.desc&limit=5",
            headers=HEADERS
        ).json()
        if not resp:
            return "Keine bisherigen Trades für dieses Asset."
        summary = []
        for t in resp:
            direction = t.get('decision', 'HOLD')
            pnl = t.get('net_pnl', 0.0)
            reason = t.get('Begründung', 'Keine Angabe')[:30]
            win_loss = "GEWINN" if pnl > 0 else "VERLUST"
            summary.append(f"{direction} ({win_loss}): {pnl:.2f}$ - Grund: {reason}...")
        return "\n".join(summary)
    except:
        return "Konnte Historie nicht laden."

# --- FLEXIBLE KI-ENTSCHEIDUNG (MIT GUTHABEN & RISIKO) ---
def get_entry_decision(market_data, balance):
    router = ModelRouter()
    
    rsi_5m = calculate_rsi(market_data['closes_5m'])
    rsi_15m = calculate_rsi(market_data['closes_15m'])
    rsi_1h = calculate_rsi(market_data['closes_1h'])
    rsi_4h = calculate_rsi(market_data['closes_4h'])
    rsi_1d = calculate_rsi(market_data['closes_1d'])
    
    history = get_performance_summary(market_data['symbol'])
    
    prompt = f"""
    Du bist ein erfahrener KI-Trader mit 200 € Startkapital.
    Aktuelles Guthaben: {balance:.2f} €.
    Du riskierst bei jedem Trade 10 % deines Guthabens (Marge).
    
    Marktdaten für {market_data['symbol']} (Kurs: {market_data['last']}):
    - 5m RSI: {rsi_5m:.1f}
    - 15m RSI: {rsi_15m:.1f}
    - 1h RSI: {rsi_1h:.1f}
    - 4h RSI: {rsi_4h:.1f}
    - 1d RSI: {rsi_1d:.1f}
    
    --- DEINE LETZTEN 5 TRADES (LERNEN) ---
    {history}
    -----------------------------------------
    
    AUFGABE:
    Analysiere die RSIs. Entscheide, ob du jetzt kaufen, verkaufen oder warten solltest.
    Wenn du handelst, gib auch einen Stop-Loss und Take-Profit an.
    Denke daran: Du willst langfristig reich werden, also handle diszipliniert.
    
    Antworte NUR im JSON-Format:
    {{"decision": "BUY" oder "SELL" oder "HOLD", "reasoning": "Deine Überlegung auf Deutsch (max. 2 Sätze)", "stop_loss": 0.0, "take_profit": 0.0}}
    """
    
    answer, _ = router.route(prompt, system_context="Du antwortest NUR mit JSON.", preferred_model="groq")
    match = re.search(r'\{.*\}', answer, re.DOTALL)
    if match:
        try: return json.loads(match.group(0))
        except: pass
    return {"decision": "HOLD", "reasoning": "Groq nicht verfügbar, Sicherheits-HOLD.", "stop_loss": 0.0, "take_profit": 0.0}

# --- BELOHNUNG / BESTRAFUNG NACH DEM TRADE ---
def analyze_learn(asset, entry_price, exit_price, pnl, margin, reasoning):
    profit_text = "GEWINN" if pnl > 0 else "VERLUST"
    # Wir geben eine motivierende oder korrigierende Rückmeldung
    prompt = f"""
    Ich habe soeben einen Trade auf {asset} mit einem {profit_text} von ${pnl:.2f} abgeschlossen.
    Investierte Marge: ${margin:.2f}.
    Einstieg: {entry_price}, Ausstieg: {exit_price}.
    Meine Begründung war: {reasoning}.
    
    Gib mir eine kurze, professionelle Lektion. Wenn es ein Gewinn war, lobe mich und erkläre, warum es gut war. Wenn es ein Verlust war, tadle mich konstruktiv und zeige mir, wie ich es beim nächsten Mal besser machen kann.
    Antworte kurz und prägnant auf Deutsch.
    """
    router = ModelRouter()
    answer, _ = router.route(prompt, system_context="Du bist ein motivierender Trading-Coach.", preferred_model="groq")
    send_chat_message("system", f"📘 Lektion aus dem {profit_text}: {answer}")

# --- HAUPTLOOP ---
def main_loop():
    print("🧠 KI-Trader gestartet (Guthaben 200 €, 10 % Risiko). 24/7 aktiv.", flush=True)
    from agents.gemini_agent import GeminiCoreAgent
    agent = GeminiCoreAgent()
    last_chat_id = 0

    # Timer für API-Limits
    last_api_call = {asset: 0 for asset in MONITORED_ASSETS}

    while True:
        try:
            # 1. Aktuelles Guthaben berechnen
            balance = get_current_balance()
            margin_per_trade = balance * 0.10  # 10% des Guthabens als Marge

            for symbol in MONITORED_ASSETS:
                # Nur 1x pro Minute pro Asset Groq fragen
                if time.time() - last_api_call.get(symbol, 0) < 60:
                    continue
                
                data = get_asset_data(symbol)
                if not data:
                    continue
                
                # 2. Offene Position prüfen
                active_trades = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id,Eintrittspreis&Vermögenswert=eq.{symbol}&Status=eq.ACTIVE",
                    headers=HEADERS
                ).json()
                
                has_position = len(active_trades) > 0
                entry_price = float(active_trades[0]['Eintrittspreis']) if has_position else 0.0
                
                rsi_5m = calculate_rsi(data['closes_5m'])
                rsi_15m = calculate_rsi(data['closes_15m'])
                
                # 3. EXIT (Notfall-Exit bei überkauftem RSI > 70)
                if has_position and (rsi_5m > 70 or rsi_15m > 70):
                    # Berechne Gewinn/Verlust (Hebel 1x)
                    pnl = (data['last'] - entry_price) / entry_price * margin_per_trade
                    close_trade(symbol, data['last'], pnl)
                    send_chat_message("system", f"⚡ {symbol}: Blitz-Exit! RSI {rsi_5m:.1f}. PnL: ${pnl:.2f}")
                    analyze_learn(symbol, entry_price, data['last'], pnl, margin_per_trade, "Notfall-Exit")
                    continue
                
                # 4. ENTRY (Entscheidung durch Groq)
                elif not has_position:
                    decision = get_entry_decision(data, balance)
                    last_api_call[symbol] = time.time()
                    
                    if decision['decision'] in ['BUY', 'SELL']:
                        # Trade mit Marge und Hebel 1x speichern
                        save_trade(
                            asset=symbol,
                            direction=decision['decision'],
                            entry_price=data['last'],
                            stop_loss=decision.get('stop_loss', 0.0),
                            take_profit=decision.get('take_profit', 0.0),
                            reasoning=decision.get('reasoning', 'Flexible KI-Analyse'),
                            indicators=f"5m RSI:{rsi_5m:.1f}, 15m RSI:{rsi_15m:.1f}, 1h RSI:{calculate_rsi(data['closes_1h']):.1f}",
                            expected_move='Scalping',
                            margin_usd=margin_per_trade,
                            leverage=1,
                            status='ACTIVE'
                        )
                        send_chat_message("system", f"🟢 Einstieg {symbol}: {decision['decision']} bei {data['last']}. Marge: ${margin_per_trade:.2f}. Grund: {decision['reasoning']}")
                    else:
                        print(f"⏸️ {symbol} - HOLD (Groq: {decision['reasoning']})", flush=True)
            
            # 5. Chat bearbeiten
            if int(time.time()) % 5 == 0:
                new_id = agent.process_live_chat(last_chat_id)
                if new_id is not None:
                    last_chat_id = new_id

            time.sleep(1)
        except Exception as e:
            print(f"❌ Fehler im Hauptloop: {e}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    main_loop()

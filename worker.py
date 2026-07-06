import os
import time
import requests
from datetime import datetime

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

KRAKEN_TAKER_FEE = 0.0026
MAX_TOTAL_BUDGET_USD = 200.0  
POSITION_SIZE_USD = 50.0      
FIXED_LEVERAGE = 10           

def get_live_kraken_markets():
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        res = requests.get(url, timeout=10).json()
        all_pairs = res.get("result", {})
        return [pair for pair in all_pairs.keys() if pair.endswith("USDT")][:50]
    except:
        return ["XBTUSDT", "ETHUSDT", "SOLUSDT"]

def calculate_market_metrics(pair):
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        res = requests.get(url, timeout=10).json()
        if "result" not in res: return None
        data_points = list(res["result"].values())[0]
        closes = [float(x[4]) for x in data_points[-50:]]
        
        ema20 = sum(closes[-20:]) / 20
        highs = [float(x[2]) for x in data_points[-14:]]
        lows = [float(x[3]) for x in data_points[-14:]]
        expected_move_p = round(((max(highs) - min(lows)) / min(lows)) * 100, 2)

        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            gains.append(diff if diff > 0 else 0)
            losses.append(abs(diff) if diff < 0 else 0)
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14
        rsi = 100 - (100 / (1 + (avg_gain / avg_loss))) if avg_loss > 0 else 100

        return {"rsi": round(rsi, 2), "ema": round(ema20, 4), "live_price": closes[-1], "expected_move": expected_move_p}
    except:
        return None

def fetch_ai_market_research(pair, price, rsi):
    prompt = (
        f"Führe eine professionelle Krypto-Marktanalyse durch für {pair} beim aktuellen Kurs von {price}$. "
        f"Der mathematische RSI liegt bei {rsi}. Nutze deine Echtzeit-Websuche und suche im Internet nach Faktoren wie Open Interest Veränderungen, "
        f"Kerzenmustern, Orderbuch-Liquidität und Krypto-News. Entscheide, ob ein 10x LONG-Einstieg Sinn macht.\n\n"
        f"Antworte exakt in diesem Format:\n"
        f"ENTSCHEIDUNG: [GO oder HOLD]\n"
        f"BEGRÜNDUNG: [Deine fundamentale Analyse aus dem Web]\n"
        f"ERWARTETE_BEWEGUNG: [Schätzung in % z.B. 3.8%]\n"
        f"TARGETS: TP=[Wert] SL=[Wert]"
    )
    return ask_gemini_expert(prompt)

def check_and_close_trades():
    try:
        url = f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?Status=eq.ACTIVE"
        active_trades = requests.get(url, headers=HEADERS).json()
        if not isinstance(active_trades, list) or len(active_trades) == 0: return

        for trade in active_trades:
            pair = trade.get("Vermögenswert")
            trade_id = trade.get("Ausweis")
            if not pair: continue
            
            metrics = calculate_market_metrics(pair)
            if not metrics: continue
            current_price = metrics["live_price"]
            
            # Liest die spezifischen TP/SL Preise aus, die beim Einstieg definiert wurden
            tp = float(trade.get("Take_Profit_Preis") or (float(trade.get("Eintrittspreis")) * 1.03))
            sl = float(trade.get("Stop_Loss_Preis") or (float(trade.get("Eintrittspreis")) * 0.985))
            
            closed = False
            reason = ""
            if current_price <= sl:
                closed = True
                reason = "STOP-LOSS"
            elif current_price >= tp:
                closed = True
                reason = "TAKE-PROFIT"
                
            if closed:
                price_change_p = (current_price - float(trade.get("Eintrittspreis"))) / float(trade.get("Eintrittspreis"))
                realized_pnl = POSITION_SIZE_USD * price_change_p * FIXED_LEVERAGE
                fees = float(trade.get("Gebühren_USD", 0))
                final_pnl = round(realized_pnl - fees, 4)

                requests.patch(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?Ausweis=eq.{trade_id}", headers=HEADERS, json={
                    "Status": "CLOSED",
                    "Ausstiegspreis": current_price,
                    "net_pnl": final_pnl,
                    "Begründung": f"🔴 Geschlossen bei {current_price}$ via {reason}. Net-PnL: {final_pnl}$"
                })
    except Exception as e:
        print(f"Fehler Schließung: {e}")

def run_unlimited_expert_trading():
    try:
        url = f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?Status=eq.ACTIVE"
        active_res = requests.get(url, headers=HEADERS).json()
        if isinstance(active_res, list) and sum(float(t.get("Marge in USD", 0)) for t in active_res) >= MAX_TOTAL_BUDGET_USD: return

        all_pairs = get_live_kraken_markets()
        for pair in all_pairs:
            metrics = calculate_market_metrics(pair)
            if not metrics or metrics["rsi"] > 65: continue

            analysis = fetch_ai_market_research(pair, metrics["live_price"], metrics["rsi"])
            
            if "ENTSCHEIDUNG: GO" in analysis:
                try:
                    lines = analysis.split("\n")
                    rationale = [l for l in lines if "BEGRÜNDUNG:" in l][0].replace("BEGRÜNDUNG:", "").strip()
                    exp_move = [l for l in lines if "ERWARTETE_BEWEGUNG:" in l][0].replace("ERWARTETE_BEWEGUNG:", "").strip()
                    targets = [l for l in lines if "TARGETS:" in l][0].replace("TARGETS:", "").strip()
                    
                    entry = metrics["live_price"]
                    tp_price = entry * 1.03
                    sl_price = entry * 0.985
                    
                    if "TP=" in targets:
                        parts = targets.split()
                        tp_price = float(parts[0].split("=")[1])
                        sl_price = float(parts[1].split("=")[1])

                    requests.post(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS, json={
                        "Vermögenswert": pair,
                        "Richtung": "LONG",
                        "Hebelwirkung": FIXED_LEVERAGE,
                        "Eintrittspreis": entry,
                        "Marge in USD": POSITION_SIZE_USD,
                        "Gebühren_USD": POSITION_SIZE_USD * KRAKEN_TAKER_FEE * 2,
                        "Status": "ACTIVE",
                        "Begründung": rationale,
                        "Erwartete_Bewegung": exp_move,
                        "Indikatoren_Setup": f"RSI: {metrics['rsi']} | EMA20: {metrics['ema']}",
                        "Take_Profit_Preis": tp_price,
                        "Stop_Loss_Preis": sl_price
                    })
                    break
                except:
                    pass
            time.sleep(1)
    except Exception as e:
        print(f"Fehler Loop: {e}")

def ask_gemini_expert(prompt_text):
    if not GEMINI_API_KEY: return "HOLD"
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_API_KEY.strip()}"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt_text}]}]}, timeout=15)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except: return "HOLD"

def process_chat():
    try:
        messages = requests.get(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS).json()
        if messages and len(messages) > 0:
            latest_msg = sorted(messages, key=lambda x: x.get('Ausweis', 0))[-1]
            if latest_msg["role"] == "user":
                user_input = latest_msg["content"]
                system_context = "Du bist der unfehlbare Krypto-Trading-Experte. Antworte kurz auf Deutsch. Beende mit LEKTION: ..."
                bot_response = ask_gemini_expert(f"{system_context}\n\nMaster schreibt: {user_input}")
                requests.post(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS, json={"role": "assistant", "content": bot_response})
    except Exception as e: print(f"Fehler im Chat: {e}")

# --- HAUPTLOOP ---
while True:
    process_chat()
    check_and_close_trades() 
    run_unlimited_expert_trading()
    time.sleep(15)

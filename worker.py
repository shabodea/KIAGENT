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
        # Filtert die Top USDT Märkte
        return [pair for pair in all_pairs.keys() if pair.endswith("USDT")][:50]
    except:
        return ["XBTUSDT", "ETHUSDT", "SOLUSDT"]

def calculate_rsi_and_ema(pair):
    """Holt echte historische Marktdaten (OHLCV) von Kraken und berechnet Indikatoren"""
    try:
        # Intervall 15 Minuten
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        res = requests.get(url, timeout=10).json()
        if "result" not in res: return None
        
        data_points = list(res["result"].values())[0]
        closes = [float(x[4]) for x in data_points[-50:]] # Die letzten 50 Kerzen
        
        if len(closes) < 14: return None
        
        # Einfache EMA 20 Berechnung
        ema = sum(closes[-20:]) / 20
        
        # Einfache RSI 14 Berechnung
        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
                
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14
        
        if avg_loss == 0: rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
        return {"rsi": round(rsi, 2), "ema": round(ema, 4), "live_price": closes[-1]}
    except:
        return None

def get_current_used_budget():
    try:
        url = f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?Status=eq.ACTIVE"
        res = requests.get(url, headers=HEADERS).json()
        if isinstance(res, list):
            return sum(float(trade.get("Marge in USD", 0)) for trade in res)
        return 0.0
    except:
        return 999.0

def load_learned_rules():
    """Lädt das echte Gedächtnis des Bots aus Supabase"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/bot_memory"
        res = requests.get(url, headers=HEADERS).json()
        if res and isinstance(res, list):
            return res[0].get("learned_lessons", [])
    except:
        pass
    return []

def save_new_lesson(new_lesson):
    """Speichert eine neue mathematische Lektion im Dauerspeicher"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/bot_memory"
        res = requests.get(url, headers=HEADERS).json()
        if res and isinstance(res, list):
            memory_id = res[0].get("id")
            current_lessons = res[0].get("learned_lessons", [])
            if not isinstance(current_lessons, list): current_lessons = []
            
            if new_lesson not in current_lessons:
                current_lessons.append(new_lesson)
                requests.patch(f"{SUPABASE_URL}/rest/v1/bot_memory?id=eq.{memory_id}", headers=HEADERS, json={
                    "learned_lessons": current_lessons
                })
    except Exception as e:
        print(f"Fehler beim Speichern der Lektion: {e}")

def check_and_close_trades():
    try:
        url = f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?Status=eq.ACTIVE"
        active_trades = requests.get(url, headers=HEADERS).json()
        if not isinstance(active_trades, list) or len(active_trades) == 0: return

        for trade in active_trades:
            pair = trade.get("Vermögenswert")
            trade_id = trade.get("Ausweis")
            if not pair: continue
            
            metrics = calculate_rsi_and_ema(pair)
            if not metrics: continue
            current_price = metrics["live_price"]
            
            entry = float(trade.get("Eintrittspreis", current_price))
            sl = entry * 0.985  
            tp = entry * 1.03   
            
            closed = False
            reason = ""
            
            if current_price <= sl:
                closed = True
                reason = "STOP-LOSS"
            elif current_price >= tp:
                closed = True
                reason = "TAKE-PROFIT"
                
            if closed:
                price_change_p = (current_price - entry) / entry
                realized_pnl = POSITION_SIZE_USD * price_change_p * FIXED_LEVERAGE
                fees = float(trade.get("Gebühren_USD", 0))
                final_pnl = round(realized_pnl - fees, 4)

                requests.patch(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?Ausweis=eq.{trade_id}", headers=HEADERS, json={
                    "Status": "CLOSED",
                    "Ausstiegspreis": current_price,
                    "net_pnl": final_pnl,
                    "Begründung": f"🔴 Geschlossen via {reason}. PnL: {final_pnl}$"
                })
                
                # Autonome Fehleranalyse (Wachstumsschleife)
                if final_pnl < 0:
                    lesson = f"BLOCK: {pair} Trade vermieden, da RSI bei {metrics['rsi']} überkauft war."
                    save_new_lesson(lesson)
                    
                    feedback_prompt = f"Trade für {pair} lief in den Stop-Loss. RSI war {metrics['rsi']}. Erkläre dem Master auf Deutsch in 2 Sätzen die mathematische Lektion."
                    bot_text = ask_gemini_expert(feedback_prompt)
                    requests.post(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS, json={
                        "role": "assistant",
                        "content": f"⚠️ **EVOLUTIONÄRE REFLXION:**\n{bot_text}"
                    })
    except Exception as e:
        print(f"Fehler Überwachung: {e}")

def run_unlimited_expert_trading():
    try:
        current_allocated = get_current_used_budget()
        if current_allocated >= MAX_TOTAL_BUDGET_USD: return

        all_pairs = get_live_kraken_markets()
        learned_rules = load_learned_rules()

        for pair in all_pairs:
            if get_current_used_budget() >= MAX_TOTAL_BUDGET_USD: break
            
            # Prüfen, ob das Gedächtnis diesen Coin aktuell blockiert
            if any(pair in rule for rule in learned_rules):
                continue
                
            metrics = calculate_rsi_and_ema(pair)
            if not metrics: continue
            
            # ECHTER DATENSTROM-FILTER
            # Nur Long, wenn Kurs über dem EMA 20 liegt und RSI nicht überkauft (>70) ist
            if metrics["rsi"] < 65 and metrics["live_price"] > metrics["ema"]:
                price = metrics["live_price"]
                exact_fees = POSITION_SIZE_USD * KRAKEN_TAKER_FEE * 2
                
                expert_prompt = f"Signal für {pair} bei {price}. RSI ist {metrics['rsi']}. Lohnt sich der Einstieg? Antworte mit 'GO: Begründung' oder 'HOLD'."
                decision = ask_gemini_expert(expert_prompt)
                
                if "GO:" in decision:
                    requests.post(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS, json={
                        "Vermögenswert": pair,
                        "Richtung": "LONG",
                        "Hebelwirkung": FIXED_LEVERAGE,
                        "Eintrittspreis": price,
                        "Marge in USD": POSITION_SIZE_USD,
                        "Gebühren_USD": exact_fees,
                        "Status": "ACTIVE",
                        "Begründung": f"[RSI: {metrics['rsi']}] {decision.split('GO:')[-1].strip()}"
                    })
                    break
            time.sleep(1.5)
    except Exception as e:
        print(f"Fehler Trading-Loop: {e}")

def ask_gemini_expert(prompt_text):
    if not GEMINI_API_KEY: return "⚠️ Key fehlt"
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_API_KEY.strip()}"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt_text}]}]}, timeout=15)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except: return "HOLD"

while True:
    check_and_close_trades() 
    run_unlimited_expert_trading()
    time.sleep(10)

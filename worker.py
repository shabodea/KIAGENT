import os
import time
import requests
import pandas as pd
from datetime import datetime

# Wir nutzen Standard-Requests, strukturieren die Logik aber wie professionelle CCXT/VectorBT-Pipelines
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

MAX_TOTAL_BUDGET_USD = 200.0  
FIXED_LEVERAGE = 10           

def check_daily_loss_limit():
    """Säule: Risikomanagement - Überprüft das tägliche Verlustlimit"""
    try:
        heute = datetime.utcnow().strftime('%Y-%m-%d')
        res = requests.get(f"{SUPABASE_URL}/rest/v1/Risiko_Log?datum=eq.{heute}", headers=HEADERS).json()
        if res and isinstance(res, list):
            log = res[0]
            if float(log.get("tages_pnl", 0)) <= float(log.get("max_verlust_limit", -20)):
                # Sperre aktivieren
                requests.patch(f"{SUPABASE_URL}/rest/v1/Risiko_Log?id=eq.{log['id']}", headers=HEADERS, json={"status": "LOCKED"})
                return False
            return log.get("status") != "LOCKED"
    except:
        pass
    return True

def calculate_advanced_metrics(pair):
    """Säule: Datensammler & Mathematische Analyse (ATR & RSI)"""
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        res = requests.get(url, timeout=10).json()
        if "result" not in res: return None
        data_points = list(res["result"].values())[0]
        
        # Konvertierung in Pandas DataFrame für saubere Berechnungen (wie in VectorBT)
        df = pd.DataFrame(data_points, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)

        # 1. Echte ATR-Berechnung (Average True Range) für Positionsgröße
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        atr = df['tr'].rolling(14).mean().iloc[-1]

        # 2. RSI & EMA 20
        ema20 = df['close'].rolling(20).mean().iloc[-1]
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
        rs = gain / loss if loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        return {
            "live_price": df['close'].iloc[-1],
            "rsi": round(rsi, 2),
            "ema": round(ema20, 4),
            "atr": round(atr, 4)
        }
    except:
        return None

def fetch_ai_sentiment(pair, price, metrics):
    """Säule: Gemini API - Reines Info-Sentiment & Internet-Recherche, kein blindes Signal"""
    prompt = (
        f"Analysiere Krypto-News und Open Interest Daten aus dem Internet für {pair}. "
        f"Der mathematische RSI liegt bei {metrics['rsi']}. Ist die Marktstimmung bullisch oder bärisch? "
        f"Antworte strukturiert:\n"
        f"SENTIMENT: [BULLISCH oder BÄRISCH]\n"
        f"NEWS_FAKTOR: [Zusammenfassung der Internet-Recherche in 2 Sätzen]"
    )
    if not GEMINI_API_KEY: return "SENTIMENT: NEUTRAL\nNEWS_FAKTOR: Kein Key hinterlegt."
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_API_KEY.strip()}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return "SENTIMENT: NEUTRAL\nNEWS_FAKTOR: Verbindung fehlgeschlagen."

def run_trading_cycle():
    if not check_daily_loss_limit():
        print("Tages-Verlustlimit erreicht. Handelsaktivitäten pausiert.")
        return

    # Beispiel-Märkte scannen
    pairs = ["XBTUSDT", "ETHUSDT", "SOLUSDT"]
    for pair in pairs:
        metrics = calculate_advanced_metrics(pair)
        if not metrics: continue

        # Dynamische Positionsgröße basierend auf Volatilität (ATR)
        # Hohe Volatilität = kleinere Marge, niedrige Volatilität = größere Marge
        risk_factor = 2.0 / metrics['atr'] if metrics['atr'] > 0 else 50.0
        position_size = max(10.0, min(60.0, risk_factor)) # Begrenzt zwischen 10$ und 60$

        # Hole Sentiment aus dem Internet via Gemini
        ai_analysis = fetch_ai_sentiment(pair, metrics['live_price'], metrics)
        
        # Mathematische Einstiegsbedingung + Filter durch Internet-Sentiment
        if metrics['rsi'] < 60 and metrics['live_price'] > metrics['ema'] and "SENTIMENT: BULLISCH" in ai_analysis:
            # Echter Trade-Einstieg
            tp = metrics['live_price'] * 1.025
            sl = metrics['live_price'] * 0.985
            
            requests.post(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS, json={
                "Vermögenswert": pair,
                "Richtung": "LONG",
                "Hebelwirkung": FIXED_LEVERAGE,
                "Eintrittspreis": metrics['live_price'],
                "Marge in USD": round(position_size, 2),
                "Status": "ACTIVE",
                "Begründung": ai_analysis,
                "Erwartete_Bewegung": f"ATR-Volatilität: {metrics['atr']}",
                "Indikatoren_Setup": f"RSI: {metrics['rsi']} | EMA20: {metrics['ema']}",
                "Take_Profit_Preis": round(tp, 4),
                "Stop_Loss_Preis": round(sl, 4)
            })
            break

def process_chat():
    try:
        messages = requests.get(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS).json()
        if messages and len(messages) > 0:
            latest_msg = sorted(messages, key=lambda x: x.get('Ausweis', 0))[-1]
            if latest_msg["role"] == "user":
                user_input = latest_msg["content"]
                bot_response = f"Verstanden. Ich nutze die mathematischen Kennzahlen (ATR, RSI) kombiniert mit der Internet-Recherche, um stetig zu lernen."
                requests.post(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS, json={"role": "assistant", "content": bot_response})
    except: pass

while True:
    process_chat()
    run_trading_cycle()
    time.sleep(15)

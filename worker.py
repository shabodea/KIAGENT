import sys
import os
import time
import requests
import pandas as pd
from datetime import datetime

# --- CRITICAL: PFAD-WEGWEISER ---
ZENTRALER_PFAD = os.path.dirname(os.path.abspath(__file__))
if ZENTRALER_PFAD not in sys.path:
    sys.path.insert(0, ZENTRALER_PFAD)

# --- MODULARE IMPORTS ---
from config.settings import GEMINI_API_KEY, HEADERS, SUPABASE_URL
from database.supabase import get_all_data_live, send_chat_message

def get_live_kraken_markets():
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        res = requests.get(url, timeout=10).json()
        if "result" not in res: return ["XBTUSDT", "ETHUSDT"]
        pairs = [pair for pair in res.get("result", {}).keys() if pair.endswith("USDT")]
        return pairs[:15]  # Auf 15 Märkte begrenzen für schnellere Performance
    except:
        return ["XBTUSDT", "ETHUSDT"]

def calculate_advanced_metrics(pair):
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        res = requests.get(url, timeout=10).json()
        if "result" not in res or not res["result"]: return None
            
        data_points = list(res["result"].values())[0]
        df = pd.DataFrame(data_points, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)

        df['tr'] = df['high'] - df['low']
        atr = df['tr'].rolling(14).mean().iloc[-1]
        ema20 = df['close'].rolling(20).mean().iloc[-1]
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
        rsi = 100 - (100 / (1 + (gain / loss))) if loss > 0 else 100

        return {"live_price": df['close'].iloc[-1], "rsi": round(rsi, 2), "ema": round(ema20, 4), "atr": round(atr, 4)}
    except:
        return None

def ask_gemini_expert(prompt_text):
    if not GEMINI_API_KEY: return "HOLD"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY.strip()}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt_text}]}]}, timeout=15).json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except:
        return "HOLD"

# --- BRANDNEU: HIER WIRD DIREKT AUF KRAKEN GEHANDELT (SIMULATION) ---
def run_trading_cycle():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚙️ Starte mathematischen Marktscan...")
    märkte = get_live_kraken_markets()
    
    for markt in märkte:
        metriken = calculate_advanced_metrics(markt)
        if not metriken: continue
        
        rsi = metriken["rsi"]
        preis = metriken["live_price"]
        ema = metriken["ema"]
        
        print(f" -> Markt: {markt} | Preis: {preis}$ | RSI: {rsi} | EMA20: {ema}")
        
        # SCHARFE MATHEMATISCHE BEDINGUNG (EMA-Trend & RSI unterverkauft)
        if preis > ema and rsi < 45:
            print(f"🎯 SIGNAL GEFUNDEN FÜR {markt}! Frage Gemini-Sentiment ab...")
            sentiment = ask_gemini_expert(f"Analysiere das aktuelle Internet-Sentiment für {markt}. Antworte NUR mit 'BUY' oder 'HOLD'.")
            
            if "BUY" in sentiment.upper():
                print(f"🚀 Gemini gibt GO! Trage simulierten Trade für {markt} in Supabase ein...")
                # Erstelle den Trade live in deiner Tabelle
                trade_data = {
                    "Vermögenswert": markt,
                    "Richtung": "LONG",
                    "Eintrittspreis": preis,
                    "Marge in USD": 20.0,
                    "Hebelwirkung": 10,
                    "Take_Profit_Preis": round(preis * 1.03, 2),
                    "Stop_Loss_Preis": round(preis * 0.97, 2),
                    "Status": "ACTIVE",
                    "Begründung": f"Automatischer Ausbruch über EMA20 bei einem RSI von {rsi}.",
                    "Indikatoren_Setup": f"RSI: {rsi}, EMA: {ema}",
                    "Erwartete_Bewegung": "+3.00%"
                }
                requests.post(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS, json=trade_data)
                break # Nur einen Trade pro Zyklus erlauben

def process_chat():
    try:
        trades, chat, risiko, knowledge = get_all_data_live()
        if chat and len(chat) > 0:
            latest_msg = sorted(chat, key=lambda x: x.get('id', 0))[-1]
            
            # WICHTIG: Nur antworten, wenn die letzte Nachricht vom User stammt!
            if latest_msg["role"] == "user":
                user_input = latest_msg["content"]
                print(f"📩 Neuer Master-Befehl empfangen: {user_input}")
                
                kontext = f"Regeln: {str(knowledge)} | Offene Trades: {str(trades)}"
                prompt = f"System-Kontext: {kontext}\n\nMaster fragt: {user_input}\nAntworte als professioneller Broker kurz auf Deutsch."
                
                bot_response = ask_gemini_expert(prompt)
                send_chat_message("assistant", bot_response)
                print(f"📤 Antwort erfolgreich gesendet: {bot_response}")
    except Exception as e:
        print(f"Chat-Loop Fehler: {e}")

if __name__ == "__main__":
    print("🦅 KIAgent Triebwerk erfolgreich scharfgeschaltet...")
    while True:
        process_chat()
        run_trading_cycle() # <--- HIER ZÜNDEN WIR JETZT DIE LIVE-ANALYSE
        time.sleep(20)

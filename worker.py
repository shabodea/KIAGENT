import os
import time
import requests
import math

# Schlüssel und Cloud-Datenbank-Konfiguration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

KRAKEN_TAKER_FEE = 0.0026  # 0.26%

# Parameter des Masters
MAX_TOTAL_BUDGET_USD = 200.0  
POSITION_SIZE_USD = 50.0      
FIXED_LEVERAGE = 10           

def get_live_kraken_markets():
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        res = requests.get(url, timeout=10).json()
        all_pairs = res.get("result", {})
        return [pair for pair in all_pairs.keys() if pair.endswith("USDT")]
    except:
        return ["XBTUSDT", "ETHUSDT", "SOLUSDT"]

def get_current_used_budget():
    """Zählt das Budget NUR von den echten, aktuell laufenden Positionen"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/trade_history?status=eq.ACTIVE"
        res = requests.get(url, headers=HEADERS).json()
        if isinstance(res, list):
            return sum(float(trade.get("margin_usd", 0)) for trade in res if "leverage" in trade)
        return 0.0
    except:
        return 999.0

def get_orderbook_and_atr(pair):
    try:
        url_depth = f"https://api.kraken.com/0/public/Depth?pair={pair}&count=5"
        url_ticker = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
        res_depth = requests.get(url_depth, timeout=10).json()
        res_ticker = requests.get(url_ticker, timeout=10).json()
        pair_depth = list(res_depth.get("result", {}).values())[0]
        pair_ticker = list(res_ticker.get("result", {}).values())[0]
        
        best_bid = float(pair_depth.get("bids", [[0]])[0][0])
        best_ask = float(pair_depth.get("asks", [[0]])[0][0])
        live_price = (best_bid + best_ask) / 2
        
        total_bid_vol = sum(float(b[1]) for b in pair_depth.get("bids", []))
        total_ask_vol = sum(float(a[1]) for a in pair_depth.get("asks", []))
        ratio = total_bid_vol / total_ask_vol if total_ask_vol > 0 else 1
        
        high_24h = float(pair_ticker.get("h", [live_price])[0])
        low_24h = float(pair_ticker.get("l", [live_price])[0])
        
        return {"live_price": live_price, "orderbook_ratio": round(ratio, 2), "volatility": (high_24h - low_24h)}
    except:
        return None

def check_and_close_trades():
    """
    NEU: Die Schließungs-Maschine.
    Prüft alle offenen Trades gegen den aktuellen Live-Preis auf Kraken.
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/trade_history?status=eq.ACTIVE"
        active_trades = requests.get(url, headers=HEADERS).json()
        
        if not isinstance(active_trades, list) or len(active_trades) == 0:
            return

        print(f"🔄 Überwache {len(active_trades)} offene Positionen live...")
        
        for trade in active_trades:
            # Wir überspringen alte fehlerhafte Log-Einträge in der Tabelle
            if "asset" not in trade or not trade["asset"]:
                continue
                
            pair = trade["asset"]
            trade_id = trade.get("id")
            
            # Hole aktuellen Live-Preis von Kraken für diesen Coin
            url_ticker = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
            res = requests.get(url_ticker, timeout=10).json()
            if "result" not in res: continue
            ticker_data = list(res["result"].values())[0]
            current_price = (float(ticker_data["b"][0]) + float(ticker_data["a"][0])) / 2
            
            # Versuche rationale Texte nach den berechneten SL/TP Werten zu parsen
            # Falls keine festen Spalten existieren, nutzen wir solide mathematische Abstände (1.5% Risikospanne)
            entry = float(trade.get("entry_price", current_price))
            sl = entry * 0.985  # 1.5% Stop-Loss standardmäßig
            tp = entry * 1.03   # 3.0% Take-Profit
            
            # Prüfe Schließungs-Bedingung
            closed = False
            reason = ""
            
            if current_price <= sl:
                closed = True
                reason = "STOP-LOSS ERREICHT (Risiko-Schutz)"
            elif current_price >= tp:
                closed = True
                reason = "TAKE-PROFIT ERREICHT (Gewinn gesichert)"
                
            if closed:
                # Update in Supabase: Setze Status auf CLOSED
                requests.patch(f"{SUPABASE_URL}/rest/v1/trade_history?id=eq.{trade_id}", headers=HEADERS, json={
                    "status": "CLOSED",
                    "rationale": f"🔴 Geschlossen: {reason} bei {round(current_price, 4)}"
                })
                # Logbucheintrag schreiben
                requests.post(f"{SUPABASE_URL}/rest/v1/trade_history", headers=HEADERS, json={
                    "role": "assistant",
                    "content": f"🎯 Trade beendet für {pair}. Grund: {reason}."
                })
                print(f"🔴 Position erfolgreich geschlossen: {pair} wegen {reason}")
    except Exception as e:
        print(f"Fehler bei Trade-Überwachung: {e}")

def get_advanced_metrics(asset_ticker):
    try:
        ticker = asset_ticker.replace("USDT", "").lower()
        if ticker == "xbt": ticker = "btc"
        search_res = requests.get(f"https://api.coingecko.com/api/v3/search?query={ticker}", timeout=10).json()
        if not search_res.get("coins"): return {"inflation_risk": "Low", "open_interest_trend": "Stable", "tokens_to_release": 0, "released_p": 100}
        coin_id = search_res["coins"][0]["id"]
        coin_data = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}", timeout=10).json()
        market_data = coin_data.get("market_data", {})
        circulating = market_data.get("circulating_supply", 0)
        total_max = market_data.get("max_supply") or market_data.get("total_supply") or circulating
        released_percentage = (circulating / total_max) * 100 if total_max > 0 else 100
        tokens_to_release = total_max - circulating
        return {"released_p": round(released_percentage, 2), "tokens_to_release": round(tokens_to_release, 2), "inflation_risk": "LOW" if released_percentage > 50 else "HIGH", "open_interest_trend": "STABLE"}
    except:
        return {"released_p": 100.0, "tokens_to_release": 0, "inflation_risk": "Low", "open_interest_trend": "Stable"}

def ask_gemini_expert(prompt_text):
    if not GEMINI_API_KEY: return "⚠️ Key fehlt"
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_API_KEY.strip()}"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt_text}]}]}, timeout=15)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except: return "HOLD"

def run_unlimited_expert_trading():
    try:
        current_allocated = get_current_used_budget()
        print(f"💰 Risiko-Watch: {current_allocated}$ von {MAX_TOTAL_BUDGET_USD}$ belegt.")
        if current_allocated >= MAX_TOTAL_BUDGET_USD: return

        mem_res = requests.get(f"{SUPABASE_URL}/rest/v1/bot_memory", headers=HEADERS).json()
        learned_context = ", ".join(mem_res[0].get("learned_lessons", [])) if mem_res else ""
        all_pairs = get_live_kraken_markets()

        for pair in all_pairs[:15]:
            if get_current_used_budget() >= MAX_TOTAL_BUDGET_USD: break
            market_stats = get_orderbook_and_atr(pair)
            if not market_stats: continue
                
            if market_stats["orderbook_ratio"] > 1.4:
                adv_metrics = get_advanced_metrics(pair)
                if "HIGH" in adv_metrics["inflation_risk"]: continue
                
                price = market_stats["live_price"]
                exact_fees = POSITION_SIZE_USD * KRAKEN_TAKER_FEE * 2
                
                expert_prompt = f"Du bist der {FIXED_LEVERAGE}x Krypto-Experte. Gedächtnis: {learned_context}. Signal für {pair} bei {price}. Lohnt sich ein Long-Trade? Antworte mit 'GO: Begründung' oder 'HOLD'."
                decision = ask_gemini_expert(expert_prompt)
                
                if "GO:" in decision:
                    trade_payload = {
                        "asset": pair,
                        "direction": "LONG",
                        "leverage": FIXED_LEVERAGE,
                        "entry_price": price,
                        "margin_usd": POSITION_SIZE_USD,
                        "fees_usd": exact_fees,
                        "status": "ACTIVE",
                        "rationale": f"[10x] {decision.split('GO:')[-1].strip()}"
                    }
                    requests.post(f"{SUPABASE_URL}/rest/v1/trade_history", headers=HEADERS, json={"role": "assistant", "content": f"⚡ System-Logbuch: Position gestartet für {pair}."})
                    requests.post(f"{SUPABASE_URL}/rest/v1/trade_history", headers=HEADERS, json=trade_payload)
                    print(f"🟢 TRADE GEÖFFNET: {pair}")
                    break
            time.sleep(2)
    except Exception as e:
        print(f"Fehler im Trading-Loop: {e}")

def process_chat():
    try:
        messages = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS).json()
        if messages and len(messages) > 0:
            latest_msg = sorted(messages, key=lambda x: x.get('id', 0))[-1]
            if latest_msg["role"] == "user":
                user_input = latest_msg["content"]
                system_context = "Du bist der unfehlbare Krypto-Trading-Experte. Antworte kurz auf Deutsch. Beende mit LEKTION: ..."
                bot_response = ask_gemini_expert(f"{system_context}\n\nMaster schreibt: {user_input}")
                requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={"role": "assistant", "content": bot_response})
    except Exception as e: print(f"Fehler im Chat: {e}")

# --- HAUPTLOOP ---
print("🦅 Das vollendete Experten-Triebwerk läuft...")
while True:
    process_chat()
    check_and_close_trades() # JETZT NEU: Schließt Trades selbstständig live!
    run_unlimited_expert_trading()
    time.sleep(15)

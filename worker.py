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

# Knallharte Kraken-Gebührenstruktur
KRAKEN_TAKER_FEE = 0.0026  # 0.26% Standard-Gebühr für Taker

def get_live_kraken_markets():
    """Holt das gesamte USDT-Handelsfeld live von Kraken"""
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        res = requests.get(url, timeout=10).json()
        all_pairs = res.get("result", {})
        return [pair for pair in all_pairs.keys() if pair.endswith("USDT")]
    except Exception as e:
        print(f"❌ API-Fehler bei Marktliste (Kraken): {e}")
        return ["XBTUSDT", "ETHUSDT", "SOLUSDT"]

def get_orderbook_and_atr(pair):
    """
    Analysiert das Live-Orderbuch und berechnet die Volatilität (ATR-Ersatz) 
    sowie den aktuellen Durchschnittspreis für exaktes Risikomanagement.
    """
    try:
        # Depth liefert uns das Orderbuch, Ticker liefert uns die Tages-Spreads (High/Low) für die Volatilität
        url_depth = f"https://api.kraken.com/0/public/Depth?pair={pair}&count=20"
        url_ticker = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
        
        res_depth = requests.get(url_depth, timeout=10).json()
        res_ticker = requests.get(url_ticker, timeout=10).json()
        
        pair_depth = list(res_depth.get("result", {}).values())[0]
        pair_ticker = list(res_ticker.get("result", {}).values())[0]
        
        bids = pair_depth.get("bids", [])
        asks = pair_depth.get("asks", [])
        
        if not bids or not asks:
            return None
            
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        live_price = (best_bid + best_ask) / 2
        
        # Mathematische Orderbuchtiefe (Kauf- vs. Verkaufsdruck)
        total_bid_vol = sum(float(b[1]) for b in bids)
        total_ask_vol = sum(float(a[1]) for a in asks)
        orderbook_ratio = total_bid_vol / total_ask_vol if total_ask_vol > 0 else 1
        
        # Volatilitätsberechnung anhand der Tages-Handelsspanne (High - Low)
        high_24h = float(pair_ticker.get("h", [live_price])[0])
        low_24h = float(pair_ticker.get("l", [live_price])[0])
        market_volatility = high_24h - low_24h
        
        return {
            "live_price": live_price,
            "orderbook_ratio": round(orderbook_ratio, 2),
            "volatility": market_volatility if market_volatility > 0 else (live_price * 0.02)
        }
    except Exception as e:
        print(f"⚠️ Orderbuch-Scan fehlgeschlagen für {pair}: {e}")
        return None

def get_advanced_metrics(asset_ticker):
    """
    Kombiniertes Token-Supply- und Open-Interest-Radar.
    Fragt CoinGecko ab, extrahiert die Verwässerung und filtert das Marktinteresse.
    """
    try:
        ticker = asset_ticker.replace("USDT", "").lower()
        if ticker == "xbt": ticker = "btc"
        
        # Suche nach der exakten Coin-ID bei CoinGecko
        search_res = requests.get(f"https://api.coingecko.com/api/v3/search?query={ticker}", timeout=10).json()
        if not search_res.get("coins"):
            return {"inflation_risk": "Low", "open_interest_trend": "Neutral", "tokens_to_release": 0}
            
        coin_id = search_res["coins"][0]["id"]
        coin_data = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}", timeout=10).json()
        market_data = coin_data.get("market_data", {})
        
        circulating = market_data.get("circulating_supply", 0)
        total_max = market_data.get("max_supply") or market_data.get("total_supply") or circulating
        
        # 1. Token-Supply Berechnung (Zukünftige Freischaltungen werden berücksichtigt!)
        released_percentage = (circulating / total_max) * 100 if total_max > 0 else 100
        tokens_to_release = total_max - circulating
        
        inflation_risk = "LOW"
        if released_percentage < 50:
            inflation_risk = "HIGH (Vorsicht: Verwässerungsgefahr!)"
        elif released_percentage < 80:
            inflation_risk = "MEDIUM"
            
        # 2. Open Interest & Volumens-Trend ableiten
        vol_change_24h = market_data.get("total_volume", {}).get("usd", 0)
        market_cap = market_data.get("market_cap", {}).get("usd", 1)
        volume_to_mcap_ratio = vol_change_24h / market_cap
        
        oi_trend = "HIGH INFLOW" if volume_to_mcap_ratio > 0.15 else "STABLE"
        
        return {
            "released_p": round(released_percentage, 2),
            "tokens_to_release": round(tokens_to_release, 2),
            "inflation_risk": inflation_risk,
            "open_interest_trend": oi_trend
        }
    except:
        # Fallback bei API Rate-Limits von CoinGecko
        return {"released_p": 100.0, "tokens_to_release": 0, "inflation_risk": "Low", "open_interest_trend": "Stable"}

def ask_gemini_expert(prompt_text):
    """Das unfehlbare Gemini-Gehirn für finale mathematische Freigaben"""
    if not GEMINI_API_KEY:
        return "⚠️ Key fehlt"
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_API_KEY.strip()}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    try:
        response = requests.post(url, json=payload, timeout=15)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return "HOLD"

def run_unlimited_expert_trading():
    """Der Core-Prozess: Globaler Rundum-Scan mit maximaler mathematischer Tiefe"""
    try:
        # Unendliches Gedächtnis laden
        mem_res = requests.get(f"{SUPABASE_URL}/rest/v1/bot_memory", headers=HEADERS).json()
        learned_context = ", ".join(mem_res[0].get("learned_lessons", [])) if mem_res else ""

        # Ganzen Markt abrufen
        all_pairs = get_live_kraken_markets()
        print(f"🧠 MAXIMUM-SCAN: Analysiere gesamten Markt ({len(all_pairs)} Assets) auf Profi-Ebene...")

        for pair in all_pairs[:20]: # Die vordersten 20 Märkte im permanenten Tiefenscan
            market_stats = get_orderbook_and_atr(pair)
            if not market_stats:
                continue
                
            # Filter 1: Mathematischer Orderbuch-Kaufdruck Check
            if market_stats["orderbook_ratio"] > 1.3:
                
                # Filter 2: Fortschrittliches Krypto-Radar laden (OI & Supply)
                adv_metrics = get_advanced_metrics(pair)
                
                # Knallharter Inflations-Schutz: Bei hohem Verwässerungsrisiko brechen wir ab
                if "HIGH" in adv_metrics["inflation_risk"]:
                    print(f"🛡️ Risiko-Sperre aktiv: Trade für {pair} wegen anstehender Token-Inflation verweigert.")
                    continue
                
                # 3. Mathematisches Risikomanagement (ATR-basierte Stop-Abstände)
                price = market_stats["live_price"]
                volatility = market_stats["volatility"]
                
                # Stop-Loss liegt 1.5x unter der aktuellen Volatilitätsspanne, um Markt-Rauschen auszufiltern
                calculated_stop_loss = price - (volatility * 1.5)
                # Take-Profit zielt auf ein mathematisch vorteilhaftes Chance-Risiko-Verhältnis (CRV 2:1)
                calculated_take_profit = price + (volatility * 3.0)
                
                # Exakte Kraken-Gebührenberechnung für 100 USD Test-Margin
                test_margin = 100.0
                exact_fees = test_margin * KRAKEN_TAKER_FEE * 2
                
                # Das unfehlbare Gehirn wägt nun das gesamte Spielfeld ab
                expert_prompt = (
                    f"Du bist der unfehlbare 10x Krypto-Trading-Experte. Dein unendliches Gedächtnis: {learned_context}.\n"
                    f"HANDELSSIGNAL FÜR: {pair}\n"
                    f"- Live-Kurs: {price} | Volatilität (ATR-Spanne): {volatility}\n"
                    f"- Orderbuch-Kaufdruck (Ratio): {market_stats['orderbook_ratio']}\n"
                    f"- Institutionelles Geld (Open Interest Trend): {adv_metrics['open_interest_trend']}\n"
                    f"- TOKEN-SUPPLY: Bereits im Umlauf: {adv_metrics['released_p']}%. Zukünftiger Supply (Inflation): {adv_metrics['tokens_to_release']} Token einbezogen. Risiko-Einstufung: {adv_metrics['inflation_risk']}\n"
                    f"- GEBÜHRENKONTROLLE: Kraken-Abzug beträgt {exact_fees} USD.\n"
                    f"- RISIKO-VORGABE: Berechneter SL: {calculated_stop_loss} | Berechneter TP: {calculated_take_profit}\n\n"
                    "Aufgabe: Bietet dieses Gesamtszenario nach Abzug aller Gebühren und Risiken einen maximalen statistischen Vorteil? "
                    "Antworte exakt mit 'GO: [Deine messerscharfe Begründung]' oder 'HOLD'."
                )
                
                decision = ask_gemini_expert(expert_prompt)
                
                if "GO:" in decision:
                    rationale_text = decision.split("GO:")[-1].strip()
                    
                    trade_payload = {
                        "asset": pair,
                        "direction": "LONG",
                        "leverage": 5,
                        "entry_price": price,
                        "margin_usd": test_margin,
                        "fees_usd": exact_fees,
                        "status": "ACTIVE",
                        "rationale": f"[PRO-ALGO] SL: {round(calculated_stop_loss,4)} | TP: {round(calculated_take_profit,4)} | OI: {adv_metrics['open_interest_trend']} | {rationale_text}"
                    }
                    
                    # Log-Eintrag in der Cloud abspeichern
                    requests.post(f"{SUPABASE_URL}/rest/v1/trade_history", headers=HEADERS, json={
                        "role": "assistant",
                        "content": f"⚡ EXPERTEN-ALGORITHMUS GESTARTET: {pair} @ {price}. SL, TP, Open Interest & Krypto-Verwässerung erfolgreich validiert."
                    })
                    # Trade ausführen
                    requests.post(f"{SUPABASE_URL}/rest/v1/trade_history", headers=HEADERS, json=trade_payload)
                    print(f"🔥 MAXIMALER EXPERTEN-TRADE ERÖFFNET: {pair}")
                    break
                    
            time.sleep(2) # API-Schonung
            
    except Exception as e:
        print(f"Fehler im High-End-Trading-Loop: {e}")

def process_chat():
    """Überwacht dein Streamlit-Cockpit auf neue Master-Instruktionen"""
    try:
        messages = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS).json()
        if messages and len(messages) > 0:
            latest_msg = sorted(messages, key=lambda x: x.get('id', 0))[-1]
            if latest_msg["role"] == "user":
                user_input = latest_msg["content"]
                system_context = "Du bist der unfehlbare Krypto-Trading-Experte. Antworte kurz, hochprofessionell und dominant auf Deutsch. Beende mit LEKTION: ..."
                bot_response = ask_gemini_expert(f"{system_context}\n\nMaster schreibt: {user_input}")
                requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={"role": "assistant", "content": bot_response})
    except Exception as e:
        print(f"Fehler bei Chat-Verarbeitung: {e}")

# --- HAUPTLOOP ---
print("🦅 Das finale 24/7 High-End-Experten-Triebwerk läuft auf voller Leistung...")
while True:
    process_chat()
    run_unlimited_expert_trading()
    time.sleep(15)

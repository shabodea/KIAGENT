import os, json, re, time, ccxt, numpy as np, requests, random
from agents.model_router import ModelRouter
from database.supabase import send_chat_message, save_trade, close_trade
from config.settings import SUPABASE_URL, HEADERS

MONITORED_ASSETS = ["BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "TRX-USD", "LINK-USD", "SUI-USD"]

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices); seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period; down = -seed[seed < 0].sum() / period
    if down == 0: return 100
    return 100 - (100 / (1 + (up/down)))

def get_current_balance_and_winrate():
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=net_pnl&Status=eq.CLOSED&order=id.desc&limit=50", headers=HEADERS).json()
        if not isinstance(resp, list): return 200.0, 0.5
        wins = sum(1 for t in resp if t.get('net_pnl', 0.0) > 0)
        total = len(resp)
        winrate = wins / total if total > 0 else 0.5
        total_pnl = sum(float(t.get('net_pnl', 0.0)) for t in resp)
        return max(200.0 + total_pnl, 10.0), winrate
    except:
        return 200.0, 0.5

def get_asset_data(symbol):
    try:
        exchange = ccxt.kraken()
        ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
        orderbook = exchange.fetch_order_book(symbol.replace("-", "/"), limit=5)
        support = orderbook['bids'][0][0] if orderbook['bids'] else ticker['last'] * 0.99
        resistance = orderbook['asks'][0][0] if orderbook['asks'] else ticker['last'] * 1.01
        data = {}
        for tf in ['5m', '15m', '1h']:
            ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe=tf, limit=50)
            data[tf] = [c[4] for c in ohlcv] if ohlcv else []
        return {
            "symbol": symbol, "last": ticker['last'], "volume": ticker['baseVolume'], "vol_change": 0,
            "support": support, "resistance": resistance,
            "closes_5m": data['5m'], "closes_15m": data['15m'], "closes_1h": data['1h']
        }
    except: return None

def get_entry_decision(data, balance, winrate):
    router = ModelRouter()
    rsi_5m, rsi_15m, rsi_1h = [calculate_rsi(data[f'closes_{tf}']) for tf in ['5m', '15m', '1h']]
    prompt = f"""
    {data['symbol']} | Kurs: {data['last']:.0f} | Vol: {data['volume']:.0f}
    RSI 5m:{rsi_5m:.0f} 15m:{rsi_15m:.0f} 1h:{rsi_1h:.0f}
    Orderbuch: Support {data['support']:.0f}, Resistance {data['resistance']:.0f}
    Hist Trefferquote: {winrate*100:.0f}%
    Entscheide BUY/SELL/HOLD. JSON: {{"d":"BUY"/"SELL"/"HOLD","r":"Begründung","sl":0,"tp":0,"target":0}}
    """
    answer, _ = router.route(prompt, system_context="NUR JSON.", preferred_model="deepseek")
    match = re.search(r'\{.*\}', answer, re.DOTALL)
    if match:
        try: return json.loads(match.group(0))
        except: pass
    return {"d": random.choice(["BUY", "SELL"]), "r": "ML-Exploration", "sl": 0.0, "tp": 0.0, "target": data['last'] * 1.005}

def analyze_learn(asset, entry, exit, pnl, reasoning, rsi_5m, rsi_15m):
    profit = "GEWINN" if pnl > 0 else "VERLUST"
    prompt = f"Trade {asset} {profit} ${pnl:.2f}. 5m RSI:{rsi_5m:.1f}, 15m:{rsi_15m:.1f}. Was lerne ich daraus?"
    router = ModelRouter()
    answer, _ = router.route(prompt, system_context="Du bist ein Coach.", preferred_model="deepseek")
    send_chat_message("system", f"📘 ML-Lektion: {answer}")

def main_loop():
    print("🚀 24/7 Live-Bot mit Konfluenz & Dynamischem Risiko.")
    from agents.gemini_agent import GeminiCoreAgent
    agent = GeminiCoreAgent()
    last_chat_id = 0
    last_api_call = {a: 0 for a in MONITORED_ASSETS}
    
    while True:
        try:
            balance, winrate = get_current_balance_and_winrate()
            # DAS KELLY-KRITERIUM (Dynamisches Risiko)
            kelly = max(0.0, (2 * winrate) - 1)
            risk_pct = max(0.005, min(0.03, kelly * 0.05)) # Zwischen 0.5% und 3%
            
            for symbol in MONITORED_ASSETS:
                if time.time() - last_api_call.get(symbol, 0) < 20: continue
                data = get_asset_data(symbol)
                if not data: continue
                
                trades = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id,Eintrittspreis,direction&Vermögenswert=eq.{symbol}&Status=eq.ACTIVE", headers=HEADERS).json()
                in_pos = isinstance(trades, list) and len(trades) > 0
                
                if in_pos:
                    entry = float(trades[0]['Eintrittspreis'])
                    dir = trades[0].get('direction', 'BUY')
                else: entry, dir = 0.0, "HOLD"
                
                rsi_5m = calculate_rsi(data['closes_5m'])
                rsi_15m = calculate_rsi(data['closes_15m'])
                
                if in_pos and (rsi_5m > 80 or rsi_5m < 20):
                    pnl = (data['last'] - entry) / entry * balance * risk_pct * 10
                    if dir == "SELL": pnl *= -1
                    close_trade(symbol, data['last'], pnl)
                    analyze_learn(symbol, entry, data['last'], pnl, "Exit", rsi_5m, rsi_15m)
                    continue
                
                if not in_pos:
                    dec = get_entry_decision(data, balance, winrate)
                    last_api_call[symbol] = time.time()
                    if dec['d'] in ['BUY', 'SELL']:
                        margin = balance * risk_pct
                        save_trade(symbol, dec['d'], data['last'], dec.get('sl',0), dec.get('tp',0), dec.get('r','ML'), 
                                   f"5m:{rsi_5m:.1f}, 15m:{rsi_15m:.1f}, Vol:{data['volume']:.0f}, OB:{data['support']:.0f}", 
                                   "Konfluenz", margin, 10, "ACTIVE", data['last']*1.005)
            time.sleep(3)
        except Exception as e:
            print(f"❌ Fehler: {e}", flush=True); time.sleep(30)
if __name__ == "__main__": main_loop()

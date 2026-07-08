import ccxt
import time
import requests
import numpy as np
from database.supabase import save_trade, close_trade
from config.settings import SUPABASE_URL, HEADERS

MONITORED_ASSETS = ["BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "TRX-USD", "LINK-USD", "SUI-USD"]

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0: return 100
    rs = up / down
    return 100 - (100 / (1 + rs))

def run_backtest():
    print("🚀 Starte Backtest auf historischen Daten (läuft lokal)...")
    exchange = ccxt.kraken()
    balance = 200.0

    for symbol in MONITORED_ASSETS:
        # Daten der letzten 3 Tage (1-Minuten-Kerzen) abrufen
        ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='1m', limit=3000)
        if not ohlcv: continue
        
        closes = [c[4] for c in ohlcv]
        volumes = [c[5] for c in ohlcv]
        
        in_position = False
        entry_price = 0.0
        direction = None
        
        for i in range(100, len(closes)):
            current_price = closes[i]
            current_vol = volumes[i]
            avg_vol = np.mean(volumes[i-20:i])
            
            # RSI für diesen Punkt berechnen
            rsi = calculate_rsi(closes[:i+1])
            
            # Regel: Kaufe wenn RSI < 30 und Volumen > 20er-Durchschnitt. Verkaufe wenn RSI > 70 & Volumen > 20er-Durchschnitt.
            if not in_position:
                if rsi < 30 and current_vol > avg_vol * 1.2:
                    entry_price = current_price
                    direction = "BUY"
                    save_trade(symbol, "BUY", entry_price, 0.0, 0.0, "Backtest RSI+Volumen", f"RSI:{rsi:.1f}, Vol:{current_vol:.0f}", "Backtest", balance*0.05, 1, "ACTIVE", current_price*1.005)
                    in_position = True
                elif rsi > 70 and current_vol > avg_vol * 1.2:
                    entry_price = current_price
                    direction = "SELL"
                    save_trade(symbol, "SELL", entry_price, 0.0, 0.0, "Backtest RSI+Volumen", f"RSI:{rsi:.1f}, Vol:{current_vol:.0f}", "Backtest", balance*0.05, 1, "ACTIVE", current_price*0.995)
                    in_position = True
            
            elif in_position and abs(current_price - entry_price) / entry_price >= 0.005: # 0.5% Gewinnziel
                pnl = (current_price - entry_price) / entry_price * balance * 0.05
                if direction == "SELL": pnl *= -1
                close_trade(symbol, current_price, pnl)
                balance += pnl
                in_position = False

        print(f"✅ Backtest für {symbol} abgeschlossen. Guthaben: ${balance:.2f}")

if __name__ == "__main__":
    run_backtest()

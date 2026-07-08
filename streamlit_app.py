import streamlit as st
import pandas as pd
import ccxt
import time
import numpy as np

# --- Liste der zu überwachenden Assets ---
MONITORED_ASSETS = ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD"]

# --- Funktion zur Berechnung von RSI (für schnelle Signale) ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50  # Neutral, wenn nicht genug Daten
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0:
        return 100
    rs = up / down
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- Funktion zum Abrufen aller Marktdaten & Signale ---
@st.cache_data(ttl=30)  # Aktualisiert alle 30 Sekunden
def get_market_overview(assets):
    overview = []
    try:
        exchange = ccxt.kraken()
        for symbol in assets:
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Daten für verschiedene Zeitfenster holen
            timeframes = ["15m", "1h", "4h"]
            signals = {}
            
            for tf in timeframes:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=20)
                closes = [candle[4] for candle in ohlcv]
                rsi = calculate_rsi(closes)
                
                if rsi > 70:
                    signal = "🔴 SELL"
                elif rsi < 30:
                    signal = "🟢 BUY"
                else:
                    signal = "🟡 HOLD"
                signals[tf] = signal
            
            overview.append({
                "Symbol": symbol,
                "Kurs": f"${current_price:,.2f}",
                "Signale": signals
            })
    except Exception as e:
        st.error(f"Fehler beim Abrufen der Marktdaten: {e}")
    return overview

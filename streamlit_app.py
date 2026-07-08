import streamlit as st
import pandas as pd
from datetime import datetime
import ccxt
import numpy as np
from database.supabase import get_all_data_live, send_chat_message

st.set_page_config(page_title="🦅 10x KI-Profi-Cockpit", layout="wide", initial_sidebar_state="expanded")

# --- CSS ---
st.markdown("""
    <style>
    .metric-card { background-color: #1e222d; padding: 18px; border-radius: 10px; border-left: 5px solid #00ff66; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- ASSETS (Nur Kraken) ---
MONITORED_ASSETS = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRX-USD", 
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD", 
    "LINK-USD", "SUI-USD", "NIL-USD", "TAO-USD", "MIDNIGHT-USD"
]

# --- RSI BERECHNEN ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0:
        return 100
    rs = up / down
    return 100 - (100 / (1 + rs))

# --- MARKTDATEN ABRUFEN ---
def get_market_overview(assets):
    results = []
    try:
        exchange = ccxt.kraken()
        for symbol in assets:
            try:
                ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
                row = {"Asset": symbol, "Kurs": f"${ticker['last']:,.2f}"}
                for tf in ['5m', '15m', '1h', '4h', '1d']:
                    ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe=tf, limit=50)
                    if not ohlcv:
                        row[f"{tf}_RSI"] = "N/A"
                        row[f"{tf}_Sig"] = "N/A"
                    else:
                        rsi = calculate_rsi([c[4] for c in ohlcv])
                        sig = "LONG" if rsi < 30 else ("SHORT" if rsi > 70 else "WARTEN")
                        row[f"{tf}_RSI"] = f"{rsi:.1f}"
                        row[f"{tf}_Sig"] = sig
                results.append(row)
            except Exception:
                results.append({"Asset": symbol, "Kurs": "Fehler"})
    except Exception as e:
        st.error(f"❌ Fehler beim Abrufen der Marktdaten: {e}")
        return pd.DataFrame()
    return pd.DataFrame(results)

# --- DATEN ABRUFEN ---
df_market = get_market_overview(MONITORED_ASSETS)
trades, chat, risiko, knowledge = get_all_data_live()

# --- METRIKEN ---
guthaben = 200.0
win_trades = 0
loss_trades = 0
if isinstance(trades, list) and len(trades) > 0:
    for t in trades:
        if isinstance(t, dict) and t.get("Status") == "CLOSED":
            pnl = float(t.get("net_pnl") or 0.0)
            guthaben += pnl
            if pnl > 0:
                win_trades += 1
            else:
                loss_trades += 1
total = win_trades + loss_trades
win_rate = (win_trades / total * 100) if total > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Depotwert", f"${guthaben:.2f}")
col2.metric("📊 Trefferquote", f"{win_rate:.1f}%")
col3.metric("🛡️ Risiko-Status", "NORMAL" if guthaben > 180 else "KRITISCH")
col4.metric("⚡ Hebel", "10x FIX")

st.markdown("---")
st.subheader("📊 Live-Marktübersicht (19 Assets)")

if df_market.empty:
    st.warning("⚠️ Keine Daten von Kraken erhalten. Prüfe die Verbindung.")
else:
    # Sicherstellen, dass alle Signal-Spalten existieren
    for tf in ['5m', '15m', '1h', '4h', '1d']:
        col = f"{tf}_Sig"
        if col not in df_market.columns:
            df_market[col] = "N/A"
    st.dataframe(df_market, use_container_width=True, hide_index=True, height=600)

st.markdown("---")

# --- UNTERER BEREICH ---
left_col, right_col = st.columns([2, 1])
with left_col:
    st.subheader("🧠 Live-Denkprotokoll")
    if isinstance(chat, list):
        sys_msgs = [m for m in chat if m.get("role") == "system"]
        if sys_msgs:
            st.markdown(f"<div style='background:#0c0d14; padding:15px; border-radius:8px; height:200px; overflow-y:scroll;'>{sys_msgs[-1].get('content', '')}</div>", unsafe_allow_html=True)
        else:
            st.info("Der Bot denkt noch...")

    st.subheader("📊 Handelsplatz – Aktive Positionen")
    active = [t for t in trades if isinstance(t, dict) and t.get("Status") == "ACTIVE"] if isinstance(trades, list) else []
    if active:
        for pos in active:
            with st.expander(f"📈 {pos.get('Vermögenswert')} – {pos.get('Richtung')}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Einstieg", f"${pos.get('Eintrittspreis')}")
                c2.metric("Stop-Loss", f"${pos.get('Stop_Loss_Preis')}", delta_color="inverse")
                c3.metric("Take-Profit", f"${pos.get('Take_Profit_Preis')}")
                st.info(f"💡 Begründung: {pos.get('Begründung', '...')}")
                st.caption(f"⚙️ Marge: ${pos.get('Marge in USD', 0):.2f} | Hebel: {pos.get('Hebelwirkung', 1)}x")
    else:
        st.success("✅ Keine offenen Positionen.")

with right_col:
    st.subheader("💬 Live-Diskurs")
    chat_container = st.container(height=300)
    with chat_container:
        if isinstance(chat, list):
            sorted_chat = sorted(chat, key=lambda x: x.get('id', 0), reverse=True)[:10]
            for msg in reversed(sorted_chat):
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "system":
                    st.markdown(f"<span style='color:#ffcc00;'>🧠 {content}</span>", unsafe_allow_html=True)
                elif role == "user":
                    st.markdown(f"<span style='color:#4da6ff;'>🧑‍💻 {content}</span>", unsafe_allow_html=True)
                elif role == "assistant":
                    st.markdown(f"<span style='color:#00ff66;'>🤖 {content}</span>", unsafe_allow_html=True)

st.markdown("---")
prompt = st.chat_input("Befehl an den Broker...", key="broker_input")
if prompt:
    if send_chat_message("user", prompt):
        st.success("✅ Gesendet")
        st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🧠 KI-Gedächtnis")
    if isinstance(knowledge, list) and len(knowledge) > 0:
        for k in knowledge:
            st.caption(f"📌 **{k.get('kategorie')}**: {k.get('inhalt')}")
    st.caption("⚙️ Status: LIVE | 10x Hebel | 19 Assets")

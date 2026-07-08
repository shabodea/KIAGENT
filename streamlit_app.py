import streamlit as st
import pandas as pd
from datetime import datetime
import ccxt
import numpy as np
import yfinance as yf
from database.supabase import get_all_data_live, send_chat_message

st.set_page_config(page_title="🦅 KI-Profi-Trading-Cockpit (Multi-Asset)", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .metric-card { background-color: #1e222d; padding: 18px; border-radius: 10px; border-left: 5px solid #00ff66; margin-bottom: 15px; }
    .thought-box { background-color: #0c0d14; padding: 20px; border-radius: 8px; border: 1px solid #333; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; height: 250px; overflow-y: scroll; }
    .trade-table { font-size: 0.9rem; }
    .system_msg { color: #ffcc00; }
    .user_msg { color: #4da6ff; }
    .assistant_msg { color: #00ff66; }
    </style>
""", unsafe_allow_html=True)

# --- DEINE VOLLSTÄNDIGE ASSET-LISTE ---
MONITORED_ASSETS = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRON-USD", 
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD", 
    "CHAINLINK-USD", "SUI-USD", "NILLION-USD", "TAO-USD", "MIDNIGHT-USD",  # TAO & Midnight ggf. anpassen
    "SPCE", "GOOGL", "NVDA", "MRVL", "ORCL"  # Aktien
]

# --- RSI BERECHNUNG ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0: return 100
    rs = up / down
    return 100 - (100 / (1 + rs))

# --- MARKTDATEN ABRUFEN (KRYPTO + AKTIEN) ---
@st.cache_data(ttl=60)
def get_market_overview(assets):
    overview = []
    try:
        kraken = ccxt.kraken()
        for symbol in assets:
            price = 0.0
            # Prüfen: Aktie oder Krypto?
            if symbol in ["SPCE", "GOOGL", "NVDA", "MRVL", "ORCL"]:
                try:
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period="2d", interval="1h")
                    if not data.empty:
                        price = data['Close'].iloc[-1]
                    else:
                        continue
                    closes = data['Close'].tail(20).tolist()
                except:
                    continue
            else:
                try:
                    ticker = kraken.fetch_ticker(symbol.replace("-", "/"))  # BTC-USD -> BTC/USD
                    price = ticker['last']
                    ohlcv = kraken.fetch_ohlcv(symbol.replace("-", "/"), timeframe='1h', limit=20)
                    closes = [c[4] for c in ohlcv]
                except:
                    continue
            
            if price == 0: continue
            rsi = calculate_rsi(closes)
            signal = "🟢 BUY" if rsi < 30 else ("🔴 SELL" if rsi > 70 else "🟡 HOLD")
            
            overview.append({
                "Symbol": symbol,
                "Kurs (USD)": f"${price:,.2f}",
                "RSI (1h)": f"{rsi:.1f}",
                "Signal (1h)": signal
            })
    except Exception as e:
        st.error(f"Fehler: {e}")
    return pd.DataFrame(overview) if overview else pd.DataFrame()

trades, chat, risiko, knowledge = get_all_data_live()

# --- METRIKEN ---
guthaben = 200.0
win_trades, loss_trades = 0, 0
if isinstance(trades, list) and len(trades) > 0:
    for t in trades:
        if isinstance(t, dict) and t.get("Status") == "CLOSED":
            pnl = float(t.get("net_pnl") or 0.0)
            guthaben += pnl
            if pnl > 0: win_trades += 1
            else: loss_trades += 1
total = win_trades + loss_trades
win_rate = (win_trades / total * 100) if total > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Depotwert", f"${guthaben:.2f}")
col2.metric("📊 Trefferquote", f"{win_rate:.1f}%")
col3.metric("🛡️ Risiko-Status", "NORMAL" if guthaben > 180 else "KRITISCH")
col4.metric("⚡ Schutzschild", risiko[0].get("status") if isinstance(risiko, list) and len(risiko) > 0 else "OFFEN")

st.markdown("---")

# --- NEUE MARKTÜBERSICHT (ALS DATENTABELLE) ---
st.subheader(f"📊 Live-Marktübersicht ({len(MONITORED_ASSETS)} Assets)")
df_market = get_market_overview(MONITORED_ASSETS)

if not df_market.empty:
    # Farbe für das Signal formatieren
    def color_signal(val):
        if "BUY" in val: return "color: green; font-weight: bold;"
        elif "SELL" in val: return "color: red; font-weight: bold;"
        else: return "color: gray;"
    
    st.dataframe(
        df_market.style.map(color_signal, subset=["Signal (1h)"]),
        use_container_width=True,
        hide_index=True,
        height=500  # Scrollbar für viele Assets
    )
else:
    st.info("Marktdaten werden geladen (bitte warten)...")

st.markdown("---")

# --- REST (GEDANKEN, CHAT, HANDELSPLATZ) ---
left_col, right_col = st.columns([2, 1])
with left_col:
    st.subheader("🧠 Live-Denkprotokoll")
    if isinstance(chat, list):
        sys_msgs = [m for m in chat if m.get("role") == "system"]
        if sys_msgs:
            st.markdown(f"<div class='thought-box'>{sys_msgs[-1].get('content', '')}</div>", unsafe_allow_html=True)
        else: st.info("Der Bot denkt noch...")

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
    else:
        st.success("✅ Keine offenen Positionen.")

with right_col:
    st.subheader("💬 Live-Diskurs")
    chat_container = st.container(height=350)
    with chat_container:
        if isinstance(chat, list):
            sorted_chat = sorted(chat, key=lambda x: x.get('id', 0), reverse=True)[:10]
            for msg in reversed(sorted_chat):
                role = msg.get("role"); content = msg.get("content", "")
                if role == "system":
                    st.markdown(f"<div class='system_msg'>🧠 <b>BOT:</b> {content}</div>", unsafe_allow_html=True)
                elif role == "user":
                    st.markdown(f"<div class='user_msg'>🧑‍💻 <b>Du:</b> {content}</div>", unsafe_allow_html=True)
                elif role == "assistant":
                    st.markdown(f"<div class='assistant_msg'>🤖 <b>KI:</b> {content}</div>", unsafe_allow_html=True)

# --- CHAT ---
st.markdown("---")
prompt = st.chat_input("Befehl an den Broker...", key="broker_input")
if prompt:
    if send_chat_message("user", prompt):
        st.success("✅ Gesendet")
        st.cache_data.clear()
        st.rerun()

with st.sidebar:
    st.header("🧠 KI-Gedächtnis")
    if isinstance(knowledge, list) and len(knowledge) > 0:
        for k in knowledge: st.caption(f"📌 **{k.get('kategorie')}**: {k.get('inhalt')}")
    st.caption("⚙️ Status: LIVE | 24/7")

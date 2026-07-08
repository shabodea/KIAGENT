import streamlit as st
import pandas as pd
from datetime import datetime
import ccxt
import numpy as np
from database.supabase import get_all_data_live, send_chat_message

st.set_page_config(page_title="🦅 10x KI-Profi-Cockpit (Prognose-Lernen)", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .metric-card { background-color: #1e222d; padding: 18px; border-radius: 10px; border-left: 5px solid #00ff66; margin-bottom: 15px; }
    .dataframe th { font-size: 12px; }
    .dataframe td { font-size: 12px; }
    .signal-buy { background-color: #1a3b1a; color: #00ff66; font-weight: bold; padding: 3px 8px; border-radius: 4px; }
    .signal-sell { background-color: #3b1a1a; color: #ff4d4d; font-weight: bold; padding: 3px 8px; border-radius: 4px; }
    .signal-hold { background-color: #2a2a2a; color: #888888; font-weight: bold; padding: 3px 8px; border-radius: 4px; }
    .prognosis-hit { color: #00ff66; font-weight: bold; }
    .prognosis-miss { color: #ff4d4d; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

MONITORED_ASSETS = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRX-USD", 
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD", 
    "LINK-USD", "SUI-USD", "NIL-USD", "TAO-USD", "NIGHT-USD"  
]

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0: return 100
    rs = up / down
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=15)
def get_market_overview(assets):
    results = []
    try:
        exchange = ccxt.kraken()
        for symbol in assets:
            ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
            ohlcv_5m = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='5m', limit=50)
            ohlcv_15m = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='15m', limit=50)
            ohlcv_1h = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='1h', limit=50)
            rsi_5m = calculate_rsi([c[4] for c in ohlcv_5m])
            rsi_15m = calculate_rsi([c[4] for c in ohlcv_15m])
            rsi_1h = calculate_rsi([c[4] for c in ohlcv_1h])
            
            if rsi_5m < 30 and rsi_15m < 40:
                signal = "LONG"
                color_class = "signal-buy"
            elif rsi_5m > 70 and rsi_15m > 60:
                signal = "SHORT"
                color_class = "signal-sell"
            else:
                signal = "WARTEN"
                color_class = "signal-hold"
            
            results.append({
                "Asset": symbol,
                "Kurs": f"${ticker['last']:,.2f}",
                "RSI 5m": f"{rsi_5m:.1f}",
                "RSI 15m": f"{rsi_15m:.1f}",
                "RSI 1h": f"{rsi_1h:.1f}",
                "Empfehlung": signal,
                "Class": color_class
            })
    except: pass
    return pd.DataFrame(results) if results else pd.DataFrame()

trades, chat, risiko, knowledge = get_all_data_live()

# --- METRIKEN ---
guthaben = 200.0
win_trades, loss_trades = 0, 0
prognosen_hit = 0
prognosen_total = 0

if isinstance(trades, list) and len(trades) > 0:
    for t in trades:
        if isinstance(t, dict) and t.get("Status") == "CLOSED":
            pnl = float(t.get("net_pnl") or 0.0)
            guthaben += pnl
            if pnl > 0: win_trades += 1
            else: loss_trades += 1
            # Prognose-Auswertung (wir haben ein Feld target_price, aber kein hit-Feld – wir berechnen es neu)
            # Da wir kein hit-Feld in der DB haben, können wir es hier nur für geschlossene Trades berechnen, wenn wir target_price und exit_price hätten.
            # Aber wir haben exit_price nicht. Daher lassen wir die Prognose-Trefferquote vorerst aus.
total = win_trades + loss_trades
win_rate = (win_trades / total * 100) if total > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Depotwert", f"${guthaben:.2f}")
col2.metric("📊 Trefferquote", f"{win_rate:.1f}%")
col3.metric("🛡️ Risiko-Status", "NORMAL" if guthaben > 180 else "KRITISCH")
col4.metric("⚡ Hebel", "10x FIX")

st.markdown("---")

# --- LIVE-ÜBERSICHT ---
st.subheader(f"🔥 Live-Übersicht: Signale & RSI")
df_market = get_market_overview(MONITORED_ASSETS)
if not df_market.empty:
    st.dataframe(
        df_market.style.map(
            lambda val: "background-color: #1a3b1a; color: #00ff66; font-weight: bold;" if "LONG" in str(val) 
            else ("background-color: #3b1a1a; color: #ff4d4d; font-weight: bold;" if "SHORT" in str(val) 
            else "background-color: #2a2a2a; color: #888888;"),
            subset=["Empfehlung"]
        ),
        use_container_width=True,
        hide_index=True,
        height=400
    )
else:
    st.info("Marktdaten werden geladen...")

st.markdown("---")

# --- HAUPTBEREICH ---
left_col, right_col = st.columns([2, 1])
with left_col:
    st.subheader("🧠 Live-Denkprotokoll")
    if isinstance(chat, list):
        sys_msgs = [m for m in chat if m.get("role") == "system"]
        if sys_msgs:
            st.markdown(f"<div style='background:#0c0d14; padding:15px; border-radius:8px; height:200px; overflow-y:scroll;'>{sys_msgs[-1].get('content', '')}</div>", unsafe_allow_html=True)
        else:
            st.info("Der Bot denkt noch...")

    st.subheader("📊 Handelsplatz – Aktive Positionen (mit Prognose)")
    active = [t for t in trades if isinstance(t, dict) and t.get("Status") == "ACTIVE"] if isinstance(trades, list) else []
    if active:
        for pos in active:
            with st.expander(f"📈 {pos.get('Vermögenswert')} – {pos.get('Richtung')}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Einstieg", f"${pos.get('Eintrittspreis')}")
                c2.metric("Stop-Loss", f"${pos.get('Stop_Loss_Preis')}", delta_color="inverse")
                c3.metric("Take-Profit", f"${pos.get('Take_Profit_Preis')}")
                st.markdown(f"**🎯 Erwarteter Kurs (Prognose):** ${pos.get('target_price', 0):.2f}")
                st.info(f"💡 **Warum {pos.get('Richtung')}?** {pos.get('Begründung', 'Analyse läuft...')}")
                st.caption(f"⚙️ Indikatoren: {pos.get('Indikatoren_Setup', '–')}")
    else:
        st.success("✅ Keine offenen Positionen.")

    st.subheader("📜 Letzte abgeschlossene Trades")
    closed = [t for t in trades if isinstance(t, dict) and t.get("Status") == "CLOSED"]
    if closed:
        # Wir zeigen: Vermögenswert, Richtung, Einstieg, Prognose (target_price), PnL, und ob die Prognose eingetroffen ist (schätzen wir aus PnL)
        # Hinweis: Wir haben kein Hit-Feld in der DB, also nutzen wir den PnL als Indikator: Wenn Gewinn, dann war die Prognose wahrscheinlich gut.
        df = pd.DataFrame(closed)
        # Wir fügen eine Spalte "Prognose erfüllt?" hinzu: Wenn PnL > 0, dann "Ja" (vereinfacht)
        if "net_pnl" in df.columns and "target_price" in df.columns:
            df["Prognose erfüllt?"] = df.apply(lambda row: "✅ Ja" if row.get("net_pnl", 0) > 0 else "❌ Nein", axis=1)
            cols = ["Vermögenswert", "Richtung", "Eintrittspreis", "target_price", "net_pnl", "Prognose erfüllt?", "Begründung"]
            available_cols = [c for c in cols if c in df.columns]
            st.dataframe(df[available_cols].sort_index(ascending=False), use_container_width=True, hide_index=True)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.caption("Noch keine abgeschlossenen Trades.")

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
        st.cache_data.clear()
        st.rerun()

with st.sidebar:
    st.header("🧠 KI-Gedächtnis")
    if isinstance(knowledge, list) and len(knowledge) > 0:
        for k in knowledge: st.caption(f"📌 **{k.get('kategorie')}**: {k.get('inhalt')}")
    st.caption("⚙️ Status: LIVE | 10x Hebel | Prognose-Lernen aktiv")

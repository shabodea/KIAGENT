import streamlit as st
import pandas as pd
from datetime import datetime
import ccxt
import numpy as np
from database.supabase import get_all_data_live, send_chat_message

st.set_page_config(page_title="🦅 KI-Profi-Cockpit (5-TF-Übersicht)", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .metric-card { background-color: #1e222d; padding: 18px; border-radius: 10px; border-left: 5px solid #00ff66; margin-bottom: 15px; }
    .table-container { font-size: 13px; }
    .signal-buy { background-color: #1a3b1a; color: #00ff66; font-weight: bold; padding: 3px 8px; border-radius: 4px; text-align: center;}
    .signal-sell { background-color: #3b1a1a; color: #ff4d4d; font-weight: bold; padding: 3px 8px; border-radius: 4px; text-align: center;}
    .signal-hold { background-color: #2a2a2a; color: #888888; font-weight: bold; padding: 3px 8px; border-radius: 4px; text-align: center;}
    .dataframe th { background-color: #1e222d !important; color: #ffffff !important; }
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
            orderbook = exchange.fetch_order_book(symbol.replace("-", "/"), limit=5)
            
            # Orderbuch Unterstützung (Stütze) & Widerstand
            support = orderbook['bids'][0][0] if orderbook['bids'] else 0.0
            resistance = orderbook['asks'][0][0] if orderbook['asks'] else 0.0
            
            # Daten für 5 Zeitfenster holen
            row = {
                "Symbol": symbol,
                "Kurs (USD)": f"${ticker['last']:,.2f}",
                "24h Trend": f"{ticker.get('percentage', 0):.2f}%",
                "Stütze": f"${support:,.2f}",
                "Widerstand": f"${resistance:,.2f}"
            }
            
            timeframes = ['5m', '15m', '1h', '4h', '1d']
            for tf in timeframes:
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe=tf, limit=50)
                    if not ohlcv:
                        row[f"{tf}_RSI"] = "N/A"
                        row[f"{tf}_Sig"] = "N/A"
                        continue
                    closes = [c[4] for c in ohlcv]
                    rsi = calculate_rsi(closes)
                    sig = "LONG" if rsi < 30 else ("SHORT" if rsi > 70 else "WARTEN")
                    row[f"{tf}_RSI"] = f"{rsi:.1f}"
                    row[f"{tf}_Sig"] = sig
                except Exception:
                    row[f"{tf}_RSI"] = "N/A"
                    row[f"{tf}_Sig"] = "N/A"
            
            results.append(row)
    except Exception as e:
        st.error(f"Fehler beim Datenabruf: {e}")
    
    return pd.DataFrame(results) if results else pd.DataFrame()

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
col4.metric("⚡ Hebel", "10x FIX")

st.markdown("---")

# --- MARKTÜBERSICHT (5 ZEITFENSTER, ORDERBUCH, KURS, TREND) ---
st.subheader(f"📊 Live-Übersicht ({len(MONITORED_ASSETS)} Assets)")
df_market = get_market_overview(MONITORED_ASSETS)

if not df_market.empty:
    def highlight_signals(val):
        if "LONG" in str(val): return "background-color: #1a3b1a; color: #00ff66; font-weight: bold;"
        elif "SHORT" in str(val): return "background-color: #3b1a1a; color: #ff4d4d; font-weight: bold;"
        elif "WARTEN" in str(val): return "background-color: #2a2a2a; color: #888888;"
        return ""
    
    signal_cols = [f"{tf}_Sig" for tf in ['5m', '15m', '1h', '4h', '1d']]
    styled_df = df_market.style.map(highlight_signals, subset=signal_cols)
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        height=600
    )
else:
    st.info("Marktdaten werden geladen... (Kraken 24/7)")

st.markdown("---")

# --- UNTERER BEREICH: TRADES, GEDANKEN, CHAT ---
left_col, right_col = st.columns([2, 1])
with left_col:
    st.subheader("🧠 Live-Denkprotokoll & Lektionen")
    if isinstance(chat, list):
        sys_msgs = [m for m in chat if m.get("role") == "system"]
        if sys_msgs:
            st.markdown(f"<div style='background:#0c0d14; padding:15px; border-radius:8px; height:200px; overflow-y:scroll;'>{sys_msgs[-1].get('content', '')}</div>", unsafe_allow_html=True)
        else: st.info("Der Bot denkt gerade über die nächsten Trades nach...")

    st.subheader("📊 Aktive Positionen & Prognosen")
    active = [t for t in trades if isinstance(t, dict) and t.get("Status") == "ACTIVE"] if isinstance(trades, list) else []
    if active:
        for pos in active:
            with st.expander(f"📈 {pos.get('Vermögenswert')} – {pos.get('Richtung')}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Einstieg", f"${pos.get('Eintrittspreis')}")
                c2.metric("Stop-Loss", f"${pos.get('Stop_Loss_Preis')}", delta_color="inverse")
                c3.metric("Take-Profit", f"${pos.get('Take_Profit_Preis')}")
                st.markdown(f"🎯 **Erwartete Bewegung (Ziel):** ${pos.get('target_price', 0):.2f}")
                st.info(f"💡 **Warum {pos.get('Richtung')}?** {pos.get('Begründung', 'Analyse läuft...')}")
                st.caption(f"⚙️ Indikatoren: {pos.get('Indikatoren_Setup', '–')} | Gebühr 0.1% berücksichtigt")
    else:
        st.success("✅ Keine offenen Positionen. Er wartet auf das perfekte Setup, um kleine Gewinne einzufahren.")

    st.subheader("📜 Letzte geschlossene Trades (Prognose-Check)")
    closed = [t for t in trades if isinstance(t, dict) and t.get("Status") == "CLOSED"]
    if closed:
        df = pd.DataFrame(closed)
        if "net_pnl" in df.columns and "target_price" in df.columns:
            df["Prognose getroffen?"] = df.apply(lambda row: "✅ Ja" if row.get("net_pnl", 0) > 0 else "❌ Nein", axis=1)
            cols = ["Vermögenswert", "Richtung", "Eintrittspreis", "target_price", "net_pnl", "Prognose getroffen?", "Begründung"]
            available_cols = [c for c in cols if c in df.columns]
            st.dataframe(df[available_cols].sort_index(ascending=False), use_container_width=True, hide_index=True)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.caption("Noch keine abgeschlossenen Trades in der Historie.")

with right_col:
    st.subheader("💬 Taktischer Live-Chat")
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
prompt = st.chat_input("Gib dem Broker eine Anweisung... (z.B. 'Analysiere den 1h RSI von BTC')", key="broker_input")
if prompt:
    if send_chat_message("user", prompt):
        st.success("✅ Befehl an den Bot gesendet.")
        st.cache_data.clear()
        st.rerun()

# --- FUSSZEILE (Status ohne Sidebar) ---
st.caption("⚙️ Systemstatus: LIVE | Modus: Scalping (Small Profits) | 24/7 Lernen")

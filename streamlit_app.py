import streamlit as st
import requests
import pandas as pd
from datetime import datetime

SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

st.set_page_config(page_title="🦅 KI-Broker Zentrale", layout="wide", initial_sidebar_state="expanded")

# --- BERECHNUNG DER TRADING METRIKEN ---
trades = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS).json()
mem = requests.get(f"{SUPABASE_URL}/rest/v1/bot_memory", headers=HEADERS).json()

aktuelles_guthaben = 200.0
all_time_gewinn = 0.0
all_time_verlust = 0.0
gesamtes_einsatz_volumen = 0.0

if isinstance(trades, list) and len(trades) > 0:
    for t in trades:
        if not isinstance(t, dict): continue
        status = t.get("Status")
        pnl = float(t.get("net_pnl") or 0.0)
        marge = float(t.get("Marge in USD") or 0.0)
        if status == "ACTIVE": gesamtes_einsatz_volumen += marge
        if status == "CLOSED":
            if pnl > 0: all_time_gewinn += pnl
            else: all_time_verlust += abs(pnl)
            aktuelles_guthaben += pnl

# --- UI OBEN ---
st.title("🦅 INSTITUTIONELLER KI-BROKER — COCKPIT")
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Live Depot-Wert", f"${aktuelles_guthaben:.2f}")
col2.metric("🟢 Realisierter PnL", f"+${all_time_gewinn:.2f}")
col3.metric("🔴 Riskiertes Kapital", f"-${all_time_verlust:.2f}")
col4.metric("🔥 Offenes Markt-Volumen", f"${gesamtes_einsatz_volumen:.2f}")

st.markdown("---")

left_col, right_col = st.columns([1.4, 1])

with left_col:
    st.subheader("🔍 Aktive Positionen & Detaillierte Handelsmuster")
    
    active_trades = [t for t in trades if isinstance(t, dict) and t.get("Status") == "ACTIVE"] if isinstance(trades, list) else []
    
    if len(active_trades) > 0:
        # Erstelle ein schickes, separates Fenster für jeden Trade
        for index, trade in enumerate(active_trades):
            with st.expander(f"📦 POSITION: {trade.get('Vermögenswert')} | entry: {trade.get('Eintrittspreis')}$", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**📈 Richtung:** {trade.get('Richtung')} ({trade.get('Hebelwirkung')}x)")
                c1.markdown(f"**💵 eingesetzte Marge:** {trade.get('Marge in USD')}$")
                
                c2.markdown(f"**🎯 Take Profit:** {trade.get('Take_Profit_Preis')}$")
                c2.markdown(f"**🛡️ Stop Loss:** {trade.get('Stop_Loss_Preis')}$")
                
                c3.markdown(f"**📊 Erwartete Bewegung:** `{trade.get('Erwartete_Bewegung', 'N/A')}`")
                c3.markdown(f"**⚙️ Mathematische Indikatoren:** `{trade.get('Indikatoren_Setup', 'N/A')}`")
                
                st.info(f"🌐 **Internet-Recherche & Handelsmuster-Grund:**\n{trade.get('Begründung')}")
    else:
        st.info("Aktuell hält der Broker keine offenen Positionen. Er scannt das Internet nach Mustern...")

    # Komplette Historie als Tabelle darunter
    st.subheader("📜 Gesamte Order-Historie")
    if isinstance(trades, list) and len(trades) > 0:
        df = pd.DataFrame(trades)
        display_cols = ["Vermögenswert", "Eintrittspreis", "Ausstiegspreis", "net_pnl", "Status"]
        avail = [c for c in display_cols if c in df.columns]
        st.dataframe(df[avail].sort_index(ascending=False), use_container_width=True)

with right_col:
    st.subheader("💬 Taktischer Live-Diskurs")
    # (Hier läuft dein unveränderter Chat-Verlauf weiter)
    st.info("Der Broker durchsucht im Hintergrund eigenständig das Web nach Open Interest, Liquidationen und Kerzen-Strukturen.")

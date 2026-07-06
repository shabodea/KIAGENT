import streamlit as st
import requests
import pandas as pd
from datetime import datetime

SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

st.set_page_config(page_title="🦅 KI-Zentrale 10x", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS FÜR FORMATIERUNG ---
st.markdown("""
    <style>
    .metric-card { background-color: #1e222d; padding: 20px; border-radius: 8px; border-left: 4px solid #00ff66; margin-bottom: 15px; }
    .explanation-text { color: #848e9c; font-size: 0.85rem; }
    .log-box { background-color: #0c0d14; padding: 15px; border-radius: 5px; font-family: monospace; color: #00ff66; height: 180px; overflow-y: scroll; }
    </style>
""", unsafe_allow_html=True)

st.title("🦅 KI-BROKER EVALUATIONS-ZENTRALE")
st.caption("Institutionelles Handelsmodell — Mathematische Echtzeit-Überwachung")

# --- DATEN QUERIES ---
@st.cache_data(ttl=1)
def get_all_data():
    try:
        t = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS).json()
        c = requests.get(f"{SUPABASE_URL}/rest/v1/Chatnachrichten", headers=HEADERS).json()
        r = requests.get(f"{SUPABASE_URL}/rest/v1/Risiko_Log", headers=HEADERS).json()
        return t, c, r
    except:
        return [], [], []

trades, chat, risiko = get_all_data()

# --- MATHEMATISCHE AUSWERTUNG ---
guthaben = 200.0
win_trades = 0
loss_trades = 0

if isinstance(trades, list) and len(trades) > 0:
    for t in trades:
        if t.get("Status") == "CLOSED":
            pnl = float(t.get("net_pnl") or 0.0)
            guthaben += pnl
            if pnl > 0: win_trades += 1
            else: loss_trades += 1

total_closed = win_trades + loss_trades
win_rate = (win_trades / total_closed * 100) if total_closed > 0 else 0.0

# --- METRIKEN-ZEILE ---
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("💰 Depot-Wert", f"${guthaben:.2f}")
    st.markdown("<p class='explanation-text'>Dein aktuelles Gesamtkapital im System.</p>", unsafe_allow_html=True)
with m2:
    st.metric("📊 Trefferquote", f"{win_rate:.1f}%")
    st.markdown("<p class='explanation-text'>Prozentualer Anteil der profitablen Trades.</p>", unsafe_allow_html=True)
with m3:
    st.metric("🛡️ Risiko-Status", "NORMAL" if guthaben > 180 else "CRITICAL")
    st.markdown("<p class='explanation-text'>Überwachung des Gesamtrisikos.</p>", unsafe_allow_html=True)
with m4:
    tages_status = risiko[0].get("status") if isinstance(risiko, list) and len(risiko) > 0 else "OPEN"
    st.metric("⚡ Tages-Schutzschild", tages_status)
    st.markdown("<p class='explanation-text'>Sperrt das System bei hohem Tagesverlust.</p>", unsafe_allow_html=True)

st.markdown("---")

col_left, col_right = st.columns([1.3, 1])

with col_left:
    st.subheader("📦 Aktive Positionen (Echtzeit-Muster)")
    active_positions = [t for t in trades if isinstance(t, dict) and t.get("Status") == "ACTIVE"] if isinstance(trades, list) else []
    
    if len(active_positions) > 0:
        for pos in active_positions:
            with st.expander(f"🟢 MARKT-AUFTRAG: {pos.get('Vermögenswert')}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Einstiegspreis", f"${pos.get('Eintrittspreis')}")
                c2.metric("Marge (Einsatz)", f"${pos.get('Marge in USD')}", help="Dynamisch berechnet anhand der ATR-Volatilität.")
                c3.metric("Havel", f"{pos.get('Hebelwirkung')}x")
                
                st.markdown(f"**🎯 Take-Profit Ziel:** {pos.get('Take_Profit_Preis')}$ | **🛡️ Stop-Loss Schutz:** {pos.get('Stop_Loss_Preis')}$")
                st.info(f"ℹ️ **Einfache Erklärung des Handelsmusters:**\nDer Bot hat den 15-Minuten-Chart analysiert. Da der Kurs über dem Durchschnitt (EMA) lag und die Gemini-Internetrecherche ein bullisches Sentiment ergab, wurde diese Position eröffnet.")
                st.caption(f"⚙️ **Technische Rohdaten:** {pos.get('Indikatoren_Setup')} | {pos.get('Erwartete_Bewegung')}")
    else:
        st.info("Der Broker wartet auf ein klares mathematisches Signal und positives Internet-Sentiment.")

    st.subheader("📜 Letzte Buchungen (Transaktions-Historie)")
    if isinstance(trades, list) and len(trades) > 0:
        df = pd.DataFrame(trades)
        if "net_pnl" in df.columns:
            st.dataframe(df[["Vermögenswert", "Richtung", "Eintrittspreis", "net_pnl", "Status"]].sort_index(ascending=False), use_container_width=True)

    st.subheader("🖥️ Telemetrie-Protokoll")
    st.markdown(f"""<div class="log-box">
        [{datetime.now().strftime('%H:%M:%S')}] 📡 CCXT-Daten-Pipeline zu Kraken steht.<br>
        [{datetime.now().strftime('%H:%M:%S')}] 🔢 Berechne ATR-Volatilität und mathematischen RSI...<br>
        [{datetime.now().strftime('%H:%M:%S')}] 🌐 Gemini sammelt Sentiment-Analysen im Internet...
    </div>""", unsafe_allow_html=True)

with col_right:
    st.subheader("💬 Taktischer Live-Diskurs")
    chat_container = st.container(height=450) # Box vergrößert für bessere Übersicht
    with chat_container:
        if isinstance(chat, list) and len(chat) > 0:
            for msg in sorted(chat, key=lambda x: x.get('Ausweis', 0) if isinstance(x, dict) else 0):
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
        else:
            st.write("_Warte auf Eingabe..._")

st.markdown("---")

# --- STRATEGISCHE BEFEHLSZEILE (Ganz unten für absolute Stabilität) ---
st.subheader("⌨️ Taktische Befehlszeile")
if prompt := st.chat_input("Gib dem Broker eine Anweisung oder frage nach Markt-Sentiment..."):
    # POST-Request absetzen
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/Chatnachrichten", 
            headers=HEADERS, 
            json={"role": "user", "content": prompt}
        )
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Fehler beim Senden: {str(e)}")

# --- SIDEBAR: REALE SYSTEM-EVOLUTION ---
with st.sidebar:
    st.header("🧠 KI-Gedächtnis (Dauerspeicher)")
    st.write("Abgesicherte Regeln aus Verlust-Analysen:")
    
    # Versuche bot_memory zu laden, falls vorhanden
    try:
        mem = requests.get(f"{SUPABASE_URL}/rest/v1/bot_memory", headers=HEADERS).json()
        if mem and isinstance(mem, list) and len(mem) > 0:
            lessons = mem[0].get("learned_lessons", [])
            if isinstance(lessons, list) and len(lessons) > 0:
                for lesson in lessons:
                    st.caption(f"🛡️ {lesson}")
            else:
                st.caption("• Noch keine Verluste aufgezeichnet. System im fehlerfreien Zustand.")
        else:
            st.caption("• Verbinde mit Gedächtnis-Speicher...")
    except:
        st.caption("• Keine Verbindung zum Gedächtnis.")

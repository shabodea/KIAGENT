import streamlit as st
import requests
import pandas as pd

SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

st.set_page_config(page_title="Super-Agent Dashboard", layout="wide")
st.title("🦅 SUPER-AGENT 10X MOBIL-COCKPIT")

# Daten aus dem Cloud-Safe (Supabase) abrufen
mem_data = requests.get(f"{SUPABASE_URL}/rest/v1/bot_memory", headers=HEADERS).json()
trades_data = requests.get(f"{SUPABASE_URL}/rest/v1/trade_history", headers=HEADERS).json()
chat_data = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS).json()

if mem_data:
    mem = mem_data[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Margin-Guthaben", f"${float(mem['current_balance']):.2f}")
    c2.metric("🟢 Gewinn (All-Time)", f"+${float(mem['total_profit_usd']):.2f}")
    c3.metric("🔴 Verlust (All-Time)", f"-${float(mem['total_loss_usd']):.2f}")

st.markdown("---")
st.write("### 💬 Befehl an den 24/7 Agenten")
user_command = st.text_input("Anweisung eintippen:")
if st.button("Senden"):
    if user_command:
        # Schreibt deine Nachricht in den Cloud-Safe, wo der Worker sie liest
        requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={"role": "user", "content": user_command})
        st.success("Befehl in Cloud-Safe repliziert!")
        st.rerun()

if chat_data:
    for msg in sorted(chat_data, key=lambda x: x['id'])[-3:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

st.markdown("---")
st.write("### 📜 Live-Positionen (Multitasking)")
if trades_data:
    st.dataframe(pd.DataFrame(trades_data), use_container_width=True)

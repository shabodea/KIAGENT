import os
import time
import requests
from datetime import datetime

SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

FIXED_LEVERAGE = 10

def get_supabase_data(table):
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def insert_supabase_data(table, data):
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, json=data)
    except:
        pass

def update_supabase_data(table, row_id, data):
    try:
        requests.patch(f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{row_id}", headers=HEADERS, json=data)
    except:
        pass

def fetch_kraken_derivatives():
    # Liste aller Hebel-Assets auf Kraken, die nacheinander abgefahren werden
    return ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "LINK/USDT:USDT", "DOT/USDT:USDT"]

def process_chat_commands():
    messages = get_supabase_data("chat_messages")
    if messages:
        latest_msg = sorted(messages, key=lambda x: x['id'])[-1]
        if latest_msg["role"] == "user":
            print(f"Befehl erhalten: {latest_msg['content']}")
            bot_reply = {
                "role": "assistant",
                "content": f"🦅 **Cloud-Zentrale:** Befehl '{latest_msg['content']}' empfangen. Passe den Nacheinander-Scan an."
            }
            insert_supabase_data("chat_messages", bot_reply)

def manage_active_trades():
    trades = get_supabase_data("trade_history")
    if trades:
        active_trades = [t for t in trades if t["status"] == "ACTIVE"]
        for trade in active_trades:
            outcome = time.time() % 2
            mem = get_supabase_data("bot_memory")[0]
            
            if outcome < 0.5:
                net_profit = float(trade["margin_usd"]) * 1.93
                update_supabase_data("trade_history", trade["id"], {"status": "WIN", "closed_at": datetime.now().isoformat(), "net_pnl": net_profit})
                update_supabase_data("bot_memory", mem["id"], {"current_balance": float(mem["current_balance"]) + net_profit, "total_profit_usd": float(mem["total_profit_usd"]) + net_profit})
            else:
                verlust = float(trade["margin_usd"]) + 0.70
                update_supabase_data("trade_history", trade["id"], {"status": "LOSS", "closed_at": datetime.now().isoformat(), "net_pnl": -verlust})
                update_supabase_data("bot_memory", mem["id"], {"current_balance": float(mem["current_balance"]) - verlust, "total_loss_usd": float(mem["total_loss_usd"]) + verlust})

print("🦅 24/7 Cloud-Worker im Dienst...")
assets = fetch_kraken_derivatives()
asset_index = 0

while True:
    try:
        # 1. Bestehende Trades prüfen & managen (Multitasking)
        manage_active_trades()
        # 2. Auf Chat-Befehle vom Handy reagieren
        process_chat_commands()
        
        # 3. Nächstes Asset scannen
        current_asset = assets[asset_index]
        print(f"🔍 Loop-Check: {current_asset}")
        
        # Simulierter Signal-Treffer
        if time.time() % 10 < 2:
            insert_supabase_data("trade_history", {
                "asset": current_asset, "direction": "LONG", "leverage": FIXED_LEVERAGE,
                "entry_price": 60000.0, "margin_usd": 10.00, "fees_usd": 0.70, "status": "ACTIVE",
                "rationale": "Orderbuch-Ungleichgewicht autonom erkannt."
            })
            
        asset_index = (asset_index + 1) % len(assets)
        time.sleep(30)
    except Exception as e:
        print(f"Fehler: {e}")
        time.sleep(10)

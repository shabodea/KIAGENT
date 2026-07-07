import requests
from config.settings import SUPABASE_URL, HEADERS

def get_all_data_live():
    """
    Fragt alle 4 Haupttabellen synchron aus Supabase ab.
    FEHLERBEHEBUNG: Cache-Buster (_ts) entfernt, da PostgREST ihn als Spalten-Filter interpretiert!
    """
    try:
        t = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=*", headers=HEADERS).json()
        c = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages?select=*", headers=HEADERS).json()
        r = requests.get(f"{SUPABASE_URL}/rest/v1/Risiko_Log?select=*", headers=HEADERS).json()
        k = requests.get(f"{SUPABASE_URL}/rest/v1/system_knowledge?select=*", headers=HEADERS).json()
        
        # Falls Supabase Fehler-Dictionaries statt Listen zurückgibt, Fallback aktivieren
        trades = t if isinstance(t, list) else []
        chat = c if isinstance(c, list) else []
        risiko = r if isinstance(r, list) else []
        knowledge = k if isinstance(k, list) else []
        
        return trades, chat, risiko, knowledge
    except Exception as e:
        print(f" Kritischer Datenbank-Verbindungsfehler: {e}")
        return [], [], [], []

def send_chat_message(role, content):
    """
    Sendet eine neue Nachricht (user oder assistant) an die chat_messages Tabelle.
    """
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/chat_messages", 
            headers=HEADERS, 
            json={"role": role, "content": content}
        )
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"Fehler beim Senden der Chat-Nachricht: {e}")
        return False

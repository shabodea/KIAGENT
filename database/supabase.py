import requests
from datetime import datetime

from config.settings import SUPABASE_URL, HEADERS


# ==================================================
# SUPABASE LIVE DATEN
# ==================================================

def get_all_data_live():

    try:

        timestamp = int(
            datetime.utcnow().timestamp()
        )


        trades_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/Handelsgeschichte",
            headers=HEADERS,
            params={
                "select": "*",
                "_ts": timestamp
            },
            timeout=10
        )


        chat_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/chat_messages",
            headers=HEADERS,
            params={
                "select": "*",
                "order": "id.asc",
                "_ts": timestamp
            },
            timeout=10
        )


        risiko_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/Risiko_Log",
            headers=HEADERS,
            params={
                "select": "*",
                "_ts": timestamp
            },
            timeout=10
        )


        knowledge_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/system_knowledge",
            headers=HEADERS,
            params={
                "select": "*",
                "_ts": timestamp
            },
            timeout=10
        )


        trades = trades_response.json()
        chat = chat_response.json()
        risiko = risiko_response.json()
        knowledge = knowledge_response.json()


        print(
            f"DB STATUS | Trades:{len(trades) if isinstance(trades,list) else 0} "
            f"Chat:{len(chat) if isinstance(chat,list) else 0}",
            flush=True
        )


        return (

            trades if isinstance(trades,list) else [],
            chat if isinstance(chat,list) else [],
            risiko if isinstance(risiko,list) else [],
            knowledge if isinstance(knowledge,list) else []

        )


    except Exception as e:


        print(
            f"🔥 Supabase Lesefehler: {e}",
            flush=True
        )


        return [], [], [], []



# ==================================================
# CHAT SCHREIBEN
# ==================================================

def send_chat_message(role, content):

    try:

        payload = {

            "role": role,
            "content": content,
            "created_at":
                datetime.utcnow().isoformat()

        }


        response = requests.post(

            f"{SUPABASE_URL}/rest/v1/chat_messages",

            headers={
                **HEADERS,
                "Prefer":
                "return=minimal"
            },

            json=payload,

            timeout=10

        )


        print(
            f"CHAT WRITE {role}: {response.status_code}",
            flush=True
        )


        return response.status_code in [
            200,
            201,
            204
        ]


    except Exception as e:


        print(
            f"🔥 Chat Schreibfehler: {e}",
            flush=True
        )


        return False

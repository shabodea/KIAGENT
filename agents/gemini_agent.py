import sys
import os
import requests


# ==================================================
# SYSTEM PFAD
# ==================================================

BASE_PATH = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)


# ==================================================
# IMPORTS
# ==================================================

from config.settings import GEMINI_API_KEY
from database.supabase import (
    get_all_data_live,
    send_chat_message
)


# ==================================================
# GEMINI CORE AGENT
# ==================================================

class GeminiCoreAgent:


    def __init__(self):

        self.model = "gemini-3.5"
        self.api_key = GEMINI_API_KEY

        print(
            f"🤖 Gemini Agent geladen: {self.model}",
            flush=True
        )


    # ==================================================
    # GEMINI API
    # ==================================================

    def execute_thought_cycle(self, user_prompt):

        try:

            trades, chat, risiko, knowledge = get_all_data_live()


            system_context = f"""

Du bist der zentrale KI-Agent eines Trading-Systems.

Deine Aufgaben:

- erkläre Marktbewegungen
- analysiere Trading-Entscheidungen
- überwache Risiken
- unterstütze den Nutzer
- lerne aus gespeicherten Erfahrungen

SYSTEMSTATUS:

Risiko:
{risiko}

Wissen:
{knowledge}

Letzte Trades:
{trades[:5] if trades else "Keine Trades"}

"""


            if not self.api_key:

                return "❌ GEMINI_API_KEY fehlt."


            url = (
                "https://generativelanguage.googleapis.com/"
                f"v1beta/models/{self.model}:generateContent"
                f"?key={self.api_key.strip()}"
            )


            payload = {

                "contents": [

                    {

                        "parts": [

                            {

                                "text":
                                system_context
                                +
                                "\n\nBenutzer Anfrage:\n"
                                +
                                user_prompt

                            }

                        ]

                    }

                ]

            }


            response = requests.post(
                url,
                json=payload,
                timeout=30
            )


            data = response.json()


            print(
                f"Gemini API Antwort: {data.keys()}",
                flush=True
            )


            if "candidates" not in data:

                return (
                    "❌ Gemini Fehler:\n"
                    +
                    str(data)
                )


            return (
                data["candidates"][0]
                ["content"]
                ["parts"][0]
                ["text"]
            )


        except Exception as e:

            return (
                f"❌ Denkprozess Fehler: {e}"
            )


    # ==================================================
    # LIVE CHAT
    # ==================================================

    def process_live_chat(self):

        try:

            print(
                "💬 Chatprüfung gestartet...",
                flush=True
            )


            _, chat, _, _ = get_all_data_live()


            print(
                f"Chat Inhalt: {chat}",
                flush=True
            )


            if not chat:

                print(
                    "Keine Chatnachrichten gefunden.",
                    flush=True
                )

                return False



            latest = sorted(
                chat,
                key=lambda x: x.get("id",0)
            )[-1]


            print(
                f"Letzte Nachricht: {latest}",
                flush=True
            )



            role = latest.get("role")


            if role != "user":

                print(
                    "Letzte Nachricht ist keine User Nachricht.",
                    flush=True
                )

                return False



            user_text = latest.get(
                "content",
                ""
            )


            if not user_text:

                return False



            print(
                f"🧠 Gemini verarbeitet: {user_text}",
                flush=True
            )



            answer = self.execute_thought_cycle(
                user_text
            )



            print(
                f"💬 Gemini Antwort: {answer[:200]}",
                flush=True
            )



            send_chat_message(
                "assistant",
                answer
            )



            print(
                "✅ Antwort in Supabase gespeichert.",
                flush=True
            )


            return True



        except Exception as e:


            print(
                f"🔥 Fehler im Chat-Prozess: {e}",
                flush=True
            )

            return False

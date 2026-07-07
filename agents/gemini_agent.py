import sys
import os
import requests
from datetime import datetime


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

        # Aktuelles Gemini Modell
        self.model = "gemini-3.5"

        self.api_key = GEMINI_API_KEY


        print(
            f"🤖 Gemini Agent geladen: {self.model}",
            flush=True
        )



    # ==================================================
    # GEMINI DENKPROZESS
    # ==================================================

    def execute_thought_cycle(self, user_prompt):


        try:


            trades, chat, risiko, knowledge = (
                get_all_data_live()
            )


            system_context = f"""

Du bist der zentrale KI-Agent eines Trading-Systems.

Deine Aufgaben:

- analysiere Marktdaten
- erkläre Trading-Entscheidungen
- überwache Risiken
- lerne aus gespeicherten Erfahrungen
- unterstütze den Benutzer

SYSTEM STATUS:

Risiko:
{risiko}

Wissen:
{knowledge}

Aktuelle Trades:
{trades[:5] if trades else "Keine Trades"}

"""


            if not self.api_key:

                return (
                    "❌ Kein GEMINI_API_KEY gefunden."
                )



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
                                "\n\nBenutzer:\n"
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



            if "candidates" not in data:

                return (
                    "❌ Gemini API Fehler:\n"
                    +
                    str(data)
                )



            answer = (
                data["candidates"][0]
                ["content"]
                ["parts"][0]
                ["text"]
            )


            return answer



        except Exception as e:


            return (
                f"❌ Denkprozess Fehler: {e}"
            )



    # ==================================================
    # CHAT ÜBERWACHUNG
    # ==================================================

    def process_live_chat(self):


        try:


            print(
                "🔎 Prüfe Chat...",
                flush=True
            )


            _, chat, _, _ = (
                get_all_data_live()
            )


            if not chat:


                print(
                    "Keine Nachrichten.",
                    flush=True
                )

                return



            latest = sorted(
                chat,
                key=lambda x:
                x.get("id", 0)
            )[-1]



            print(
                f"Letzte Nachricht: {latest}",
                flush=True
            )



            if latest.get("role") != "user":


                print(
                    "Keine neue User-Anfrage.",
                    flush=True
                )

                return



            user_text = (
                latest.get("content", "")
            )



            if not user_text:

                return



            print(
                f"🧠 Gemini denkt über: {user_text}",
                flush=True
            )



            answer = (
                self.execute_thought_cycle(
                    user_text
                )
            )



            print(
                "💬 Antwort erzeugt",
                flush=True
            )



            send_chat_message(
                "assistant",
                answer
            )



            print(
                "✅ Antwort gespeichert",
                flush=True
            )



        except Exception as e:


            print(
                f"🔥 Chat Fehler: {e}",
                flush=True
            )

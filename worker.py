import sys
import os
import time
import requests
from datetime import datetime

print("🛑 SYSTEM-TEST: Worker startet jetzt...", flush=True)

# Pfad-Wegweiser
ZENTRALER_PFAD = os.path.dirname(os.path.abspath(__file__))
if ZENTRALER_PFAD not in sys.path:
    sys.path.insert(0, ZENTRALER_PFAD)

try:
    from config.settings import HEADERS, SUPABASE_URL
    print(f"📡 Supabase-URL erfolgreich geladen: {SUPABASE_URL}", flush=True)
except Exception as e:
    print(f"❌ Kritischer Fehler beim Import der Config: {e}", flush=True)
    sys.exit(1)

if __name__ == "__main__":
    print("🚀 TEST-LOOP BEGONNEN. Schaue jetzt auf dein Streamlit-Dashboard!", flush=True)
    
    # Sende eine einmalige Test-Nachricht direkt an dein Dashboard
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={
            "role": "assistant", 
            "content": f"⚠️ SYSTEM-TEST: Das Triebwerk ist online! Zeitstempel: {datetime.now().strftime('%H:%M:%S')}"
        })
        print("📤 Test-Nachricht erfolgreich an Supabase gesendet!", flush=True)
    except Exception as e:
        print(f"❌ Senden an Supabase fehlgeschlagen: {e}", flush=True)

    # Einfacher Endlos-Loop, der die Logs füllen MUSS
    zaehler = 1
    while True:
        print(f"⏱️ Worker Lebenszeichen #{zaehler} - Zeit: {datetime.now().strftime('%H:%M:%S')}", flush=True)
        zaehler += 1
        time.sleep(5)

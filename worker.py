import os
import time
import requests

# Schlüssel aus dem Render-Tresor laden
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def ask_gemini(prompt_text):
    """Verbindet den Server direkt mit dem echten Google-Gemini-Gehirn"""
    if not GEMINI_API_KEY:
        return "⚠️ Fehler: Kein GEMINI_API_KEY auf Render hinterlegt!"
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        res_json = response.json()
        return res_json['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Ausfall im KI-Kortex: {str(e)}"

def process_chat_and_learning():
    """Liest deine Chat-Nachrichten, antwortet via Gemini und speichert gelerntes Wissen"""
    try:
        messages = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS).json()
        
        if messages and len(messages) > 0:
            # Sortiert nach ID, um die allerneueste Nachricht zu finden
            latest_msg = sorted(messages, key=lambda x: x.get('id', 0))[-1]
            
            # Wenn die letzte Nachricht von DIR (User) kam, muss die KI antworten!
            if latest_msg["role"] == "user":
                user_input = latest_msg["content"]
                print(f"📥 Neuer Input empfangen: '{user_input}'")
                
                system_context = (
                    "Du bist der autonome 10x Krypto-Trading-Agent. Du filterst das Wissen, das dir dein "
                    "Master gibt, ab, lernst daraus für deine künftigen Strategien und antwortest hochprofessionell, "
                    "präzise und interaktiv auf Deutsch. Formuliere am Ende deiner Antwort immer eine ultrakurze Kern-Lektion (max. 1 Satz), "
                    "die mit 'LEKTION:' beginnt."
                )
                
                full_prompt = f"{system_context}\n\nMaster schreibt: {user_input}"
                
                # Gemini berechnet die Antwort
                bot_response = ask_gemini(full_prompt)
                
                # 1. Antwort in den Chat schreiben
                requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={
                    "role": "assistant",
                    "content": bot_response
                })
                print("📤 Antwort erfolgreich im Chat gesendet!")
                
                # 2. Evolution: Extrahiere die Lektion und brenne sie ins unendliche Gedächtnis
                if "LEKTION:" in bot_response:
                    lesson = bot_response.split("LEKTION:")[-1].strip()
                    
                    mem_res = requests.get(f"{SUPABASE_URL}/rest/v1/bot_memory", headers=HEADERS).json()
                    if mem_res:
                        mem = mem_res[0]
                        current_lessons = mem.get("learned_lessons", [])
                        
                        if lesson not in current_lessons:
                            current_lessons.append(lesson)
                            requests.patch(f"{SUPABASE_URL}/rest/v1/bot_memory?id=eq.1", headers=HEADERS, json={
                                "learned_lessons": current_lessons[-10:]
                            })
                            print(f"💾 Evolution: Neue Lektion gespeichert: {lesson}")
    except Exception as e:
        print(f"Fehler beim Chat-Check: {e}")

# --- HAUPTPROGRAMM ---
print("🦅 Die voll funktionsfähige KI-Maschine läuft jetzt 24/7...")

while True:
    process_chat_and_learning()
    time.sleep(3)  # Alle 3 Sekunden die Datenbank prüfen

import os
from openai import OpenAI

# Wir holen den Key aus deiner Render-Variable
my_key = os.environ.get("OPENROUTER_API_KEY")

# Falls der Key leer ist, geben wir eine klare Fehlermeldung
if not my_key:
    raise ValueError("FEHLER: OPENROUTER_API_KEY wurde in Render nicht gefunden!")

# Wir initialisieren den Client
client = OpenAI(
    api_key=my_key,
    base_url="https://openrouter.ai/api/v1"
)
)

def get_trading_decision(market_data):
    """
    Fragt DeepSeek nach einer Handelsentscheidung und extrahiert das JSON.
    """
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1",
            messages=[
                {
                    "role": "system", 
                    "content": "Du bist ein Trading-Experte. Antworte AUSSCHLIESSLICH als valides JSON im Format: {'decision': 'BUY' oder 'SELL' oder 'HOLD', 'reasoning': 'Deine ausführliche Logik und Indikatoren-Analyse'}. Kein Text außerhalb des JSON."
                },
                {"role": "user", "content": f"Marktdaten: {market_data}"}
            ]
        )
        
        content = response.choices[0].message.content
        
        # Versuche das JSON aus dem Text zu extrahieren (falls DeepSeek Text drumherum schreibt)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            decision_data = json.loads(json_match.group(0))
            return decision_data
        else:
            # Fallback, falls kein JSON gefunden wurde
            return {"decision": "HOLD", "reasoning": "Fehler: Kein valides JSON von KI erhalten. Inhalt: " + content[:50]}
            
    except Exception as e:
        print(f"Fehler bei der KI-Anfrage: {e}")
        return {"decision": "HOLD", "reasoning": f"Systemfehler: {str(e)}"}

# Beispiel für die Integration in deinen Trading-Loop:
# decision_dict = get_trading_decision(market_data)
# buy_sell = decision_dict.get("decision")
# reason = decision_dict.get("reasoning")
# ... jetzt kannst du buy_sell und reason in deine Supabase-Tabelle schreiben!

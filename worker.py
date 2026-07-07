import os
import json
import re
from openai import OpenAI

# 1. API-Key Konfiguration
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "")

# 2. Client Initialisierung (OHNE die Klammer, die den Fehler verursacht)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1"
)

# 3. Funktion
def get_trading_decision(market_data):
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1",
            messages=[
                {"role": "system", "content": "Antworte NUR mit JSON: {'decision': 'BUY/SELL/HOLD', 'reasoning': '...'}"},
                {"role": "user", "content": f"Marktdaten: {market_data}"}
            ]
        )
        content = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"decision": "HOLD", "reasoning": "Kein JSON gefunden"}
    except Exception as e:
        print(f"Fehler: {e}")
        return {"decision": "HOLD", "reasoning": "Fehler"}

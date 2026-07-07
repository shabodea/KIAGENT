import os
from openai import OpenAI

# Wir verbinden uns jetzt mit OpenRouter
client = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

def get_trading_decision(market_data):
    response = client.chat.completions.create(
        model="deepseek/deepseek-r1",
        messages=[
            {"role": "system", "content": "Du bist ein Trading-Experte. Analysiere den Markt. Gib dein Ergebnis im JSON-Format: {'decision': 'BUY', 'reasoning': '...deine ausführliche Logik...'}"},
            {"role": "user", "content": f"Marktdaten: {market_data}"}
        ]
    )
    # Das extrahierte JSON wird jetzt in Supabase gespeichert
    return response.choices[0].message.content

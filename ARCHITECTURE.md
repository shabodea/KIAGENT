# KI Trading Agent - Software Architektur

## 1. Projektziel
Autonomes KI-System zur Marktanalyse, Strategieentwicklung und Simulation von Trading-Entscheidungen (24/7-Überwachung, Backtesting, Paper-Trading). 
*Wichtig:* Kein unkontrollierter Einsatz von Echtgeld. Maximales Risiko-Management.

## 2. Technologie-Stack
- Frontend: Streamlit Dashboard (`streamlit_app.py`)
- Backend: Python Core (`worker.py`)
- Hosting: Render (Backend), Streamlit Cloud (Frontend)
- Datenbank: Supabase PostgreSQL
- Daten-Pipeline: REST/CCXT (Kraken)
- KI: Gemini API (Modell: gemini-1.5-flash für Chat & Sentiment)

## 3. Projektregeln für die KI (PROMPT-RESTRIKTIONEN)
- **Niemals** bestehenden funktionierenden Code oder imports löschen.
- Keine Funktionen entfernen ohne ausdrückliche Zustimmung.
- Änderungen immer **abwärtskompatibel** und modular durchführen.
- Vor jeder Änderung den vorhandenen Code analysieren.
- Tabellennamen im Schema strikt einhalten: `public.Handelsgeschichte` (Trades), `public.chat_messages` (Chat-Protokoll, Spalten: id, role, content), `public.Risiko_Log` (Tageslimits), `public.system_knowledge` (Master-Gedächtnis).

## 4. Aktuelle Modulstruktur (Version 0.1)
- `streamlit_app.py`: Zentrales Cockpit, Risikomanagement-Anzeige, unblockierte Befehlszeile, Telemetrie-Logbuch.
- `worker.py`: Autonomes Hintergrund-Triebwerk auf Render (Datenbeschaffung, ATR-Positionsberechnung, Chat-Verarbeitung).

## 5. Entwicklungsablauf
1. Architektur prüfen -> 2. Betroffene Module nennen -> 3. Änderung planen -> 4. Modular erweitern -> 5. CHANGELOG.md aktualisieren.

# KI Trading Agent - Software Architektur & Master-Gedächtnis

## 1. Projektziel
Ein absolut autonomes KI-System zur Krypto-Marktanalyse, algorithmischen Strategieentwicklung und Simulation von Trading-Entscheidungen (24/7-Überwachung, Backtesting, Paper-Trading).
*Wichtig:* Striktes Risiko-Management. Kein unkontrollierter Einsatz von Kapital.

## 2. Server- & Host-Infrastruktur
- **Frontend (Das Cockpit):** Läuft auf Streamlit Cloud über die Datei `streamlit_app.py`.
- **Backend (Das Triebwerk):** Läuft als autonomer Dauerprozess auf Render über die Datei `worker.py`.
- **Datenbank:** Supabase PostgreSQL. Beide Systeme (Render & Streamlit) kommunizieren in Echtzeit über die Supabase REST-API.
- **Daten-Pipeline:** CCXT-Anbindung an die Krypto-Börse **Kraken**.

## 3. Technische API-Verbindungsdaten
Jeder Bot muss diese exakten Endpunkte und Schlüssel für HTTP-Requests (GET/POST) nutzen:
- **Supabase URL:** `https://swyjycklcbcfhiafibar.supabase.co`
- **Supabase Key:** `sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4`
- **Headers für Requests:**
  ```json
  {
    "apikey": "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4",
    "Authorization": "Bearer sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4",
    "Content-Type": "application/json"
  }

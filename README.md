# 🦅 KIAgent - Autonomer KI-Trading-Broker

Dieses Repository enthält ein modulares, KI-gestütztes Handelssystem, das Marktdaten analysiert, Sentiment-Recherchen durchführt und autonome Handelsentscheidungen simuliert.

## 📁 Projektstruktur & Gedächtnis
Das Projekt wird strikt über ein KI-Gedächtnis-Framework gesteuert. Jede KI, die an diesem Repository arbeitet, muss sich zwingend an die Master-Dateien halten:
- `ARCHITECTURE.md` - Technische Struktur, Tabellenschemata und API-Verbindungen.
- `RULES.md` - Unumstößliche Verhaltens- und Programmierregeln für die KI.
- `CHANGELOG.md` - Historie aller vorgenommenen Änderungen.
- `ROADMAP.md` - Die langfristige Vision und Phasenplanung des Projekts.
- `TODO.md` - Aktuelle offene Tasks der laufenden Sitzung.
- `PROMPTS.md` - Master-Anweisungen für den Systemstart.

## 🚀 Infrastruktur
- **Cockpit (Frontend):** Streamlit Cloud (`streamlit_app.py`)
- **Triebwerk (Backend):** Render Dauerprozess (`worker.py`)
- **Datenbank:** Supabase (PostgreSQL REST-API)

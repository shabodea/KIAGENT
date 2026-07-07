# 🛡️ Unumstößliche KI-Entwicklungsregeln (RULES.md)

Dieses Dokument definiert die Sicherheitsgrenzen für die künstliche Intelligenz. Eine Verletzung dieser Regeln führt zum Systemkonflikt.

## ❌ NIEMALS:
1. Bestehenden, funktionierenden Code oder funktionierende Logiken löschen.
2. Funktionen ohne ausdrückliche Autorisierung des Masters umbenennen oder entfernen.
3. Imports (`import ...`) oder Konfigurationsvariablen löschen, nur weil sie temporär ungenutzt scheinen.
4. API-Keys, Tabellennamen oder Endpunkte eigenmächtig abändern oder eindeutschen.
5. Das Streamlit-Dashboard-Layout so verändern, dass Steuerelemente doppelt generiert werden (`StreamlitDuplicateElementId`).

##  IMMER:
1. Vor jeder Code-Generierung die gesamte betroffene Datei analysieren.
2. Vollständigen, fehlerfreien und abwärtskompatiblen Code ausgeben.
3. Jede Änderung sofort im `CHANGELOG.md` festhalten.
4. Nach erfolgreichem Code-Design die `TODO.md` aktualisieren.
5. Fehler präzise mathematisch oder syntaktisch erklären, statt Annahmen zu treffen.

## 🛑 BEI UNSICHERHEIT:
Stoppen. Keine Code-Generierung durchführen. Den Master um Klarstellung bitten.

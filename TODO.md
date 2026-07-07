# 📝 Aktuelle offene Aufgaben (TODO.md)

*Hinweis für die KI: Dieses Dokument muss nach jeder erfolgreichen Sitzung aktualisiert werden.*

## 🛑 Höchste Priorität (Fehlerbehebung)
- [ ] `worker.py`: Beheben des Einrückungsproblems (`SyntaxError: 'return' outside function`) in der Funktion `get_live_kraken_markets`.
- [ ] `streamlit_app.py`: Verifizieren, dass der `StreamlitDuplicateElementId`-Fehler nach der Dateibereinigung und dem Hard-Reboot dauerhaft gelöscht bleibt.

## ⚙️ Optimierung
- [ ] Überprüfung, ob das System-Gedächtnis aus `public.system_knowledge` stabil von der App geladen wird.
- [ ] Implementierung eines automatischen Re-Connects bei Supabase-Verbindungsabbrüchen.

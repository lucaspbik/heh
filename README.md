# Lagerverwaltungssystem für Maschinenbauunternehmen

Dieses Projekt stellt ein leichtgewichtiges Lagerverwaltungssystem (Warehouse Management System, WMS) für Maschinenbauunternehmen bereit. Es kombiniert ein webbasiertes Bedien-Interface mit einer REST-API und einer Schnittstelle für ein angebundenes ERP-System.

## Funktionen

- Verwaltung von Artikeln mit Stammdaten wie Artikelnummer, Beschreibung, Einheit und Meldebestand
- Pflege von Lagerorten und Beständen pro Artikel/Lagerort
- Erfassung von Wareneingängen, Warenausgängen und Bestandskorrekturen inklusive Historie
- Verwaltung von Lieferanten und Bestellungen (inklusive Bestellpositionen)
- Dashboard mit Kennzahlen, Bestandswarnungen und jüngsten Bewegungen
- REST-API zur Integration mit anderen Anwendungen
- ERP-Schnittstelle zum Export des aktuellen Bestands und zum Import offener Bestellungen

## Projektstruktur

```
app/
  api/              # REST-API-Router und Endpunkte
  templates/        # Jinja2 Templates für die Weboberfläche
  static/           # Statische Assets wie CSS
```

## Installation & Start

1. Virtuelle Umgebung erstellen und aktivieren (optional)
2. Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

3. Server starten:

```bash
uvicorn app.main:app --reload
```

4. Weboberfläche im Browser unter `http://127.0.0.1:8000` öffnen.

## Konfiguration der ERP-Schnittstelle

Die Kommunikation mit einem externen ERP-System lässt sich über Umgebungsvariablen konfigurieren. Unterstützte Variablen:

- `WMS_ERP_BASE_URL`: Basis-URL des ERP-Endpunkts (z. B. `https://erp.example.com/api`)
- `WMS_ERP_API_KEY`: Optionaler API-Key zur Authentifizierung

Werden keine Werte gesetzt, bleibt die ERP-Schnittstelle aktiv, sendet aber keine externen Requests und liefert aussagekräftige Hinweise zurück.

## Tests & Qualitätssicherung

Zur schnellen Syntax-Prüfung kann `python -m compileall app` ausgeführt werden. Für weiterführende Tests lassen sich auf Basis der REST-API eigene Testfälle ergänzen.

## Datenbank

Standardmäßig wird eine SQLite-Datenbank (`warehouse.db`) im Projektverzeichnis genutzt. Für produktive Setups kann die Verbindung über die Umgebungsvariable `DATABASE_URL` auf andere Datenbanken (z. B. PostgreSQL) umgestellt werden.


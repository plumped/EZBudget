# ezbudget

Ein einfaches, aktives Haushaltsbuch — Alternative zu Actual Budget / Firefly III,
mit CAMT.053-Import und einem eingebauten "Schuldenberater".

## Konzept

- **Umschlag-Budgetierung (Envelope/Zero-Based)** für Fixkosten, variable Kosten,
  Sparen und Schuldentilgung. Jeder Franken bekommt einen Umschlag.
- **CAMT.053-Import** (ISO-20022-Kontoauszüge deiner Bank) mit automatischer
  Duplikaterkennung und stichwortbasierter Auto-Zuordnung zu Umschlägen.
- **Schuldenabbau-Modul** simuliert einen monatlichen Tilgungsplan nach
  **Avalanche** (höchster Zins zuerst, spart am meisten Geld) oder
  **Snowball** (kleinste Restschuld zuerst, schnelle Erfolgserlebnisse) und
  zeigt ein realistisches "schuldenfrei am ..."-Datum.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python3 manage.py migrate
python3 manage.py createsuperuser   # eigenen Admin-Login anlegen

# optional: Demo-Daten (2 Konten, 11 Umschläge, Buchungen, 3 Schulden)
python3 manage.py seed_demo

python3 manage.py runserver
```

Dann [http://127.0.0.1:8000/](http://127.0.0.1:8000/) öffnen.
Die Django-Admin unter `/admin/` dient aktuell zum Anlegen von Konten und
Umschlägen (eigene Formulare dafür sind ein sinnvoller nächster Schritt).

Mitgeliefertes Beispiel für den CAMT.053-Import: `sample_data/beispiel_camt053.xml`.

## Projektstruktur

```
ezbudget/          Projekt-Settings, URLs
core/               Konten, Umschläge (Category), Buchungen (Transaction)
debts/               Schulden, Zahlungen, Avalanche/Snowball-Simulation (services.py)
imports_camt/        CAMT.053-Parser (camt053.py) + Upload/Vorschau/Bestätigen-Flow
templates/            Ledger-Design (eigenes CSS, kein Framework), Chart.js für den Tilgungsverlauf
```

## Was als Nächstes sinnvoll wäre

- Eigene Formulare für Konten/Umschläge (statt Django-Admin)
- Monats-Rollover-Logik für Umschläge (bisher: reiner Monatsreset ohne Übertrag)
- Wiederkehrende Buchungen / Fixkosten automatisch generieren
- Mehrbenutzer-/Auth-Flow (aktuell ein einzelner Admin-Login für den MVP)
- CAMT.053-Testdateien mit weiteren Bank-Exportvarianten (z.B. camt.053.001.08)
- Unit-Tests für Parser und Tilgungssimulation (aktuell manuell verifiziert)

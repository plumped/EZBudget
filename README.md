# ezbudget

Ein einfaches, aktives Haushaltsbuch — Alternative zu Actual Budget / Firefly III,
mit CAMT.053-Import und einem eingebauten "Schuldenberater".

## 1. Konzept

- **Umschlag-Budgetierung (Envelope/Zero-Based)** für Fixkosten, variable Kosten,
  Sparen und Schuldentilgung. Jeder Franken bekommt einen Umschlag — nicht verbrauchtes
  Budget wird automatisch in den nächsten Monat übertragen (siehe [4.2](#42-umschlag-übertrag-rollover)).
- **CAMT.053-Import** (ISO-20022-Kontoauszüge deiner Bank) mit automatischer
  Duplikaterkennung und stichwortbasierter Auto-Zuordnung zu Umschlägen. Der Parser ist
  tolerant gegenüber Namespace- und Strukturvarianten verschiedener Banken
  (z.B. camt.053.001.02 vs. camt.053.001.08, `Dt` vs. `DtTm`, verschachteltes vs.
  direktes `AddtlNtryInf`).
- **Wiederkehrende Buchungen** für Fixkosten, Abos und Lohn: einmal als Dauerauftrag
  angelegt, werden fällige Buchungen automatisch generiert (siehe [4.3](#43-wiederkehrende-buchungen)).
- **Schuldenabbau-Modul** simuliert einen monatlichen Tilgungsplan nach
  **Avalanche** (höchster Zins zuerst, spart am meisten Geld) oder
  **Snowball** (kleinste Restschuld zuerst, schnelle Erfolgserlebnisse) und
  zeigt ein realistisches "schuldenfrei am ..."-Datum.
- **Login-pflichtig**: jedes Haushaltsmitglied bekommt einen eigenen Account und
  sieht dasselbe gemeinsame Budget (siehe [4.4](#44-auth-flow)).

## 2. Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python3 manage.py migrate
python3 manage.py createsuperuser   # optional: Admin-Login für /admin/

# optional: Demo-Daten (2 Konten, 11 Umschläge, Buchungen, 3 Schulden, 4 Daueraufträge)
python3 manage.py seed_demo

python3 manage.py runserver
```

Dann [http://127.0.0.1:8000/](http://127.0.0.1:8000/) öffnen und über **/signup/** ein
eigenes Login anlegen (oder mit dem Superuser einloggen). Konten, Umschläge und
Daueraufträge lassen sich direkt in der App verwalten; `/admin/` bleibt als
zusätzliches Werkzeug für Detailarbeiten nutzbar.

Wiederkehrende Buchungen werden beim Öffnen der Übersicht automatisch generiert.
Für einen Cronjob (z.B. täglich um Mitternacht) steht zusätzlich an:

```bash
python3 manage.py generate_recurring
```

Mitgeliefertes Beispiel für den CAMT.053-Import: `sample_data/beispiel_camt053.xml`
sowie zwei weitere Bank-Exportvarianten in `sample_data/` (siehe [4.5](#45-camt053-bank-exportvarianten)).

## 3. Projektstruktur

```
ezbudget/          Projekt-Settings, URLs
core/               Konten, Umschläge (Category), Buchungen (Transaction),
                     wiederkehrende Buchungen (RecurringTransaction), Auth-Views
debts/               Schulden, Zahlungen, Avalanche/Snowball-Simulation (services.py)
imports_camt/        CAMT.053-Parser (camt053.py) + Upload/Vorschau/Bestätigen-Flow
templates/            Ledger-Design (eigenes CSS, kein Framework), Chart.js für den Tilgungsverlauf
sample_data/          Beispiel- und Test-CAMT.053-Dateien verschiedener Bank-Varianten
```

## 4. Umgesetzte Themen

Nummerierter Überblick über die zuletzt umgesetzten Aufgaben (vormals unter
"Was als Nächstes sinnvoll wäre" gelistet):

### 4.1 Eigene Formulare für Konten/Umschläge

Konten (`/accounts/`) und Umschläge (`/envelopes/`) lassen sich jetzt direkt in der App
anlegen, bearbeiten und archivieren/reaktivieren (`core/forms.py`, `core/views.py`).
Die Django-Admin bleibt zusätzlich nutzbar, ist für den Alltag aber nicht mehr nötig.

### 4.2 Umschlag-Übertrag (Rollover)

`Category.rollover_balance(year, month)` (`core/models.py`) kumuliert seit Anlage des
Umschlags Budget minus Ausgaben über alle Monate bis zum Zielmonat — nicht verbrauchtes
Geld bleibt im Umschlag, statt monatlich zu verfallen. Umschlag-Liste und -Detailansicht
zeigen sowohl den reinen Monatswert als auch den Saldo inklusive Übertrag.

*Hinweis:* Der Übertrag rechnet rückwirkend mit dem aktuell hinterlegten Monatsbudget,
nicht mit einer historischen Budgethöhe pro Monat — für das MVP ausreichend, aber keine
rückwirkend exakte Budget-Historie (siehe [Kapitel 5](#5-nächste-schritte)).

### 4.3 Wiederkehrende Buchungen

Neues Modell `RecurringTransaction` (Konto, Umschlag, Betrag, Tag im Monat, aktiv/pausiert)
plus `core/services.py::generate_due_recurring()`: erzeugt für jede fällige Vorlage genau
eine Buchung pro Monat (Duplikatschutz über `import_ref`). Läuft automatisch beim Laden
der Übersicht sowie manuell über "Jetzt generieren" unter `/recurring/` oder per
Management-Command `generate_recurring` (z.B. für Cron).

### 4.4 Auth-Flow

Login (`/login/`), Logout (`/logout/`) und Selbstregistrierung (`/signup/`) über
`django.contrib.auth`; alle Views sind mit `@login_required` geschützt
(`LOGIN_URL` in `ezbudget/settings.py`). Statt eines einzelnen Admin-Logins kann jedes
Haushaltsmitglied ein eigenes Konto anlegen — alle eingeloggten Nutzer teilen sich
weiterhin dasselbe Budget (keine Datentrennung pro Nutzer, siehe [Kapitel 5](#5-nächste-schritte)).

### 4.5 CAMT.053-Bank-Exportvarianten

Zwei weitere Beispieldateien in `sample_data/` decken zusätzliche Strukturvarianten ab:

- `camt053_001_08_ubs_variante.xml` — camt.053.001.08, `DtTm` statt `Dt`, mehrere
  `<Stmt>`-Blöcke, fehlende `AcctSvcrRef` (Fallback-Hash-Referenz).
- `camt053_001_02_postfinance_variante.xml` — camt.053.001.02, Fremdwährungsbuchung,
  `AddtlNtryInf` direkt unter `<Ntry>` statt verschachtelt.

Die zweite Variante deckte eine echte Parser-Lücke auf (`AddtlNtryInf` wurde nur als
direktes Kind von `<Ntry>` gefunden, nicht verschachtelt unter `NtryDtls/TxDtls`) —
`imports_camt/camt053.py` wurde entsprechend robuster gemacht.

### 4.6 Unit-Tests

- `imports_camt/tests.py`: Parser gegen alle drei Beispieldateien, Fehlerfälle
  (ungültiges XML, fehlendes `<Stmt>`), stichwortbasierte Auto-Zuordnung.
- `debts/tests.py`: Avalanche- vs. Snowball-Priorisierung, Zinseszins, Wirkung von
  Extra-Budget, "schuldenfrei am ..."-Datum, Abbruch bei `max_months`.
- `core/tests.py`: Kontostand, Umschlag-Übertrag über mehrere Monate, wiederkehrende
  Buchungen (Generierung, Idempotenz, pausierte Vorlagen), Login-Pflicht.

```bash
python3 manage.py test
```

## 5. Nächste Schritte

1. **Mehrbenutzer-Datentrennung**: aktuell teilen sich alle eingeloggten Nutzer ein
   gemeinsames Budget (passend für einen Haushalt) — getrennte Budgets pro Nutzer/Gruppe
   wären ein separates, größeres Feature.
2. **Historische Budgethöhen** für einen rückwirkend exakten Umschlag-Übertrag, statt mit
   dem aktuellen Monatsbudget zu rechnen.
3. Weitere CAMT.053-/CAMT.054-Exportvarianten anderer Banken und Länder bei Bedarf ergänzen.
4. Benachrichtigungen (E-Mail) bei Budgetüberschreitung oder anstehenden Daueraufträgen.

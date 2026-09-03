# ezbudget

Ein einfaches, aktives Haushaltsbuch — Alternative zu Actual Budget / Firefly III,
mit CAMT.053-Import und einem eingebauten "Schuldenberater".

## 1. Konzept

- **Umschlag-Budgetierung (Envelope/Zero-Based)** für Fixkosten, variable Kosten,
  Sparen und Schuldentilgung. Jeder Franken bekommt einen Umschlag — nicht verbrauchtes
  Budget wird automatisch in den nächsten Monat übertragen (siehe [5.2](#52-umschlag-übertrag-rollover)).
- **CAMT.053-Import** (ISO-20022-Kontoauszüge deiner Bank) mit automatischer
  Duplikaterkennung und stichwortbasierter Auto-Zuordnung zu Umschlägen. Der Parser ist
  tolerant gegenüber Namespace- und Strukturvarianten verschiedener Banken
  (z.B. camt.053.001.02 vs. camt.053.001.08, `Dt` vs. `DtTm`, verschachteltes vs.
  direktes `AddtlNtryInf`).
- **Wiederkehrende Buchungen** für Fixkosten, Abos und Lohn: einmal als Dauerauftrag
  angelegt, werden fällige Buchungen automatisch generiert (siehe [5.3](#53-wiederkehrende-buchungen)).
- **Schuldenabbau-Modul** simuliert einen monatlichen Tilgungsplan nach
  **Avalanche** (höchster Zins zuerst, spart am meisten Geld) oder
  **Snowball** (kleinste Restschuld zuerst, schnelle Erfolgserlebnisse) und
  zeigt ein realistisches "schuldenfrei am ..."-Datum, inklusive Tilgungsverlauf-Chart.
- **Login-pflichtig**: jedes Haushaltsmitglied bekommt einen eigenen Account und
  sieht dasselbe gemeinsame Budget (siehe [5.4](#54-auth-flow)).
- **React-Oberfläche**: eine von Django komplett getrennte Single-Page-Application
  (React + TypeScript), die über eine JSON-API mit dem Backend spricht
  (siehe [2. Architektur](#2-architektur)).

## 2. Architektur

ezbudget ist in zwei unabhängige Teile getrennt:

- **Backend** (`/`): Django + [Django REST Framework](https://www.django-rest-framework.org/)
  unter `/api/…`. Reine JSON-API, kein Server-Side-Rendering mehr. Auth läuft
  session-/cookie-basiert (kein JWT) — einfacher fürs MVP, inkl. CSRF-Schutz für
  schreibende Requests. Die komplette Business-Logik (Umschlag-Übertrag,
  Tilgungssimulation, CAMT.053-Parser, wiederkehrende Buchungen) lebt unverändert
  in Python und ist über die Django-Tests abgesichert.
- **Frontend** (`frontend/`): React 19 + TypeScript, gebaut mit [Vite](https://vite.dev/).
  Eigenständiges, handgeschriebenes CSS-Design-System (**kein Tailwind**) —
  React Router für Client-Side-Routing, Axios als API-Client.

Im Dev-Betrieb laufen beide Server parallel: Django auf Port 8000, Vite auf Port 5173.
Der Vite-Dev-Server reicht alle `/api`-Requests transparent an Django weiter
(`frontend/vite.config.ts`), wodurch der Browser alles als **gleiche Origin** sieht —
Cookies und CSRF funktionieren dadurch im Dev-Betrieb ohne CORS-Klimmzüge. Für andere
Setups (z.B. Frontend und Backend auf getrennten Domains) sind CORS und
`CSRF_TRUSTED_ORIGINS` in `ezbudget/settings.py` zusätzlich konfiguriert.

Für den produktiven Einsatz gibt es noch keinen fertigen Single-Server-Aufbau
(`npm run build` erzeugt `frontend/dist/`, das über einen eigenen Static-Server oder
Reverse-Proxy vor Django ausgeliefert werden müsste) — siehe [6. Nächste Schritte](#6-nächste-schritte).

## 3. Setup

### 3.1 Backend

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

Das Backend läuft danach auf [http://127.0.0.1:8000/](http://127.0.0.1:8000/) — die
JSON-API unter `/api/…`, die Django-Admin weiterhin unter `/admin/`.

Wiederkehrende Buchungen werden bei jedem Laden der Übersicht automatisch generiert.
Für einen Cronjob (z.B. täglich um Mitternacht) steht zusätzlich an:

```bash
python3 manage.py generate_recurring
```

### 3.2 Frontend

In einem zweiten Terminal, bei laufendem Backend:

```bash
cd frontend
npm install
npm run dev
```

Dann [http://localhost:5173/](http://localhost:5173/) öffnen und über **„Jetzt
registrieren“** ein eigenes Login anlegen (oder mit dem Django-Superuser einloggen).
Konten, Umschläge und Daueraufträge lassen sich direkt in der App verwalten;
`/admin/` bleibt als zusätzliches Werkzeug für Detailarbeiten nutzbar.

Mitgeliefertes Beispiel für den CAMT.053-Import: `sample_data/beispiel_camt053.xml`
sowie zwei weitere Bank-Exportvarianten in `sample_data/` (siehe [5.5](#55-camt053-bank-exportvarianten)).

## 4. Projektstruktur

```
ezbudget/            Projekt-Settings, URL-Routing (/api/…), DRF-/CORS-Konfiguration
core/                 Konten, Umschläge (Category), Buchungen (Transaction), wiederkehrende
                       Buchungen (RecurringTransaction); serializers.py + api_views.py + api_urls.py
debts/                Schulden, Zahlungen, Avalanche/Snowball-Simulation (services.py) + REST-API
imports_camt/         CAMT.053-Parser (camt053.py) + zustandslose Parse-/Bestätigen-API
sample_data/          Beispiel- und Test-CAMT.053-Dateien verschiedener Bank-Varianten

frontend/             React 19 + TypeScript (Vite) — eigenes CSS-Design-System, kein Tailwind
  src/api/              Axios-Client (client.ts), TypeScript-Typen (types.ts), Fehler-Helper
  src/context/          AuthContext (Login/Signup/Logout), ToastContext (Meldungen)
  src/components/       Layout/Sidebar, geteilte UI-Bausteine (Badges, Progress-Bar, Chart, ...)
  src/pages/            Eine Seite pro Route (Dashboard, Umschläge, Buchungen, Konten,
                         Daueraufträge, Schulden, Import)
```

## 5. Umgesetzte Themen

Nummerierter Überblick über die zuletzt umgesetzten Aufgaben:

### 5.1 Eigene Formulare für Konten/Umschläge

Konten (`/accounts`) und Umschläge (`/envelopes`) lassen sich direkt im React-Frontend
anlegen, bearbeiten und archivieren/reaktivieren — über die REST-Endpunkte
`/api/accounts/…` und `/api/categories/…`. Die Django-Admin bleibt zusätzlich nutzbar,
ist für den Alltag aber nicht mehr nötig.

### 5.2 Umschlag-Übertrag (Rollover)

`Category.rollover_balance(year, month)` (`core/models.py`) kumuliert seit Anlage des
Umschlags Budget minus Ausgaben über alle Monate bis zum Zielmonat — nicht verbrauchtes
Geld bleibt im Umschlag, statt monatlich zu verfallen. Umschlag-Liste und -Detailansicht
zeigen sowohl den reinen Monatswert als auch den Saldo inklusive Übertrag.

*Hinweis:* Der Übertrag rechnet rückwirkend mit dem aktuell hinterlegten Monatsbudget,
nicht mit einer historischen Budgethöhe pro Monat — für das MVP ausreichend, aber keine
rückwirkend exakte Budget-Historie (siehe [6. Nächste Schritte](#6-nächste-schritte)).

### 5.3 Wiederkehrende Buchungen

Modell `RecurringTransaction` (Konto, Umschlag, Betrag, Tag im Monat, aktiv/pausiert)
plus `core/services.py::generate_due_recurring()`: erzeugt für jede fällige Vorlage genau
eine Buchung pro Monat (Duplikatschutz über `import_ref`). Läuft automatisch beim Laden
der Übersicht sowie manuell über "Jetzt generieren" unter `/recurring` oder per
Management-Command `generate_recurring` (z.B. für Cron).

### 5.4 Auth-Flow

Login, Logout und Selbstregistrierung über `django.contrib.auth` (Session-Cookies) mit
eigenen React-Seiten (`/login`, `/signup`) statt Django-Templates. Alle API-Endpunkte
sind per DRF `IsAuthenticated` geschützt, das Frontend leitet nicht eingeloggte
Besucher:innen automatisch zum Login um. Statt eines einzelnen Admin-Logins kann jedes
Haushaltsmitglied ein eigenes Konto anlegen — alle eingeloggten Nutzer teilen sich
weiterhin dasselbe Budget (keine Datentrennung pro Nutzer, siehe
[6. Nächste Schritte](#6-nächste-schritte)).

### 5.5 CAMT.053-Bank-Exportvarianten

Zwei weitere Beispieldateien in `sample_data/` decken zusätzliche Strukturvarianten ab:

- `camt053_001_08_ubs_variante.xml` — camt.053.001.08, `DtTm` statt `Dt`, mehrere
  `<Stmt>`-Blöcke, fehlende `AcctSvcrRef` (Fallback-Hash-Referenz).
- `camt053_001_02_postfinance_variante.xml` — camt.053.001.02, Fremdwährungsbuchung,
  `AddtlNtryInf` direkt unter `<Ntry>` statt verschachtelt.

Die zweite Variante deckte eine echte Parser-Lücke auf (`AddtlNtryInf` wurde nur als
direktes Kind von `<Ntry>` gefunden, nicht verschachtelt unter `NtryDtls/TxDtls`) —
`imports_camt/camt053.py` wurde entsprechend robuster gemacht.

### 5.6 Unit-Tests

- `imports_camt/tests.py`: Parser gegen alle drei Beispieldateien, Fehlerfälle
  (ungültiges XML, fehlendes `<Stmt>`), stichwortbasierte Auto-Zuordnung, plus
  API-Tests für Parse-/Bestätigen-/Historie-Endpunkte.
- `debts/tests.py`: Avalanche- vs. Snowball-Priorisierung, Zinseszins, Wirkung von
  Extra-Budget, "schuldenfrei am ..."-Datum, Abbruch bei `max_months`, plus API-Tests
  für Schulden-CRUD, Zahlungserfassung und den Tilgungsplan-Endpunkt.
- `core/tests.py`: Kontostand, Umschlag-Übertrag über mehrere Monate, wiederkehrende
  Buchungen (Generierung, Idempotenz, pausierte Vorlagen), Auth-Endpunkte
  (Signup/Login/Logout/Passwortvalidierung) sowie CRUD- und Filter-Verhalten der
  Accounts-/Categories-/Transactions-/Recurring-API.

```bash
python3 manage.py test
```

### 5.7 Backend zu REST-API umgebaut

Django liefert keine HTML-Templates mehr — alle bisherigen Views wurden durch
Django-REST-Framework-Serializer und -ViewSets ersetzt (`core/serializers.py` +
`core/api_views.py`, analog in `debts/` und `imports_camt/`). Der CAMT.053-Import
ist jetzt zustandslos: `/api/import/parse/` parst eine Datei und liefert die Vorschau
direkt als JSON zurück (keine serverseitige Session mehr nötig), `/api/import/confirm/`
legt die ausgewählten Buchungen an. Geldbeträge werden konsistent als Strings
serialisiert (nie als JSON-Float), um Rundungsfehler zu vermeiden.

### 5.8 Frontend komplett auf React + TypeScript umgestellt

Die komplette Oberfläche wurde von Django-Templates auf eine React-19-+-TypeScript-SPA
(Vite, React Router, Axios) umgebaut — bewusst **ohne Tailwind**: ein eigenes,
handgeschriebenes CSS-Design-System (`frontend/src/index.css`) mit CSS-Custom-Properties
für Farben/Radien/Schatten. Der Tilgungsverlauf-Chart ist eine kleine, selbst
geschriebene Inline-SVG-Komponente (keine zusätzliche Chart-Bibliothek).

## 6. Nächste Schritte

1. **Historische Budgethöhen** für einen rückwirkend exakten Umschlag-Übertrag, statt mit
   dem aktuellen Monatsbudget zu rechnen.
2. **Produktions-Deployment**: Single-Server-Aufbau, der `frontend/dist/` (nach
   `npm run build`) über Django/WhiteNoise oder einen Reverse-Proxy vor die API schaltet,
   inkl. `DEBUG=False`, echtem `SECRET_KEY` und Postgres statt SQLite.
3. **Frontend-Tests**: bisher nur manuell/End-to-End verifiziert — Komponenten- bzw.
   Integrationstests (z.B. Vitest + Testing Library) wären ein sinnvoller nächster Schritt.

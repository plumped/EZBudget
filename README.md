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
  src/context/          AuthContext (Login/Signup/Logout), SettingsContext, ThemeContext (Dark-Mode), ToastContext
  src/components/       Layout/Sidebar, geteilte UI-Bausteine (Badges, Progress-Bar, Chart, ...)
  src/pages/            Eine Seite pro Route (Dashboard, Umschläge, Buchungen, Konten,
                         Daueraufträge, Schulden, Import, Transfer, ...)
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

### 5.9 Design-Überarbeitung mit dem ui-ux-pro-max-Skill

Das Farb-/Typografie-/Icon-System wurde mit dem lokalen Claude-Code-Skill
[`ui-ux-pro-max`](.claude/skills/ui-ux-pro-max/) (`nextlevelbuilder/ui-ux-pro-max-skill`,
MIT-lizenziert) recherchiert statt frei erfunden. Die Recherche und die daraus
resultierenden Entscheidungen sind in `design-system/ezbudget/MASTER.md` dokumentiert —
inklusive der Fälle, in denen ein automatischer Treffer verworfen wurde (der erste breite
Suchtreffer war ein Dark-OLED-Marketing-Landingpage-Pattern, das für eine eingeloggte
Finance-App nicht passt; gezielte Nachfragen lieferten die tatsächlich verwendeten Werte).

- **Farben/Style**: "Minimalism & Swiss Style" (Banking/Finance-Palette, Navy/Blue),
  automatischer Light-/Dark-Modus über `prefers-color-scheme`.
- **Typografie**: Lexend (Headings) + Source Sans 3 (Body) — "Corporate Trust"-Pairing,
  explizit für Finance/Accessibility empfohlen.
- **Icons**: Emoji-Chrome (Sidebar, Buttons, Toasts, Empty-States) durch
  [`@phosphor-icons/react`](https://phosphoricons.com/) ersetzt — das vom Skill als
  Anti-Pattern geflaggte "Emoji als Icon" betraf ursprünglich nur UI-Chrome, das frei
  wählbare Umschlag-Icon blieb zunächst bewusst Emoji als "Nutzerinhalt". Diese Ausnahme
  wurde später verworfen: die App verwendet jetzt konsequent Phosphor-Icons, auch für das
  Umschlag-Icon (siehe [5.16](#516-icon-katalog-für-umschläge)).
- **Barrierefreiheit**: Skeleton-Loading (`aria-busy`) statt reinem Text, strukturierte
  Formularfehler (`aria-describedby`/`aria-invalid` pro Feld statt einem Sammelfehler),
  Fokus-Management bei fehlgeschlagenem Submit, Toasts mit `role="status"`/`"alert"`,
  Text-Caption am Tilgungsverlauf-Chart (Trend nicht nur über Farbe erkennbar).

### 5.10 Historische Budgethöhen

`CategoryBudgetHistory` (`core/models.py`) speichert bei jeder echten Änderung von
`Category.monthly_budget` einen Snapshot ab dem jeweils gültigen Budget-Monat —
`Category.save()` schreibt den Eintrag automatisch, inklusive rückwirkender
Selbstheilung für Umschläge, die schon vor diesem Feature bestanden (ihr bisheriger
Wert wird beim ersten Wechsel danach am Erstellungsmonat verankert). `budget_for_month()`,
`rollover_balance()` und `progress_percent()` rechnen dadurch für vergangene Monate mit
dem damals gültigen statt dem aktuellen Budget. Der Verlauf ist über `budget_history` im
Umschlag-API sichtbar und wird auf der Umschlag-Detailseite als Tabelle angezeigt, sobald
sich das Budget mindestens einmal geändert hat.

### 5.11 Konto-zu-Konto-Transfer

`POST /api/transfers/` (`TransferView`) legt zwei verknüpfte, umschlaglose Buchungen an
(`Transaction.transfer_pair`, ein selbstreferenzierendes `OneToOneField` mit
`on_delete=CASCADE`) — Geld zwischen eigenen Konten verschieben, ohne es als Einnahme/Ausgabe
in Umschlägen oder im Dashboard-Total zu zählen (dort per `transfer_pair__isnull=True`
ausgeschlossen). Löschen einer Seite löscht automatisch beide. Eigene Seite unter
`/transactions/transfer`, Transfers erscheinen in der Buchungsliste mit "Transfer"-Badge
statt Umschlag.

### 5.12 Sparziel bei Umschlägen

Optionale Felder `target_amount`/`target_date` auf `Category` — der Fortschritt
(`target_progress_percent`) wird aus `rollover_balance()` (verfügbar inkl. Übertrag) gegen
das Ziel berechnet und auf der Umschlag-Detailseite als eigene Fortschrittsanzeige samt
Zieldatum dargestellt.

### 5.13 Wiederkehrende Buchungen: mehr Frequenzen

`RecurringTransaction.frequency` (wöchentlich / alle 2 Wochen / monatlich / jährlich) statt
nur "Tag im Monat" — je nach Frequenz greifen `weekday` (wöchentlich/2-wöchentlich),
`month_of_year` (jährlich) oder weiterhin `day_of_month`; `start_date` dient als Anker für den
2-Wochen-Rhythmus. `generate_due_recurring()` bestimmt Fälligkeit und Perioden-Schlüssel pro
Frequenz (`RecurringTransaction.is_due_on()`/`period_key()`); das monatliche Format ist
bewusst identisch zum bisherigen `import_ref` geblieben, damit bestehende Daten kompatibel
bleiben.

### 5.14 Buchungen-Suche/-Filter erweitern

Die Buchungen-API filtert zusätzlich per `search` (Freitext auf Beschreibung/Gegenpartei,
case-insensitive) sowie `date_from`/`date_to` — ein gesetzter Datumsbereich ersetzt dabei den
Monatsfilter, sodass über den aktuell gewählten Budget-Monat hinaus gesucht werden kann. Im
Frontend eine Filterleiste mit debounced Suchfeld und zwei Datumsfeldern oberhalb der
Buchungsliste.

### 5.15 Manueller Dark-Mode-Toggle

`ThemeContext` (`frontend/src/context/ThemeContext.tsx`) verwaltet System/Hell/Dunkel in
`localStorage` und setzt ein `data-theme`-Attribut auf `<html>`. `index.css` definiert die
Dark-Palette entsprechend doppelt: einmal unter `prefers-color-scheme: dark` (nur wenn kein
`data-theme="light"` gesetzt ist) und einmal unter `[data-theme="dark"]`, damit die manuelle
Wahl in beide Richtungen über die Systemeinstellung gewinnt. Umschaltbar unter
**Einstellungen → Darstellung**.

### 5.16 Icon-Katalog für Umschläge

`Category.icon` (bislang ein ungenutztes Feld) ist jetzt über `IconPicker`
(`frontend/src/components/IconPicker.tsx`) im Umschlag-Formular frei aus einem kuratierten,
nach Themen gruppierten Katalog wählbar (Finanzen, Essen & Haushalt, Wohnen, Verkehr,
Gesundheit, Freizeit & Familie, Sonstiges) — **Phosphor-Icons, kein Emoji**, damit
Umschlag-Icons genau wie der Rest der Oberfläche aussehen. Gespeichert wird der
`@phosphor-icons/react`-Exportname (z.B. `"ShoppingCart"`); `iconCatalog.ts` bildet die
zentrale Registry aus Katalog-Gruppen und Name-→-Komponente-Zuordnung, die sowohl
`IconPicker` als auch `KindIcon` verwenden. `KindIcon` rendert das gewählte Icon überall, wo
ein Umschlag auftaucht (Liste, Karten-Ansicht, Detailseite, Dashboard) — ohne Auswahl fällt
`Category.save()` serverseitig auf ein zur Art passendes Standard-Icon zurück
(`Category.KIND_ICON_DEFAULTS`, ebenfalls ein Phosphor-Name) statt pauschal dasselbe Icon für
alle Arten zu setzen. Eine erste Version dieses Features nutzte fälschlich Emoji (siehe
[5.9](#59-design-überarbeitung-mit-dem-ui-ux-pro-max-skill)) — eine spätere Migration hat
alle Umschläge auf die Phosphor-Namen umgestellt.

### 5.17 Trends & Insights

Neue Seite `/trends` (`TrendsPage.tsx`) über `GET /api/trends/?months=` (Default 12, max. 24
Budget-Monate zurück): Verlauf von Einnahmen/Ausgaben als Liniendiagramm (`TrendChart.tsx`,
eine generische Mehrfach-Serien-Variante des bestehenden Tilgungsverlauf-Charts — weiterhin
selbst geschriebenes Inline-SVG, keine Chart-Bibliothek), ein Jahresvergleich (aktueller Monat
vs. derselbe Monat im Vorjahr, für Einnahmen und Ausgaben), eine Top-Ausgaben-Rangliste über
den Zeitraum sowie ein wählbarer Ausgabenverlauf pro Umschlag. `TrendsView`
(`core/api_views.py`) aggregiert dafür pro Monat im Zeitraum über `Category.spent_in_month()`
sowie Einnahmen-/Ausgaben-Summen (Transfers wie beim Dashboard ausgeschlossen).

### 5.18 Warnung bei unzugeordneten Buchungen

Das Dashboard zeigt eine Warnleiste, sobald im gewählten Monat Buchungen ohne Umschlag
existieren (`DashboardView` liefert `uncategorized_count`, ohne Transfers — die sind
absichtlich umschlaglos), mit Link direkt zu den gefilterten Buchungen. Der
Umschlag-Filter auf der Buchungen-Seite hat dafür eine neue Option "Ohne Umschlag"
(`category=none` in `TransactionViewSet.get_queryset()`), die auch per Deep-Link aus der
Warnung vorausgewählt wird.

### 5.19 Kreditkarten/laufende Kreditlinien als Schuld mit Konto-Verknüpfung

Eine Schuld lässt sich optional direkt mit einem Konto verknüpfen (`Debt.account`,
z.B. dem Kontotyp "Kreditkarte") — gedacht für eine laufende Kreditlinie, bei der
zusätzlich zu Zahlungen auch wieder neue Ausgaben dazukommen, statt nur getilgt zu
werden:

- **Ausgaben**: jede normale, mit einem echten Umschlag kategorisierte Buchung auf dem
  verknüpften Konto erhöht die Restschuld automatisch — Budget-Tracking bleibt dabei
  voll erhalten (Lebensmittel bleibt Lebensmittel, egal mit welcher Karte bezahlt).
- **Zahlungen**: ein normaler Transfer auf das verknüpfte Konto senkt die Restschuld
  automatisch; der manuelle "Zahlung erfassen"-Kurzweg (weiterhin der Standardweg für
  Schulden ohne Kontoverknüpfung, z.B. ein Privatdarlehen) ist für kontoverknüpfte
  Schulden gesperrt, um zwei parallele Buchungswege zu vermeiden.
- **Zins**: wird jetzt echt und automatisch verbucht statt nur in der
  Tilgungsplan-Simulation berücksichtigt — einmal pro Kalendermonat, ausgelöst beim
  Laden des Dashboards (`accrue_monthly_interest()` in `debts/services.py`, zusätzlich
  als Management-Command `accrue_debt_interest` für Cron). Bei einer Konto-Verknüpfung
  als echte, sichtbare Buchung auf diesem Konto (Duplikatschutz über `import_ref`, damit
  eine gelöschte Zinsbuchung im selben Monat erneut buchbar bleibt); ohne Verknüpfung
  direkt auf `current_balance` (Duplikatschutz über `last_interest_year`/`-month`, da
  keine echte Kontobewegung stattfindet).

`Transaction._linked_debts_with_deltas()` (`core/models.py`) verallgemeinert dafür die
bisherige, rein umschlagbasierte Verknüpfung: eine Buchung kann jetzt sowohl über ihren
Umschlag als auch über ihr Konto eine Schuld beeinflussen (mit invertiertem Vorzeichen,
da eine Ausgabe auf dem Konto die Restschuld erhöht statt senkt) — betrifft
ausnahmsweise beides dieselbe Schuld, zählt nur der Konto-Weg.

### 5.20 Kappungsgrenze für Zusatzzahlungen im Tilgungsplan-Rechner

Nicht jeder Kredit erlaubt beliebige Sondertilgungen: ein Ratenkredit mit fixem
Tilgungsplan (z.B. ein Cembra-Konsumkredit) lässt sich oft gar nicht oder nur bis zu
einem festen Betrag pro Monat zusätzlich zurückzahlen — anders als eine Kreditkarte, bei
der jede Zuzahlung willkommen ist. Der Avalanche/Snowball-Rechner (`simulate_payoff()` in
`debts/services.py`) hat das bisher ignoriert und ging von einem beliebig verteilbaren
Extra-Budget aus.

Jede Schuld hat jetzt ein optionales Feld `max_extra_payment` ("Maximale Zusatzzahlung /
Monat"): leer = unbegrenzt (Standard, passend für eine Kreditkarte), `0` = überhaupt keine
Zuzahlung über die Mindestrate hinaus möglich (ein fixer Ratenkredit). Der Rechner
berücksichtigt das bei der monatlichen Verteilung des Extra-Budgets:

- Was eine gedeckelte Schuld nicht aufnehmen darf, fliesst an die nächste Schuld in der
  Prioritätsreihenfolge (Avalanche/Snowball), statt einfach dort liegen zu bleiben.
- Was am Ende wirklich nirgends platziert werden kann — weil alle noch offenen Schulden
  gedeckelt sind —, wird als `unallocated_extra` im Simulationsergebnis gemeldet, statt
  still zu verschwinden. Auf der Schulden-Seite erscheint dafür ein Warnbanner mit dem
  betroffenen Betrag. Explizit **nicht** mitgezählt wird das übliche "Restgeld" im letzten
  Monat, wenn alle Schulden bereits vollständig getilgt sind — das ist kein blockierter
  Betrag, sondern schlicht frei gewordenes Budget.

### 5.21 Monatsende-Sweep-Vorschlag: nicht ausgegebenes Budget zur Tilgung nutzen

EZBudget ist ein reines Abbild der eigenen Finanzen — die App löst selbst keine
Überweisung aus, das bleibt immer Sache des Nutzers bei seiner Bank. Der
Sweep-Vorschlag hilft trotzdem beim schnelleren Schuldenabbau: Er zeigt, wie viel
Budget diesen Monat nicht ausgegeben wurde und wie sich dieser Betrag nach der
gewählten Strategie (Avalanche/Snowball, unter Beachtung von `max_extra_payment`,
siehe 5.20) auf die offenen Schulden verteilen liesse.

- `debts/services.py::eligible_envelope_surplus()` summiert den positiven
  `rollover_balance()` aller nicht archivierten Umschläge ausser Einnahmen,
  Schulden-Umschlägen selbst und Umschlägen mit eigenem Sparziel (`target_amount`) —
  wer für etwas anderes bewusst zurücklegt, wird nicht angetastet. Ein überzogener
  Umschlag mindert die Summe nicht (kein negativer Beitrag).
- `debts/services.py::allocate_extra_once()` verteilt diesen Betrag einmalig nach
  Priorität auf die Schulden — dieselbe Kappungs-/Rollover-Logik wie in
  `simulate_payoff()`, aber als eigenständige, einfachere Funktion für einen
  einzelnen Moment statt einer Mehrmonatssimulation.
- Neuer Endpoint `GET /api/debts/sweep-proposal/?strategy=...` liefert Gesamtbetrag,
  beitragende Umschläge und die vorgeschlagene Verteilung.
- Auf der Schulden-Seite erscheint bei verfügbarem Überschuss eine Karte mit der
  Verteilung und je Schuld einem Link "Zahlung erfassen" (führt zur Schuld, Betrag
  vorausgefüllt) — mit dem ausdrücklichen Hinweis, die Zahlung erst einzutragen,
  **nachdem** die Überweisung tatsächlich bei der Bank gemacht wurde. Ein Button
  übernimmt den Gesamtbetrag zusätzlich als Extra-Budget in den bestehenden
  Tilgungsplan-Rechner, um den Zinseffekt direkt sichtbar zu machen.
- **Zeitfenster**: `rollover_balance()` wächst im Lauf des Monats einfach an, weil
  noch nicht alles ausgegeben wurde — am 5. Tag des Monats wäre ein angezeigter
  "Überschuss" meist nur Geld, das man diesen Monat noch braucht, kein echter Rest.
  `debts/services.py::sweep_window_status()` berechnet deshalb, ob `heute` in den
  letzten `SWEEP_WINDOW_DAYS` (5) Tagen des aktuellen Budget-Monats liegt — nur dann
  liefert die Karte einen `in_window: true`-Flag, den das Frontend zum Anzeigen
  nutzt. Ausserhalb des Fensters bleibt die Karte komplett unsichtbar, statt eine
  verfrühte, potenziell irreführende Zahl zu zeigen.

### 5.22 Weiche Duplikat-Erkennung beim CAMT.053-Import (Datum + Betrag)

Trägt man eine Zahlung zuerst manuell ein (z.B. über "Zahlung erfassen" aus dem
Sweep-Vorschlag) und importiert später den Kontoauszug, der dieselbe Zahlung enthält,
erkannte der Import das bisher nicht als Duplikat: Die bestehende Prüfung vergleicht nur
die Bank-Referenznummer (`import_ref`), die eine manuell erfasste Buchung nie hat — die
Zahlung würde also doppelt gezählt (Restschuld und Kontostand sinken zweimal).

- `ImportParseView` markiert jetzt zusätzlich Zeilen mit `is_possible_duplicate`, wenn
  Datum und Betrag exakt mit einer bestehenden Buchung OHNE `import_ref` übereinstimmen.
  Als Multiset gezählt (`collections.Counter`), damit zwei unabhängige echte Buchungen am
  selben Tag mit demselben Betrag nicht beide fälschlich markiert werden — nur so viele
  wie tatsächlich passende bestehende Buchungen existieren.
  `is_duplicate` (Referenz-Treffer) bleibt unverändert die harte, sichere Prüfung.
- Anders als bei `is_duplicate` bleibt die Checkbox bei `is_possible_duplicate` bedienbar
  (nicht deaktiviert) und wird nur vorausgewählt abgewählt — reine Heuristik ohne
  Gewissheit, der Nutzer kann sie bei Bedarf trotzdem einschliessen. Badge "Evtl. schon
  erfasst?" statt "Duplikat" macht den Unterschied auch optisch klar.
- Der Hinweistext beim Erfassen einer Zahlung mit vorausgefülltem Betrag (aus dem
  Sweep-Vorschlag) macht jetzt explizit klar: entweder hier erfassen ODER später
  importieren, nicht beides.

### 5.23 "Schuldenfrei am ..." aufs Dashboard + Tilgungs-Meilensteine

Für jemanden, der sich aus Schulden rausarbeitet, soll das Zieldatum + der
Fortschritt das Allererste sein, was er beim Öffnen der App sieht — nicht erst nach
einem Klick auf /debts.

- `DashboardView` berechnet jetzt zusätzlich `debt_free_date` (via `simulate_payoff()`,
  bewusst nur mit den Mindestraten/`extra_budget=0` — die pessimistischste, aber
  garantierte Prognose ohne Zusatzzahlungen) und `overall_debt_progress_percent`
  (Summe `paid_so_far` / Summe `principal` über **alle** je erfassten Schulden,
  auch bereits komplett getilgte zählen ihren vollen Anteil mit). Beides erscheint
  jetzt direkt in der Schulden-Karte auf dem Dashboard.
- **Meilensteine** (25/50/75/100% einer einzelnen Schuld getilgt) sind bewusst
  zustandsbehaftet umgesetzt statt live aus `progress_percent` berechnet: neues Feld
  `Debt.last_milestone_reached` merkt sich den höchsten bereits gemeldeten
  Meilenstein, damit dieselbe Meldung nicht bei jedem Dashboard-Aufruf erneut
  auftaucht. `debts/services.py::check_new_milestones()` läuft bei jedem
  Dashboard-Load (wie schon `accrue_monthly_interest()`), meldet nur wirklich neu
  erreichte Meilensteine und aktualisiert dabei gleich den gespeicherten Stand.
  Springt eine Zahlung über mehrere Schwellen auf einmal, wird nur der höchste neu
  erreichte gemeldet. Eine komplett getilgte Schuld (`is_paid_off=True`) wird dabei
  nicht ausgeschlossen — sonst würde der wichtigste Meilenstein (100%) verloren
  gehen, genau in dem Moment, in dem die Schuld archiviert wird.
- Frontend zeigt neue Meilensteine als Erfolgs-Toast beim Laden des Dashboards.

### 5.24 Notfallfonds-Priorität vor Extra-Tilgung

Bewährtes Prinzip aus der Schuldenberatung: erst einen kleinen Puffer ansparen,
bevor man aggressiv Extra-Zahlungen auf Schulden macht — sonst landet man bei der
nächsten unerwarteten Rechnung wieder auf der Kreditkarte.

- Neues Feld `Category.is_emergency_fund` markiert einen Umschlag als Notfallfonds.
  Rein opt-in — ohne markierten Umschlag ändert sich am bisherigen Verhalten nichts.
  Es kann immer nur einer aktiv sein: `Category.save()` wählt einen zuvor markierten
  automatisch ab, sobald ein neuer gesetzt wird (wie eine Radio-Auswahl). Braucht
  zwingend ein gesetztes Sparziel (`target_amount`) — der Serializer lehnt
  `is_emergency_fund=True` ohne Zielbetrag ab, sonst gäbe es keine Lücke, die zuerst
  gefüllt werden müsste.
- `debts/services.py::emergency_fund_status()` berechnet die Lücke zum Sparziel
  (`target_amount - rollover_balance()`, nie negativ). Sowohl `simulate_payoff()`
  als auch `allocate_extra_once()` (Sweep-Vorschlag) nehmen jetzt ein
  `emergency_fund_gap`-Argument entgegen und füllen diese Lücke aus dem
  Extra-Budget/Überschuss zuerst, bevor irgendetwas an Schulden geht — im
  Tilgungsplan-Rechner über mehrere Monate hinweg als laufender Zustand
  (`emergency_fund_total`, `emergency_fund_filled_date` im Ergebnis), im
  Sweep-Vorschlag als einmaliger Abzug (`to_emergency_fund`).
- Frontend: neue Checkbox "Das ist mein Notfallfonds" im Umschlag-Formular; die
  Schulden-Seite zeigt einen Hinweis-Banner, solange der Fonds nicht voll ist, und
  der Sweep-Vorschlag listet die Notfallfonds-Zuteilung vor den Schulden-Zeilen.

### 5.25 Hilfe-Seite mit vollständiger Benutzeranleitung

Neuer Menüpunkt "Hilfe" (`/help`, `frontend/src/pages/HelpPage.tsx`) mit einer
zusammenhängenden, für Endnutzer geschriebenen Anleitung zu allen Funktionen der
App — Envelope-Budgeting-Grundidee, Konten, Umschläge (inkl. Sparziel und
Notfallfonds-Markierung), Buchungen, Transfer, Daueraufträge, CAMT.053-Import
(inkl. Duplikat-Erkennung), Regeln, Schulden/Tilgungsplan (inkl. maximaler
Zusatzzahlung, Kontoverknüpfung, Sweep-Vorschlag, Notfallfonds-Priorität), Trends
und Einstellungen. Ein Inhaltsverzeichnis mit Anker-Links oben auf der Seite
springt per Klick zum jeweiligen Abschnitt (`html { scroll-behavior: smooth }`,
respektiert `prefers-reduced-motion`).

## 6. Nächste Schritte

1. **Produktions-Deployment**: Single-Server-Aufbau, der `frontend/dist/` (nach
   `npm run build`) über Django/WhiteNoise oder einen Reverse-Proxy vor die API schaltet,
   inkl. `DEBUG=False`, echtem `SECRET_KEY` und Postgres statt SQLite.
2. **Frontend-Tests**: bisher nur manuell/End-to-End verifiziert — Komponenten- bzw.
   Integrationstests (z.B. Vitest + Testing Library) wären ein sinnvoller nächster Schritt.

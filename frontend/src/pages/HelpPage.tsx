export function HelpPage() {
  return (
    <>
      <div className="page-header">
        <div>
          <h1>Hilfe &amp; Anleitung</h1>
          <p>So funktioniert EZBudget — ausführlich erklärt, mit Beispielen.</p>
        </div>
      </div>

      <div className="card">
        <p className="helptext" style={{ marginBottom: 12 }}>
          Ein Grundsatz zieht sich durch die ganze App: EZBudget <strong>bildet</strong> deine Finanzen ab, es
          <strong> überweist nie selbst Geld</strong>. Jede Zahlung, jeder Transfer und jede Tilgung, die du hier
          siehst, hast du entweder selbst eingetragen oder aus einem Kontoauszug importiert. Die App rechnet,
          erinnert und schlägt vor — die Bank-Überweisung machst immer du.
        </p>
        <ul className="help-toc">
          <li>
            <a href="#grundidee">Grundidee: Envelope-Budgeting</a>
          </li>
          <li>
            <a href="#konten">Konten</a>
          </li>
          <li>
            <a href="#umschlaege">Umschläge &amp; Budgetieren</a>
          </li>
          <li>
            <a href="#buchungen">Buchungen erfassen</a>
          </li>
          <li>
            <a href="#transfer">Geld verschieben</a>
          </li>
          <li>
            <a href="#dauerauftraege">Wiederkehrende Buchungen</a>
          </li>
          <li>
            <a href="#import">Bankauszug importieren</a>
          </li>
          <li>
            <a href="#regeln">Regeln für Auto-Zuordnung</a>
          </li>
          <li>
            <a href="#schulden">Schulden &amp; Tilgungsplan</a>
          </li>
          <li>
            <a href="#trends">Trends &amp; Insights</a>
          </li>
          <li>
            <a href="#dashboard">Dashboard verstehen</a>
          </li>
          <li>
            <a href="#einstellungen">Einstellungen</a>
          </li>
        </ul>
      </div>

      <div className="section-title" id="grundidee">
        Grundidee: Envelope-Budgeting
      </div>
      <div className="card help-section">
        <div className="help-callout">
          <strong className="label">Kurz gesagt</strong>
          <p>
            Stell dir vor, du hebst dein ganzes Gehalt bar ab und steckst es in mehrere beschriftete Couverts:
            „Miete", „Essen", „Ausgehen", „Sparen". Du darfst aus jedem Couvert nur so viel ausgeben, wie drin ist.
            Ist ein Couvert leer, ist der Monat für diesen Zweck vorbei — auch wenn in einem anderen Couvert noch
            Geld liegt. Genau das macht EZBudget, nur digital: Ein „Umschlag" in der App ist so ein Couvert.
          </p>
        </div>
        <p>
          Du musst dein Geld nicht wirklich physisch aufteilen — es bleibt ganz normal auf deinen echten Bankkonten.
          Die App führt nur mit, wie viel von deinem Budget in jedem Umschlag noch übrig ist. Gibst du in einem
          Monat weniger aus als geplant, wird der Rest automatisch in den nächsten Monat mitgenommen (siehe
          „Rollover" weiter unten) — nichts geht verloren, wie bei einem Couvert, das du einfach weiter aufbewahrst.
        </p>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            Monatslohn CHF 4500. Du richtest folgende Umschläge ein: Miete CHF 1400, Krankenkasse CHF 350,
            Lebensmittel CHF 500, Auto CHF 250, Freizeit CHF 200, Sparen „Ferien" CHF 150, Schuldentilgung CHF 200.
            Das sind zusammen CHF 3050 fest verplant — die restlichen CHF 1450 bleiben frei verfügbar (musst du
            keinem Umschlag zuweisen, wenn du das nicht willst). Am Ende des Monats siehst du für jeden Umschlag
            sofort, ob noch etwas übrig ist oder ob du überzogen hast.
          </p>
        </div>
        <p>
          Der übliche Ablauf: Konten und Umschläge einmal einrichten (dauert 10–15 Minuten), danach nur noch laufend
          Buchungen erfassen oder Kontoauszüge importieren. Das Dashboard zeigt dir danach auf einen Blick, wo du
          stehst.
        </p>
      </div>

      <div className="section-title" id="konten">
        Konten
      </div>
      <div className="card help-section">
        <div className="help-callout">
          <strong className="label">Kurz gesagt</strong>
          <p>
            Ein Konto in der App entspricht einem echten „Geld-Ort": deinem Girokonto bei der Bank, deinem
            Sparkonto, dem Bargeld in deinem Portemonnaie oder deiner Kreditkarte.
          </p>
        </div>
        <h3>Anlegen</h3>
        <p>
          Beim Anlegen wählst du eine Art (Girokonto, Sparkonto, Bargeld oder Kreditkarte) und gibst ein
          <strong> Startguthaben</strong> ein — den Betrag, der am Tag, an dem du mit der App beginnst, tatsächlich
          auf diesem Konto liegt (bei einer Kreditkarte: die aktuelle Restschuld als negativer Betrag, falls schon
          vorhanden). Ab diesem Zeitpunkt rechnet die App automatisch:
        </p>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            Startguthaben Girokonto: CHF 1200. Danach erfasst du eine Ausgabe „Migros CHF −82.30" und eine Einnahme
            „Lohn CHF +4500". Der aktuelle Kontostand ist dann automatisch 1200 − 82.30 + 4500 = CHF 5617.70 — du
            musst nirgends selbst nachrechnen.
          </p>
        </div>
        <h3>Wann welche Art?</h3>
        <ul>
          <li><strong>Girokonto</strong>: dein Alltagskonto für Lohn, Miete, Einkäufe.</li>
          <li><strong>Sparkonto</strong>: separates Konto für Erspartes, z.B. Ziel „Notgroschen" oder „Ferien".</li>
          <li><strong>Bargeld</strong>: was in deinem Portemonnaie liegt, falls du das mitverfolgen willst.</li>
          <li>
            <strong>Kreditkarte</strong>: nur nötig, wenn du sie zusätzlich als Schuld erfassen und automatisch mit
            Käufen/Zahlungen verknüpfen willst (siehe Abschnitt „Schulden").
          </li>
        </ul>
        <h3>Archivieren</h3>
        <p>
          Ein archiviertes Konto verschwindet aus den Auswahllisten für neue Buchungen, bleibt aber in der Historie
          sichtbar — praktisch für ein gekündigtes Konto, dessen alte Buchungen du nicht löschen willst.
        </p>
      </div>

      <div className="section-title" id="umschlaege">
        Umschläge &amp; Budgetieren
      </div>
      <div className="card help-section">
        <h3>Die fünf Arten</h3>
        <p>Jeder Umschlag gehört zu einer Art — das entscheidet, wo er auf dem Dashboard gruppiert erscheint:</p>
        <ul>
          <li><strong>Fixkosten</strong> — jeden Monat (fast) derselbe Betrag: Miete, Krankenkasse, Handy-Abo, Versicherungen.</li>
          <li><strong>Variable Kosten</strong> — schwankt: Lebensmittel, Kleider, Tanken, Freizeit.</li>
          <li><strong>Einnahmen</strong> — Lohn, Nebenjob, Kindergeld.</li>
          <li><strong>Sparen</strong> — Ferien, Notgroschen, ein neues Velo.</li>
          <li>
            <strong>Schuldentilgung</strong> — wird automatisch angelegt, sobald du eine Schuld erfasst (siehe
            Abschnitt „Schulden"); musst du normalerweise nicht selbst wählen.
          </li>
        </ul>

        <h3>Monatsbudget &amp; Übertrag (Rollover)</h3>
        <p>
          Das Monatsbudget gilt ab dem Monat, in dem du es setzt. Änderst du es später, bleiben vergangene Monate
          trotzdem korrekt — die App merkt sich, welches Budget in welchem Monat galt, statt rückwirkend den neuen
          Wert überall einzusetzen.
        </p>
        <div className="help-callout example">
          <strong className="label">Beispiel: Übertrag nach unten</strong>
          <p>
            Umschlag „Lebensmittel", Budget CHF 400/Monat. Im September gibst du nur CHF 350 aus — die restlichen
            CHF 50 werden automatisch in den Oktober übertragen. Dort stehen dir dann effektiv CHF 450 zur Verfügung
            (CHF 400 neues Budget + CHF 50 Übertrag), bis du sie ausgegeben hast.
          </p>
        </div>
        <div className="help-callout example">
          <strong className="label">Beispiel: Übertrag nach oben (Überzug)</strong>
          <p>
            Umschlag „Kleider", Budget CHF 100/Monat. Im September gibst du CHF 150 aus, überziehst also um CHF 50.
            Im Oktober startest du dann nicht bei CHF 100, sondern effektiv bei CHF 50 (CHF 100 neues Budget − CHF
            50 Überzug aus dem Vormonat) — der Umschlag „erinnert" sich an den Überzug, bis er ausgeglichen ist.
          </p>
        </div>

        <h3>Sparziel</h3>
        <p>
          Optional gibst du einem Umschlag ein Sparziel: einen Zielbetrag und optional ein Zieldatum. Der
          Fortschritt (in Prozent) wird direkt am Umschlag angezeigt.
        </p>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            Umschlag „Ferien", Monatsbudget CHF 150, Sparziel CHF 1800, Zieldatum in 12 Monaten. Nach 4 Monaten
            zeigt der Umschlag ca. 33% Fortschritt (CHF 600 von CHF 1800) an — vorausgesetzt, du hast das Budget
            nicht für etwas anderes ausgegeben.
          </p>
        </div>

        <h3>Notfallfonds markieren</h3>
        <p>
          Ein Umschlag mit Sparziel lässt sich zusätzlich als <strong>Notfallfonds</strong> markieren (Checkbox im
          Umschlag-Formular „Das ist mein Notfallfonds"). Es kann immer nur einer aktiv sein: markierst du einen
          neuen, wird ein vorheriger automatisch abgewählt. Das hat eine konkrete Auswirkung: Sobald ein
          Notfallfonds markiert ist, füllen der Tilgungsplan-Rechner und der Sweep-Vorschlag automatisch zuerst
          dessen Lücke zum Sparziel, bevor irgendetwas an Schulden geht — Details dazu im Abschnitt „Schulden".
        </p>
        <div className="help-callout tip">
          <strong className="label">Tipp</strong>
          <p>
            Eine gängige Faustregel aus der Schuldenberatung: ca. ein Monat Fixkosten als Notfallfonds, bevor du
            aggressiv Schulden zusätzlich abbezahlst. Hast du z.B. CHF 2200 Fixkosten/Monat, wäre CHF 2000–2500 ein
            sinnvolles Sparziel für den Notfallfonds.
          </p>
        </div>

        <h3>Farbe &amp; Icon</h3>
        <p>Jeder Umschlag bekommt zur besseren Wiedererkennung eine Farbe und ein Icon, die du frei wählen kannst.</p>
      </div>

      <div className="section-title" id="buchungen">
        Buchungen erfassen
      </div>
      <div className="card help-section">
        <div className="help-callout">
          <strong className="label">Kurz gesagt</strong>
          <p>
            Eine Buchung ist ein einzelner Geldfluss: Du hast etwas gekauft (Ausgabe) oder Geld erhalten (Einnahme).
            Jede Buchung gehört zu einem Konto und optional zu einem Umschlag.
          </p>
        </div>
        <h3>Vorzeichen</h3>
        <p>
          Ein <strong>negativer</strong> Betrag ist eine Ausgabe (Geld verlässt das Konto), ein
          <strong> positiver</strong> Betrag eine Einnahme (Geld kommt rein).
        </p>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            „Einkauf bei Migros, CHF −82.30, Konto Girokonto, Umschlag Lebensmittel, Datum 5.9.2026" — eine ganz
            normale Ausgabe. „Lohn September, CHF +4500, Konto Girokonto, Umschlag Lohn" — eine Einnahme.
          </p>
        </div>
        <h3>Warum der Umschlag wichtig ist</h3>
        <p>
          Ohne Umschlag weiss die App nicht, wofür das Geld ausgegeben wurde — die Buchung zählt zwar für den
          Kontostand, aber nicht für dein Budget. Das Dashboard warnt dich deshalb, wenn diesen Monat Buchungen
          ohne Umschlag herumliegen, damit dir keine „vergisst".
        </p>
        <h3>Suchen &amp; Filtern</h3>
        <p>Auf der Buchungen-Seite kannst du:</p>
        <ul>
          <li>nach Text suchen (Beschreibung oder Gegenpartei), z.B. „Migros" oder „SBB",</li>
          <li>nach Umschlag filtern — auch gezielt nach <strong>„kein Umschlag"</strong>, um vergessene Buchungen aufzuspüren,</li>
          <li>statt nur des aktuellen Monats einen freien Zeitraum wählen, z.B. „1.1.–31.3.2026" für ein Quartal.</li>
        </ul>
      </div>

      <div className="section-title" id="transfer">
        Geld zwischen Konten verschieben
      </div>
      <div className="card help-section">
        <div className="help-callout">
          <strong className="label">Kurz gesagt</strong>
          <p>
            Ein Transfer ist kein Einkauf und kein Lohn — es ist Geld, das von einem deiner Konten zu einem anderen
            wandert. Es verlässt deinen Haushalt nicht, deshalb zählt es nicht als Ausgabe oder Einnahme.
          </p>
        </div>
        <div className="help-callout example">
          <strong className="label">Beispiel 1: Sparen</strong>
          <p>
            Am Monatsende verschiebst du CHF 300 von deinem Girokonto auf dein Sparkonto. Das Girokonto sinkt um
            CHF 300, das Sparkonto steigt um CHF 300 — im Dashboard verändert sich weder „Einnahmen" noch
            „Ausgaben" diesen Monat.
          </p>
        </div>
        <div className="help-callout example">
          <strong className="label">Beispiel 2: Kreditkarte bezahlen</strong>
          <p>
            Du hast eine Kreditkarte als Schuld mit Kontoverknüpfung erfasst (siehe „Schulden"). Um sie zu bezahlen,
            machst du einen Transfer von CHF 500 vom Girokonto auf das Kreditkarten-Konto — die Restschuld der
            Kreditkarte sinkt dadurch automatisch um CHF 500.
          </p>
        </div>
      </div>

      <div className="section-title" id="dauerauftraege">
        Wiederkehrende Buchungen (Daueraufträge)
      </div>
      <div className="card help-section">
        <div className="help-callout">
          <strong className="label">Kurz gesagt</strong>
          <p>
            Für Dinge, die immer wiederkehren (Miete, Abos, Lohn), musst du nicht jeden Monat von Hand eine Buchung
            eintippen — einmal einrichten, die App erledigt den Rest automatisch.
          </p>
        </div>
        <h3>Einrichten</h3>
        <p>Du gibst Betrag, Konto, Umschlag, eine Beschreibung und die Frequenz an:</p>
        <ul>
          <li><strong>Monatlich</strong> — z.B. Miete am 1., Krankenkasse am 25.</li>
          <li><strong>Wöchentlich</strong> — z.B. ein Putzabo jeden Montag.</li>
          <li><strong>Alle zwei Wochen</strong> — z.B. Lohn bei manchen Stundenlohn-Jobs.</li>
          <li><strong>Jährlich</strong> — z.B. Autoversicherung oder Serafe-Gebühr im März.</li>
        </ul>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            „Miete", CHF −1400, Konto Girokonto, Umschlag Miete, monatlich am 1. Sobald du die App am oder nach dem
            1. eines Monats öffnest, wird die Buchung für diesen Monat automatisch erstellt — auch wenn du die App
            z.B. erst am 4. öffnest, wird sie rückwirkend auf den 1. gebucht, nicht doppelt für denselben Monat.
          </p>
        </div>
        <div className="help-callout tip">
          <strong className="label">Tipp</strong>
          <p>
            Bei wöchentlichen/zweiwöchentlichen Daueraufträgen lohnt es sich, die App ungefähr am Fälligkeitstag zu
            öffnen — im Gegensatz zu monatlich/jährlich wird eine verpasste Woche nicht rückwirkend nachgeholt.
          </p>
        </div>
      </div>

      <div className="section-title" id="import">
        Bankauszug importieren (CAMT.053)
      </div>
      <div className="card help-section">
        <div className="help-callout">
          <strong className="label">Kurz gesagt</strong>
          <p>
            Statt jede Buchung von Hand einzutippen, lädst du eine Datei aus deinem E-Banking hoch, und die App
            übernimmt alle Buchungen daraus auf einmal — inklusive Vorschlag, welchem Umschlag sie zugeordnet
            werden sollten.
          </p>
        </div>
        <h3>Was ist CAMT.053?</h3>
        <p>
          CAMT.053 ist ein standardisiertes XML-Dateiformat für Kontoauszüge, das praktisch alle Schweizer Banken
          im E-Banking anbieten — meist unter „Kontoauszug", „Export" oder „Bewegungen exportieren", mit einer
          Formatauswahl wie „camt.053" oder „ISO 20022". Frag im Zweifel den Support deiner Bank, wo genau das zu
          finden ist.
        </p>
        <h3>Schritt für Schritt</h3>
        <ol>
          <li>Im E-Banking deiner Bank den gewünschten Zeitraum als camt.053-XML-Datei herunterladen.</li>
          <li>In EZBudget auf „Import" gehen, das passende Konto wählen und die Datei hochladen.</li>
          <li>
            Die Vorschau zeigt jede Buchung mit einem automatischen Zuordnungsvorschlag (aus Stichworten am
            Umschlag oder passenden Regeln, siehe unten) — prüfen, korrigieren wo nötig, einzelne Zeilen bei Bedarf
            abwählen.
          </li>
          <li>„Import bestätigen" — erst jetzt werden die Buchungen tatsächlich gespeichert.</li>
        </ol>
        <h3>Duplikat-Erkennung</h3>
        <p>Zwei Sicherheitsnetze verhindern, dass eine Buchung doppelt gezählt wird:</p>
        <ul>
          <li>
            <strong>Hartes Duplikat</strong> — die Bank-Referenznummer der Buchung wurde schon einmal importiert.
            Diese Zeile ist automatisch abgewählt und lässt sich nicht erneut importieren.
          </li>
          <li>
            <strong>„Evtl. schon erfasst?"</strong> — Datum und Betrag stimmen mit einer bereits manuell erfassten
            Buchung überein (z.B. eine Zahlung, die du zuvor selbst über „Zahlung erfassen" eingetragen hattest).
            Diese Markierung blockiert nichts — die Zeile ist nur vorsorglich abgewählt, du kannst sie bei Bedarf
            trotzdem einschliessen, falls es doch zwei unterschiedliche Buchungen sind.
          </li>
        </ul>
        <div className="help-callout tip">
          <strong className="label">Tipp</strong>
          <p>
            Hast du eine Tilgungszahlung schon manuell über „Zahlung erfassen" eingetragen (z.B. aus dem
            Sweep-Vorschlag), taucht sie beim späteren Import als „Evtl. schon erfasst?" auf — lass sie in dem Fall
            abgewählt, sonst zählt die Zahlung doppelt.
          </p>
        </div>
      </div>

      <div className="section-title" id="regeln">
        Regeln für automatische Zuordnung
      </div>
      <div className="card help-section">
        <div className="help-callout">
          <strong className="label">Kurz gesagt</strong>
          <p>
            Eine Regel sagt der App: „Wenn eine Buchung so aussieht, geht sie automatisch in diesen Umschlag" —
            damit du das beim Import nicht jedes Mal von Hand machen musst.
          </p>
        </div>
        <h3>Aufbau einer Regel</h3>
        <p>Eine Regel prüft eine oder mehrere Bedingungen und weist bei Treffer einen Ziel-Umschlag zu:</p>
        <ul>
          <li>Beschreibung <strong>enthält</strong> / <strong>beginnt mit</strong> / <strong>ist exakt</strong> ein Stichwort,</li>
          <li>Gegenpartei enthält / beginnt mit / ist exakt ein Stichwort,</li>
          <li>optional zusätzlich ein Betragsbereich (z.B. nur zwischen CHF −50 und CHF −10).</li>
        </ul>
        <div className="help-callout example">
          <strong className="label">Beispiel 1</strong>
          <p>Beschreibung <strong>enthält</strong> „Migros" → Umschlag „Lebensmittel".</p>
        </div>
        <div className="help-callout example">
          <strong className="label">Beispiel 2</strong>
          <p>Gegenpartei <strong>beginnt mit</strong> „SBB" → Umschlag „Verkehr".</p>
        </div>
        <div className="help-callout example">
          <strong className="label">Beispiel 3: mit Betragsbereich</strong>
          <p>
            Beschreibung enthält „Kartenzahlung" UND Betrag zwischen CHF −20 und CHF −5 → Umschlag „Kleinausgaben"
            — so lassen sich z.B. kleine Kaffee-/Snack-Käufe automatisch von grösseren Kartenzahlungen trennen.
          </p>
        </div>
        <h3>Anwenden</h3>
        <p>
          Neue Regeln greifen ab sofort beim nächsten Import. Auf der Regeln-Seite kannst du eine Regel zusätzlich
          rückwirkend auf bereits bestehende Buchungen anwenden — mit einer Vorschau, wie viele Buchungen
          betroffen wären, bevor du bestätigst.
        </p>
      </div>

      <div className="section-title" id="schulden">
        Schulden &amp; Tilgungsplan
      </div>
      <div className="card help-section">
        <h3>Eine Schuld erfassen</h3>
        <p>
          Kredit, Kreditkarte oder Privatdarlehen — du gibst Name, Ursprungsbetrag, aktuelle Restschuld, Zinssatz
          p.a. und Mindestrate an. Jede Schuld bekommt automatisch einen eigenen Umschlag, über den sich Zahlungen
          mit ihr verknüpfen lassen.
        </p>
        <div className="help-callout tip">
          <strong className="label">Wichtig zu wissen</strong>
          <p>
            Die Mindestrate ist erstmal nur eine <strong>Planungsgrösse</strong> — sie zieht nicht automatisch Geld
            ab. Damit die monatliche Zahlung tatsächlich passiert, brauchst du zusätzlich entweder eine
            wiederkehrende Buchung (siehe oben) für die Mindestrate, oder du erfasst jede Zahlung manuell, sobald du
            sie bei deiner Bank ausgeführt hast.
          </p>
        </div>
        <div className="help-callout example">
          <strong className="label">Beispiel: Konsumkredit</strong>
          <p>
            Du nimmst bei einer Bank einen Kredit über CHF 2000 zu 7.9% effektivem Jahreszins mit 12 Monaten
            Laufzeit auf. Du erfasst: Ursprungsbetrag CHF 2000, Restschuld CHF 2000, Zinssatz 7.9%, Mindestrate ca.
            CHF 178 (die Rate, die dir die Bank im Kreditvertrag nennt). Zusätzlich richtest du einen Dauerauftrag
            über CHF 178/Monat auf den Schulden-Umschlag ein, damit die Rate auch wirklich automatisch abgebucht
            und erfasst wird.
          </p>
        </div>

        <h3>Maximale Zusatzzahlung</h3>
        <p>
          Manche Kredite mit fixem Tilgungsplan (wie im Beispiel oben) erlauben keine oder nur eine begrenzte
          Sondertilgung über die Mindestrate hinaus. Trage das im Feld „Maximale Zusatzzahlung" ein:
        </p>
        <ul>
          <li><strong>Leer</strong> = unbegrenzt, z.B. bei einer Kreditkarte.</li>
          <li><strong>0</strong> = gar keine Zuzahlung möglich, z.B. beim fixen Konsumkredit oben.</li>
          <li>ein <strong>fixer Betrag</strong>, falls der Kreditvertrag eine begrenzte Sondertilgung erlaubt.</li>
        </ul>
        <p>
          Der Tilgungsplan-Rechner und der Sweep-Vorschlag respektieren das automatisch: Was eine gedeckelte Schuld
          nicht aufnehmen darf, fliesst an die nächste Schuld in der Prioritätsreihenfolge, statt einfach zu
          verschwinden.
        </p>

        <h3>Laufende Kreditlinie (z.B. Kreditkarte) verknüpfen</h3>
        <p>
          Bei einer Kreditkarte, mit der du laufend neue Einkäufe machst, lohnt sich die Kontoverknüpfung: Du legst
          ein Konto vom Typ „Kreditkarte" an und verknüpfst die Schuld damit.
        </p>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            Konto „Viseca Karte" verknüpft mit Schuld „Kreditkarte Viseca". Du kaufst für CHF 80 bei Migros mit
            dieser Karte — die Buchung landet ganz normal im Umschlag „Lebensmittel" (dein Budget-Tracking bleibt
            exakt), und gleichzeitig steigt die Restschuld der Kreditkarte automatisch um CHF 80. Am Monatsende
            überweist du CHF 500 per Transfer vom Girokonto auf die Karte — die Restschuld sinkt automatisch um
            CHF 500, und der monatliche Zins wird automatisch als eigene Buchung verbucht.
          </p>
        </div>
        <p>
          Ohne Kontoverknüpfung bleibt der klassische Weg: eine Zahlung manuell über den Schulden-Umschlag der
          jeweiligen Schuld erfassen.
        </p>

        <h3>Tilgungsplan-Rechner: Avalanche vs. Snowball</h3>
        <p>
          Auf der Schulden-Seite wählst du eine Strategie und ein monatliches Extra-Budget oberhalb der
          Mindestraten. Beide Strategien zahlen bei ALLEN Schulden immer mindestens die Mindestrate — der
          Unterschied liegt nur darin, wohin das <strong>zusätzliche</strong> Geld zuerst fliesst:
        </p>
        <ul>
          <li>
            <strong>Avalanche</strong> — zuerst an die Schuld mit dem <strong>höchsten Zinssatz</strong>. Spart
            mathematisch am meisten Zinskosten.
          </li>
          <li>
            <strong>Snowball</strong> — zuerst an die Schuld mit der <strong>kleinsten Restschuld</strong>. Sie ist
            dadurch am schnellsten komplett getilgt, was psychologisch motiviert, auch wenn es insgesamt minim mehr
            Zinsen kostet.
          </li>
        </ul>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            Schuld A: Kreditkarte, Restschuld CHF 3000, Zins 12%, Mindestrate CHF 90. Schuld B: Kleinkredit,
            Restschuld CHF 1000, Zins 6%, Mindestrate CHF 50. Extra-Budget: CHF 200/Monat.
          </p>
          <p>
            Bei <strong>Avalanche</strong> gehen die CHF 200 Extra zuerst an Schuld A (höherer Zins, 12% &gt; 6%) —
            Schuld B bleibt vorerst bei ihrer Mindestrate. Bei <strong>Snowball</strong> gehen die CHF 200 Extra
            zuerst an Schuld B (kleinere Restschuld) — sie ist dadurch schon nach ca. 4 Monaten komplett getilgt,
            danach fliesst ihre freigewordene Mindestrate zusätzlich in Schuld A.
          </p>
        </div>
        <p>
          Der Rechner zeigt dir für die gewählte Strategie das voraussichtliche Schuldenfrei-Datum, die gesamten
          Zinskosten, die Tilgungsreihenfolge und den Verlauf als Diagramm — so siehst du den Effekt einer Strategie
          sofort, statt sie erraten zu müssen.
        </p>

        <h3>Monatsende-Sweep-Vorschlag</h3>
        <div className="help-callout">
          <strong className="label">Kurz gesagt</strong>
          <p>
            In den letzten Tagen des Monats schaut die App in alle deine Umschläge und sagt dir: „Hier ist noch
            Geld übrig, das du nicht gebraucht hast — willst du es stattdessen deinen Schulden geben?"
          </p>
        </div>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            Am 27. des Monats zeigt die Schulden-Seite: Umschlag „Lebensmittel" CHF 30 übrig, „Freizeit" CHF 20
            übrig — zusammen CHF 50 verfügbar. Nach deiner gewählten Strategie schlägt die App vor, diese CHF 50
            an deine höchstverzinste Schuld zu leiten.
          </p>
        </div>
        <p>
          Wichtig: Die App überweist dabei <strong>nichts automatisch</strong>. Du überweist den Betrag zuerst
          selbst bei deiner Bank und trägst die Zahlung danach über den Link „Zahlung erfassen" ein (der Betrag ist
          bereits vorausgefüllt). Erfasse eine Zahlung entweder so ODER importiere sie später per Kontoauszug — nicht
          beides, sonst zählt sie doppelt (die App markiert das im Zweifel als „Evtl. schon erfasst?", siehe oben).
        </p>
        <p>
          Der Vorschlag erscheint bewusst nur in den letzten Tagen des Monats: Am 5. Tag wäre „noch nicht
          ausgegeben" kein echter Überschuss, sondern Geld, das du diesen Monat noch brauchst.
        </p>

        <h3>Notfallfonds-Priorität</h3>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            Du hast den Umschlag „Notgroschen" als Notfallfonds markiert, Sparziel CHF 3000, aktuell CHF 1200
            gespart — Lücke also CHF 1800. Dein monatliches Extra-Budget beträgt CHF 200. Sowohl der
            Tilgungsplan-Rechner als auch der Sweep-Vorschlag leiten diese CHF 200 zuerst in den Notgroschen, Monat
            für Monat, bis die Lücke von CHF 1800 geschlossen ist (nach 9 Monaten) — erst danach fliesst
            Extra-Budget an deine Schulden.
          </p>
        </div>
        <p>
          Hintergrund: ein bewährtes Prinzip aus der Schuldenberatung. Ohne Puffer landet die nächste unerwartete
          Rechnung (kaputte Waschmaschine, Zahnarzt) sonst wieder auf der Kreditkarte — und der ganze
          Tilgungsfortschritt beginnt von vorn.
        </p>
      </div>

      <div className="section-title" id="trends">
        Trends &amp; Insights
      </div>
      <div className="card help-section">
        <div className="help-callout">
          <strong className="label">Kurz gesagt</strong>
          <p>Die Trends-Seite zeigt dir, wie sich dein Geld über mehrere Monate hinweg entwickelt — nicht nur einen Monat isoliert.</p>
        </div>
        <p>Konkret siehst du:</p>
        <ul>
          <li>Einnahmen und Ausgaben im Verlauf über mehrere Monate,</li>
          <li>wie sich die Ausgaben pro einzelnem Umschlag entwickeln (z.B. steigende Stromkosten im Winter),</li>
          <li>einen Jahresvergleich für den aktuellsten Monat im gewählten Zeitraum.</li>
        </ul>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            Du bemerkst über die Trends-Ansicht, dass der Umschlag „Freizeit" in den letzten drei Monaten jedes Mal
            leicht überzogen wurde — ein Hinweis, das Budget entweder zu erhöhen oder bewusster zu planen, statt es
            jeden Monat aufs Neue zu übersehen.
          </p>
        </div>
      </div>

      <div className="section-title" id="dashboard">
        Dashboard verstehen
      </div>
      <div className="card help-section">
        <p>Das Dashboard ist dein täglicher Einstieg und zeigt auf einen Blick:</p>
        <ul>
          <li>Gesamtguthaben über alle Konten,</li>
          <li>Einnahmen, Ausgaben und Netto des aktuellen Monats,</li>
          <li>Fixkosten- und variable Umschläge mit Fortschrittsbalken,</li>
          <li>bei offenen Schulden: Restschuld gesamt, Mindestraten, voraussichtliches Schuldenfrei-Datum (bei reiner Mindestratenzahlung, ohne Extra-Budget) und dein Gesamtfortschritt über alle je erfassten Schulden.</li>
        </ul>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            Erreichst du bei einer Schuld 50% Tilgungsfortschritt, erscheint einmalig eine Erfolgsmeldung
            „Meilenstein erreicht: 50% von ‚Kreditkarte Viseca' getilgt!" — danach nicht nochmal für denselben
            Meilenstein, aber wieder bei 75% und 100%.
          </p>
        </div>
        <p>Fehlt einer Buchung dieses Monat ein Umschlag, weist ausserdem ein Banner mit direktem Link zur Korrektur darauf hin.</p>
      </div>

      <div className="section-title" id="einstellungen">
        Einstellungen
      </div>
      <div className="card help-section">
        <h3>Budget-Monat-Starttag</h3>
        <p>
          Standardmässig läuft ein Budget-Monat vom 1. bis zum Monatsletzten, wie der Kalendermonat. Falls dein
          Lohn nicht am Monatsersten kommt, lässt sich das anpassen.
        </p>
        <div className="help-callout example">
          <strong className="label">Beispiel</strong>
          <p>
            Dein Lohn kommt am 25., deine grossen Fixkosten gehen kurz danach ab. Stellst du den Starttag auf 25,
            läuft dein „September-Budget" vom 25.8. bis 24.9. — passend zu deinem tatsächlichen Zahlungsrhythmus,
            statt künstlich am Kalendermonat zu kleben.
          </p>
        </div>
        <h3>Darstellung</h3>
        <p>Hell/Dunkel lässt sich manuell umschalten, unabhängig von der Systemeinstellung deines Geräts.</p>
      </div>
    </>
  )
}

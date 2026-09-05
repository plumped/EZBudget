export function HelpPage() {
  return (
    <>
      <div className="page-header">
        <div>
          <h1>Hilfe &amp; Anleitung</h1>
          <p>So funktioniert EZBudget — von der ersten Buchung bis zum Tilgungsplan.</p>
        </div>
      </div>

      <div className="card">
        <p className="helptext" style={{ marginBottom: 12 }}>
          EZBudget bildet deine Finanzen ab — es überweist nie selbst Geld. Jede Zahlung, jeder Transfer und jede
          Tilgung, die du hier siehst, hast du entweder selbst eingetragen oder aus einem Kontoauszug importiert.
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
        <p>
          EZBudget folgt dem Prinzip des Envelope-Budgetings (Umschlagsystem): Statt nur den Gesamt-Kontostand im
          Blick zu haben, teilst du dein Geld gedanklich auf verschiedene „Umschläge" auf — Lebensmittel, Miete,
          Freizeit, Sparen, Schuldentilgung. Jeder Umschlag hat ein Monatsbudget. Gibst du weniger aus als
          budgetiert, wird der Rest automatisch in den nächsten Monat übertragen (Rollover) — nichts geht verloren.
        </p>
        <p>
          Der typische Ablauf: Konten und Umschläge einmal anlegen, danach laufend Buchungen erfassen oder
          Kontoauszüge importieren. Das Dashboard zeigt dir jederzeit, wo du stehst.
        </p>
      </div>

      <div className="section-title" id="konten">
        Konten
      </div>
      <div className="card help-section">
        <p>
          Ein Konto bildet ein reales Bankkonto, Bargeld oder eine Kreditkarte ab (Girokonto, Sparkonto, Bargeld,
          Kreditkarte). Beim Anlegen gibst du ein Startguthaben an — der aktuelle Kontostand ergibt sich danach
          automatisch aus Startguthaben plus allen Buchungen auf diesem Konto.
        </p>
        <p>
          Ein archiviertes Konto verschwindet aus den meisten Auswahllisten, bleibt aber in der Historie sichtbar —
          nützlich für ein geschlossenes Konto, dessen alte Buchungen du behalten willst.
        </p>
      </div>

      <div className="section-title" id="umschlaege">
        Umschläge &amp; Budgetieren
      </div>
      <div className="card help-section">
        <h3>Art eines Umschlags</h3>
        <p>
          Jeder Umschlag hat eine Art: Fixkosten, Variable Kosten, Einnahmen, Sparen oder Schuldentilgung. Die Art
          bestimmt, in welcher Gruppe der Umschlag auf dem Dashboard erscheint, und bei Schuldentilgung wird der
          Umschlag automatisch von der jeweiligen Schuld verwaltet (siehe Abschnitt Schulden).
        </p>
        <h3>Monatsbudget &amp; Übertrag (Rollover)</h3>
        <p>
          Das Monatsbudget gilt ab dem Monat, in dem du es einstellst — änderst du es später, bleiben vergangene
          Monate rückwirkend korrekt (die App merkt sich, welches Budget wann galt). Nicht ausgegebenes Budget wird
          automatisch in den Folgemonat übertragen; ein überzogener Umschlag zehrt entsprechend vom nächsten Monat.
        </p>
        <h3>Sparziel</h3>
        <p>
          Optional kannst du einem Umschlag ein Sparziel (Zielbetrag, optional mit Zieldatum) geben — praktisch für
          „Ferien sparen" oder einen Notfallfonds (siehe unten). Der Fortschritt wird direkt am Umschlag angezeigt.
        </p>
        <h3>Notfallfonds markieren</h3>
        <p>
          Ein Umschlag mit Sparziel kann zusätzlich als <strong>Notfallfonds</strong> markiert werden (Checkbox im
          Umschlag-Formular). Es kann immer nur einer aktiv sein — markierst du einen neuen, wird ein vorheriger
          automatisch abgewählt. Das hat direkte Auswirkung auf den Tilgungsplan-Rechner und den
          Monatsende-Sweep-Vorschlag: siehe Abschnitt „Notfallfonds-Priorität" unten.
        </p>
        <h3>Farbe &amp; Icon</h3>
        <p>Jeder Umschlag bekommt zur besseren Wiedererkennung eine Farbe und ein Icon, die du frei wählen kannst.</p>
      </div>

      <div className="section-title" id="buchungen">
        Buchungen erfassen
      </div>
      <div className="card help-section">
        <p>
          Eine Buchung braucht ein Konto, einen Betrag (negativ = Ausgabe, positiv = Einnahme) und optional einen
          Umschlag. Ohne Umschlag zeigt das Dashboard eine Warnung „Buchungen sind keinem Umschlag zugewiesen" — so
          gehst du keiner Buchung aus Versehen verloren.
        </p>
        <p>
          Auf der Buchungen-Seite kannst du nach Text (Beschreibung/Gegenpartei) suchen, nach Umschlag filtern
          (auch gezielt nach „kein Umschlag") und einen freien Datumsbereich statt nur des aktuellen Monats wählen.
        </p>
      </div>

      <div className="section-title" id="transfer">
        Geld zwischen Konten verschieben
      </div>
      <div className="card help-section">
        <p>
          Ein Transfer verschiebt Geld zwischen zwei eigenen Konten (z.B. Girokonto → Sparkonto oder eine Zahlung an
          eine verknüpfte Kreditkarte). Ein Transfer zählt bewusst nicht als Einnahme oder Ausgabe im Dashboard —
          es verlässt ja kein Geld deinen Haushalt, es wechselt nur den Ort.
        </p>
      </div>

      <div className="section-title" id="dauerauftraege">
        Wiederkehrende Buchungen (Daueraufträge)
      </div>
      <div className="card help-section">
        <p>
          Für Miete, Abos oder den Lohneingang lohnt sich ein Dauerauftrag: einmal mit Betrag, Konto, Umschlag und
          Frequenz (monatlich, wöchentlich, alle zwei Wochen oder jährlich) einrichten — die zugehörige Buchung wird
          danach automatisch erstellt, sobald sie fällig ist (geprüft beim Öffnen des Dashboards).
        </p>
      </div>

      <div className="section-title" id="import">
        Bankauszug importieren (CAMT.053)
      </div>
      <div className="card help-section">
        <p>
          Statt jede Buchung manuell einzutippen, kannst du eine CAMT.053-XML-Datei (Standard-Kontoauszugsformat
          Schweizer Banken) hochladen. Die App zeigt eine Vorschau mit einem automatischen Zuordnungsvorschlag pro
          Buchung (aus Stichworten am Umschlag oder passenden Regeln, siehe unten) — du bestätigst oder korrigierst,
          bevor irgendetwas gespeichert wird.
        </p>
        <h3>Duplikat-Erkennung</h3>
        <p>
          Bereits importierte Buchungen werden anhand ihrer Bank-Referenznummer sicher als „Duplikat" erkannt und
          lassen sich nicht nochmals importieren. Zusätzlich markiert die App Buchungen als „Evtl. schon erfasst?",
          wenn Datum und Betrag zu einer bereits manuell eingetragenen Buchung passen (z.B. eine Zahlung, die du
          zuvor schon selbst erfasst hattest) — diese Markierung blockiert nichts, du entscheidest selbst, ob es
          wirklich dieselbe Buchung ist.
        </p>
      </div>

      <div className="section-title" id="regeln">
        Regeln für automatische Zuordnung
      </div>
      <div className="card help-section">
        <p>
          Eine Regel ordnet Buchungen anhand von Bedingungen automatisch einem Umschlag zu — z.B. „enthält 'Migros'"
          oder „Gegenpartei beginnt mit 'SBB'", optional zusätzlich eingegrenzt auf einen Betragsbereich. Regeln
          greifen beim Import (Vorschlag) und lassen sich auf der Regeln-Seite auch rückwirkend auf bereits
          bestehende Buchungen anwenden — mit Vorschau, bevor etwas geändert wird.
        </p>
      </div>

      <div className="section-title" id="schulden">
        Schulden &amp; Tilgungsplan
      </div>
      <div className="card help-section">
        <h3>Eine Schuld erfassen</h3>
        <p>
          Kredit, Kreditkarte oder Privatdarlehen: Name, Ursprungsbetrag, aktuelle Restschuld, Zinssatz p.a. und
          Mindestrate. Jede Schuld bekommt automatisch einen eigenen Umschlag, über den sich Zahlungen mit ihr
          verknüpfen — Restschuld und Zahlungshistorie hängen so direkt zusammen.
        </p>
        <h3>Maximale Zusatzzahlung</h3>
        <p>
          Manche Kredite (z.B. ein Ratenkredit mit fixem Tilgungsplan) erlauben keine oder nur eine begrenzte
          Sondertilgung über die Mindestrate hinaus. Trage das im Feld „Maximale Zusatzzahlung" ein: leer bedeutet
          unbegrenzt (z.B. Kreditkarte), 0 bedeutet gar keine Zuzahlung möglich. Der Tilgungsplan-Rechner und der
          Sweep-Vorschlag respektieren das automatisch — was eine gedeckelte Schuld nicht aufnehmen darf, fliesst an
          die nächste Schuld in der Prioritätsreihenfolge.
        </p>
        <h3>Laufende Kreditlinie (z.B. Kreditkarte) verknüpfen</h3>
        <p>
          Bei einer Kreditkarte kannst du die Schuld direkt mit dem Kreditkarten-Konto verknüpfen: jeder Einkauf auf
          diesem Konto erhöht automatisch die Restschuld, jede Zahlung per Transfer senkt sie, und der Zins wird
          monatlich automatisch verbucht. Ohne Verknüpfung bleibt der klassische Weg: Zahlung manuell über den
          Schulden-Umschlag erfassen.
        </p>
        <h3>Tilgungsplan-Rechner</h3>
        <p>
          Auf der Schulden-Seite wählst du eine Strategie — <strong>Avalanche</strong> (höchster Zinssatz zuerst,
          spart am meisten Zinsen) oder <strong>Snowball</strong> (kleinste Restschuld zuerst, schnelle
          Erfolgserlebnisse) — und ein monatliches Extra-Budget oberhalb der Mindestraten. Die App zeigt dir das
          voraussichtliche Schuldenfrei-Datum, die gesamten Zinskosten, die Tilgungsreihenfolge und den Verlauf als
          Diagramm.
        </p>
        <h3>Monatsende-Sweep-Vorschlag</h3>
        <p>
          In den letzten Tagen des Budget-Monats zeigt die Schulden-Seite, wie viel Budget diesen Monat nicht
          ausgegeben wurde, und schlägt vor, wie sich dieser Betrag nach deiner gewählten Strategie auf die
          Schulden verteilen liesse. Die App überweist dabei nichts automatisch — überweise den Betrag zuerst
          selbst bei deiner Bank und trage die Zahlung danach über den Link „Zahlung erfassen" ein (Betrag ist
          bereits vorausgefüllt). Erfasse eine Zahlung entweder so ODER importiere sie später per Kontoauszug, nicht
          beides — sonst zählt sie doppelt.
        </p>
        <h3>Notfallfonds-Priorität</h3>
        <p>
          Hast du einen Umschlag als Notfallfonds markiert (siehe oben), füllen sowohl der Tilgungsplan-Rechner als
          auch der Sweep-Vorschlag zuerst die Lücke zu dessen Sparziel, bevor überhaupt etwas an die Schulden geht —
          ein bewährtes Prinzip aus der Schuldenberatung: erst einen kleinen Puffer aufbauen, damit die nächste
          unerwartete Rechnung nicht wieder auf der Kreditkarte landet.
        </p>
      </div>

      <div className="section-title" id="trends">
        Trends &amp; Insights
      </div>
      <div className="card help-section">
        <p>
          Die Trends-Seite zeigt Einnahmen und Ausgaben über mehrere Monate im Verlauf, die Entwicklung pro
          Umschlag sowie einen Jahresvergleich für den aktuellsten Monat im gewählten Zeitraum — hilfreich, um
          saisonale Muster oder schleichende Budgetüberschreitungen zu erkennen.
        </p>
      </div>

      <div className="section-title" id="dashboard">
        Dashboard verstehen
      </div>
      <div className="card help-section">
        <p>
          Das Dashboard ist dein täglicher Einstieg: Gesamtguthaben über alle Konten, Einnahmen/Ausgaben/Netto des
          Monats, die Fixkosten- und variablen Umschläge mit Fortschrittsbalken, sowie — bei offenen Schulden —
          Restschuld gesamt, Mindestraten, das voraussichtliche Schuldenfrei-Datum (bei reiner Mindestratenzahlung)
          und dein Gesamtfortschritt über alle je erfassten Schulden.
        </p>
        <p>
          Erreichst du bei einer Schuld einen Meilenstein (25/50/75/100% getilgt), erscheint dafür einmalig eine
          Erfolgsmeldung. Fehlt einer Buchung dieses Monat ein Umschlag, weist ein Banner darauf hin.
        </p>
      </div>

      <div className="section-title" id="einstellungen">
        Einstellungen
      </div>
      <div className="card help-section">
        <p>
          <strong>Budget-Monat-Starttag</strong>: Falls dein Lohn nicht am Monatsersten kommt (z.B. am 25.), lässt
          sich der Budget-Monat entsprechend verschieben (z.B. 25. bis 24. des Folgemonats), statt starr dem
          Kalendermonat zu folgen.
        </p>
        <p>
          <strong>Darstellung</strong>: Hell/Dunkel lässt sich manuell umschalten, unabhängig von der
          Systemeinstellung.
        </p>
      </div>
    </>
  )
}

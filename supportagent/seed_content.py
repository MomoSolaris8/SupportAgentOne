"""Synthetic German insurance content used to seed a real Confluence space + Jira project.

All content is fictional internal documentation inspired by typical German
insurance terminology (Hausrat-, Haftpflicht-, Rechtsschutz-, Wohngebaeude-,
Kfz-Versicherung). It is written from scratch for this learning project and
is not copied from any real insurer's terms and conditions.
"""

# "Projects" are top-level Confluence pages; every entry in CONFLUENCE_PAGES is
# created as a child page under the project named in its "project" key.
PROJECTS = [
    {
        "key": "privatkunden",
        "title": "Privatkundenprodukte",
        "body": (
            "<p>Produktdokumentation fuer die privaten Versicherungsprodukte: "
            "Hausrat-, Haftpflicht-, Wohngebaeude- und Rechtsschutzversicherung.</p>"
        ),
    },
    {
        "key": "kfz",
        "title": "Kfz-Versicherung",
        "body": "<p>Produkt- und Schadeninformationen rund um Kfz-Versicherungen.</p>",
    },
    {
        "key": "schadenbearbeitung",
        "title": "Schadenbearbeitung",
        "body": (
            "<p>Prozesse rund um Schadenmeldung, Bearbeitung und Eskalation, "
            "uebergreifend fuer alle Versicherungsprodukte.</p>"
        ),
    },
]


CONFLUENCE_PAGES = [
    {
        "title": "Hausratversicherung - Leistungsuebersicht",
        "project": "privatkunden",
        "labels": ["hausrat", "produkt"],
        "body": (
            "<h2>Was ist versichert?</h2>"
            "<p>Die Hausratversicherung deckt alle Gegenstaende ab, die sich im Eigentum des "
            "Versicherungsnehmers befinden und der Einrichtung des versicherten Haushalts dienen. "
            "Dazu zaehlen Moebel, Kleidung, elektronische Geraete, Hausrat in Kueche und Bad sowie "
            "persoenliche Gegenstaende wie Schmuck und Buecher.</p>"
            "<h2>Versicherte Gefahren</h2>"
            "<p>Im Standardtarif sind folgende Gefahren eingeschlossen:</p>"
            "<ul>"
            "<li>Feuer, Blitzschlag und Explosion</li>"
            "<li>Einbruchdiebstahl, Vandalismus nach Einbruch und Raub</li>"
            "<li>Leitungswasserschaeden, auch durch Aquarien oder Wasserbetten</li>"
            "<li>Sturm (ab Windstaerke 8) und Hagel</li>"
            "</ul>"
            "<h2>Versicherungssumme und Unterversicherung</h2>"
            "<p>Die Versicherungssumme richtet sich nach der Wohnflaeche und sollte den Neuwert des "
            "gesamten Hausrats abdecken. Bei vielen Tarifen gilt ein Unterversicherungsverzicht bis "
            "zu einer bestimmten Quadratmeterzahl, sodass im Schadenfall keine Kuerzung wegen zu "
            "niedriger Versicherungssumme erfolgt.</p>"
            "<h2>Geltungsbereich</h2>"
            "<p>Versichert sind Gegenstaende innerhalb der Wohnung, in zugehoerigen Kellerraeumen, "
            "Dachboden und Garage. Gegenstaende im Freien (z. B. Gartenmoebel) sind nur eingeschraenkt "
            "mitversichert.</p>"
            "<h2>Fahrraddiebstahl</h2>"
            "<p>Der Diebstahl eines Fahrrads aus der Wohnung, dem Keller oder der abgeschlossenen "
            "Garage ist im Standardtarif mitversichert, sofern Einbruchspuren vorliegen. Diebstahl aus "
            "dem oeffentlichen Raum (z. B. von der Strasse) ist nur ueber den Zusatzbaustein "
            "'Fahrrad-Schutzbrief' abgedeckt.</p>"
        ),
    },
    {
        "title": "Private Haftpflichtversicherung - Produktbeschreibung",
        "project": "privatkunden",
        "labels": ["haftpflicht", "produkt"],
        "body": (
            "<h2>Deckungsumfang</h2>"
            "<p>Die private Haftpflichtversicherung schuetzt vor Schadenersatzanspruechen Dritter, "
            "wenn der Versicherungsnehmer oder mitversicherte Familienmitglieder einer anderen Person "
            "einen Schaden zufuegen. Abgedeckt sind Personenschaeden, Sachschaeden und daraus "
            "resultierende Vermoegensschaeden.</p>"
            "<h2>Deckungssumme</h2>"
            "<p>Uebliche Deckungssummen liegen zwischen 10 und 50 Millionen Euro pauschal fuer "
            "Personen-, Sach- und Vermoegensschaeden. Eine hoehere Deckungssumme wird insbesondere bei "
            "Personenschaeden empfohlen, da Folgekosten (z. B. Pflege, Verdienstausfall) erheblich sein "
            "koennen.</p>"
            "<h2>Was ist nicht versichert?</h2>"
            "<ul>"
            "<li>Vorsaetzlich verursachte Schaeden</li>"
            "<li>Schaeden im Rahmen einer beruflichen oder gewerblichen Taetigkeit</li>"
            "<li>Schaeden an eigenen Sachen des Versicherungsnehmers</li>"
            "<li>Schaeden durch bestimmte Tierhaltung, sofern keine separate Tierhalterhaftpflicht "
            "besteht</li>"
            "</ul>"
            "<h2>Zusatzbausteine</h2>"
            "<p>Ueber den Zusatzbaustein 'Mietsachschaeden' koennen auch Schaeden an gemieteten "
            "Wohnungen (z. B. durch Brand oder Leitungswasser) eingeschlossen werden. Der Baustein "
            "'Forderungsausfalldeckung' greift, wenn ein Dritter dem Versicherungsnehmer einen Schaden "
            "zufuegt, dieser jedoch selbst nicht versichert oder zahlungsfaehig ist.</p>"
        ),
    },
    {
        "title": "Schadenmeldung - Prozessablauf und benoetigte Unterlagen",
        "project": "schadenbearbeitung",
        "labels": ["claims", "schadenmeldung", "produkt"],
        "body": (
            "<h2>Meldefrist</h2>"
            "<p>Schaeden sind dem Versicherer unverzueglich, spaetestens jedoch innerhalb von einer "
            "Woche nach Kenntnisnahme, zu melden. Bei Schaeden durch Diebstahl oder Einbruch ist "
            "zusaetzlich unverzueglich die Polizei zu informieren.</p>"
            "<h2>Meldewege</h2>"
            "<p>Eine Schadenmeldung kann ueber das Kunden-Onlineportal, die mobile App oder telefonisch "
            "ueber die Schadenhotline erfolgen. Fuer die meisten Standardfaelle wird die Meldung ueber "
            "das Onlineportal empfohlen, da hier direkt Dokumente hochgeladen werden koennen.</p>"
            "<h2>Benoetigte Unterlagen</h2>"
            "<ul>"
            "<li>Ausgefuelltes Schadenformular mit Schilderung des Schadenablaufs</li>"
            "<li>Fotos des Schadens bzw. der beschaedigten Gegenstaende</li>"
            "<li>Kaufbelege oder Rechnungen fuer beschaedigte oder gestohlene Gegenstaende</li>"
            "<li>Polizeibericht bei Einbruch, Diebstahl oder Vandalismus</li>"
            "<li>Kostenvoranschlag oder Reparaturrechnung eines Fachbetriebs, sofern vorhanden</li>"
            "</ul>"
            "<h2>Wartezeiten</h2>"
            "<p>Fuer neu abgeschlossene Vertraege gelten je nach Produkt unterschiedliche Wartezeiten, "
            "bevor Versicherungsschutz greift. Bei der Rechtsschutzversicherung betraegt die Wartezeit "
            "in der Regel drei Monate, bei Hausrat- und Haftpflichtversicherung besteht in der Regel "
            "keine Wartezeit.</p>"
            "<h2>Bearbeitungszeit</h2>"
            "<p>Nach vollstaendigem Eingang aller Unterlagen erfolgt in der Regel innerhalb von 10 "
            "Werktagen eine erste Rueckmeldung zur Schadenregulierung. Bei komplexen Schaeden oder "
            "Eskalationsfaellen kann sich die Bearbeitungszeit verlaengern.</p>"
        ),
    },
    {
        "title": "Rechtsschutzversicherung - Leistungsuebersicht und Ausschluesse",
        "project": "privatkunden",
        "labels": ["rechtsschutz", "produkt"],
        "body": (
            "<h2>Deckungsbereiche</h2>"
            "<p>Die Rechtsschutzversicherung umfasst je nach Tarif mehrere Bausteine: "
            "Privat-Rechtsschutz (z. B. Streitigkeiten im Alltag, Kauf- und Mietrecht), "
            "Verkehrs-Rechtsschutz (Streitigkeiten rund um das eigene Fahrzeug) und Berufs-Rechtsschutz "
            "(arbeitsrechtliche Streitigkeiten).</p>"
            "<h2>Wartezeit</h2>"
            "<p>Fuer die meisten Bausteine gilt eine Wartezeit von drei Monaten nach Vertragsbeginn. "
            "Eine Ausnahme bildet der Verkehrs-Rechtsschutz nach einem Unfall: Hier besteht "
            "Versicherungsschutz bereits ab dem ersten Tag, wenn der Unfall ohne eigenes Verschulden "
            "geschah.</p>"
            "<h2>Ausschluesse</h2>"
            "<ul>"
            "<li>Streitigkeiten rund um Bauvorhaben oder Grundstuecksgeschaefte sind im Standardtarif "
            "nicht versichert und erfordern den Zusatzbaustein 'Bau- und Grundstuecks-Rechtsschutz'.</li>"
            "<li>Familien- und erbrechtliche Streitigkeiten sind teilweise ausgeschlossen, insbesondere "
            "wenn sie vor Vertragsbeginn entstanden sind.</li>"
            "<li>Rechtsfaelle, deren Ursache bereits vor Vertragsabschluss eingetreten ist "
            "(Vorvertraglichkeit), sind generell ausgeschlossen.</li>"
            "</ul>"
            "<h2>Mediation</h2>"
            "<p>Im Premium-Tarif ist eine Mediationsleistung enthalten. Diese deckt die Kosten fuer ein "
            "Mediationsverfahren in allen versicherten Rechtsbereichen ab, sofern der Streitgegenstand "
            "grundsaetzlich vom jeweiligen Baustein gedeckt ist.</p>"
        ),
    },
    {
        "title": "Wohngebaeudeversicherung - Produktbeschreibung",
        "project": "privatkunden",
        "labels": ["wohngebaeude", "produkt"],
        "body": (
            "<h2>Deckungsumfang</h2>"
            "<p>Die Wohngebaeudeversicherung schuetzt das Gebaeude selbst sowie fest mit dem Gebaeude "
            "verbundene Bestandteile gegen Schaeden durch Feuer, Leitungswasser, Sturm und Hagel. "
            "Mitversichert sind in der Regel auch Garagen, Carports und Nebengebaeude auf demselben "
            "Grundstueck.</p>"
            "<h2>Elementarschutz</h2>"
            "<p>Schaeden durch Naturgefahren wie Ueberschwemmung, Erdbeben, Erdsenkung oder "
            "Schneedruck sind nur ueber den optionalen Zusatzbaustein 'Elementarschadenversicherung' "
            "abgedeckt und nicht im Basistarif enthalten.</p>"
            "<h2>Unterversicherung</h2>"
            "<p>Bei Berechnung der Versicherungssumme nach dem Wert-1914-Verfahren verzichtet der "
            "Versicherer auf die Einrede der Unterversicherung, sofern die Angaben zum Gebaeude bei "
            "Vertragsschluss korrekt waren.</p>"
            "<h2>Besonderheiten bei Leitungswasserschaeden</h2>"
            "<p>Bei einem Leitungswasserschaden sollten vor Beginn von Reparaturarbeiten Fotos der "
            "betroffenen Stellen gemacht werden. Die Rechnung des Handwerksbetriebs sowie ein kurzer "
            "Bericht zur Schadenursache (z. B. Rohrbruch, undichte Anschlussleitung) sind fuer die "
            "Bearbeitung erforderlich.</p>"
        ),
    },
    {
        "title": "Kfz-Schaden - Ablauf, Selbstbeteiligung und Unterlagen",
        "project": "kfz",
        "labels": ["kfz", "claims", "produkt"],
        "body": (
            "<h2>Versicherungsarten</h2>"
            "<p>Bei Kraftfahrzeugversicherungen wird zwischen Kfz-Haftpflichtversicherung (Pflicht), "
            "Teilkaskoversicherung und Vollkaskoversicherung unterschieden. Die Teilkasko deckt unter "
            "anderem Diebstahl, Glasbruch, Wildunfaelle und Naturereignisse ab, die Vollkasko "
            "zusaetzlich auch selbst verursachte Unfallschaeden.</p>"
            "<h2>Selbstbeteiligung</h2>"
            "<p>Je nach Tarif und Schadenart gelten unterschiedliche Selbstbeteiligungen, typischerweise "
            "zwischen 150 und 500 Euro fuer Teilkasko- und 300 bis 1000 Euro fuer Vollkaskoschaeden. Bei "
            "Glasschaeden (z. B. Steinschlag an der Windschutzscheibe) sind die Tarife 'Komfort' und "
            "'Premium' selbstbeteiligungsfrei, im Tarif 'Basis' gilt die normale "
            "Teilkasko-Selbstbeteiligung.</p>"
            "<h2>Benoetigte Unterlagen</h2>"
            "<ul>"
            "<li>Europaeischer Unfallbericht oder eigene Schadenschilderung</li>"
            "<li>Fotos der Schaeden am eigenen und ggf. am gegnerischen Fahrzeug</li>"
            "<li>Kostenvoranschlag oder Gutachten einer Werkstatt bzw. eines Sachverstaendigen</li>"
            "<li>Polizeiprotokoll bei Personenschaeden, Fahrerflucht oder Verdacht auf "
            "Alkoholeinfluss</li>"
            "</ul>"
            "<h2>Schadenfreiheitsklasse</h2>"
            "<p>Die Inanspruchnahme der Vollkaskoversicherung fuer selbst verschuldete Schaeden fuehrt "
            "in der Regel zu einer Rueckstufung in der Schadenfreiheitsklasse und damit zu hoeheren "
            "Beitraegen in den Folgejahren. Bei kleineren Schaeden kann ein Rueckstufungsverzicht oder "
            "eine Schadenfreiheitsklassen-Garantie greifen, sofern vereinbart.</p>"
        ),
    },
    {
        "title": "Eskalationsprozesse in der Schadenbearbeitung",
        "project": "schadenbearbeitung",
        "labels": ["eskalation", "claims", "prozess"],
        "body": (
            "<h2>Wann wird eskaliert?</h2>"
            "<p>Eine Eskalation an die naechste Bearbeitungsebene erfolgt insbesondere in folgenden "
            "Faellen: Schadenhoehe ueberschreitet die Bearbeitungsvollmacht des Sachbearbeiters, "
            "Verdacht auf Versicherungsbetrug, schriftliche Kundenbeschwerde oder unklare "
            "Vertragsauslegung, die nicht anhand der bestehenden Produktdokumentation geklaert werden "
            "kann.</p>"
            "<h2>Eskalationsstufen</h2>"
            "<ul>"
            "<li>Stufe 1: Sachbearbeiter Claims (Erstbearbeitung)</li>"
            "<li>Stufe 2: Teamleitung Claims (bei Schadenhoehe ueber dem individuellen "
            "Bearbeitungslimit oder bei Kundenbeschwerden)</li>"
            "<li>Stufe 3: Fachbereich Recht (bei Verdacht auf Betrug, rechtlichen Streitfragen oder "
            "unklarer Vertragsauslegung)</li>"
            "</ul>"
            "<h2>Service Level fuer Rueckmeldungen</h2>"
            "<p>Nach Eskalation an die Teamleitung erfolgt eine Rueckmeldung innerhalb von zwei "
            "Werktagen. Eskalationen an den Fachbereich Recht werden innerhalb von fuenf Werktagen "
            "bearbeitet.</p>"
            "<h2>Dokumentationspflicht</h2>"
            "<p>Jede Eskalation muss im Schadenfallsystem mit Grund, Eskalationsstufe und Datum "
            "dokumentiert werden, damit der Bearbeitungsverlauf fuer nachfolgende Bearbeiter und fuer "
            "das Qualitaetsmanagement nachvollziehbar bleibt.</p>"
        ),
    },
]


JIRA_ISSUES = [
    {
        "summary": "Unklare Meldefrist bei Leitungswasserschaden: Hausrat vs. Wohngebaeude",
        "issue_type": "Task",
        "labels": ["hausrat", "wohngebaeude", "doku-luecke"],
        "description": (
            "Im Confluence-Artikel zur Schadenmeldung steht eine allgemeine Meldefrist von einer "
            "Woche. Fuer Leitungswasserschaeden bei der Wohngebaeudeversicherung wird in der Praxis "
            "jedoch oft eine Frist von 48 Stunden kommuniziert, um Folgeschaeden zu vermeiden. Bitte "
            "klaeren, ob es sich um eine separate Regel oder nur eine Empfehlung handelt, und die "
            "Dokumentation entsprechend anpassen."
        ),
        "comments": [
            "Ruecksprache mit dem Fachbereich Schaden ergab: Die vertragliche Meldefrist bleibt "
            "einheitlich bei einer Woche. Die 48-Stunden-Angabe ist keine Frist, sondern eine interne "
            "Empfehlung zur Schadenminimierung bei Wasserschaeden. Der Confluence-Artikel sollte diesen "
            "Unterschied explizit erklaeren, um Missverstaendnisse bei Kunden zu vermeiden."
        ],
    },
    {
        "summary": "Frage: Deckt Rechtsschutz Premium Mediationskosten bei Nachbarschaftsstreit ab?",
        "issue_type": "Task",
        "labels": ["rechtsschutz", "faq"],
        "description": (
            "Ein Kunde mit Rechtsschutz-Premium-Tarif fragt an, ob die Kosten fuer ein "
            "Mediationsverfahren bei einem Nachbarschaftsstreit (Grenzbepflanzung) uebernommen werden. "
            "Im Confluence-Artikel steht nur allgemein, dass Mediation im Premium-Tarif enthalten ist, "
            "ohne konkrete Beispiele fuer Rechtsbereiche."
        ),
        "comments": [
            "Laut Produktbedingungen Premium gilt die Mediationsleistung fuer alle versicherten "
            "Rechtsbereiche, also auch fuer Nachbarschaftsrecht im Rahmen des Privat-Rechtsschutzes. "
            "Voraussetzung ist, dass der Streitgegenstand grundsaetzlich vom jeweiligen Baustein "
            "gedeckt ist. Vorschlag: Im Confluence-Artikel ein konkretes Beispiel fuer "
            "Nachbarschaftsstreitigkeiten ergaenzen."
        ],
    },
    {
        "summary": "Selbstbeteiligung bei Kfz-Teilkasko nach Glasschaden uneinheitlich kommuniziert",
        "issue_type": "Task",
        "labels": ["kfz", "doku-luecke", "claims"],
        "description": (
            "Es gibt mehrere Kundenanfragen zur Selbstbeteiligung bei Glasschaeden (z. B. Steinschlag "
            "an der Windschutzscheibe). Der Confluence-Artikel nennt nur die allgemeine "
            "Teilkasko-Selbstbeteiligung, erwaehnt aber nicht, dass bestimmte Tarife bei Glasschaeden "
            "selbstbeteiligungsfrei sind."
        ),
        "comments": [
            "Bestaetigt durch Produktmanagement: In den Tarifen 'Komfort' und 'Premium' entfaellt die "
            "Selbstbeteiligung bei reinen Glasschaeden vollstaendig. Im Tarif 'Basis' gilt weiterhin "
            "die normale Teilkasko-Selbstbeteiligung. Bitte Produktuebersicht in Confluence um eine "
            "Tabelle je Tarif ergaenzen."
        ],
    },
    {
        "summary": "Eskalation bei Betrugsverdacht: Ansprechpartner im Fachbereich Recht unklar",
        "issue_type": "Task",
        "labels": ["eskalation", "doku-luecke"],
        "description": (
            "Im Confluence-Artikel zu Eskalationsprozessen wird bei Verdacht auf Versicherungsbetrug "
            "auf den 'Fachbereich Recht' verwiesen. Neue Mitarbeitende im Support wissen jedoch nicht, "
            "ueber welchen Kanal (Ticket-Queue, E-Mail-Verteiler, direkter Kontakt) der Fachbereich "
            "erreicht wird. Bitte konkretisieren und im Artikel ergaenzen."
        ),
        "comments": [],
    },
    {
        "summary": "Onboarding-Frage: Ist Fahrraddiebstahl ausserhalb der Wohnung ueber Hausrat versichert?",
        "issue_type": "Task",
        "labels": ["hausrat", "faq", "onboarding"],
        "description": (
            "Ein neuer Support Agent fragt, ob der Diebstahl eines Fahrrads von der Strasse oder aus "
            "einem oeffentlichen Fahrradstaender ueber die normale Hausratversicherung abgedeckt ist, "
            "oder ob dafuer in jedem Fall der Zusatzbaustein 'Fahrrad-Schutzbrief' erforderlich ist."
        ),
        "comments": [
            "Im Standardtarif ist ein Fahrraddiebstahl nur versichert, wenn das Fahrrad aus der "
            "Wohnung, dem Keller oder einer abgeschlossenen Garage gestohlen wurde und Einbruchspuren "
            "vorliegen. Diebstahl aus dem oeffentlichen Raum, auch bei angeschlossenem Fahrrad, ist "
            "ausschliesslich ueber den Zusatzbaustein 'Fahrrad-Schutzbrief' versichert. Dies ist im "
            "Confluence-Artikel zur Hausratversicherung bereits korrekt beschrieben, kann aber in den "
            "FAQ fuer Support Agents zusaetzlich hervorgehoben werden."
        ],
    },
]

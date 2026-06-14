# Insurance Knowledge Search Dashboard - Architekturvorschlag v0.1

Status: Entwurf  
Owner: AI Engineering Candidate Project  
Zielgruppen: Support Agents, Claims Operations, Product Owner, Knowledge Manager  
Primaersprache: Deutsch  
Letzte Aktualisierung: 2026-06-12

## 1. Projektvision

Versicherungsunternehmen verteilen operatives Wissen haeufig auf mehrere interne Systeme. Produktregeln, Onboarding-Material, Schadenprozesse, Eskalationswege und haeufig gestellte Fragen liegen oft in Confluence, waehrend offene Fragen, Dokumentationsluecken und fachliche Klaerungen in Jira-Tickets diskutiert werden.

Ziel dieses Projekts ist der Aufbau eines internen Knowledge-Search-Dashboards. Mitarbeitende sollen deutschsprachige Fragen in natuerlicher Sprache stellen koennen und belastbare Antworten mit Quellenverweisen auf die urspruenglichen Confluence-Seiten oder Jira-Tickets erhalten.

Das Projekt ist kein generischer Chatbot-Demo-Prototyp. Es wird als Enterprise-Knowledge-Retrieval-System konzipiert, bei dem Nachvollziehbarkeit, Aktualitaet, Metadatenfilterung und Quellenangaben zentrale Anforderungen sind.

Beispielfrage:

> Welche Unterlagen benoetige ich fuer die Schadenmeldung in der privaten Haftpflichtversicherung?

Erwartetes Systemverhalten:

- relevante Confluence-Onboarding- und Prozessseiten abrufen
- optional verwandte Jira-Tickets zu Dokumentationsluecken oder Prozessklaerungen beruecksichtigen
- auf Deutsch antworten
- Quellenangaben zu Seiten oder Tickets anzeigen
- die Antwort einschraenken oder verweigern, wenn die verfuegbaren Quellen nicht ausreichen

## 2. User Stories

Als neuer Support Agent moechte ich deutschsprachige Fragen zu Versicherungsprodukten und Schadenprozessen stellen, damit ich schneller onboarden kann, ohne viele Wiki-Seiten manuell zu durchsuchen.

Als Claims Handler moechte ich die benoetigten Unterlagen fuer einen bestimmten Schadenfall abrufen, damit ich Kundenfaelle konsistent bearbeiten kann.

Als Product Owner moechte ich Jira-Tickets finden, die auf unklare Dokumentation hinweisen, damit ich Wissensluecken identifizieren und interne Anleitungen verbessern kann.

Als Knowledge Manager moechte ich, dass jede generierte Antwort Quellen enthaelt, damit ich pruefen kann, ob die Antwort auf freigegebenen internen Inhalten basiert.

Als Operations Lead moechte ich Suchergebnisse nach Quelle, Produktlinie, Label und Aktualisierungszeit filtern koennen, damit Nutzer den relevanten fachlichen Kontext eingrenzen koennen.

Als Admin moechte ich aktualisierte Confluence-Seiten und Jira-Issues inkrementell synchronisieren, damit der Suchindex aktuell bleibt, ohne alle Inhalte erneut zu verarbeiten.

## 3. Datenquellen-Design

### 3.1 Confluence

Confluence wird als primaere Quelle fuer freigegebenes Wissen behandelt.

Typische Inhalte:

- Produktbeschreibungen
- Onboarding-Dokumente
- Schadenprozess-Dokumentation
- FAQ-Seiten
- Eskalationsregeln
- interne Erklaerungen zu Policen und Bedingungen

Relevante Felder:

- Page ID
- Titel
- Space Key
- Labels
- Body Content
- Version
- Zeitpunkt der letzten Aktualisierung
- Autor oder verantwortliches Team
- Web-URL
- Access Scope

Confluence-Seiten sind in der Regel autoritativer als Jira-Tickets. Wenn Confluence und Jira ueberschneidende Informationen enthalten, sollte die Antwortgenerierung freigegebene Confluence-Inhalte bevorzugen.

### 3.2 Jira

Jira wird als sekundaere Quelle fuer operatives und historisches Wissen behandelt.

Typische Inhalte:

- Support-Fragen
- Dokumentations-Bugs
- fachliche Klaerungstickets
- Incidents im Schadenprozess
- Aufgaben zur Aktualisierung interner Dokumentation
- Diskussionen in Kommentaren

Relevante Felder:

- Issue ID
- Issue Key
- Summary
- Description
- Kommentare
- Project Key
- Issue Type
- Status
- Labels
- Erstellungs- und Aktualisierungszeitpunkt
- verknuepfte Confluence-Seiten
- Web-URL
- Access Scope

Jira-Daten sind nuetzlich, aber potenziell verrauscht. Sie koennen offene Diskussionen, veraltete Annahmen oder falsche Zwischenergebnisse enthalten. Das System soll Jira-Quellen sichtbar machen, aber nicht jeden Jira-Kommentar als autoritative Wahrheit behandeln.

### 3.3 Mock-Datenstrategie

Das MVP startet mit mock-basierten Atlassian APIs, damit keine echten Atlassian-Zugangsdaten erforderlich sind.

Die Mock APIs sollen die Struktur realer Confluence- und Jira-Antworten nachbilden:

- `GET /wiki/api/v2/pages`
- `GET /wiki/api/v2/pages/{id}`
- `GET /rest/api/3/search`

Die fachlichen Inhalte sollen synthetisch, aber realistisch fuer den deutschen Versicherungsbereich sein. Der erste Datensatz soll folgende Themen abdecken:

- Hausratversicherung
- private Haftpflichtversicherung
- Rechtsschutzversicherung
- Wohngebaeudeversicherung
- Kfz-Schaden
- Schadenmeldung
- Wartezeiten
- Ausschluesse
- benoetigte Unterlagen
- Eskalationsprozesse

Oeffentliche Versicherungsunterlagen, zum Beispiel deutsche Musterbedingungen, koennen als Inspiration fuer Themen und Terminologie dienen. Der oeffentlich demonstrierbare Datensatz soll dennoch als synthetische interne Unternehmensdokumentation formuliert werden, um urheberrechtliche und lizenzrechtliche Risiken zu vermeiden.

## 4. Document Contract

Alle quellenspezifischen Datensaetze werden vor Chunking und Embedding in ein gemeinsames internes Dokumentmodell normalisiert.

```text
Document {
  id: string
  text: string
  metadata: {
    source: "confluence" | "jira"
    source_id: string
    title: string
    url: string
    labels: string[]
    updated_at: datetime
    version?: string
    space_key?: string
    project_key?: string
    issue_key?: string
    issue_type?: string
    status?: string
    owner_team?: string
    access_scope?: string
  }
}
```

Das Feld `text` wird fuer Chunking, Embeddings und Retrieval verwendet.

Das Feld `metadata` wird verwendet fuer:

- Source Filtering
- Quellenangaben
- inkrementelle Synchronisierung
- Zugriffskontrolle
- Ranking-Anpassungen
- Observability und Debugging

Dieser Contract entkoppelt die nachgelagerte RAG-Pipeline von Atlassian-spezifischen APIs. Wenn spaeter SharePoint, ServiceNow oder interne PDFs hinzukommen, sollte nur ein neuer Connector und Normalizer erforderlich sein.

## 5. Systemarchitektur

### 5.1 High-Level-Architektur

```text
Confluence API          Jira API
      |                    |
      v                    v
Source Connectors / API Clients
      |
      v
Document Normalizer
      |
      v
Chunking Pipeline
      |
      v
Embedding Service
      |
      v
PostgreSQL + pgvector
      |
      v
Retrieval Service
      |
      v
LLM Answer Service
      |
      v
Dashboard UI
```

### 5.2 Verantwortlichkeiten der Komponenten

Source Connectors laden Rohdaten aus Confluence und Jira. Sie behandeln Pagination, Authentifizierung, Retry-Verhalten und Grenzen fuer inkrementelle Synchronisierung.

Der Document Normalizer wandelt quellenspezifische Rohdaten in den gemeinsamen `Document` Contract um.

Die Chunking Pipeline zerlegt Dokumente in wiederauffindbare Einheiten und erhaelt die Metadaten des Ursprungsdokuments fuer spaetere Quellenangaben.

Der Embedding Service wandelt Chunks und Nutzerfragen in Vektoren um. Dafuer wird ein mehrsprachiges Embedding-Modell benoetigt, das gut mit deutschen Fachbegriffen aus der Versicherungsdomaene funktioniert.

PostgreSQL mit pgvector speichert Chunks, Embeddings, Metadaten und Referenzen auf Ursprungsdokumente in einer gemeinsamen Datenbank.

Der Retrieval Service fuehrt semantische Suche, Metadatenfilterung und Ranking durch.

Der LLM Answer Service generiert deutschsprachige Antworten aus dem abgerufenen Kontext und erzwingt Regeln fuer Quellenangaben und kontrollierte Ablehnung.

Die Dashboard UI stellt Chat- und Suchinteraktion, Source-Filter, Quellenvorschau und Links auf Ursprungsdokumente bereit.

### 5.3 Einordnung von Frameworks

Das MVP sollte nicht von LangGraph abhaengen. Die erste Version ist eine deterministische RAG-Pipeline, kein mehrstufiger autonomer Agent.

LangChain kann selektiv fuer Model Adapter, Text Splitter oder Vector-Store-Integration genutzt werden. Die Kerninterfaces des Projekts sollen jedoch framework-unabhaengig bleiben.

LangGraph wird in einer spaeteren Version relevant, wenn das System zustandsbehaftete mehrstufige Workflows benoetigt, zum Beispiel:

- Query Intent klassifizieren
- zwischen Confluence, Jira oder beiden Quellen routen
- JQL generieren und validieren
- vor Antworten zu sensiblen Schadenfragen menschliche Freigabe einholen
- Fallback Retrieval oder Retry-Strategien ausfuehren
- laenger laufende Rechercheprozesse mit Zustand verwalten

Graphdatenbanken sind nicht Teil des MVP. Sie koennen spaeter evaluiert werden, wenn explizite Beziehungstraversierung benoetigt wird, zum Beispiel Policy-to-Coverage-to-Exclusion-Graphen.

## 6. Retrieval-Strategie

### 6.1 MVP Retrieval Flow

```text
Nutzerfrage
  -> sprachliche Normalisierung
  -> Query Embedding
  -> pgvector Top-k Retrieval
  -> Metadatenfilter
  -> Kontextzusammenstellung
  -> LLM-Antwortgenerierung
  -> Quellenangaben an die UI
```

Das System soll Filter unterstützen wie:

- Quelle: Confluence oder Jira
- Produktlinie
- Label
- Project Key
- Space Key
- Aktualisierungsdatum
- Issue Status

### 6.2 Chunking-Strategie

Confluence-Seiten sollen moeglichst nach Ueberschriften und Absaetzen gechunkt werden. Dadurch bleibt die semantische Struktur erhalten und Quellenangaben werden praeziser.

Jira-Issues sollen zunaechst als Issue-Level-Dokumente indexiert werden, da Summary, Description und Kommentare meist kurz und stark kontextabhaengig sind. Wenn Kommentare sehr lang werden, koennen sie separat gechunkt werden, wobei der Parent Issue Key erhalten bleibt.

Jeder Chunk soll folgende Informationen speichern:

```text
chunk_id
document_id
chunk_index
content
embedding
metadata
```

### 6.3 Ranking-Strategie

Das MVP verwendet Vektoraehnlichkeit als primaeres Ranking-Signal.

Das Ranking soll durch die Qualitaet der Quelle angepasst werden:

- freigegebene Confluence-Seiten ranken hoeher als Jira-Kommentare
- neuere Versionen ranken hoeher als veraltete Seiten
- exakte Label- oder Produktfilter ranken hoeher als generische Treffer
- abgeschlossene Jira-Tickets koennen fuer fachliche Antworten hoeher ranken als offene Diskussionen

### 6.4 Regeln fuer Antwortgenerierung

Das LLM muss auf Deutsch antworten.

Das LLM muss die fuer die Antwort verwendeten Quelldokumente zitieren.

Das LLM darf keine Policen-, Leistungs- oder Prozessdetails erfinden, die nicht im abgerufenen Kontext enthalten sind.

Wenn der abgerufene Kontext nicht ausreicht, soll das System kontrolliert ausweichen:

```text
Ich kann diese Frage anhand der verfuegbaren Quellen nicht verlaesslich beantworten.
Bitte pruefen Sie die offiziellen Versicherungsbedingungen oder eskalieren Sie an das zustaendige Fachteam.
```

Bei widerspruechlichen Quellen soll die Antwort freigegebene Confluence-Inhalte bevorzugen und erwaehnen, wenn verwandte Jira-Tickets auf eine moegliche Dokumentationsluecke hindeuten.

## 7. Deployment-Plan

### 7.1 MVP Deployment

Das MVP soll mit Docker Compose lauffaehig sein.

Services:

- Dashboard Frontend
- Backend API
- Ingestion Worker
- PostgreSQL mit pgvector

Optionale lokale Services:

- lokales Embedding-Modell oder externe Embedding API
- lokales LLM ueber Ollama oder externer LLM Provider

Die erste deploybare Version soll lokal und auf einer kleinen Cloud VM laufen koennen.

### 7.2 Entwicklung Richtung Produktion

Eine produktionsnahe Version wuerde ergaenzen:

- echte Atlassian-Cloud-Authentifizierung
- Secret Management
- geplante Ingestion Jobs
- Retry- und Dead-Letter-Mechanismen
- strukturiertes Logging
- Tracing fuer Retrieval- und LLM-Aufrufe
- Evaluationsdatensaetze
- SSO
- rollenbasierte Zugriffskontrolle
- Monitoring und Alerting
- Backup und Restore fuer PostgreSQL
- CI/CD

Die Architektur trennt Ingestion, Retrieval, Antwortgenerierung und Frontend-Verantwortlichkeiten, damit diese Komponenten spaeter unabhaengig deployed werden koennen.

## 8. Risiken und Tradeoffs

### Halluzination

Risiko: Das LLM generiert Antworten, die nicht durch die abgerufenen Quellen gedeckt sind.

Mitigation:

- Quellenangaben verpflichtend machen
- strikte Answer Prompts verwenden
- bei unzureichendem Kontext kontrolliert ablehnen
- Antworten gegen Testfragen evaluieren

### Veraltetes Wissen

Risiko: Suchergebnisse verwenden veraltete Confluence-Seiten oder alte Jira-Diskussionen.

Mitigation:

- `updated_at` und Version-Metadaten speichern
- inkrementelle Synchronisierung durchfuehren
- neuere freigegebene Seiten bevorzugen
- Quellenzeitpunkte in der UI anzeigen

### Permission Leakage

Risiko: Nutzer koennen Inhalte abrufen, fuer die sie keine Berechtigung haben.

Mitigation:

- Access-Metadaten auf Source-Ebene speichern
- Permission Filter vor dem Retrieval anwenden
- nicht nur auf Frontend-Filter vertrauen
- in Produktion am Atlassian-Berechtigungsmodell ausrichten

### Noisy Jira Data

Risiko: Jira-Kommentare enthalten ungepruefte oder veraltete Informationen.

Mitigation:

- Confluence fuer fachliche Antworten hoeher ranken
- Jira-Tickets als unterstuetzende Evidenz sichtbar machen
- offene Tickets nicht als autoritative Quelle behandeln

### Schlechte deutsche Retrieval-Qualitaet

Risiko: Das Embedding-Modell funktioniert schlecht mit deutscher Versicherungsterminologie.

Mitigation:

- mehrsprachige Embeddings verwenden
- deutschen Evaluationsdatensatz erstellen
- Suchanfragen mit Synonymen und fachlicher Terminologie testen

### Framework Lock-in

Risiko: Uebermaessige Nutzung von LangChain oder LangGraph erschwert Wartung oder Migration.

Mitigation:

- interne Interfaces fuer Connectors, Normalizers, Retrievers und Generators definieren
- LangChain/LangGraph hinter Adapter-Schichten halten
- mit deterministischer Pipeline starten

## 9. MVP Scope

### In Scope

- synthetischer deutscher Versicherungsdatensatz
- Mock Confluence API
- Mock Jira API
- Source Connectors
- Document Normalization
- Chunking
- PostgreSQL mit pgvector
- semantisches Retrieval
- Metadatenfilterung
- deutschsprachige Antwortgenerierung
- Quellenangaben zu Ursprungsdokumenten
- einfaches Dashboard UI
- Docker Compose Deployment

### Out of Scope

- echtes SSO
- vollstaendige Atlassian-Permission-Synchronisierung
- Write-back nach Confluence oder Jira
- Graphdatenbank
- LangGraph Workflow Orchestration
- automatisierte Schadenentscheidung
- Produktionsmonitoring
- Multi-Tenant Deployment

## 10. Meilensteine

### Meilenstein 1: Architektur- und Datensatzdesign

Deliverables:

- Architekturvorschlag
- Document Contract
- synthetisches Confluence/Jira-Datensatzdesign
- Mock-API-Design

### Meilenstein 2: Ingestion und Normalisierung

Deliverables:

- Confluence Connector
- Jira Connector
- normalisierte Dokumente
- Ingestion Logs

### Meilenstein 3: Vector Storage und Retrieval

Deliverables:

- PostgreSQL- und pgvector-Schema
- Chunking Pipeline
- Embedding Pipeline
- Semantic-Search-Endpunkt

### Meilenstein 4: RAG Answer API

Deliverables:

- deutschsprachiger Question-Answering-Endpunkt
- Quellenangaben
- Fallback-Verhalten bei unzureichendem Kontext
- grundlegende Evaluationsfragen

### Meilenstein 5: Dashboard

Deliverables:

- Chat- und Such-UI
- Filter
- Quellenvorschau
- Source Links

### Meilenstein 6: Production-Hardening-Plan

Deliverables:

- Security Review
- Permission-Model-Design
- Strategie fuer inkrementelle Synchronisierung
- Deployment-Dokumentation

## 11. Offene Fragen

- Welches Embedding-Modell eignet sich am besten fuer deutsche Versicherungsterminologie?
- Soll das Backend vollstaendig in Python umgesetzt werden, oder als Split aus Spring Boot fuer Business APIs und Python fuer die RAG-Pipeline?
- Wie koennen Source Permissions im MVP modelliert werden, ohne echtes Atlassian SSO zu integrieren?
- Sollen Jira-Tickets standardmaessig im Antwortkontext enthalten sein, oder nur wenn der Nutzer Jira explizit auswaehlt?
- Wie gross muss der Evaluationsdatensatz mindestens sein, bevor das MVP als verlaesslich bezeichnet werden kann?

## 12. Empfohlene Initialentscheidung

Das MVP wird als deterministisches RAG-System ohne LangGraph und ohne Graphdatenbank gebaut.

Zuerst werden mock-basierte Atlassian APIs und synthetische deutsche Versicherungsinhalte verwendet. Source Connectors, Document Normalization, Retrieval und Antwortgenerierung bleiben durch klare Interfaces getrennt.

PostgreSQL mit pgvector wird fuer Metadaten und Vektorsuche genutzt. LangGraph wird erst eingefuehrt, wenn die Basispipeline funktioniert und ein konkreter Bedarf fuer zustandsbehaftete mehrstufige Orchestrierung besteht.

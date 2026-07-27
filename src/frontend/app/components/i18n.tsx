"use client";

import { createContext, ReactNode, useContext, useEffect, useState } from "react";

export type UiLocale = "de" | "en";

const storageKey = "supportagent.ui-locale";

const german: Record<string, string> = {
  "Account": "Konto",
  "Create account": "Konto erstellen",
  "Create a local account": "Lokales Konto erstellen",
  "Display name": "Anzeigename",
  "Email": "E-Mail",
  "Forgot password?": "Passwort vergessen?",
  "New password": "Neues Passwort",
  "Open password reset link": "Link zum Zurücksetzen öffnen",
  "Password": "Passwort",
  "Register": "Registrieren",
  "Reset password": "Passwort zurücksetzen",
  "Send reset link": "Link zum Zurücksetzen senden",
  "Sign in": "Anmelden",
  "Update password": "Passwort aktualisieren",
  "Use existing account": "Bestehendes Konto verwenden",
  "Active case": "Aktiver Schadenfall",
  "Agent mode": "Agentenmodus",
  "All": "Alle",
  "Answer": "Antwort",
  "Approvals": "Freigaben",
  "Ask about claims operations…": "Fragen Sie zu Schadenprozessen…",
  "Ask about the active case": "Fragen Sie zum aktiven Schadenfall",
  "Ask about this claim…": "Fragen Sie zu diesem Schadenfall…",
  "Assistant": "Assistent",
  "Assistant model": "Assistentenmodell",
  "Audit": "Audit",
  "Business": "Fachbereich",
  "Cancel": "Abbrechen",
  "Case assistant": "Fallassistent",
  "Chat": "Chat",
  "Chats": "Chats",
  "Claims": "Schadenfälle",
  "Claims Control": "Schadensteuerung",
  "Claims desk": "Schadenbearbeitung",
  "Claims operator": "Schadenbearbeiter",
  "Close assistant": "Assistent schließen",
  "Close navigation": "Navigation schließen",
  "Connect Microsoft": "Microsoft verbinden",
  "Controlled workspace": "Kontrollierter Arbeitsbereich",
  "Daily mode": "Alltagsmodus",
  "Dark": "Dunkel",
  "Delete": "Löschen",
  "Enable dark mode": "Dunkelmodus aktivieren",
  "Enable light mode": "Hellmodus aktivieren",
  "Edit": "Bearbeiten",
  "Evidence-bound guidance": "Evidenzgebundene Unterstützung",
  "Evidence-bound · No status changes": "Evidenzgebunden · Keine Statusänderungen",
  "Existing event reused": "Bestehender Termin verwendet",
  "Harness": "Harness",
  "Human control": "Menschliche Kontrolle",
  "Image": "Bild",
  "Insurance Knowledge Workspace": "Arbeitsbereich Versicherungswissen",
  "Insurance SupportAgent": "Versicherungs-SupportAgent",
  "Integrations": "Integrationen",
  "Knowledge assistant": "Wissensassistent",
  "Loading account": "Konto wird geladen",
  "Loading conversation.": "Unterhaltung wird geladen.",
  "Loading conversation…": "Unterhaltung wird geladen…",
  "Light": "Hell",
  "Local account": "Lokales Konto",
  "MCP Center": "MCP-Zentrale",
  "Model": "Modell",
  "Navigation": "Navigation",
  "New chat": "Neuer Chat",
  "No saved chats yet.": "Noch keine gespeicherten Chats.",
  "Open navigation": "Navigation öffnen",
  "Operations assistant": "Prozessassistent",
  "Question": "Frage",
  "Remove": "Entfernen",
  "Resize assistant": "Assistentengröße ändern",
  "Restoring messages from this thread.": "Nachrichten dieser Unterhaltung werden wiederhergestellt.",
  "Reviewing available evidence…": "Verfügbare Evidenz wird geprüft…",
  "Runs": "Ausführungen",
  "Save": "Speichern",
  "Send": "Senden",
  "Send message": "Nachricht senden",
  "Send a message to SupportAgent...": "Nachricht an SupportAgent senden…",
  "Sign out": "Abmelden",
  "Source": "Quelle",
  "Synthetic training data": "Synthetische Trainingsdaten",
  "Thinking...": "Denke nach…",
  "Try": "Beispiele",
  "Uploading...": "Wird hochgeladen…",
  "You": "Sie",
  "Calendar action detected. Review the details before execution.":
    "Kalenderaktion erkannt. Bitte prüfen Sie die Angaben vor der Ausführung.",
  "Calendar action failed.": "Kalenderaktion fehlgeschlagen.",
  "Calendar event": "Kalendertermin",
  "Created": "Erstellt",
  "Approval required": "Freigabe erforderlich",
  "Title": "Titel",
  "Date": "Datum",
  "Time": "Zeit",
  "Details": "Details",
  "Participants": "Teilnehmer",
  "Agenda": "Agenda",
  "Email addresses are required to send invitations; names are saved in the event details.":
    "Für Einladungen sind E-Mail-Adressen erforderlich; Namen werden in den Termindetails gespeichert.",
  "Confirm": "Bestätigen",
  "Creating calendar event…": "Kalendertermin wird erstellt…",
  "Open in Outlook": "In Outlook öffnen",
  "Action cancelled.": "Aktion abgebrochen.",
  "Edit & resend": "Bearbeiten & erneut senden",
  "Copy message": "Nachricht kopieren",
  "Copied": "Kopiert",
  "Calendar template": "Kalendervorlage",
  "Draft from chat": "Entwurf aus Chat",
  "Event title": "Termintitel",
  "Start": "Beginn",
  "End": "Ende",
  "Names or email addresses": "Namen oder E-Mail-Adressen",
  "Meeting purpose and discussion topics": "Zweck und Besprechungsthemen",
  "Complete title, date, start, and end before confirmation.":
    "Bitte Titel, Datum, Beginn und Ende vor der Bestätigung ausfüllen.",
  "Continue": "Weiter",
  "Evidence-bound claims control.": "Evidenzbasierte Schadensteuerung.",
  "Evidence gates": "Evidenzprüfungen",
  "Human approval": "Menschliche Freigabe",
  "Insurance operations": "Versicherungsprozesse",
  "Open reset link": "Link zum Zurücksetzen öffnen",
  "Please wait…": "Bitte warten…",
  "Set new password": "Neues Passwort festlegen",
  "Use an existing account": "Bestehendes Konto verwenden",
  "Review claim materials, inspect policy evidence, and govern every operational action.":
    "Prüfen Sie Schadenunterlagen und Vertragsnachweise und steuern Sie jede operative Aktion.",
  "for controlled actions": "für kontrollierte Aktionen",
  "before recommendations": "vor Empfehlungen",
  "Use your SupportAgent account to access the claims workspace.":
    "Melden Sie sich mit Ihrem SupportAgent-Konto an, um den Schadenarbeitsbereich zu öffnen.",
  "Actions require an explicit decision before execution.":
    "Aktionen erfordern vor der Ausführung eine ausdrückliche Entscheidung.",
  "Answers are constrained by approved policy evidence. Operational actions remain in the approval workflow.":
    "Antworten sind auf freigegebene Vertragsnachweise beschränkt. Operative Aktionen verbleiben im Freigabeprozess.",
  "Ask insurance questions, select MCP servers, and let the agent decide which tools to call.":
    "Stellen Sie Versicherungsfragen, wählen Sie MCP-Server und lassen Sie den Agenten über den Werkzeugeinsatz entscheiden."
};

type I18nContextValue = {
  locale: UiLocale;
  setLocale: (locale: UiLocale) => void;
  t: (text: string) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<UiLocale>("de");

  useEffect(() => {
    const stored = window.localStorage.getItem(storageKey);
    const initial: UiLocale = stored === "en" || stored === "de"
      ? stored
      : window.navigator.language.toLowerCase().startsWith("de")
        ? "de"
        : "en";
    setLocaleState(initial);
    document.documentElement.lang = initial;
  }, []);

  function setLocale(nextLocale: UiLocale) {
    setLocaleState(nextLocale);
    window.localStorage.setItem(storageKey, nextLocale);
    document.documentElement.lang = nextLocale;
  }

  function t(text: string) {
    return locale === "de" ? german[text] ?? text : text;
  }

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used inside I18nProvider");
  return context;
}

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale } = useI18n();

  return (
    <div className={`languageSwitcher ${compact ? "compact" : ""}`} aria-label="Language / Sprache" role="group">
      {(["de", "en"] as const).map((value) => (
        <button
          aria-pressed={locale === value}
          className={locale === value ? "active" : ""}
          key={value}
          onClick={() => setLocale(value)}
          type="button"
        >
          {value.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

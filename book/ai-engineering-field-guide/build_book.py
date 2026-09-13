from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf" / "deep-understanding-ai-engineering-v0.1.pdf"

NAVY = colors.HexColor("#153563")
BLUE = colors.HexColor("#2F66C5")
CYAN = colors.HexColor("#2AA9A1")
INK = colors.HexColor("#152033")
MUTED = colors.HexColor("#5D6A7E")
PALE = colors.HexColor("#EEF4FB")
PALE_GREEN = colors.HexColor("#EAF7F4")
LINE = colors.HexColor("#D7E0EB")
WHITE = colors.white


def register_fonts() -> None:
    font = Path("/Library/Fonts/Arial Unicode.ttf")
    if not font.exists():
        raise FileNotFoundError("Arial Unicode MS is required for bilingual rendering")
    pdfmetrics.registerFont(TTFont("BookSans", str(font)))


register_fonts()


styles = getSampleStyleSheet()
BODY = ParagraphStyle(
    "Body",
    parent=styles["BodyText"],
    fontName="BookSans",
    fontSize=9.4,
    leading=14.2,
    textColor=INK,
    spaceAfter=7,
)
SMALL = ParagraphStyle(
    "Small",
    parent=BODY,
    fontSize=7.7,
    leading=11,
    textColor=MUTED,
)
TITLE = ParagraphStyle(
    "Title",
    parent=BODY,
    fontSize=25,
    leading=31,
    textColor=NAVY,
    spaceAfter=9,
)
H1 = ParagraphStyle(
    "H1",
    parent=BODY,
    fontSize=17,
    leading=22,
    textColor=NAVY,
    spaceAfter=12,
)
H2 = ParagraphStyle(
    "H2",
    parent=BODY,
    fontSize=12.2,
    leading=16,
    textColor=NAVY,
    spaceBefore=4,
    spaceAfter=7,
)
EYEBROW = ParagraphStyle(
    "Eyebrow",
    parent=BODY,
    fontSize=8,
    leading=10,
    textColor=BLUE,
    spaceAfter=5,
)
BULLET = ParagraphStyle(
    "Bullet",
    parent=BODY,
    leftIndent=12,
    firstLineIndent=-7,
    bulletIndent=0,
    spaceAfter=4,
)
CODE = ParagraphStyle(
    "Code",
    parent=BODY,
    fontName="Courier",
    fontSize=7.3,
    leading=10,
    leftIndent=8,
    rightIndent=8,
    borderColor=LINE,
    borderWidth=0.6,
    borderPadding=8,
    backColor=colors.HexColor("#F7F9FC"),
)


@dataclass(frozen=True)
class ContentPage:
    chapter: int
    title: str
    thesis: str
    body: tuple[str, ...]
    bullets: tuple[str, ...]
    field_note: str
    interview: str
    code: str | None = None
    table: tuple[tuple[str, ...], ...] | None = None


CHAPTERS = [
    (1, "The AI Engineer Role", "AI engineering begins where probabilistic models meet production responsibility."),
    (2, "From Demo to Production", "The product is the controlled system around the model, not the model call."),
    (3, "Context, Retrieval and Memory", "Context quality is a runtime architecture problem, not a prompt-writing trick."),
    (4, "Workflows, Tools and Agents", "Use deterministic workflows until uncertainty genuinely requires model-directed action."),
    (5, "Evaluation and Observability", "A system you cannot evaluate cannot be improved or safely released."),
    (6, "Reliability, Cost and Latency", "Production quality is a portfolio of explicit trade-offs, budgets and failure modes."),
    (7, "Security and European Governance", "Permissions, provenance and evidence must be designed before autonomy is added."),
    (8, "The DACH Market", "The opportunity is real, but the market rewards evidence and senior-level ownership."),
    (9, "The AI Engineer Interview", "Strong candidates turn projects into measurable engineering decisions."),
    (10, "Production and Publishing Checklists", "A reusable checklist converts knowledge into operating leverage."),
]


PAGES: list[ContentPage] = [
    ContentPage(1, "Four roles, four centers of gravity",
        "Job titles overlap. The useful distinction is the artifact each role is accountable for.",
        ("A data scientist is usually judged on the quality of an analysis or model. An ML engineer owns the repeatable training and serving path. A software engineer owns a reliable product surface. An AI engineer combines the last two with model behavior, evaluation and human interaction.",
         "This is not a hierarchy. It is a change in the unit of responsibility: from a notebook result to a monitored decision system."),
        ("Data Scientist - insight, experiment, statistical validity.", "ML Engineer - pipelines, serving, feature and model lifecycle.", "Software Engineer - product behavior, APIs, state, reliability.", "AI Engineer - model behavior plus the complete production envelope."),
        "When a role description says 'AI Engineer' but measures only offline accuracy, the organization may still be operating with a data-science mental model.",
        "Explain which artifact you owned, which failure you prevented, and which metric changed.",
        table=(("Role", "Primary artifact", "Typical failure"), ("DS", "Decision / model", "Invalid inference"), ("MLE", "ML platform", "Training-serving skew"), ("SWE", "Product service", "Reliability defect"), ("AI Eng", "AI product system", "Uncontrolled behavior"))),
    ContentPage(1, "The production ownership test",
        "You are doing AI engineering when you are accountable for behavior after the model returns a response.",
        ("A production owner decides what happens when retrieval is empty, a provider times out, a tool changes schema, a user requests a forbidden action, or the model produces a plausible but unsupported claim.",
         "The role therefore spans interface design, data contracts, runtime policy, evaluation, observability and incident response. Model selection matters, but it is one decision among many."),
        ("Can the system fail safely?", "Can a result be traced to inputs, prompts, tools and versions?", "Can quality regressions be detected before users report them?", "Can cost and latency be explained per user journey?"),
        "A useful self-test: draw the system without the model box. If nothing remains, you have a demo rather than a product.",
        "Use one incident story to prove production ownership: symptom, blast radius, diagnosis, fix and prevention."),
    ContentPage(1, "A practical competency map",
        "Depth in one area plus working fluency across the system is more credible than claiming mastery everywhere.",
        ("The T-shaped profile for an AI engineer has a strong vertical in software, data or ML and a horizontal layer across prompting, retrieval, evaluation, security, product discovery and operations.",
         "For hiring, evidence beats tool lists. A small system with evaluation, traces and a rollback story demonstrates more than ten framework logos."),
        ("Foundation: Python or TypeScript, APIs, SQL, testing, Git.", "AI runtime: model APIs, structured outputs, tool calling, retrieval.", "Operations: deployment, telemetry, SLOs, incident handling.", "Judgment: problem framing, evaluation design, risk and product trade-offs."),
        "Choose one vertical advantage and make it visible: regulated data, platform engineering, evaluation, voice, vision or domain expertise.",
        "Frame your profile as 'deep in X, production-capable across Y' and support each claim with an artifact."),

    ContentPage(2, "The production envelope",
        "A model call becomes a product only after contracts, policy and feedback surround it.",
        ("The minimum production envelope contains input validation, context assembly, model routing, structured output validation, policy enforcement, telemetry and a user-visible recovery path.",
         "Every layer should have a deterministic responsibility. The model proposes; code validates, authorizes and commits."),
        ("Validate inputs before they enter context.", "Separate generation from side effects.", "Make provider and model versions explicit.", "Persist enough evidence to reproduce a failure without retaining unnecessary sensitive data."),
        "The most important boundary is between suggesting an action and executing it.",
        "Draw the envelope and point to the exact place where an unsafe or malformed output is stopped.",
        code="request -> validate -> retrieve -> generate\n        -> validate_output -> authorize -> act\n        -> observe -> evaluate"),
    ContentPage(2, "Release gates for probabilistic systems",
        "A passing unit-test suite is necessary but insufficient when behavior varies across inputs and model versions.",
        ("Release criteria should combine deterministic tests, an evaluation set, security tests, load tests and a human review sample. The gate must compare a candidate against the current production baseline.",
         "Separate hard constraints from quality preferences. Schema validity and permission checks are hard gates; tone and helpfulness may be scored and traded off."),
        ("Contract tests for tools and provider adapters.", "Golden evaluation set with versioned expected properties.", "Regression thresholds by segment, not only an average.", "Canary release with rollback and a limited blast radius."),
        "Averages hide rare but severe failures. Track the worst relevant segment and high-impact tasks separately.",
        "Describe a release decision you would block even if the average score improved."),
    ContentPage(2, "A failure taxonomy",
        "Debugging accelerates when failures are classified by system layer rather than called 'hallucinations'.",
        ("A wrong answer can originate in the request, retrieval, context ordering, model reasoning, tool output, output parser, authorization rule or stale business data. Each class needs a different owner and mitigation.",
         "Attach a failure label to evaluation examples and incidents. Over time, the distribution tells you whether to change prompts, data, tools, models or the product promise."),
        ("Knowledge failure - missing, stale or conflicting evidence.", "Reasoning failure - evidence exists but is misused.", "Action failure - wrong tool, parameters or permissions.", "Product failure - the system promised more certainty than it could deliver."),
        "A taxonomy is useful only when each label maps to an engineering action.",
        "Take one bad output and trace it through the layers instead of blaming the model."),

    ContentPage(3, "Context is a data product",
        "The model sees a temporary database assembled for one request.",
        ("Context assembly should have sources, ownership, freshness, access rules and a measurable retrieval contract. The prompt is only the final serialization of that data product.",
         "Keep stable instructions separate from dynamic evidence. This improves auditability, caching and the ability to reason about what changed."),
        ("Define allowed source classes and trust levels.", "Record document identity, timestamp and retrieval score.", "Preserve citations through generation.", "Measure evidence coverage, not only answer similarity."),
        "If a user cannot tell where a claim came from, the system has lost provenance even when the answer is correct.",
        "Explain how you test whether the answer is supported by the retrieved evidence."),
    ContentPage(3, "RAG as an information-retrieval system",
        "Chunking and embeddings are implementation details; the goal is evidence recall under a context budget.",
        ("Start by defining questions, answer-bearing units and the acceptable source corpus. Build a small labeled query set before tuning chunk size or adding a reranker.",
         "Hybrid search often helps when exact identifiers and semantic meaning both matter. Metadata filters enforce tenancy, language, date and document type before ranking."),
        ("Measure retrieval recall at k on answer-bearing evidence.", "Test empty, conflicting and stale retrieval cases.", "Use reranking only when it improves the labeled set.", "Expose 'insufficient evidence' as a valid product outcome."),
        "A generation model cannot recover evidence that retrieval never supplied.",
        "Be ready to explain one retrieval metric and one end-to-end answer metric."),
    ContentPage(3, "Memory without surveillance",
        "Memory should be an explicit product capability with scope, consent and deletion semantics.",
        ("Separate session state, user preferences, task artifacts and long-term summaries. They have different retention periods and different risk.",
         "Write memory through a policy-controlled path. Do not automatically preserve every conversation. Store the minimum useful representation and let the user inspect or remove it."),
        ("Session state - temporary facts required for the current task.", "Preference memory - user-controlled defaults.", "Artifact memory - files and decisions with clear ownership.", "Operational traces - limited retention for reliability and audit."),
        "The safest memory is often a small structured fact with provenance, not a transcript.",
        "Explain the difference between application state and model context."),

    ContentPage(4, "Workflow before agent",
        "Predictable tasks deserve predictable control flow.",
        ("A workflow encodes the path in software. An agent lets the model select steps and tools dynamically. Both may use the same models and tools, but their failure surfaces differ.",
         "Anthropic's production guidance similarly distinguishes predefined workflows from model-directed agents and recommends adding complexity only when it measurably helps [S6]."),
        ("Use a workflow when steps and validation rules are known.", "Use routing when inputs form stable categories.", "Use an agent when the path cannot be known in advance.", "Keep stopping conditions and approval points outside the model."),
        "Autonomy is not a feature by itself; it is a trade for flexibility.",
        "Give an example where you deliberately chose not to use an agent."),
    ContentPage(4, "Tools are capability boundaries",
        "A well-designed tool exposes a narrow business capability, not unrestricted infrastructure.",
        ("Tool descriptions, schemas and examples form an interface for a probabilistic caller. Parameters should be typed, enums constrained and error messages actionable.",
         "Authorization must be evaluated with the user identity and requested action at execution time. The model must never be the authority."),
        ("Prefer read tools and proposal tools before mutation tools.", "Make idempotency keys available for side effects.", "Return typed errors rather than prose-only failures.", "Require approval for costly, irreversible or external actions."),
        "Give the model the smallest capability that can complete the task.",
        "Sketch a tool schema and identify where authentication, authorization and idempotency live.",
        code='create_refund(case_id: str, amount_cents: int,\n              reason: RefundReason, idempotency_key: str)\n# authorization is enforced by the service'),
    ContentPage(4, "Agent loop and stopping conditions",
        "A useful loop is plan, act, observe and verify - with bounded resources and explicit exits.",
        ("Each observation should contain ground truth from the environment. The agent then decides whether the task is complete, blocked or requires another action.",
         "Stop on success, user input, a policy boundary, repeated failure, time budget, step budget or cost budget. A loop without termination policy is an incident waiting to happen."),
        ("Track step count, tool errors and repeated action signatures.", "Detect no-progress loops.", "Persist resumable state for long-running work.", "Escalate ambiguity rather than inventing authority."),
        "The strongest agent architecture often contains more deterministic controls than agent code.",
        "Explain how the system knows it is done and what happens when it is not."),

    ContentPage(5, "Evaluation starts with the product promise",
        "A metric is meaningful only when it represents what the user hired the system to do.",
        ("Write a one-sentence product promise, list unacceptable outcomes and define observable success. Then assemble examples that represent the real distribution, including adversarial and rare cases.",
         "Separate component evaluation - retrieval, tool selection, extraction - from end-to-end task success."),
        ("Task success or completion rate.", "Groundedness and citation correctness.", "Policy and permission compliance.", "Latency and cost within the user journey."),
        "Do not optimize a judge score without checking whether it predicts human preference or business success.",
        "State the product promise, the metric and the decision threshold in one answer."),
    ContentPage(5, "Build an evaluation set that ages well",
        "An evaluation set is a versioned product asset, not a one-time spreadsheet.",
        ("Seed it with real tasks, known failures and deliberately constructed boundary cases. Tag every item by segment, risk and expected property so regressions can be localized.",
         "Keep a stable core for longitudinal comparison and a rotating challenge set to reduce overfitting."),
        ("Store inputs, expected properties and evidence - not only ideal prose.", "Blind a holdout set from prompt authors.", "Review judge disagreement with humans.", "Add every material production incident as a regression case."),
        "A good evaluation set becomes the shared language between product, engineering, legal and operations.",
        "Describe how you prevent the team from overfitting to its own benchmark."),
    ContentPage(5, "Observability for model-mediated work",
        "Logs tell you what ran; traces should tell you why the system behaved as it did.",
        ("Capture request lineage across retrieval, prompts, model versions, tool calls, validation and final outcomes. Use redaction and retention limits from the start.",
         "Operational dashboards should combine system health with behavior health. A low error rate can coexist with a serious quality regression."),
        ("System: availability, latency, timeouts, queue depth.", "Model: tokens, retries, refusal and structured-output validity.", "Behavior: groundedness, task success, unsafe-action rate.", "Business: resolution, conversion, deflection or analyst time saved."),
        "Telemetry should support a decision: rollback, route, investigate or improve the evaluation set.",
        "Walk through the trace you would need to debug one wrong tool action."),

    ContentPage(6, "Latency is a user-experience budget",
        "Optimize the critical path, not an isolated model benchmark.",
        ("Break total latency into queueing, retrieval, model time, tools, validation and rendering. Decide which work can run in parallel and what can be streamed.",
         "Perceived latency improves when users receive progress, partial evidence or a useful first result while deeper work continues."),
        ("Set p50 and p95 targets by journey.", "Cache stable prefixes and retrieval results where safe.", "Parallelize independent retrieval or validation.", "Route simple tasks to smaller, faster models."),
        "A faster wrong answer is not an optimization. Quality and latency must be evaluated together.",
        "Quantify the latency budget and name the dominant stage."),
    ContentPage(6, "Cost is an architectural signal",
        "Unit economics should be visible per successful task, not only per token.",
        ("Track provider cost, retrieval infrastructure, tool execution, retries and human review. Divide by completed useful outcomes to avoid rewarding cheap failures.",
         "Cost controls include routing, context reduction, caching, batch work, early exits and clear limits on agent loops."),
        ("Cost per request and per successful task.", "Token distribution by prompt, retrieval and output.", "Retry and no-progress-loop cost.", "Cost by tenant, feature and model route."),
        "If the team cannot explain the cost of one user journey, it cannot price or scale it responsibly.",
        "Give a concrete example of trading a small quality change for a large cost reduction."),
    ContentPage(6, "Reliability patterns that matter",
        "Retries are only safe when the operation and failure mode are understood.",
        ("Use bounded retries with backoff for transient provider errors. Use circuit breakers and alternate routes when a dependency is unhealthy. For side effects, require idempotency and reconcile uncertain outcomes.",
         "Design degraded modes: answer from verified search only, ask a human, queue the task, or return a partial result with an explicit limitation."),
        ("Timeout every external call.", "Retry reads more freely than writes.", "Attach idempotency keys to mutations.", "Test provider outage, malformed output and partial tool failure."),
        "Graceful degradation is a product decision expressed through engineering controls.",
        "Explain the difference between retrying generation and retrying a payment-like action."),

    ContentPage(7, "Threat modeling the AI data path",
        "Treat all retrieved content and tool output as untrusted input.",
        ("Prompt injection occurs when instructions embedded in data compete with system intent. OWASP continues to list prompt injection among the central risks for LLM applications [S5].",
         "Mitigation is layered: isolate data from instructions, minimize tool privilege, validate outputs, restrict network destinations and require approval for consequential actions."),
        ("Identify every boundary where untrusted text enters context.", "Keep secrets out of model-visible context.", "Use allowlists for tools and destinations.", "Test indirect injection through documents, websites and messages."),
        "Prompt wording is not a security boundary.",
        "Draw the attack path from a malicious document to an unauthorized side effect."),
    ContentPage(7, "Govern, map, measure, manage",
        "Risk management must be tied to the system lifecycle and evidence.",
        ("The NIST AI RMF organizes work into Govern, Map, Measure and Manage, and its Generative AI Profile adds actions for GenAI-specific risks [S4].",
         "For an engineering team, this translates into ownership, use-case classification, risk and evaluation evidence, deployment controls, monitoring and incident response."),
        ("Govern - ownership, policy, documentation, accountability.", "Map - users, context, impact, dependencies and misuse.", "Measure - tests, evaluations, red teaming and uncertainty.", "Manage - prioritized controls, residual risk and ongoing monitoring."),
        "Compliance artifacts are most useful when generated from the same evidence used to operate the system.",
        "Name one control and the evidence proving it works."),
    ContentPage(7, "EU AI Act: engineer the evidence path",
        "In Europe, transparency and risk obligations increasingly affect product design and telemetry.",
        ("The EU AI Act entered into force in August 2024. AI literacy and prohibited-practice provisions began applying in February 2025; GPAI obligations followed in August 2025; broader enforcement and certain transparency rules applied from August 2026 [S3].",
         "The exact obligations depend on role and use case. Engineering should make system classification, model provenance, user disclosure, monitoring and documentation maintainable rather than assembled at the last minute."),
        ("Know whether you are provider, deployer or downstream integrator.", "Record model, data and prompt versions.", "Disclose AI interaction where required.", "Keep human oversight operational, trained and testable."),
        "This guide is engineering guidance, not legal advice. Validate obligations for the specific system and jurisdiction.",
        "Describe how a model or prompt change flows into testing, approval and documentation."),

    ContentPage(8, "A selective market, not an easy boom",
        "DACH demand is shaped by economic caution and rising technical expectations.",
        ("Germany's Federal Employment Agency reported about 13,000 registered ICT vacancies in 2025, down 22 percent year on year, while socially insured ICT employment still grew 2 percent. More than 40 percent of 39,000 new jobs targeted experts [S1].",
         "This combination suggests structural demand with a higher bar rather than indiscriminate hiring."),
        ("Expect fewer generic entry-level openings.", "Lead with production evidence and domain context.", "Show the ability to work across engineering and governance.", "Treat German language and local stakeholder fluency as leverage where relevant."),
        "The market signal is contradictory only if vacancy volume and skill intensity are treated as the same thing.",
        "Position yourself against the problem the company is solving, not against a fashionable title."),
    ContentPage(8, "Switzerland: quality, trust and domain depth",
        "Swiss opportunity sits inside a broader contraction in highly qualified IT hiring.",
        ("The Swiss federal SME portal, citing the Adecco and University of Zurich Job Market Index, reported highly qualified IT vacancies down 18 percent in 2025 [S2].",
         "That does not mean AI work disappeared. It means candidates need a sharper fit: regulated industries, data sovereignty, multilingual products, high reliability and measurable business value."),
        ("Map your experience to finance, insurance, pharma, industrial or public-sector constraints.", "Be precise about cloud, data residency and vendor dependencies.", "Show stakeholder communication across technical and non-technical teams.", "Avoid claiming production scale when you only built a prototype."),
        "Trust is an engineering property demonstrated through controls, evidence and clear limits.",
        "Prepare one story about delivering under privacy, audit or reliability constraints."),
    ContentPage(8, "From Data Science to AI Engineering",
        "The transition is a move from producing predictions to operating interactive systems.",
        ("Many DACH companies built data teams before they built AI product platforms. As generative AI moved into user-facing workflows, the missing capabilities became software integration, evaluation, access control and operations.",
         "This is an interpretation of market and interview patterns, not a claim that AI work began in 2024. The organizational label changed later than the underlying research and ML work."),
        ("Translate experiments into versioned services.", "Add evaluation before adding agent autonomy.", "Treat domain experts as part of the system.", "Build one portfolio project that demonstrates the complete loop."),
        "The strongest transition story honors data-science depth while adding production responsibility.",
        "Say: 'I moved from optimizing the model to optimizing the decision system.'"),

    ContentPage(9, "The 90-second project story",
        "A project answer should be a compact engineering argument, not a chronology.",
        ("Start with the user and the costly problem. State the baseline and constraint. Explain the architecture decision, the evaluation design, the production failure you anticipated and the measurable result.",
         "Close with what you would change now. This demonstrates judgment rather than memorized success."),
        ("Problem - who needed what, and why it mattered.", "Constraints - privacy, latency, evidence, budget, integration.", "Decision - what you chose and rejected.", "Proof - evaluation, operational metric and business result."),
        "A believable limitation increases credibility when paired with a mitigation.",
        "Prepare three versions of every project: 30 seconds, 90 seconds and 10 minutes."),
    ContentPage(9, "System-design interview frame",
        "Clarify the product contract before drawing boxes.",
        ("Ask about users, scale, data sensitivity, freshness, acceptable errors, latency and side effects. Then propose the simplest architecture that meets those constraints.",
         "Walk through request flow, data flow, evaluation, failure modes, security and operations. Make trade-offs explicit instead of presenting one architecture as universally correct."),
        ("1. Clarify success and unacceptable outcomes.", "2. Estimate scale and budgets.", "3. Draw the data and control paths.", "4. Add evaluation, security, monitoring and rollout."),
        "Interviewers often learn more from what you refuse to automate than from the number of components you add.",
        "State one assumption, one alternative and the signal that would make you switch."),
    ContentPage(9, "Questions that reveal team maturity",
        "An interview is also a system-design review of the organization you may join.",
        ("Ask how the team defines quality, who owns production incidents, how model changes are released, what data is available for evaluation and where human oversight lives.",
         "The answers reveal whether the company wants a research prototype, an integration engineer or an owner of an AI product system."),
        ("What is the current production baseline?", "Which failure is most expensive today?", "How are model and prompt changes evaluated?", "Who can stop or roll back the system?"),
        "A vague role can be an opportunity, but only if authority and success criteria can be clarified.",
        "Use your questions to connect your experience to the team's real bottleneck."),

    ContentPage(10, "Production readiness: before launch",
        "Release only when product promise, failure boundaries and evidence agree.",
        ("The checklist is intentionally vendor-neutral. Adapt thresholds to the use case and risk. A low-stakes drafting assistant and an employment decision system should not share the same gate.",),
        ("Product promise and prohibited outcomes are written.", "Representative evaluation set and release thresholds exist.", "Permissions and side effects are enforced outside the model.", "Fallback, rollback and incident ownership are tested.", "Telemetry is useful, redacted and retention-limited."),
        "If a box cannot be checked, document the residual risk and the decision owner.",
        "Bring a one-page readiness checklist to a system-design interview."),
    ContentPage(10, "Production readiness: after launch",
        "The system becomes a living measurement and incident-learning loop.",
        ("Monitor system and behavior health, review sampled outputs, capture user corrections and turn incidents into regression tests. Revalidate after changes to models, prompts, retrieval, tools or policy.",),
        ("Segment metrics by task, tenant, language and risk.", "Alert on behavior regressions as well as outages.", "Review provider changes and dependency drift.", "Maintain kill switches, route controls and clear on-call ownership.", "Publish a change log for material behavior changes."),
        "Post-launch evidence should make the next release safer and faster.",
        "Explain how one user complaint becomes a labeled failure, a test and a prevention control."),
    ContentPage(10, "Build influence by publishing evidence",
        "A field guide creates influence when it becomes a shared operating artifact.",
        ("Publish versioned PDFs, short articles and reusable checklists. Invite contributions only after the editorial position is clear. Require claims, architecture, evidence, constraints and lessons - not marketing copy.",
         "The author becomes valuable by selecting, testing and synthesizing contributions, not by collecting the largest number of pages."),
        ("v0.1 - coherent author point of view.", "v0.2 - reviewed practitioner case studies.", "v0.5 - DACH job and interview dataset.", "v1.0 - peer-reviewed annual field guide."),
        "Use every release to start conversations with engineers, hiring managers and domain leaders.",
        "End interviews with a relevant page or checklist, not a generic personal-brand pitch."),
]


SOURCES = [
    ("S1", "Bundesagentur fuer Arbeit", "The labour market in the ICT sector: caught between economic weakness and structural change", "2026-07-03", "https://www.arbeitsagentur.de/en/press/2026-24-the-labour-market-in-the-information-and-communications-technology-sector"),
    ("S2", "Swiss Confederation SME Portal", "Artificial intelligence begins to weigh on the labor market", "2026-02-18", "https://www.kmu.admin.ch/en/artificial-intelligence-begins-to-weigh-on-the-labor-market"),
    ("S3", "European Commission", "AI Act - Regulatory framework and application timeline", "updated 2026", "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai"),
    ("S4", "NIST", "AI Risk Management Framework and Generative AI Profile", "2023-2026", "https://www.nist.gov/itl/ai-risk-management-framework"),
    ("S5", "OWASP Foundation", "Top 10 for Large Language Model Applications", "2026 release", "https://owasp.org/www-project-top-10-for-large-language-model-applications/"),
    ("S6", "Anthropic", "Building Effective AI Agents", "2024-12-19", "https://www.anthropic.com/research/building-effective-agents"),
    ("S7", "Google Cloud Architecture Center", "MLOps: Continuous delivery and automation pipelines in machine learning", "accessed 2026-08", "https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning"),
    ("S8", "World Economic Forum", "The Future of Jobs Report 2025", "2025", "https://www.weforum.org/publications/the-future-of-jobs-report-2025/"),
]


class Rule(Flowable):
    def __init__(self, color=LINE, width=0.8, space=7):
        super().__init__()
        self.color, self.width, self.space = color, width, space
        self.height = space

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.width)
        self.canv.line(0, self.space / 2, self._availWidth, self.space / 2)

    def wrap(self, availWidth, availHeight):
        self._availWidth = availWidth
        return availWidth, self.height


def bullet_items(items: Iterable[str]):
    return [Paragraph(f"• {x}", BULLET) for x in items]


def callout(label: str, text: str, green: bool = False):
    bg = PALE_GREEN if green else PALE
    return Table(
        [[Paragraph(f"<font color='{BLUE.hexval()}'><b>{label}</b></font><br/>{text}", BODY)]],
        colWidths=[166 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 0.6, CYAN if green else BLUE),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]),
    )


def data_table(rows: tuple[tuple[str, ...], ...]):
    data = [[Paragraph(str(cell), SMALL if r else EYEBROW) for cell in row] for r, row in enumerate(rows)]
    widths = [166 * mm / len(rows[0])] * len(rows[0])
    return Table(data, colWidths=widths, repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F7F9FC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))


def chapter_opener(number: int, title: str, thesis: str):
    return [
        Spacer(1, 28 * mm),
        Paragraph(f"CHAPTER {number:02d}", EYEBROW),
        Paragraph(title, TITLE),
        Spacer(1, 4 * mm),
        Rule(BLUE, 1.4, 12),
        Spacer(1, 12 * mm),
        Paragraph(thesis, ParagraphStyle("quote", parent=BODY, fontSize=15, leading=22, textColor=INK)),
        Spacer(1, 12 * mm),
        callout("In this chapter", "A concise operating model, implementation tests and interview language you can reuse.", True),
        PageBreak(),
    ]


def content_page(p: ContentPage):
    story = [Paragraph(f"CHAPTER {p.chapter:02d} / FIELD NOTE", EYEBROW), Paragraph(p.title, H1)]
    story += [callout("Core idea", p.thesis), Spacer(1, 5 * mm)]
    for para in p.body:
        story.append(Paragraph(para, BODY))
    story += [Spacer(1, 2 * mm), Paragraph("Operating practices", H2)]
    story += bullet_items(p.bullets)
    if p.table:
        story += [Spacer(1, 3 * mm), data_table(p.table)]
    if p.code:
        story += [Spacer(1, 3 * mm), Paragraph(p.code.replace("\n", "<br/>"), CODE)]
    story += [Spacer(1, 4 * mm), callout("Field note", p.field_note, True), Spacer(1, 3 * mm)]
    story += [Paragraph(f"<b>Interview proof:</b> {p.interview}", BODY), PageBreak()]
    return story


class BookDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(filename, pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
                         title="Deep Understanding AI Engineering", author="Momo", subject="DACH Field Guide to Production AI")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="main")
        self.addPageTemplates(PageTemplate(id="book", frames=[frame], onPage=self.decorate))

    def decorate(self, canvas, doc):
        page = canvas.getPageNumber()
        if page == 1:
            return
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(22 * mm, A4[1] - 13 * mm, A4[0] - 22 * mm, A4[1] - 13 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("BookSans", 6.8)
        canvas.drawString(22 * mm, A4[1] - 10 * mm, "DEEP UNDERSTANDING AI ENGINEERING · v0.1")
        canvas.drawRightString(A4[0] - 22 * mm, 10 * mm, str(page))
        canvas.restoreState()


def cover_story():
    return [
        Spacer(1, 21 * mm),
        Paragraph("深入理解", ParagraphStyle("cn", parent=TITLE, fontSize=18, leading=22, textColor=BLUE)),
        Paragraph("AI Engineering", ParagraphStyle("cover", parent=TITLE, fontSize=33, leading=39, textColor=NAVY)),
        Paragraph("From Data Science to Production AI", ParagraphStyle("subtitle", parent=H1, fontSize=14, textColor=MUTED)),
        Spacer(1, 16 * mm),
        Table([
            ["MODEL", "CONTEXT", "TOOLS"],
            ["EVALS", "PRODUCT", "OPS"],
            ["SECURITY", "GOVERNANCE", "VALUE"],
        ], colWidths=[51 * mm] * 3, rowHeights=[16 * mm] * 3, style=TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "BookSans"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.8, BLUE),
            ("BACKGROUND", (1, 1), (1, 1), PALE_GREEN),
        ])),
        Spacer(1, 23 * mm),
        Paragraph("A practical DACH field guide for building, evaluating and interviewing for production AI systems.", ParagraphStyle("deck", parent=BODY, fontSize=12, leading=18, textColor=INK)),
        Spacer(1, 20 * mm),
        Paragraph("Momo · Author & Editor", H2),
        Paragraph("Version 0.1 · 28 August 2026 · Zurich", SMALL),
        PageBreak(),
    ]


def front_matter():
    toc_rows = []
    page = 5
    for num, title, _ in CHAPTERS:
        toc_rows.append((f"{num:02d}", title, str(page)))
        page += 4
    toc = Table([[Paragraph(a, EYEBROW), Paragraph(b, BODY), Paragraph(c, SMALL)] for a, b, c in toc_rows],
                colWidths=[15 * mm, 135 * mm, 12 * mm], style=TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.35, LINE),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
    return [
        Paragraph("中文导读", H1),
        Paragraph("这不是一本介绍热门框架的工具书，而是一份面向生产环境的 AI Engineering 操作手册。核心观点是：模型只是系统中的一个概率组件，真正的工程价值来自上下文、评估、权限、可靠性、成本、治理以及产品判断。", BODY),
        Paragraph("本书特别加入德国与瑞士市场观察，以及可直接用于 AI Engineer 面试的表达框架。v0.1 是作者版；后续版本可以加入 DACH 工程师案例、岗位数据和同行评审。", BODY),
        callout("适合谁", "正在从 Data Science / ML / Software Engineering 转型，或正在德国、瑞士面试 AI Engineer 的实践者。", True),
        Spacer(1, 8 * mm),
        Paragraph("How to use this guide", H2),
        *bullet_items(("Read Chapters 1-2 to define the role and production boundary.", "Use Chapters 3-7 as a system-design checklist.", "Use Chapters 8-9 for DACH positioning and interview preparation.", "Print Chapter 10 before a launch review or interview.")),
        Spacer(1, 10 * mm),
        Paragraph("Editorial note", H2),
        Paragraph("This is an independent field guide. Product names are illustrative, not endorsements. Regulatory discussion is engineering guidance and not legal advice. Market figures are dated and should be rechecked in future editions.", SMALL),
        PageBreak(),
        Paragraph("Executive summary", H1),
        callout("The central claim", "AI engineering is the discipline of turning uncertain model behavior into a useful, measurable and governable product system."),
        Spacer(1, 7 * mm),
        *bullet_items((
            "Own the behavior after the model response: validation, authorization, evidence, telemetry and recovery.",
            "Prefer deterministic workflows; add agent autonomy only when it produces measurable value.",
            "Evaluate the product promise using segmented task evidence, not a single average judge score.",
            "Treat latency, cost, security and governance as architecture inputs rather than launch cleanup.",
            "In DACH, a cautious market increases the premium on production evidence, domain depth and senior-level ownership.",
        )),
        Spacer(1, 7 * mm),
        data_table((("Demo thinking", "Production thinking"), ("Best-looking output", "Measured task distribution"), ("Prompt as product", "Controlled system around model"), ("Model has tool access", "User-authorized capability boundary"), ("Average quality", "Segmented quality and risk"), ("It worked once", "It can fail safely"))),
        Spacer(1, 8 * mm),
        callout("Portfolio test", "Build one small end-to-end system with evaluation, traces, permission boundaries, a cost view and a failure postmortem."),
        PageBreak(),
        Paragraph("Contents", H1), toc, Spacer(1, 8 * mm),
        Paragraph("Edition architecture", H2),
        Paragraph("Each chapter contains a position, operating practices, a field note and an interview proof. This structure is designed for rapid updates: new evidence can replace one field note without rewriting the whole book.", BODY),
        PageBreak(),
    ]


def appendix_story():
    return [
        Paragraph("Appendix A · One-page production review", H1),
        Paragraph("Product", H2), *bullet_items(("The user, task and success metric are explicit.", "Unacceptable outcomes and escalation paths are written.", "AI is necessary; a simpler deterministic solution was considered.")),
        Paragraph("Data and context", H2), *bullet_items(("Sources, freshness, access and deletion are defined.", "Retrieval is evaluated on answer-bearing evidence.", "Provenance survives into the user-visible result.")),
        Paragraph("Runtime", H2), *bullet_items(("Inputs and structured outputs are validated.", "Tools are least-privilege and side effects are idempotent.", "Timeouts, budgets, fallbacks and stopping conditions are tested.")),
        Paragraph("Evidence", H2), *bullet_items(("Release evaluation is segmented and compared with baseline.", "Operational and behavior health are monitored.", "Incidents become labeled regression tests.")),
        Paragraph("Governance", H2), *bullet_items(("Ownership, classification and human oversight are operational.", "Model, prompt, retrieval and policy versions are traceable.", "Residual risk has a named decision owner.")),
        PageBreak(),
        Paragraph("Appendix B · Contribution template", H1),
        Paragraph("Future contributors should submit evidence-rich case studies of four to eight pages using this structure.", BODY),
        data_table((("Section", "Required content"), ("Claim", "One falsifiable engineering claim"), ("Context", "Users, system, constraints and baseline"), ("Architecture", "Data path, control path and trust boundaries"), ("Evidence", "Evaluation, operational and business metrics"), ("Failure", "What failed, diagnosis and prevention"), ("Limits", "Where the lesson does not generalize"), ("Artifacts", "Code, diagrams, data or reproducible method"))),
        Spacer(1, 7 * mm),
        callout("Editorial rule", "No anonymous marketing copy, invented metrics or unreviewed claims. Every contribution must teach a reusable decision."),
        Spacer(1, 6 * mm),
        Paragraph("Suggested contribution categories", H2),
        *bullet_items(("Production case study", "Architecture or evaluation note", "Incident postmortem", "DACH market or regulation field note", "Career transition with verifiable artifacts")),
        PageBreak(),
    ]


def references_story():
    story = [Paragraph("Sources and further reading", H1), Paragraph("Accessed 28 August 2026 unless a publication date is shown. URLs are written in full to keep the PDF independently useful.", SMALL), Spacer(1, 4 * mm)]
    for key, org, title, date, url in SOURCES:
        story.extend([
            Paragraph(f"<b>[{key}] {org}</b> · {date}", H2),
            Paragraph(title, BODY),
            Paragraph(url, SMALL),
            Rule(LINE, 0.4, 7),
        ])
    story += [PageBreak(), Paragraph("Version notes", H1),
              Paragraph("v0.1 establishes the editorial position, production model, DACH market framing and interview system. Planned additions include original job-posting analysis, practitioner interviews, reviewed architectures and bilingual chapter summaries.", BODY),
              Spacer(1, 10 * mm), callout("Invitation", "If you have a production case, benchmark or postmortem from Germany, Switzerland or Austria, use the contribution template in Appendix B."),
              Spacer(1, 25 * mm), Paragraph("Build systems that can explain their evidence, limits and next action.", ParagraphStyle("end", parent=TITLE, fontSize=18, leading=25, alignment=TA_CENTER)),
              Spacer(1, 20 * mm), Paragraph("Momo · Zurich · 2026", ParagraphStyle("center", parent=SMALL, alignment=TA_CENTER))]
    return story


def build() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BookDoc(str(OUTPUT))
    story = []
    story += cover_story()
    story += front_matter()
    for number, title, thesis in CHAPTERS:
        story += chapter_opener(number, title, thesis)
        for page in [p for p in PAGES if p.chapter == number]:
            story += content_page(page)
    story += appendix_story()
    story += references_story()
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()

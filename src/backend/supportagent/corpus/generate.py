"""Turn the world model into Confluence pages and Jira issues.

Output shapes match what ``supportagent.seed`` already consumes, so generated
content can be published with the existing seeding path:

    page  -> {"title", "project", "labels", "body"}
    issue -> {"summary", "issue_type", "labels", "description", "comments"}

Extra keys (``fact_ids``, ``visibility``, ...) are carried for the evaluation
generator and ignored by the seeder.

The generator is the place where the single-home invariant is enforced: every
fact variant is written out exactly once, and ``Corpus.homes`` records where.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

from .render import (
    bullets,
    fact_section,
    heading,
    info_macro,
    para,
    regulation_table,
    see_also,
)
from .world import (
    Fact,
    FactVariant,
    JiraPattern,
    Product,
    SupersededEdition,
    World,
    variant_key,
)

ARCHIVE_SECTION = "archiv"
RESTRICTED_SECTION = "intern"


def slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def _rng(*parts: str) -> random.Random:
    """Deterministic RNG so regenerating the corpus does not churn the eval set."""
    return random.Random("|".join(parts))


# -- titles (shared with evalgen, so they must stay stable) -----------------


def product_overview_title(product: Product) -> str:
    return f"{product.name} - Produktuebersicht"


def tariff_page_title(product: Product, tariff: str) -> str:
    return f"{product.name} {tariff} - Leistungen im Detail"


def topic_page_title(subject_name: str, topic: str) -> str:
    return f"{subject_name} - {topic}"


def process_overview_title(name: str) -> str:
    return f"{name} - Prozessuebersicht"


def archive_page_title(product: Product, edition: SupersededEdition, tariff: str) -> str:
    return f"[Archiv {edition.label}] {product.name} {tariff} - Leistungen im Detail"


def restricted_page_title(subject_name: str, topic: str) -> str:
    return f"[Intern] {subject_name} - {topic}"


@dataclass
class Home:
    """Where a fact variant is canonically stated."""

    kind: Literal["confluence", "jira"]
    title: str
    restricted: bool = False


@dataclass
class Corpus:
    projects: list[dict] = field(default_factory=list)
    pages: list[dict] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    homes: dict[str, Home] = field(default_factory=dict)
    # variant_key -> archive page titles holding an outdated value for it
    outdated: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def stats(self) -> dict[str, int]:
        return {
            "projects": len(self.projects),
            "pages": len(self.pages),
            "issues": len(self.issues),
            "homed_facts": len(self.homes),
            "restricted_pages": sum(1 for p in self.pages if p["visibility"] == "restricted"),
            "archive_pages": sum(1 for p in self.pages if p["project"] == ARCHIVE_SECTION),
            "outdated_variants": len(self.outdated),
        }


class CorpusGenerator:
    def __init__(
        self,
        world: World,
        jira_patterns_per_variant: int = 1,
        noise_issues: int = 12,
    ):
        self.world = world
        self.jira_patterns_per_variant = jira_patterns_per_variant
        self.noise_issues = noise_issues
        self.corpus = Corpus()

    # -- public API ------------------------------------------------------

    def build(self) -> Corpus:
        self._build_projects()
        for product in self.world.products:
            self._build_product(product)
        for process in self.world.processes:
            self._build_process(process)
        self._build_restricted_pages()
        self._build_archive_pages()
        self._build_issues()
        self._assert_unique_titles()
        return self.corpus

    # -- Confluence ------------------------------------------------------

    def _build_projects(self) -> None:
        for section in self.world.sections:
            self.corpus.projects.append(
                {"key": section.key, "title": section.title, "body": section.body}
            )

    def _add_page(
        self,
        title: str,
        section: str,
        labels: list[str],
        body: str,
        fact_ids: list[str],
        visibility: str = "public",
    ) -> None:
        self.corpus.pages.append(
            {
                "title": title,
                "project": section,
                "labels": sorted({self.world.insurer.kb_label, *labels}),
                "body": body,
                "visibility": visibility,
                "fact_ids": fact_ids,
            }
        )

    def _public_confluence_facts(self, subject_key: str) -> list[Fact]:
        return [
            fact
            for fact in self.world.facts_for(subject_key)
            if fact.visibility == "public" and fact.placement == "confluence"
        ]

    def _build_product(self, product: Product) -> None:
        facts = self._public_confluence_facts(product.key)
        tariff_facts = [fact for fact in facts if fact.tariff_dependent]
        shared_facts = [fact for fact in facts if not fact.tariff_dependent]

        tariff_titles = [tariff_page_title(product, tariff) for tariff in product.tariffs]
        topic_titles = self._build_topic_pages(product.key, product.name, product.section, shared_facts)

        # Overview deliberately carries no fact values - it names topics and links
        # onward, so it never competes with a canonical page for a gold label.
        topics = sorted({fact.topic for fact in facts})
        overview = "".join(
            [
                para(product.summary),
                heading("Verfuegbare Tarife"),
                bullets(product.tariffs),
                heading("Dokumentierte Themen"),
                bullets(topics),
                para(
                    "Die konkreten Leistungen, Grenzen und Selbstbeteiligungen sind "
                    "tarifabhaengig und ausschliesslich auf den jeweiligen Tarifseiten "
                    "verbindlich dokumentiert."
                ),
                see_also(tariff_titles + topic_titles),
            ]
        )
        self._add_page(
            product_overview_title(product),
            product.section,
            [slug(product.key), "produkt", "uebersicht"],
            overview,
            fact_ids=[],
        )

        for tariff in product.tariffs:
            self._build_tariff_page(product, tariff, tariff_facts)

    def _build_tariff_page(self, product: Product, tariff: str, tariff_facts: list[Fact]) -> None:
        rows: list[tuple[str, str]] = []
        sections: list[str] = []
        fact_ids: list[str] = []

        for fact in tariff_facts:
            variant = next((v for v in fact.variants if v.tariff == tariff), None)
            if variant is None:
                continue
            rows.append((fact.attribute, variant.value))
            sections.append(fact_section(fact, variant))
            fact_ids.append(fact.id)
            self.corpus.homes[variant_key(fact.id, tariff)] = Home(
                "confluence", tariff_page_title(product, tariff)
            )

        body = "".join(
            [
                para(
                    f"Verbindliche Leistungsuebersicht fuer den Tarif {tariff} der "
                    f"{product.name}. Massgeblich ist das aktuell gueltige Bedingungswerk."
                ),
                heading("Leistungen auf einen Blick"),
                regulation_table(rows),
                heading("Regelungen im Einzelnen"),
                *sections,
                see_also([product_overview_title(product)]),
            ]
        )
        self._add_page(
            tariff_page_title(product, tariff),
            product.section,
            [slug(product.key), slug(tariff), "tarif"],
            body,
            fact_ids=fact_ids,
        )

    def _build_topic_pages(
        self, subject_key: str, subject_name: str, section: str, facts: list[Fact]
    ) -> list[str]:
        by_topic: dict[str, list[Fact]] = defaultdict(list)
        for fact in facts:
            by_topic[fact.topic].append(fact)

        titles: list[str] = []
        for topic, topic_facts in sorted(by_topic.items()):
            title = topic_page_title(subject_name, topic)
            sections = []
            for fact in topic_facts:
                variant = fact.variants[0]
                sections.append(fact_section(fact, variant))
                self.corpus.homes[variant_key(fact.id, None)] = Home("confluence", title)
            body = "".join(
                [
                    para(
                        f"Verbindliche Regelungen zum Thema {topic} im Bereich {subject_name}. "
                        "Die Angaben gelten tarifuebergreifend."
                    ),
                    *sections,
                ]
            )
            self._add_page(
                title,
                section,
                [slug(subject_key), slug(topic)],
                body,
                fact_ids=[fact.id for fact in topic_facts],
            )
            titles.append(title)
        return titles

    def _build_process(self, process) -> None:
        facts = self._public_confluence_facts(process.key)
        topic_titles = self._build_topic_pages(
            process.key, process.name, process.section, facts
        )
        body = "".join(
            [
                para(process.summary),
                heading("Dokumentierte Teilprozesse"),
                bullets(sorted({fact.topic for fact in facts})),
                see_also(topic_titles),
            ]
        )
        self._add_page(
            process_overview_title(process.name),
            process.section,
            [slug(process.key), "prozess", "uebersicht"],
            body,
            fact_ids=[],
        )

    def _build_restricted_pages(self) -> None:
        by_key: dict[tuple[str, str], list[Fact]] = defaultdict(list)
        for fact in self.world.facts:
            if fact.visibility == "restricted":
                by_key[(fact.subject, fact.topic)].append(fact)

        for (subject_key, topic), facts in sorted(by_key.items()):
            subject_name = self.world.subject_name(subject_key)
            title = restricted_page_title(subject_name, topic)
            sections = []
            for fact in facts:
                variant = fact.variants[0]
                sections.append(fact_section(fact, variant))
                self.corpus.homes[variant_key(fact.id, variant.tariff)] = Home(
                    "confluence", title, restricted=True
                )
            body = "".join(
                [
                    info_macro(
                        "Interne Arbeitsanweisung. Diese Inhalte duerfen nicht an "
                        "Kundinnen und Kunden weitergegeben werden.",
                        macro="warning",
                    ),
                    *sections,
                ]
            )
            self._add_page(
                title,
                RESTRICTED_SECTION,
                [slug(subject_key), slug(topic), "intern"],
                body,
                fact_ids=[fact.id for fact in facts],
                visibility="restricted",
            )

    def _build_archive_pages(self) -> None:
        for product in self.world.products:
            for edition in product.superseded:
                by_tariff: dict[str, list[tuple[Fact, str]]] = defaultdict(list)
                for fact_id, per_tariff in edition.overrides.items():
                    fact = self.world.facts_by_id[fact_id]
                    for tariff, old_value in per_tariff.items():
                        by_tariff[tariff].append((fact, old_value))

                for tariff, entries in sorted(by_tariff.items()):
                    title = archive_page_title(product, edition, tariff)
                    sections = []
                    for fact, old_value in entries:
                        sections.append(
                            fact_section(fact, FactVariant(tariff=tariff, value=old_value))
                        )
                        self.corpus.outdated[variant_key(fact.id, tariff)].append(title)
                    body = "".join(
                        [
                            info_macro(
                                f"Abgeloestes Bedingungswerk {edition.label}, gueltig vom "
                                f"{edition.valid_from} bis {edition.valid_to}. Fuer laufende "
                                "Vertraege gilt das aktuelle Bedingungswerk.",
                                macro="warning",
                            ),
                            heading(f"Stand {edition.label} - Tarif {tariff}"),
                            *sections,
                            see_also([tariff_page_title(product, tariff)]),
                        ]
                    )
                    self._add_page(
                        title,
                        ARCHIVE_SECTION,
                        [slug(product.key), slug(tariff), "archiv", slug(edition.label)],
                        body,
                        fact_ids=[fact.id for fact, _ in entries],
                    )

    # -- Jira ------------------------------------------------------------

    def _build_issues(self) -> None:
        self._build_jira_only_issues()
        self._build_distractor_issues()
        self._build_noise_issues()

    def _format(self, template: str, fact: Fact, variant: FactVariant, home: str) -> str:
        return " ".join(
            template.format(
                subject=self.world.subject_name(fact.subject),
                attribute=fact.attribute,
                tariff=variant.tariff or "alle Tarife",
                value=variant.value,
                detail=variant.detail or "",
                home=home,
            ).split()
        )

    def _add_issue(
        self,
        summary: str,
        pattern: JiraPattern,
        description: str,
        comments: list[str],
        status: str,
        fact_id: str | None,
        extra_labels: list[str],
    ) -> None:
        self.corpus.issues.append(
            {
                "summary": summary,
                "issue_type": pattern.issue_type,
                "labels": sorted({*pattern.labels, *extra_labels}),
                "description": description,
                "comments": comments,
                "status": status,
                "fact_id": fact_id,
            }
        )

    def _build_jira_only_issues(self) -> None:
        patterns = self.world.jira_only_patterns
        if not patterns:
            return
        for fact in self.world.facts:
            if fact.placement != "jira_only" or fact.visibility != "public":
                continue
            for variant in fact.variants:
                # Exactly one issue per variant: a second one would restate the
                # value and give the gold label two valid homes.
                rng = _rng("jira_only", variant_key(fact.id, variant.tariff))
                pattern = rng.choice(patterns)
                summary = self._format(pattern.summary, fact, variant, home="")
                self.corpus.homes[variant_key(fact.id, variant.tariff)] = Home("jira", summary)
                comments = (
                    [self._format(pattern.resolution, fact, variant, home="")]
                    if pattern.resolution
                    else []
                )
                self._add_issue(
                    summary,
                    pattern,
                    self._format(pattern.description, fact, variant, home=""),
                    comments,
                    rng.choice(pattern.statuses),
                    fact.id,
                    [slug(fact.subject), slug(fact.topic)],
                )

    def _build_distractor_issues(self) -> None:
        """Issues about Confluence-homed facts that never restate the value."""
        patterns = self.world.jira_patterns
        if not patterns or self.jira_patterns_per_variant <= 0:
            return
        seen: set[str] = set()
        for fact in self.world.facts:
            if fact.placement != "confluence" or fact.visibility != "public":
                continue
            for variant in fact.variants:
                key = variant_key(fact.id, variant.tariff)
                home = self.corpus.homes.get(key)
                if home is None:
                    continue
                rng = _rng("distractor", key)
                count = min(self.jira_patterns_per_variant, len(patterns))
                for pattern in rng.sample(patterns, count):
                    summary = self._format(pattern.summary, fact, variant, home.title)
                    if summary in seen:
                        continue
                    seen.add(summary)
                    comments = (
                        [self._format(pattern.resolution, fact, variant, home.title)]
                        if pattern.resolution
                        else []
                    )
                    self._add_issue(
                        summary,
                        pattern,
                        self._format(pattern.description, fact, variant, home.title),
                        comments,
                        rng.choice(pattern.statuses),
                        fact.id,
                        [slug(fact.subject), slug(fact.topic)],
                    )

    def _build_noise_issues(self) -> None:
        patterns = self.world.noise_patterns
        if not patterns or self.noise_issues <= 0:
            return
        for index in range(self.noise_issues):
            pattern = patterns[index % len(patterns)]
            round_number = index // len(patterns) + 1
            suffix = f" (KW {38 + round_number})" if round_number > 1 else ""
            rng = _rng("noise", pattern.key, str(index))
            self.corpus.issues.append(
                {
                    "summary": f"{pattern.summary}{suffix}",
                    "issue_type": pattern.issue_type,
                    "labels": sorted({*pattern.labels, "betriebsrauschen"}),
                    "description": " ".join(pattern.description.split()),
                    "comments": [" ".join(comment.split()) for comment in pattern.comments],
                    "status": rng.choice(pattern.statuses),
                    "fact_id": None,
                }
            )

    # -- invariants ------------------------------------------------------

    def _assert_unique_titles(self) -> None:
        titles = [page["title"] for page in self.corpus.pages]
        duplicates = {title for title in titles if titles.count(title) > 1}
        if duplicates:
            raise ValueError(f"duplicate page titles: {sorted(duplicates)}")

        summaries = [issue["summary"] for issue in self.corpus.issues]
        collisions = {summary for summary in summaries if summaries.count(summary) > 1}
        if collisions:
            raise ValueError(f"duplicate issue summaries: {sorted(collisions)}")

        # Every answerable fact variant must have exactly one home.
        for fact in self.world.facts:
            for variant in fact.variants:
                key = variant_key(fact.id, variant.tariff)
                if key not in self.corpus.homes:
                    raise ValueError(f"fact variant without a home: {key}")


def generate(world: World, **kwargs) -> Corpus:
    return CorpusGenerator(world, **kwargs).build()

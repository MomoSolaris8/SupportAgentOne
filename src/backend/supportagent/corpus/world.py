"""Typed world model - the single source of truth the corpus is derived from.

Documents (Confluence pages, Jira issues) *and* the gold evaluation set are
generated from the same facts. Because the generator records which page it
rendered a fact into, ``expected_sources`` is derived rather than hand-labelled.

Central invariant: **every fact variant has exactly one canonical home**. Other
pages may discuss the same topic, but only the home page states the value. If
that invariant breaks, the gold labels become ambiguous, so it is enforced in
the generator rather than left to convention.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, model_validator

WORLD_MODEL_PATH = Path(__file__).resolve().parent / "world_model.yaml"

Placement = Literal["confluence", "jira_only"]
Visibility = Literal["public", "restricted"]

# Sentinel used in variant keys for facts that do not depend on the tariff.
ANY_TARIFF = "*"


def variant_key(fact_id: str, tariff: str | None) -> str:
    """Stable identity of a single (fact, tariff) pair - the unit that has a home."""
    return f"{fact_id}|{tariff or ANY_TARIFF}"


class Section(BaseModel):
    """A top-level Confluence page that generated pages are filed under."""

    key: str
    title: str
    body: str
    restricted: bool = False


class SupersededEdition(BaseModel):
    """An older policy edition that is still published in the archive.

    ``overrides`` maps ``fact_id -> tariff -> old value``. The old value stays
    retrievable, which is what makes recency handling testable: the archive page
    is a highly plausible but wrong answer.
    """

    label: str
    valid_from: date
    valid_to: date
    overrides: dict[str, dict[str, str]]


class Product(BaseModel):
    key: str
    section: str
    name: str
    summary: str
    tariffs: list[str]
    superseded: list[SupersededEdition] = []


class Process(BaseModel):
    key: str
    section: str
    name: str
    summary: str


class FactVariant(BaseModel):
    """One concrete value of a fact. ``tariff=None`` means it holds for all tariffs."""

    tariff: str | None = None
    value: str
    detail: str | None = None


class Fact(BaseModel):
    id: str
    subject: str  # product or process key
    topic: str  # groups facts into a page section / topic page
    attribute: str
    variants: list[FactVariant]
    questions: list[str] = []
    placement: Placement = "confluence"
    visibility: Visibility = "public"

    @property
    def tariff_dependent(self) -> bool:
        return any(variant.tariff is not None for variant in self.variants)


class JiraPattern(BaseModel):
    """Narrative shell for a fact-grounded Jira issue.

    Templates may use ``{subject}``, ``{attribute}``, ``{tariff}``, ``{value}``,
    ``{detail}`` and ``{home}``. Patterns in ``World.jira_patterns`` point at the
    canonical Confluence page without restating the value (hard negatives);
    patterns in ``World.jira_only_patterns`` state it, because for those facts the
    resolution comment *is* the canonical home.
    """

    key: str
    issue_type: str = "Task"
    labels: list[str] = []
    summary: str
    description: str
    resolution: str | None = None
    statuses: list[str] = ["To Do", "In Progress", "Done"]


class NoisePattern(BaseModel):
    """Operational chatter with no retrievable fact - realistic Jira is mostly this."""

    key: str
    issue_type: str = "Task"
    labels: list[str] = []
    summary: str
    description: str
    comments: list[str] = []
    statuses: list[str] = ["To Do", "In Progress", "Done"]


class OutOfScopeQuestion(BaseModel):
    id: str
    question: str
    reason: str


class Insurer(BaseModel):
    name: str
    locale: str = "de-DE"
    kb_label: str = "insurance-kb"


class World(BaseModel):
    insurer: Insurer
    sections: list[Section]
    products: list[Product]
    processes: list[Process]
    facts: list[Fact]
    jira_patterns: list[JiraPattern]
    jira_only_patterns: list[JiraPattern] = []
    noise_patterns: list[NoisePattern] = []
    out_of_scope: list[OutOfScopeQuestion] = []

    # -- lookups ---------------------------------------------------------

    @property
    def products_by_key(self) -> dict[str, Product]:
        return {product.key: product for product in self.products}

    @property
    def processes_by_key(self) -> dict[str, Process]:
        return {process.key: process for process in self.processes}

    @property
    def facts_by_id(self) -> dict[str, Fact]:
        return {fact.id: fact for fact in self.facts}

    def subject_name(self, key: str) -> str:
        subject = self.products_by_key.get(key) or self.processes_by_key.get(key)
        if subject is None:
            raise KeyError(f"unknown subject: {key}")
        return subject.name

    def subject_section(self, key: str) -> str:
        subject = self.products_by_key.get(key) or self.processes_by_key.get(key)
        if subject is None:
            raise KeyError(f"unknown subject: {key}")
        return subject.section

    def facts_for(self, subject_key: str) -> list[Fact]:
        return [fact for fact in self.facts if fact.subject == subject_key]

    # -- validation ------------------------------------------------------

    @model_validator(mode="after")
    def _check_references(self) -> "World":
        section_keys = {section.key for section in self.sections}
        subject_keys = {product.key for product in self.products}
        subject_keys |= {process.key for process in self.processes}

        for product in self.products:
            if product.section not in section_keys:
                raise ValueError(f"product {product.key}: unknown section {product.section}")
        for process in self.processes:
            if process.section not in section_keys:
                raise ValueError(f"process {process.key}: unknown section {process.section}")

        seen_facts: set[str] = set()
        for fact in self.facts:
            if fact.id in seen_facts:
                raise ValueError(f"duplicate fact id: {fact.id}")
            seen_facts.add(fact.id)

            if fact.subject not in subject_keys:
                raise ValueError(f"fact {fact.id}: unknown subject {fact.subject}")
            if not fact.variants:
                raise ValueError(f"fact {fact.id}: needs at least one variant")

            product = self.products_by_key.get(fact.subject)
            seen_tariffs: set[str | None] = set()
            for variant in fact.variants:
                if variant.tariff in seen_tariffs:
                    raise ValueError(f"fact {fact.id}: duplicate tariff {variant.tariff}")
                seen_tariffs.add(variant.tariff)
                if variant.tariff is None:
                    continue
                if product is None:
                    raise ValueError(f"fact {fact.id}: tariff variant on non-product subject")
                if variant.tariff not in product.tariffs:
                    raise ValueError(
                        f"fact {fact.id}: tariff {variant.tariff} not in {product.key}"
                    )
            # A mix of tariff-specific and tariff-agnostic variants would give a
            # question two valid homes, so reject it.
            if None in seen_tariffs and len(seen_tariffs) > 1:
                raise ValueError(f"fact {fact.id}: mixes tariff-specific and shared variants")

        for product in self.products:
            for edition in product.superseded:
                for fact_id, per_tariff in edition.overrides.items():
                    fact = self.facts_by_id.get(fact_id)
                    if fact is None:
                        raise ValueError(f"{product.key}/{edition.label}: unknown fact {fact_id}")
                    if fact.subject != product.key:
                        raise ValueError(
                            f"{product.key}/{edition.label}: fact {fact_id} belongs to {fact.subject}"
                        )
                    for tariff in per_tariff:
                        if tariff not in product.tariffs:
                            raise ValueError(
                                f"{product.key}/{edition.label}: unknown tariff {tariff}"
                            )
        return self


def load_world(path: Path = WORLD_MODEL_PATH) -> World:
    return World.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))

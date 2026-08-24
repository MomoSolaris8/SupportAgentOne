"""Derive the gold evaluation set from the same world model as the corpus.

Because the generator recorded where each fact variant was written, the labels
are computed rather than annotated:

    expected_sources -> the canonical home of the fact
    must_not_use     -> sibling tariff pages and superseded archive pages, i.e.
                        the documents that look right and are not
    expect_refusal   -> restricted facts and out-of-scope questions

That is the whole point of generating corpus and eval set together: adding a
product to the world model adds documents *and* graded questions, with no
hand-labelling step in between.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .generate import Corpus, slug, tariff_page_title
from .world import Fact, FactVariant, World, variant_key


@dataclass
class GoldCase:
    case_id: str
    question: str
    category: str
    expected_sources: list[str]
    expect_refusal: bool = False
    must_not_use: list[str] = field(default_factory=list)
    expected_answer: str | None = None

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "question": self.question,
            "category": self.category,
            "expected_sources": self.expected_sources,
            "expect_refusal": self.expect_refusal,
            "must_not_use": self.must_not_use,
            "expected_answer": self.expected_answer,
        }


class EvalGenerator:
    def __init__(self, world: World, corpus: Corpus):
        self.world = world
        self.corpus = corpus

    def build(self) -> list[GoldCase]:
        cases: list[GoldCase] = []
        for fact in self.world.facts:
            for variant in fact.variants:
                cases.extend(self._cases_for_variant(fact, variant))
        cases.extend(self._out_of_scope_cases())
        self._assert_unique_ids(cases)
        return cases

    # -- fact-derived cases ---------------------------------------------

    def _render_question(self, template: str, fact: Fact, variant: FactVariant) -> str:
        return template.format(
            subject=self.world.subject_name(fact.subject),
            tariff=variant.tariff or "Standard",
            attribute=fact.attribute,
        )

    def _sibling_pages(self, fact: Fact, variant: FactVariant) -> list[str]:
        """Pages stating the same attribute for a *different* tariff."""
        if variant.tariff is None:
            return []
        product = self.world.products_by_key.get(fact.subject)
        if product is None:
            return []
        siblings = []
        for other in fact.variants:
            if other.tariff is None or other.tariff == variant.tariff:
                continue
            home = self.corpus.homes.get(variant_key(fact.id, other.tariff))
            if home is not None and home.kind == "confluence":
                siblings.append(home.title)
            else:
                siblings.append(tariff_page_title(product, other.tariff))
        return siblings

    def _cases_for_variant(self, fact: Fact, variant: FactVariant) -> list[GoldCase]:
        if not fact.questions:
            return []
        key = variant_key(fact.id, variant.tariff)
        home = self.corpus.homes[key]
        outdated = self.corpus.outdated.get(key, [])
        base_id = slug(fact.id) + ("-" + slug(variant.tariff) if variant.tariff else "")

        if home.restricted:
            category = "permission_boundary"
        elif outdated:
            category = "recency_conflict"
        elif home.kind == "jira":
            category = "cross_source_jira"
        elif variant.tariff is not None:
            category = "tariff_disambiguation"
        else:
            category = "single_source"

        cases: list[GoldCase] = []
        for index, template in enumerate(fact.questions):
            suffix = f"-q{index + 1}" if len(fact.questions) > 1 else ""
            question = self._render_question(template, fact, variant)

            if home.restricted:
                # The asker is an ordinary support user: the answer exists, but
                # not for them. Retrieving the page at all is the failure.
                cases.append(
                    GoldCase(
                        case_id=f"{base_id}{suffix}",
                        question=question,
                        category=category,
                        expected_sources=[],
                        expect_refusal=True,
                        must_not_use=[home.title],
                    )
                )
                continue

            cases.append(
                GoldCase(
                    case_id=f"{base_id}{suffix}",
                    question=question,
                    category=category,
                    expected_sources=[home.title],
                    expect_refusal=False,
                    must_not_use=sorted({*self._sibling_pages(fact, variant), *outdated}),
                    expected_answer=variant.value,
                )
            )
        return cases

    # -- refusal cases ---------------------------------------------------

    def _out_of_scope_cases(self) -> list[GoldCase]:
        return [
            GoldCase(
                case_id=f"out-of-scope-{slug(item.id)}",
                question=item.question,
                category="out_of_scope_refusal",
                expected_sources=[],
                expect_refusal=True,
            )
            for item in self.world.out_of_scope
        ]

    @staticmethod
    def _assert_unique_ids(cases: list[GoldCase]) -> None:
        ids = [case.case_id for case in cases]
        duplicates = {case_id for case_id in ids if ids.count(case_id) > 1}
        if duplicates:
            raise ValueError(f"duplicate eval case ids: {sorted(duplicates)}")


def generate_gold_set(world: World, corpus: Corpus) -> list[GoldCase]:
    return EvalGenerator(world, corpus).build()


def category_counts(cases: list[GoldCase]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        counts[case.category] = counts.get(case.category, 0) + 1
    return dict(sorted(counts.items()))

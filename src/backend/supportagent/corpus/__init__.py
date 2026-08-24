"""Synthetic corpus factory: world model -> documents + gold evaluation set.

Replaces hand-written seed content with a reproducible generator, so corpus size
and retrieval difficulty become parameters rather than manual work.
"""

from .evalgen import GoldCase, category_counts, generate_gold_set
from .generate import Corpus, generate
from .world import World, load_world

__all__ = [
    "Corpus",
    "GoldCase",
    "World",
    "category_counts",
    "generate",
    "generate_gold_set",
    "load_world",
]

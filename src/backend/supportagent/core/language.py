import re
from typing import Literal


ResponseLanguage = Literal["de", "en", "zh"]

LANGUAGE_NAMES: dict[ResponseLanguage, str] = {
    "de": "German",
    "en": "English",
    "zh": "Chinese",
}

GERMAN_MARKERS = {
    "auf",
    "bei",
    "bin",
    "bitte",
    "das",
    "dem",
    "den",
    "der",
    "des",
    "die",
    "ein",
    "eine",
    "einen",
    "einer",
    "es",
    "für",
    "hat",
    "ich",
    "ist",
    "jetzt",
    "kann",
    "mein",
    "meine",
    "meinem",
    "meinen",
    "meiner",
    "mit",
    "nicht",
    "sind",
    "uhr",
    "und",
    "warum",
    "was",
    "welche",
    "wer",
    "wie",
    "wird",
    "wo",
}

ENGLISH_MARKERS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "does",
    "for",
    "how",
    "i",
    "is",
    "it",
    "my",
    "not",
    "now",
    "of",
    "the",
    "time",
    "to",
    "what",
    "when",
    "which",
    "who",
    "why",
    "with",
    "your",
}


def detect_response_language(text: str) -> ResponseLanguage:
    """Detect the response language for German, English, and Chinese requests."""
    if any("\u3400" <= character <= "\u9fff" for character in text):
        return "zh"

    words = set(re.findall(r"[a-zäöüß]+", text.casefold()))
    german_score = len(words & GERMAN_MARKERS)
    english_score = len(words & ENGLISH_MARKERS)
    if english_score > german_score:
        return "en"
    return "de"


def response_language_name(text: str) -> str:
    return LANGUAGE_NAMES[detect_response_language(text)]

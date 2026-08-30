"""Turkish-aware text normalisation shared by the scorer and the fabrication guard.

Both need to answer "does this job term appear in this text", and they have to
answer it the same way. When they disagreed, the guard rejected a legitimate
English rendering of a Turkish source item and the whole tailoring was thrown
away.
"""

import re

_TR_TRANSLATION = str.maketrans(
    {
        "\u00e7": "c",
        "\u011f": "g",
        "\u0131": "i",
        "\u00f6": "o",
        "\u015f": "s",
        "\u00fc": "u",
        "\u00c7": "c",
        "\u011e": "g",
        "\u0130": "i",
        "\u00d6": "o",
        "\u015e": "s",
        "\u00dc": "u",
    }
)

_TURKISH_SUFFIXES = (
    "larinin",
    "lerinin",
    "larindan",
    "lerinden",
    "lardan",
    "lerden",
    "larin",
    "lerin",
    "lari",
    "leri",
    "ici",
    "ucu",
    "ucu",
    "ci",
    "cu",
    "me",
    "ma",
    "mek",
    "mak",
    "en",
    "an",
)

def normalize_text(text: str) -> str:
    return text.casefold().translate(_TR_TRANSLATION)


def _stem_token(token: str) -> str:
    # The token pattern keeps dots so "next.js" and ".net" survive, which also
    # glues on sentence punctuation: "React." would never match "React".
    stem = token.strip(".")
    if not stem:
        return ""

    for suffix in _TURKISH_SUFFIXES:
        if len(stem) > len(suffix) + 3 and stem.endswith(suffix):
            return stem[: -len(suffix)]

    # Fold the English plural so "REST APIs" reaches the same lemma as "REST
    # API". Correctness as linguistics does not matter here; both sides of every
    # comparison are folded the same way. "ss" and short tokens like "aws" are
    # left alone.
    if len(stem) > 3 and stem.endswith("s") and not stem.endswith("ss"):
        return stem[:-1]
    return stem


def semantic_keyword_lemmas(text: str) -> set[str]:
    normalized = normalize_text(text)
    return {lemma for lemma in (_stem_token(word) for word in re.findall(r"[a-z0-9+#.]+", normalized)) if lemma}

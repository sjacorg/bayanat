"""Text normalization utilities for search and storage."""

# Arabic normalization: map variant forms to canonical forms
_ARABIC_NORMALIZE = str.maketrans(
    {
        "\u0623": "\u0627",  # أ → ا
        "\u0625": "\u0627",  # إ → ا
        "\u0622": "\u0627",  # آ → ا
        "\u0671": "\u0627",  # ٱ → ا
        "\u0649": "\u064A",  # ى → ي
        "\u0629": "\u0647",  # ة → ه
        # Strip diacritics (tashkeel)
        "\u064B": None,  # fathatan
        "\u064C": None,  # dammatan
        "\u064D": None,  # kasratan
        "\u064E": None,  # fatha
        "\u064F": None,  # damma
        "\u0650": None,  # kasra
        "\u0651": None,  # shadda
        "\u0652": None,  # sukun
        # Strip tatweel (kashida)
        "\u0640": None,
    }
)


def normalize_arabic(text):
    """Normalize Arabic text for consistent search.

    - Alef variants (أ إ آ ٱ) → ا
    - Alef maksura (ى) → ي
    - Taa marbuta (ة) → ه
    - Strips diacritics/tashkeel
    - Strips tatweel/kashida

    Non-Arabic text passes through unchanged.
    """
    if not text:
        return text
    return text.translate(_ARABIC_NORMALIZE)

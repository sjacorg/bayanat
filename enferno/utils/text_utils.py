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
        # Eastern Arabic numerals → Western Arabic numerals
        "\u0660": "0",  # ٠ → 0
        "\u0661": "1",  # ١ → 1
        "\u0662": "2",  # ٢ → 2
        "\u0663": "3",  # ٣ → 3
        "\u0664": "4",  # ٤ → 4
        "\u0665": "5",  # ٥ → 5
        "\u0666": "6",  # ٦ → 6
        "\u0667": "7",  # ٧ → 7
        "\u0668": "8",  # ٨ → 8
        "\u0669": "9",  # ٩ → 9
    }
)


def normalize_arabic(text):
    """Normalize Arabic text for consistent search.

    - Alef variants (أ إ آ ٱ) → ا
    - Alef maksura (ى) → ي
    - Taa marbuta (ة) → ه
    - Strips diacritics/tashkeel
    - Strips tatweel/kashida
    - Eastern Arabic numerals (٠١٢٣٤٥٦٧٨٩) → Western numerals (0123456789)

    Non-Arabic text passes through unchanged.
    """
    if not text:
        return text
    return text.translate(_ARABIC_NORMALIZE)

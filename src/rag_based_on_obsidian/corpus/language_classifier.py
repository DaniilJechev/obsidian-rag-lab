"""Transparent rule-based language classification for corpus EDA."""

from enum import StrEnum


class WordLanguage(StrEnum):
    """Language bucket assigned to one inventory word."""

    RUSSIAN = "russian"
    ENGLISH = "english"
    MIXED_OR_OTHER = "mixed_or_other"
    UNKNOWN = "unknown"


def classify_word(word: str) -> WordLanguage:
    """Classify a word by its Unicode alphabet composition."""

    letters = [character for character in word if character.isalpha()]
    if not letters:
        return WordLanguage.UNKNOWN

    has_cyrillic = any("а" <= character.lower() <= "я" for character in letters)
    has_latin = any("a" <= character.lower() <= "z" for character in letters)
    if has_cyrillic and has_latin:
        return WordLanguage.MIXED_OR_OTHER
    if has_cyrillic:
        return WordLanguage.RUSSIAN
    if has_latin:
        return WordLanguage.ENGLISH
    return WordLanguage.MIXED_OR_OTHER

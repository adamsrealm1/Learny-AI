from __future__ import annotations

import string


_PUNCTUATION_TO_SPACE = str.maketrans({mark: " " for mark in string.punctuation})


def normalize_text(text: str) -> str:
    cleaned = text.casefold().translate(_PUNCTUATION_TO_SPACE)
    return " ".join(cleaned.split())


def tokenize(text: str) -> tuple[str, ...]:
    normalized = normalize_text(text)
    if not normalized:
        return ()
    return tuple(normalized.split(" "))


def contains_phrase(message_tokens: tuple[str, ...], phrase_tokens: tuple[str, ...]) -> bool:
    if not phrase_tokens:
        return False
    if len(phrase_tokens) > len(message_tokens):
        return False

    phrase_length = len(phrase_tokens)
    for start in range(len(message_tokens) - phrase_length + 1):
        if message_tokens[start : start + phrase_length] == phrase_tokens:
            return True
    return False


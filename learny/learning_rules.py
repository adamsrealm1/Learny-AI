from __future__ import annotations

from .text import normalize_text, tokenize


ALWAYS_LEARN_PHRASES = {"hi", "hello", "hey"}
LOW_SIGNAL_PHRASES = {
    "aight",
    "alr",
    "alright",
    "bet",
    "cool",
    "fine",
    "got it",
    "hmm",
    "hm",
    "idk",
    "k",
    "kk",
    "lol",
    "lmao",
    "maybe",
    "maybe later",
    "nah",
    "nah bro",
    "nahh",
    "naw",
    "nevermind",
    "nm",
    "no",
    "no thanks",
    "no thank you",
    "nope",
    "not really",
    "ok",
    "okay",
    "sure",
    "thanks",
    "thank you",
    "thx",
    "ty",
    "what about",
    "what now",
    "yeah",
    "yep",
    "yes",
}
LOW_SIGNAL_PREFIXES = (
    "and ",
    "also ",
    "but ",
    "how about ",
    "more about ",
    "or ",
    "then ",
    "what about ",
)
LOW_SIGNAL_WORDS = {
    "aight",
    "alr",
    "alright",
    "bet",
    "cool",
    "fine",
    "got",
    "hmm",
    "hm",
    "idk",
    "it",
    "k",
    "kk",
    "lol",
    "lmao",
    "maybe",
    "more",
    "nah",
    "nahh",
    "naw",
    "nevermind",
    "nm",
    "no",
    "nope",
    "not",
    "ok",
    "okay",
    "one",
    "same",
    "sure",
    "that",
    "thanks",
    "this",
    "thx",
    "ty",
    "yeah",
    "yep",
    "yes",
}
CONTEXT_DEPENDENT_WORDS = {
    "again",
    "another",
    "different",
    "else",
    "it",
    "more",
    "next",
    "one",
    "other",
    "same",
    "that",
    "these",
    "this",
    "those",
}
NEGATIVE_RESPONSE_WORDS = {"nah", "nahh", "naw", "no", "nope"}


def is_safe_learned_question(question: str) -> bool:
    normalized = normalize_text(question)
    if normalized in ALWAYS_LEARN_PHRASES:
        return True
    if normalized in LOW_SIGNAL_PHRASES:
        return False
    if normalized.startswith(LOW_SIGNAL_PREFIXES):
        return False

    tokens = tokenize(question)
    if not tokens:
        return False
    if len(tokens) == 1:
        return False
    if all(token in LOW_SIGNAL_WORDS for token in tokens):
        return False
    if len(tokens) <= 2 and (
        any(token in NEGATIVE_RESPONSE_WORDS for token in tokens)
        or any(token in CONTEXT_DEPENDENT_WORDS for token in tokens)
    ):
        return False
    return True

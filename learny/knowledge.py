from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .text import contains_phrase, tokenize


class KnowledgeFormatError(ValueError):
    """Raised when the JSON knowledge file cannot be used by Learny."""


@dataclass(frozen=True)
class KnowledgeEntry:
    question: str
    answers: tuple[str, ...]
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class KnowledgeBase:
    entries: tuple[KnowledgeEntry, ...]

    def best_match(self, user_message: str) -> KnowledgeEntry | None:
        message_tokens = tokenize(user_message)
        matches = [
            entry
            for entry in self.entries
            if contains_phrase(message_tokens, entry.tokens)
        ]
        if not matches:
            return None
        return max(matches, key=lambda entry: (len(entry.tokens), len(entry.question)))


def load_knowledge_file(path: str | Path) -> KnowledgeBase:
    knowledge_path = Path(path)
    with knowledge_path.open("r", encoding="utf-8") as file:
        try:
            raw_data = json.load(file)
        except json.JSONDecodeError as error:
            raise KnowledgeFormatError(
                f"{knowledge_path} is not valid JSON: {error.msg} "
                f"at line {error.lineno}, column {error.colno}."
            ) from error

    return parse_knowledge(raw_data)


def parse_knowledge(raw_data: Any) -> KnowledgeBase:
    if not isinstance(raw_data, dict):
        raise KnowledgeFormatError("The root JSON value must be an object.")

    raw_questions = raw_data.get("questions")
    if raw_questions is None:
        raise KnowledgeFormatError("The JSON object must contain a 'questions' key.")

    if isinstance(raw_questions, dict):
        entries = _parse_question_mapping(raw_questions)
    elif isinstance(raw_questions, list):
        entries = _parse_question_list(raw_questions)
    else:
        raise KnowledgeFormatError("'questions' must be an object or a list.")

    _check_duplicate_questions(entries)
    return KnowledgeBase(tuple(entries))


def _parse_question_mapping(raw_questions: dict[Any, Any]) -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    for raw_question, raw_answers in raw_questions.items():
        if not isinstance(raw_question, str):
            raise KnowledgeFormatError("Every question key must be a string.")
        entries.append(_make_entry(raw_question, raw_answers))
    return entries


def _parse_question_list(raw_questions: list[Any]) -> list[KnowledgeEntry]:
    entries: list[KnowledgeEntry] = []
    for index, raw_entry in enumerate(raw_questions, start=1):
        if not isinstance(raw_entry, dict):
            raise KnowledgeFormatError(f"Question entry #{index} must be an object.")
        if "question" not in raw_entry:
            raise KnowledgeFormatError(f"Question entry #{index} is missing 'question'.")
        if "answers" not in raw_entry:
            raise KnowledgeFormatError(f"Question entry #{index} is missing 'answers'.")
        entries.append(_make_entry(raw_entry["question"], raw_entry["answers"]))
    return entries


def _make_entry(raw_question: Any, raw_answers: Any) -> KnowledgeEntry:
    question = _clean_question(raw_question)
    answers = _clean_answers(raw_answers, question)
    tokens = tokenize(question)
    if not tokens:
        raise KnowledgeFormatError(f"Question {question!r} has no searchable words.")
    return KnowledgeEntry(question=question, answers=answers, tokens=tokens)


def _clean_question(raw_question: Any) -> str:
    if not isinstance(raw_question, str):
        raise KnowledgeFormatError("Every question must be a string.")

    question = raw_question.strip()
    if not question:
        raise KnowledgeFormatError("Questions cannot be empty.")
    return question


def _clean_answers(raw_answers: Any, question: str) -> tuple[str, ...]:
    if isinstance(raw_answers, str):
        raw_answer_list = [raw_answers]
    elif isinstance(raw_answers, list):
        raw_answer_list = raw_answers
    else:
        raise KnowledgeFormatError(
            f"Answers for question {question!r} must be a string or a list of strings."
        )

    answers: list[str] = []
    for raw_answer in raw_answer_list:
        if not isinstance(raw_answer, str):
            raise KnowledgeFormatError(
                f"Every answer for question {question!r} must be a string."
            )
        answer = raw_answer.strip()
        if not answer:
            raise KnowledgeFormatError(
                f"Answers for question {question!r} cannot be empty."
            )
        answers.append(answer)

    if not answers:
        raise KnowledgeFormatError(
            f"Question {question!r} must have at least one answer."
        )
    return tuple(answers)


def _check_duplicate_questions(entries: list[KnowledgeEntry]) -> None:
    seen: dict[tuple[str, ...], str] = {}
    for entry in entries:
        existing = seen.get(entry.tokens)
        if existing is not None:
            raise KnowledgeFormatError(
                f"Questions {existing!r} and {entry.question!r} normalize to the same phrase."
            )
        seen[entry.tokens] = entry.question


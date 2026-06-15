from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .knowledge import KnowledgeBase, KnowledgeFormatError, load_knowledge_file
from .text import tokenize


def remember_answer(path: str | Path, question: str, answer: str) -> KnowledgeBase:
    knowledge_path = Path(path)
    question = _required_text(question, "question")
    answer = _required_text(answer, "answer")

    raw_data = _load_raw_knowledge(knowledge_path)
    raw_questions = raw_data.setdefault("questions", {})

    if isinstance(raw_questions, dict):
        _remember_in_mapping(raw_questions, question, answer)
    elif isinstance(raw_questions, list):
        _remember_in_list(raw_questions, question, answer)
    else:
        raise KnowledgeFormatError("'questions' must be an object or a list.")

    _write_raw_knowledge(knowledge_path, raw_data)
    return load_knowledge_file(knowledge_path)


def _load_raw_knowledge(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        try:
            raw_data = json.load(file)
        except json.JSONDecodeError as error:
            raise KnowledgeFormatError(
                f"{path} is not valid JSON: {error.msg} "
                f"at line {error.lineno}, column {error.colno}."
            ) from error

    if not isinstance(raw_data, dict):
        raise KnowledgeFormatError("The root JSON value must be an object.")
    return raw_data


def _remember_in_mapping(
    raw_questions: dict[Any, Any],
    question: str,
    answer: str,
) -> None:
    matching_key = _find_matching_question_key(raw_questions, question)
    target_key = matching_key if matching_key is not None else question
    raw_questions[target_key] = _with_answer(raw_questions.get(target_key), answer)


def _remember_in_list(raw_questions: list[Any], question: str, answer: str) -> None:
    matching_entry = _find_matching_question_entry(raw_questions, question)
    if matching_entry is None:
        raw_questions.append({"question": question, "answers": [answer]})
        return

    matching_entry["answers"] = _with_answer(matching_entry.get("answers"), answer)


def _find_matching_question_key(
    raw_questions: dict[Any, Any],
    question: str,
) -> str | None:
    question_tokens = tokenize(question)
    for existing_question in raw_questions:
        if isinstance(existing_question, str) and tokenize(existing_question) == question_tokens:
            return existing_question
    return None


def _find_matching_question_entry(
    raw_questions: list[Any],
    question: str,
) -> dict[str, Any] | None:
    question_tokens = tokenize(question)
    for entry in raw_questions:
        if not isinstance(entry, dict):
            continue
        existing_question = entry.get("question")
        if isinstance(existing_question, str) and tokenize(existing_question) == question_tokens:
            return entry
    return None


def _with_answer(raw_answers: Any, answer: str) -> list[str]:
    if raw_answers is None:
        return [answer]
    if isinstance(raw_answers, str):
        answers = [raw_answers.strip()]
    elif isinstance(raw_answers, list):
        answers = [
            existing_answer.strip()
            for existing_answer in raw_answers
            if isinstance(existing_answer, str) and existing_answer.strip()
        ]
    else:
        raise KnowledgeFormatError("Existing answers must be a string or a list.")

    if answer not in answers:
        answers.append(answer)
    return answers


def _write_raw_knowledge(path: Path, raw_data: dict[str, Any]) -> None:
    temporary_path = path.with_name(f"{path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(raw_data, file, indent=2)
        file.write("\n")
    temporary_path.replace(path)


def _required_text(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise KnowledgeFormatError(f"Learned {label} cannot be empty.")
    return value

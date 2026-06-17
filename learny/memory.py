from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .knowledge import KnowledgeBase, KnowledgeFormatError, load_knowledge_file
from .learning_rules import is_safe_learned_question
from .text import tokenize


_MEMORY_LOCK = threading.RLock()


def remember_answer(path: str | Path, question: str, answer: str) -> KnowledgeBase:
    knowledge_path = Path(path)
    question = _required_text(question, "question")
    answer = _required_text(answer, "answer")

    if not is_safe_learned_question(question):
        return load_knowledge_file(knowledge_path)

    with _MEMORY_LOCK:
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
    raw_data = _read_recoverable_json_file(path)
    if raw_data is None:
        raw_data = _recover_from_sidecar(path)
    if raw_data is None:
        raw_data = {"questions": {}}
        _write_raw_knowledge(path, raw_data)

    if not isinstance(raw_data, dict):
        raise KnowledgeFormatError("The root JSON value must be an object.")
    return raw_data


def _read_recoverable_json_file(path: Path) -> dict[str, Any] | None:
    try:
        raw_text = path.read_bytes().decode("utf-8", errors="ignore")
    except OSError:
        return None

    try:
        raw_data = json.loads(raw_text)
    except json.JSONDecodeError:
        raw_data = _parse_recoverable_json_prefix(raw_text)

    if not isinstance(raw_data, dict):
        return None
    return raw_data


def _read_strict_json_file(path: Path) -> dict[str, Any] | None:
    try:
        raw_text = path.read_text(encoding="utf-8")
        raw_data = json.loads(raw_text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return raw_data if isinstance(raw_data, dict) else None


def _recover_from_sidecar(path: Path) -> dict[str, Any] | None:
    for recovery_path in (_next_path(path), _backup_path(path)):
        raw_data = _read_recoverable_json_file(recovery_path)
        if raw_data is not None:
            _write_raw_knowledge(path, raw_data)
            return raw_data
    return None


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
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_and_verify_json(_next_path(path), raw_data)
    _write_and_verify_json(_backup_path(path), raw_data)
    _write_and_verify_json(path, raw_data)


def _write_and_verify_json(path: Path, raw_data: dict[str, Any]) -> None:
    payload = (json.dumps(raw_data, indent=2) + "\n").encode("utf-8")
    try:
        path.unlink()
    except FileNotFoundError:
        pass

    open_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, open_flags, 0o666)
    try:
        view = memoryview(payload)
        bytes_written = 0
        while bytes_written < len(payload):
            bytes_written += os.write(descriptor, view[bytes_written:])
        try:
            os.fsync(descriptor)
        except OSError:
            pass
    finally:
        os.close(descriptor)

    verified_data = _read_strict_json_file(path)
    if verified_data != raw_data:
        raise KnowledgeFormatError(f"{path} could not be verified after writing.")


def _parse_recoverable_json_prefix(raw_text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    try:
        parsed, _ = decoder.raw_decode(raw_text.lstrip())
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _next_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.next")


def _backup_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.backup")


def _required_text(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise KnowledgeFormatError(f"Learned {label} cannot be empty.")
    return value

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .conversation import ConversationHistory


GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
PRIMARY_GROQ_MODEL = "llama-3.1-8b-instant"
FALLBACK_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_GROQ_MODELS = (PRIMARY_GROQ_MODEL, FALLBACK_GROQ_MODEL)


class GroqAPIError(RuntimeError):
    """Raised when a Groq API request fails or returns an unusable response."""


@dataclass(frozen=True)
class GeneratedAnswer:
    standalone_question: str
    answer: str
    model: str


class ChatTransport(Protocol):
    def send_chat_completion(self, payload: dict[str, Any], timeout: float) -> str:
        """Send a chat completion payload and return the assistant text."""


class UrlLibGroqTransport:
    def __init__(self, api_key: str, endpoint: str = GROQ_CHAT_COMPLETIONS_URL) -> None:
        self.api_key = api_key
        self.endpoint = endpoint

    def send_chat_completion(self, payload: dict[str, Any], timeout: float) -> str:
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise GroqAPIError(f"Groq HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise GroqAPIError(f"Could not reach Groq: {error.reason}") from error
        except TimeoutError as error:
            raise GroqAPIError("Groq request timed out.") from error

        try:
            data = json.loads(response_body)
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise GroqAPIError("Groq returned an unexpected response shape.") from error

        if not isinstance(content, str) or not content.strip():
            raise GroqAPIError("Groq returned an empty answer.")
        return content.strip()


class GroqAnswerGenerator:
    def __init__(
        self,
        transport: ChatTransport,
        *,
        models: tuple[str, ...] = DEFAULT_GROQ_MODELS,
        timeout: float = 30.0,
    ) -> None:
        if not models:
            raise ValueError("At least one Groq model is required.")
        self.transport = transport
        self.models = models
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "GroqAnswerGenerator | None":
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(UrlLibGroqTransport(api_key))

    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer | None:
        for model in self.models:
            try:
                return self._generate_with_model(model, question, history)
            except GroqAPIError:
                continue
        return None

    def _generate_with_model(
        self,
        model: str,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer:
        payload = {
            "model": model,
            "messages": build_messages(question, history),
            "temperature": 0.2,
            "max_completion_tokens": 300,
        }
        content = self.transport.send_chat_completion(payload, self.timeout)
        parsed = parse_generated_answer(content)
        return GeneratedAnswer(
            standalone_question=parsed.standalone_question,
            answer=parsed.answer,
            model=model,
        )


def build_messages(question: str, history: ConversationHistory) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You help Learny answer questions it does not know yet. "
                "Use the recent conversation only to resolve follow-up wording. "
                "Rewrite follow-ups into a clear standalone question before answering. "
                "Return only valid JSON with exactly these string keys: "
                "standalone_question and answer. Keep the answer concise and direct."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Recent conversation:\n{history.to_prompt()}\n\n"
                f"Current user question: {question.strip()}\n\n"
                "What is an answer for the current user question? "
                "If it depends on previous messages, resolve it first."
            ),
        },
    ]


def parse_generated_answer(content: str) -> GeneratedAnswer:
    data = _parse_json_object(content)
    standalone_question = _required_text(data, "standalone_question")
    answer = _required_text(data, "answer")
    return GeneratedAnswer(
        standalone_question=standalone_question,
        answer=answer,
        model="",
    )


def _parse_json_object(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = _parse_first_json_object(content)

    if not isinstance(parsed, dict):
        raise GroqAPIError("Groq did not return a JSON object.")
    return parsed


def _parse_first_json_object(content: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    start = content.find("{")
    while start != -1:
        try:
            parsed, _ = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            start = content.find("{", start + 1)
            continue
        if isinstance(parsed, dict):
            return parsed
        start = content.find("{", start + 1)
    raise GroqAPIError("Groq did not return valid JSON.")


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise GroqAPIError(f"Groq response is missing {key!r}.")
    value = value.strip()
    if not value:
        raise GroqAPIError(f"Groq response has an empty {key!r}.")
    return value

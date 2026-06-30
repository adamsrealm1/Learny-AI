from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .conversation import ConversationHistory


GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
PRIMARY_GROQ_MODEL = "openai/gpt-oss-120b"
FALLBACK_GROQ_MODEL = "llama-3.3-70b-versatile"
SECOND_FALLBACK_GROQ_MODEL = "qwen/qwen3-32b"
THIRD_FALLBACK_GROQ_MODEL = "qwen/qwen3.6-27b"
DEFAULT_GROQ_MODELS = (
    PRIMARY_GROQ_MODEL,
    FALLBACK_GROQ_MODEL,
    SECOND_FALLBACK_GROQ_MODEL,
    THIRD_FALLBACK_GROQ_MODEL,
)
GROQ_USER_AGENT = "LearnyAI/0.2 (+https://learny.env.pm)"
DEFAULT_GROQ_TIMEOUT_SECONDS = 12.0
DEFAULT_GROQ_MAX_COMPLETION_TOKENS = 2000
META_ANSWER_MARKERS = (
    "current user question",
    "previous conversation",
    "recent conversation",
    "chat context",
    "system prompt",
    "hidden instructions",
)

class GroqAPIError(RuntimeError):
    """Raised when a Groq API request fails or returns an unusable response."""


@dataclass(frozen=True)
class GeneratedAnswer:
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
        request = self._build_request(payload)

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

    def _build_request(self, payload: dict[str, Any]) -> urllib.request.Request:
        return urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": GROQ_USER_AGENT,
            },
            method="POST",
        )


class GroqAnswerGenerator:
    def __init__(
        self,
        transport: ChatTransport,
        *,
        models: tuple[str, ...] = DEFAULT_GROQ_MODELS,
        timeout: float = DEFAULT_GROQ_TIMEOUT_SECONDS,
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
            except GroqAPIError as error:
                print(f"Groq model {model} failed: {error}")
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
            "temperature": 0.35,
            "max_completion_tokens": DEFAULT_GROQ_MAX_COMPLETION_TOKENS,
        }
        content = self.transport.send_chat_completion(payload, self.timeout)
        answer = parse_generated_answer(question, content)
        return GeneratedAnswer(answer=answer, model=model)


def build_messages(question: str, history: ConversationHistory) -> list[dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are Learny, a helpful and friendly AI assistant on a website called Learny AI. "
                "Keep answers short. "
                "Never use tables."
                "Never mention providers, OpenAI, APIs, tokens, or other backend information."
                "You were made by the Learny AI development team and were trained on books, articles, academic papers, and billions of web pages scraped from the internet."
            ),
        },
    ]

    for turn in history.recent():
        messages.append({"role": "user", "content": turn.user})
        messages.append({"role": "assistant", "content": turn.learny})

    messages.append({"role": "user", "content": question.strip()})
    return messages


def parse_generated_answer(question: str, content: str) -> str:
    answer = _clean_plain_answer(content)
    _reject_unusable_answer(question, answer)
    return answer


def _clean_plain_answer(content: str) -> str:
    answer = content.strip()
    answer = re.sub(r"^```(?:text)?\s*", "", answer, flags=re.IGNORECASE)
    answer = re.sub(r"\s*```$", "", answer)
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.IGNORECASE | re.DOTALL)
    answer = answer.strip()
    if not answer:
        raise GroqAPIError("Groq returned an empty answer.")
    return answer


def _reject_unusable_answer(question: str, answer: str) -> None:
    if is_prompt_meta_answer(answer):
        raise GroqAPIError("Groq returned a prompt-meta answer.")
    if is_unusable_generated_answer(question, answer):
        raise GroqAPIError("Groq returned an unusable answer.")


def is_prompt_meta_answer(answer: str) -> bool:
    normalized = answer.casefold()
    return any(marker in normalized for marker in META_ANSWER_MARKERS)


def is_unusable_generated_answer(question: str, answer: str) -> bool:
    normalized_question = _normalize_for_comparison(question)
    normalized_answer = _normalize_for_comparison(answer)
    return bool(normalized_question and normalized_question == normalized_answer)


def _normalize_for_comparison(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))

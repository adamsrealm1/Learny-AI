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
PRIMARY_GROQ_MODEL = "llama-3.1-8b-instant"
FALLBACK_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_GROQ_MODELS = (PRIMARY_GROQ_MODEL, FALLBACK_GROQ_MODEL)
GROQ_USER_AGENT = "LearnyAI/0.1 (+https://learny-ai-adamsrealm1.wasmer.app)"
META_ANSWER_MARKERS = (
    "current user question",
    "previous conversation",
    "recent conversation",
    "chat context",
    "standalone_question",
    "system prompt",
    "valid json",
)
CLARIFYING_ANSWER_PATTERNS = (
    "can you clarify",
    "could you clarify",
    "please clarify",
    "what do you mean",
    "what would you like",
    "what do you want",
    "what kind of",
    "what type of",
    "which kind of",
    "which type of",
    "tell me more",
    "i need more information",
    "i need a little more",
    "i need some more",
)
GREETING_PHRASES = {"hi", "hello", "hey"}


class GroqAPIError(RuntimeError):
    """Raised when a Groq API request fails or returns an unusable response."""


@dataclass(frozen=True)
class GeneratedAnswer:
    standalone_question: str
    answer: str
    model: str
    should_learn: bool = True


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
        last_error: GroqAPIError | None = None
        for force_direct in (False, True):
            payload = {
                "model": model,
                "messages": build_messages(question, history, force_direct=force_direct),
                "temperature": 0.2,
                "max_completion_tokens": 300,
                "response_format": {"type": "json_object"},
            }
            content = self.transport.send_chat_completion(payload, self.timeout)
            try:
                parsed = parse_generated_answer(content)
            except GroqAPIError as error:
                last_error = error
                if "unusable answer" in str(error) and not force_direct:
                    continue
                raise
            return GeneratedAnswer(
                standalone_question=parsed.standalone_question,
                answer=parsed.answer,
                model=model,
                should_learn=parsed.should_learn,
            )
        raise last_error or GroqAPIError("Groq returned an unusable answer.")


def build_messages(
    question: str,
    history: ConversationHistory,
    *,
    force_direct: bool = False,
) -> list[dict[str, str]]:
    direct_instruction = ""
    if force_direct:
        direct_instruction = (
            "\n\nYour previous style was too much like a clarification. This time, "
            "answer directly even if the user is vague. Never return an answer "
            "that is only a question. Example: if the user says 'im bored', answer "
            "with a few concrete things they can do. If the user says 'games' "
            "after boredom was discussed, suggest specific games."
        )

    return [
        {
            "role": "system",
            "content": (
                "You are Learny, a direct and natural assistant. "
                "Use chat context only to resolve pronouns or follow-up wording. "
                "Never mention prompts, JSON, models, APIs, hidden instructions, "
                "chat context, or whether context was needed. "
                "Return only a JSON object with exactly these keys: "
                "standalone_question as a string, answer as a string, and "
                "should_learn as a boolean. The answer must be what Learny "
                "should visibly say to the user. The standalone_question must "
                "be a complete reusable question only when should_learn is true. "
                "Never use raw follow-up fragments like 'no?', 'nah', 'ok', "
                "'games', 'it', 'that', 'more', or 'what about' as "
                "standalone_question. Set should_learn to false for reactions, "
                "short follow-ups, refusals, acknowledgements, or context-only "
                "messages unless you can rewrite them into a complete reusable "
                "question. Keep answers concise and direct. "
                "Do not ask clarifying questions. If the message is vague, give "
                "a useful general answer with a few practical options."
                f"{direct_instruction}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Chat context for follow-ups only:\n{history.to_prompt()}\n\n"
                f"User message:\n{question.strip()}\n\n"
                "Write Learny's visible reply as an answer, not another question. "
                "For short follow-ups, use the chat context to answer the likely "
                "meaning directly. Mark should_learn false when the user message "
                "only makes sense because of the chat context."
            ),
        },
    ]


def parse_generated_answer(content: str) -> GeneratedAnswer:
    data = _parse_json_object(content)
    standalone_question = _required_text(data, "standalone_question")
    answer = _required_text(data, "answer")
    should_learn = _optional_bool(data, "should_learn", default=True)
    _reject_unusable_answer(standalone_question, answer)
    return GeneratedAnswer(
        standalone_question=standalone_question,
        answer=answer,
        model="",
        should_learn=should_learn,
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


def _optional_bool(data: dict[str, Any], key: str, *, default: bool) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return default


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
    if (
        normalized_question in GREETING_PHRASES
        and normalized_answer in GREETING_PHRASES
    ):
        return False
    if normalized_question and normalized_question == normalized_answer:
        return True

    lowered_answer = answer.strip().casefold()
    return any(pattern in lowered_answer for pattern in CLARIFYING_ANSWER_PATTERNS)


def _normalize_for_comparison(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))

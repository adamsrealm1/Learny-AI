from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque


@dataclass(frozen=True)
class ConversationTurn:
    user: str
    learny: str


class ConversationHistory:
    """Keeps recent in-memory chat context for follow-up questions."""

    def __init__(self, max_turns: int = 6) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1.")
        self._turns: Deque[ConversationTurn] = deque(maxlen=max_turns)

    def add(self, user: str, learny: str) -> None:
        user = user.strip()
        learny = learny.strip()
        if user and learny:
            self._turns.append(ConversationTurn(user=user, learny=learny))

    def recent(self) -> tuple[ConversationTurn, ...]:
        return tuple(self._turns)

    def to_prompt(self) -> str:
        if not self._turns:
            return "No previous conversation."

        lines: list[str] = []
        for turn in self._turns:
            lines.append(f"User: {turn.user}")
            lines.append(f"Learny: {turn.learny}")
        return "\n".join(lines)

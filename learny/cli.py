from __future__ import annotations

import argparse
import random
from pathlib import Path

from .bot import Learny
from .groq_client import GroqAnswerGenerator
from .knowledge import KnowledgeFormatError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KNOWLEDGE_PATH = PROJECT_ROOT / "data" / "knowledge.json"
EXIT_WORDS = {"exit", "quit", "q"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="learny",
        description="Run Learny, a local-only JSON-powered Python chatbot.",
    )
    parser.add_argument(
        "--knowledge",
        default=DEFAULT_KNOWLEDGE_PATH,
        type=Path,
        help="Path to the JSON knowledge file.",
    )
    parser.add_argument(
        "--once",
        metavar="QUESTION",
        help="Ask one question, print the answer, and exit.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional random seed for repeatable answer choices.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Only use local JSON knowledge. Do not call Groq for unknown questions.",
    )
    return parser


def create_bot(knowledge_path: Path, seed: int | None, offline: bool) -> Learny:
    rng = random.Random(seed) if seed is not None else None
    generator = None if offline else GroqAnswerGenerator.from_env()
    return Learny.from_file(knowledge_path, generator=generator, rng=rng)


def run_chat(bot: Learny, knowledge_path: Path) -> None:
    print("Learny AI is running locally.")
    print(f"Knowledge file: {knowledge_path}")
    print(f"Groq learning: {'on' if bot.generator is not None else 'off'}")
    print("Type a question. Type 'quit' or 'exit' to stop.")
    print()

    while True:
        try:
            user_message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not user_message:
            continue
        if user_message.casefold() in EXIT_WORDS:
            return

        print(f"Learny: {bot.answer(user_message)}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    knowledge_path = args.knowledge.resolve()

    try:
        bot = create_bot(knowledge_path, args.seed, args.offline)
    except FileNotFoundError:
        print(f"Knowledge file was not found: {knowledge_path}")
        return 1
    except KnowledgeFormatError as error:
        print(f"Knowledge file problem: {error}")
        return 1

    if args.once is not None:
        print(bot.answer(args.once))
        return 0

    run_chat(bot, knowledge_path)
    return 0

from __future__ import annotations

import argparse

from .bot import Learny
from .groq_client import DEFAULT_GROQ_MODELS, GroqAnswerGenerator
from .messages import GENERIC_ERROR_MESSAGE


EXIT_WORDS = {"exit", "quit", "q"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="learny",
        description="Run Learny as a Groq-powered Python chatbot.",
    )
    parser.add_argument(
        "--once",
        metavar="QUESTION",
        help="Ask one question, print the answer, and exit.",
    )
    return parser


def create_bot() -> Learny:
    return Learny(generator=GroqAnswerGenerator.from_env())


def run_chat(bot: Learny) -> None:
    print("Learny AI is running.")
    print(f"Groq models: {', '.join(DEFAULT_GROQ_MODELS)}")
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
    bot = create_bot()

    if bot.generator is None:
        print(GENERIC_ERROR_MESSAGE)
        return 1

    if args.once is not None:
        print(bot.answer(args.once))
        return 0

    run_chat(bot)
    return 0

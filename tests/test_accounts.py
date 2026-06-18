from __future__ import annotations

import http.cookiejar
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from learny.conversation import ConversationHistory
from learny.groq_client import GeneratedAnswer, PRIMARY_GROQ_MODEL
from learny.web_server import WebServerConfig, create_handler


class StaticAnswerGenerator:
    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer:
        context = " with context" if history.recent() else ""
        return GeneratedAnswer(
            answer=f"Stored answer{context}.",
            model=PRIMARY_GROQ_MODEL,
        )


class AccountWebTests(unittest.TestCase):
    def test_create_account_sets_cookie_and_reports_stats(self) -> None:
        with run_account_server() as server:
            data = server.post_json(
                "/api/accounts/create",
                {"username": "adamsrealm1", "password": "strong-password"},
            )
            account = server.get_json("/api/account")

        self.assertTrue(data["authenticated"])
        self.assertEqual(data["account"]["username"], "adamsrealm1")
        self.assertTrue(account["authenticated"])
        self.assertEqual(account["stats"]["chats"], 0)
        self.assertEqual(account["stats"]["messages"], 0)

    def test_signed_in_chat_sync_round_trips_from_database(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "chat_user", "password": "strong-password"},
            )
            server.post_json(
                "/api/chats/sync",
                {
                    "chats": [
                        {
                            "id": "chat-1",
                            "title": "First chat",
                            "sessionId": "session-1",
                            "createdAt": 1,
                            "updatedAt": 2,
                            "messages": [
                                {
                                    "speaker": "You",
                                    "text": "hello",
                                    "source": "sent",
                                    "createdAt": 3,
                                },
                                {
                                    "speaker": "Learny",
                                    "text": "hi",
                                    "source": "groq",
                                    "thoughtSeconds": 1.2,
                                    "createdAt": 4,
                                },
                            ],
                        }
                    ]
                },
            )
            data = server.get_json("/api/chats")

        self.assertEqual(len(data["chats"]), 1)
        self.assertEqual(data["chats"][0]["title"], "First chat")
        self.assertEqual([message["text"] for message in data["chats"][0]["messages"]], ["hello", "hi"])

    def test_signed_in_ask_persists_messages_and_uses_chat_history(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "ask_user", "password": "strong-password"},
            )
            first = server.post_json(
                "/api/ask",
                {"message": "hello", "chatId": "chat-ask", "sessionId": "session-ask"},
            )
            second = server.post_json(
                "/api/ask",
                {"message": "follow up", "chatId": "chat-ask", "sessionId": first["sessionId"]},
            )
            chats = server.get_json("/api/chats")

        self.assertEqual(first["answer"], "Stored answer.")
        self.assertEqual(second["answer"], "Stored answer with context.")
        self.assertEqual(len(chats["chats"]), 1)
        self.assertEqual(
            [message["speaker"] for message in chats["chats"][0]["messages"]],
            ["You", "Learny", "You", "Learny"],
        )

    def test_account_pages_are_served_from_extensionless_routes(self) -> None:
        with run_account_server() as server:
            my_account = server.get_text("/myaccount")
            sign_in = server.get_text("/sign-in")
            create_account = server.get_text("/create-account")

        self.assertIn("Learny Account", my_account)
        self.assertIn("Sign in", sign_in)
        self.assertIn("Create account", create_account)


class run_account_server:
    def __init__(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.base_url = ""
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))

    def __enter__(self) -> "run_account_server":
        root = Path(self.temp_dir.name)
        accounts_root = root / "accounts"
        accounts_root.mkdir()
        (root / "index.html").write_text("Learny", encoding="utf-8")
        (accounts_root / "myaccount.html").write_text("Learny Account", encoding="utf-8")
        (accounts_root / "sign-in.html").write_text("Sign in", encoding="utf-8")
        (accounts_root / "create-account.html").write_text("Create account", encoding="utf-8")
        config = WebServerConfig(
            static_dir=root,
            generator_factory=StaticAnswerGenerator,
            database_path=root / "learny-test.sqlite3",
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(config))
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)
        self.temp_dir.cleanup()

    def get_json(self, path: str) -> dict[str, Any]:
        with self.opener.open(f"{self.base_url}{path}", timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.opener.open(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_text(self, path: str) -> str:
        with self.opener.open(f"{self.base_url}{path}", timeout=10) as response:
            return response.read().decode("utf-8")


if __name__ == "__main__":
    unittest.main()

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


class CountingAnswerGenerator(StaticAnswerGenerator):
    calls = 0

    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer:
        type(self).calls += 1
        return super().generate(question, history)


class NoAnswerGenerator:
    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer | None:
        return None


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

    def test_profile_picture_can_be_added_and_removed(self) -> None:
        profile_picture = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
        )
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "picture_user", "password": "strong-password"},
            )
            added = server.post_json(
                "/api/account/profile-picture",
                {"profilePicture": profile_picture},
            )
            account_with_picture = server.get_json("/api/account")
            removed = server.post_json(
                "/api/account/profile-picture",
                {"profilePicture": None},
            )
            account_without_picture = server.get_json("/api/account")

        self.assertEqual(added["account"]["profilePicture"], profile_picture)
        self.assertEqual(account_with_picture["account"]["profilePicture"], profile_picture)
        self.assertIsNone(removed["account"]["profilePicture"])
        self.assertIsNone(account_without_picture["account"]["profilePicture"])

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

    def test_rate_limit_blocks_201st_signed_in_ask_without_persisting(self) -> None:
        CountingAnswerGenerator.calls = 0
        with run_account_server(CountingAnswerGenerator) as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "limited_user", "password": "strong-password"},
            )
            for index in range(200):
                response = server.post_json(
                    "/api/ask",
                    {
                        "message": f"hello {index}",
                        "chatId": "limited-chat",
                        "sessionId": "limited-session",
                    },
                )
                self.assertEqual(response["rateLimit"]["limit"], 200)

            blocked = server.post_json_status(
                "/api/ask",
                {
                    "message": "blocked",
                    "chatId": "limited-chat",
                    "sessionId": "limited-session",
                },
            )
            chats = server.get_json("/api/chats")

        self.assertEqual(blocked["status"], 429)
        self.assertTrue(blocked["data"]["rateLimit"]["limited"])
        self.assertGreaterEqual(int(blocked["headers"].get("Retry-After", "0")), 1)
        self.assertEqual(CountingAnswerGenerator.calls, 200)
        self.assertEqual(len(chats["chats"][0]["messages"]), 400)

    def test_signed_out_global_rate_limit_blocks_31st_guest_ask(self) -> None:
        CountingAnswerGenerator.calls = 0
        with run_account_server(CountingAnswerGenerator) as server:
            status = server.get_json("/api/rate-limit")
            headers = {"X-Learny-Rate-Session": "first-browser-session"}
            for index in range(30):
                response = server.post_json(
                    "/api/ask",
                    {"message": f"guest hello {index}", "sessionId": "guest-chat-session"},
                    headers,
                )
                self.assertEqual(response["rateLimit"]["limit"], 30)

            blocked = server.post_json_status(
                "/api/ask",
                {"message": "guest blocked", "sessionId": "guest-chat-session"},
                headers,
            )

        self.assertEqual(status["rateLimit"]["remaining"], 30)
        self.assertEqual(blocked["status"], 429)
        self.assertTrue(blocked["data"]["rateLimit"]["limited"])
        self.assertEqual(CountingAnswerGenerator.calls, 30)

    def test_signed_in_rate_limit_survives_new_login_session(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "persistent_limit", "password": "strong-password"},
            )
            for index in range(200):
                server.post_json(
                    "/api/ask",
                    {"message": f"hello {index}", "chatId": "persistent-chat"},
                )

            server.post_json("/api/accounts/sign-out", {})
            server.post_json(
                "/api/accounts/sign-in",
                {"username": "persistent_limit", "password": "strong-password"},
            )
            blocked = server.post_json_status(
                "/api/ask",
                {"message": "blocked after sign in", "chatId": "persistent-chat"},
            )

        self.assertEqual(blocked["status"], 429)
        self.assertTrue(blocked["data"]["rateLimit"]["limited"])

    def test_signed_out_global_rate_limit_cannot_be_bypassed_by_rate_session(self) -> None:
        with run_account_server() as server:
            for index in range(30):
                server.post_json(
                    "/api/ask",
                    {"message": f"global guest {index}", "sessionId": "global-guest-session"},
                    {"X-Learny-Rate-Session": f"browser-{index}"},
                )

            blocked = server.post_json_status(
                "/api/ask",
                {"message": "try a fresh browser bypass", "sessionId": "global-guest-session"},
                {"X-Learny-Rate-Session": "fresh-browser-after-limit"},
            )
            status = server.get_json("/api/rate-limit")

        self.assertEqual(blocked["status"], 429)
        self.assertTrue(blocked["data"]["rateLimit"]["limited"])
        self.assertTrue(status["rateLimit"]["limited"])

    def test_signed_in_global_limit_uses_200_message_bucket(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "signed_in_limit", "password": "strong-password"},
            )
            status = server.get_json("/api/rate-limit")

        self.assertEqual(status["rateLimit"]["limit"], 200)
        self.assertEqual(status["rateLimit"]["remaining"], 200)

    def test_failed_answer_does_not_consume_rate_limit_or_save_chat_messages(self) -> None:
        with run_account_server(NoAnswerGenerator) as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "failed_answer_user", "password": "strong-password"},
            )
            failed = server.post_json(
                "/api/ask",
                {"message": "temporary outage", "chatId": "failed-answer-chat"},
            )
            rate_limit = server.get_json("/api/rate-limit")
            chats = server.get_json("/api/chats")

        self.assertEqual(failed["source"], "unknown")
        self.assertTrue(failed["retryable"])
        self.assertEqual(rate_limit["rateLimit"]["remaining"], 200)
        self.assertEqual(chats["chats"], [])

    def test_delete_account_removes_session_and_saved_chats(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "delete_user", "password": "strong-password"},
            )
            server.post_json(
                "/api/chats/sync",
                {
                    "chats": [
                        {
                            "id": "chat-delete",
                            "title": "Delete me",
                            "sessionId": "session-delete",
                            "messages": [{"speaker": "You", "text": "remove this"}],
                        }
                    ]
                },
            )
            deleted = server.post_json("/api/accounts/delete", {})
            account = server.get_json("/api/account")
            unauthorized = server.get_status("/api/chats")

        self.assertTrue(deleted["deleted"])
        self.assertFalse(account["authenticated"])
        self.assertEqual(unauthorized, 401)

    def test_account_popup_lives_on_main_app_only(self) -> None:
        with run_account_server() as server:
            html = server.get_text("/")
            removed_routes = [
                server.get_status("/myaccount"),
                server.get_status("/sign-in"),
                server.get_status("/create-account"),
            ]

        self.assertIn('id="accountModal"', html)
        self.assertIn('data-account-view="sign-in"', html)
        self.assertIn('data-account-view="create-account"', html)
        self.assertIn('data-account-view="myaccount"', html)
        self.assertEqual(removed_routes, [404, 404, 404])

    def test_cors_preflight_has_single_credentials_header(self) -> None:
        with run_account_server() as server:
            headers = server.options_headers("/api/status")

        self.assertEqual(headers["origin"], "https://learny.env.pm")
        self.assertEqual(headers["credentials"], ["true"])

    def test_cross_site_account_cookie_uses_secure_none_samesite(self) -> None:
        with run_account_server() as server:
            headers = server.post_json_headers(
                "/api/accounts/create",
                {"username": "cross_site_user", "password": "strong-password"},
                {"Origin": "https://learny.env.pm"},
            )

        cookies = headers.get_all("Set-Cookie")
        self.assertEqual(len(cookies), 1)
        self.assertIn("SameSite=None", cookies[0])
        self.assertIn("Secure", cookies[0])


class run_account_server:
    def __init__(self, generator_factory: Any = StaticAnswerGenerator) -> None:
        self.temp_dir = TemporaryDirectory()
        self.generator_factory = generator_factory
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.base_url = ""
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))

    def __enter__(self) -> "run_account_server":
        root = Path(self.temp_dir.name)
        (root / "index.html").write_text(
            """
            <main>Learny</main>
            <div id="accountModal">
              <div data-account-view="sign-in"></div>
              <div data-account-view="create-account"></div>
              <div data-account-view="myaccount"></div>
            </div>
            """,
            encoding="utf-8",
        )
        config = WebServerConfig(
            static_dir=root,
            generator_factory=self.generator_factory,
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

    def post_json(
        self,
        path: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        with self.opener.open(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json_status(
        self,
        path: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=10) as response:
                return {
                    "status": int(response.status),
                    "data": json.loads(response.read().decode("utf-8")),
                    "headers": response.headers,
                }
        except urllib.error.HTTPError as error:
            try:
                return {
                    "status": int(error.code),
                    "data": json.loads(error.read().decode("utf-8")),
                    "headers": error.headers,
                }
            finally:
                error.close()

    def post_json_headers(
        self,
        path: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> Any:
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        with self.opener.open(request, timeout=10) as response:
            response.read()
            return response.headers

    def get_text(self, path: str) -> str:
        with self.opener.open(f"{self.base_url}{path}", timeout=10) as response:
            return response.read().decode("utf-8")

    def get_status(self, path: str) -> int:
        try:
            with self.opener.open(f"{self.base_url}{path}", timeout=10) as response:
                return int(response.status)
        except urllib.error.HTTPError as error:
            try:
                return int(error.code)
            finally:
                error.close()

    def options_headers(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            headers={
                "Origin": "https://learny.env.pm",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type,x-learny-session",
            },
            method="OPTIONS",
        )
        with self.opener.open(request, timeout=10) as response:
            return {
                "origin": response.headers.get("Access-Control-Allow-Origin"),
                "credentials": response.headers.get_all("Access-Control-Allow-Credentials"),
            }


if __name__ == "__main__":
    unittest.main()

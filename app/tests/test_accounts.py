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


class CapturingHistoryAnswerGenerator:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer:
        self.calls.append({"question": question, "history": history.recent()})
        return GeneratedAnswer(
            answer=f"Captured answer {len(self.calls)}.",
            model=PRIMARY_GROQ_MODEL,
        )


class BlockingCapturingHistoryAnswerGenerator(CapturingHistoryAnswerGenerator):
    def __init__(self) -> None:
        super().__init__()
        self.first_call_started = threading.Event()
        self.release_first_call = threading.Event()

    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer:
        self.calls.append({"question": question, "history": history.recent()})
        if len(self.calls) == 1:
            self.first_call_started.set()
            self.release_first_call.wait(timeout=5)
        return GeneratedAnswer(
            answer=f"Captured answer {len(self.calls)}.",
            model=PRIMARY_GROQ_MODEL,
        )


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
        self.assertTrue(data["account"]["canResetRateLimits"])
        self.assertTrue(account["authenticated"])
        self.assertTrue(account["account"]["canResetRateLimits"])
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

    def test_signed_in_attachment_follow_up_uses_hidden_file_history(self) -> None:
        generator = CapturingHistoryAnswerGenerator()
        with run_account_server(lambda: generator) as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "file_user", "password": "strong-password"},
            )
            verification = server.post_json(
                "/api/attachments/verify",
                {"password": "strong-password"},
            )
            first = server.post_multipart(
                "/api/ask",
                fields={
                    "message": "What does this file say?",
                    "chatId": "file-chat",
                    "sessionId": "file-session",
                    "attachmentVerificationToken": verification["attachmentVerification"]["token"],
                },
                filename="NE.md",
                content_type="text/markdown",
                content=b"# NOODLE EXTENSIONS\nExact hidden file line.",
            )
            visible_chats = server.get_json("/api/chats")
            server.post_json("/api/chats/sync", {"chats": visible_chats["chats"]})
            second = server.post_json(
                "/api/ask",
                {
                    "message": "read to me the exact thing that the file says",
                    "chatId": "file-chat",
                    "sessionId": first["sessionId"],
                },
            )

        self.assertEqual(first["answer"], "Captured answer 1.")
        self.assertEqual(second["answer"], "Captured answer 2.")
        self.assertEqual(len(generator.calls), 2)
        self.assertEqual(generator.calls[1]["question"], "read to me the exact thing that the file says")
        history = generator.calls[1]["history"]
        self.assertEqual(len(history), 1)
        self.assertIn("Attachment instructions:", history[0].user)
        self.assertIn("Name: NE.md", history[0].user)
        self.assertIn("Exact hidden file line.", history[0].user)
        self.assertNotIn("Exact hidden file line.", json.dumps(visible_chats))

    def test_attachment_history_survives_browser_sync_during_slow_answer(self) -> None:
        generator = BlockingCapturingHistoryAnswerGenerator()
        ask_result: dict[str, Any] = {}
        ask_error: list[BaseException] = []
        with run_account_server(lambda: generator) as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "slow_file_user", "password": "strong-password"},
            )
            verification = server.post_json(
                "/api/attachments/verify",
                {"password": "strong-password"},
            )

            def run_first_ask() -> None:
                try:
                    ask_result["data"] = server.post_multipart(
                        "/api/ask",
                        fields={
                            "message": "What does this file say?",
                            "chatId": "file-chat",
                            "sessionId": "file-session",
                            "attachmentVerificationToken": verification["attachmentVerification"]["token"],
                        },
                        filename="NE.md",
                        content_type="text/markdown",
                        content=b"# NOODLE EXTENSIONS\nDo not lose this file text.",
                    )
                except BaseException as error:  # pragma: no cover - re-raised below
                    ask_error.append(error)

            ask_thread = threading.Thread(target=run_first_ask)
            ask_thread.start()
            self.assertTrue(generator.first_call_started.wait(timeout=5))

            browser_chat_before_answer = {
                "id": "file-chat",
                "title": "What does this file say?",
                "sessionId": "file-session",
                "createdAt": 1,
                "updatedAt": 2,
                "messages": [
                    {
                        "speaker": "You",
                        "text": "What does this file say?",
                        "source": "sent",
                        "createdAt": 3,
                    }
                ],
            }
            server.post_json("/api/chats/sync", {"chats": [browser_chat_before_answer]})
            generator.release_first_call.set()
            ask_thread.join(timeout=5)
            self.assertFalse(ask_thread.is_alive())
            if ask_error:
                raise ask_error[0]
            self.assertEqual(ask_result["data"]["answer"], "Captured answer 1.")

            browser_chat_after_answer = {
                **browser_chat_before_answer,
                "updatedAt": 4,
                "messages": [
                    browser_chat_before_answer["messages"][0],
                    {
                        "speaker": "Learny",
                        "text": "Captured answer 1.",
                        "source": "groq",
                        "createdAt": 5,
                    },
                ],
            }
            server.post_json("/api/chats/sync", {"chats": [browser_chat_after_answer]})
            second = server.post_json(
                "/api/ask",
                {
                    "message": "read to me the exact thing that the file says",
                    "chatId": "file-chat",
                    "sessionId": "file-session",
                },
            )

        self.assertEqual(second["answer"], "Captured answer 2.")
        self.assertEqual(len(generator.calls), 2)
        history = generator.calls[1]["history"]
        self.assertEqual(len(history), 1)
        self.assertIn("Attachment instructions:", history[0].user)
        self.assertIn("Name: NE.md", history[0].user)
        self.assertIn("Do not lose this file text.", history[0].user)

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

    def test_rate_limit_reset_time_is_global_midnight_edt(self) -> None:
        with run_account_server() as server:
            guest_status = server.get_json("/api/rate-limit")["rateLimit"]
            guest_answer = server.post_json(
                "/api/ask",
                {"message": "guest reset check", "sessionId": "guest-reset-check"},
            )["rateLimit"]
            server.post_json(
                "/api/accounts/create",
                {"username": "reset_time_user_one", "password": "strong-password"},
            )
            first_account_status = server.get_json("/api/rate-limit")["rateLimit"]
            first_account_answer = server.post_json(
                "/api/ask",
                {"message": "account reset check", "chatId": "reset-time-chat"},
            )["rateLimit"]
            server.post_json("/api/accounts/sign-out", {})
            server.post_json(
                "/api/accounts/create",
                {"username": "reset_time_user_two", "password": "strong-password"},
            )
            second_account_status = server.get_json("/api/rate-limit")["rateLimit"]

        reset_times = {
            guest_status["resetAt"],
            guest_answer["resetAt"],
            first_account_status["resetAt"],
            first_account_answer["resetAt"],
            second_account_status["resetAt"],
        }
        self.assertEqual(len(reset_times), 1)
        self.assertEqual(guest_status["windowMs"], 86_400_000)
        self.assertEqual(guest_status["resetAt"] % 86_400_000, 4 * 60 * 60 * 1000)

    def test_adamsrealm1_can_reset_everyones_rate_limits(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "adamsrealm1", "password": "strong-password"},
            )
            for index in range(3):
                server.post_json(
                    "/api/ask",
                    {"message": f"admin reset setup {index}", "chatId": "admin-reset-chat"},
                )
            before_reset = server.get_json("/api/rate-limit")
            reset = server.post_json("/api/rate-limits/reset", {})
            after_reset = server.get_json("/api/rate-limit")

        self.assertEqual(before_reset["rateLimit"]["remaining"], 197)
        self.assertTrue(reset["ok"])
        self.assertGreaterEqual(reset["deleted"], 3)
        self.assertEqual(reset["rateLimit"]["remaining"], 200)
        self.assertEqual(after_reset["rateLimit"]["remaining"], 200)

    def test_non_admin_cannot_reset_rate_limits(self) -> None:
        with run_account_server() as server:
            account = server.post_json(
                "/api/accounts/create",
                {"username": "regular_user", "password": "strong-password"},
            )
            denied = server.post_json_status("/api/rate-limits/reset", {})

        self.assertFalse(account["account"]["canResetRateLimits"])
        self.assertEqual(denied["status"], 403)

    def test_admin_portal_lists_accounts_and_admins(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "adamsrealm1", "password": "strong-password"},
            )
            for index in range(2):
                server.post_json(
                    "/api/ask",
                    {"message": f"portal rate setup {index}", "chatId": "portal-rate-chat"},
                )
            portal = server.get_json("/api/admin/portal")["adminPortal"]

        self.assertFalse(portal["platform"]["available"] is False)
        self.assertEqual([account["username"] for account in portal["accounts"]], ["adamsrealm1"])
        self.assertEqual([account["username"] for account in portal["admins"]], ["adamsrealm1"])
        self.assertEqual(portal["accounts"][0]["rateLimit"]["remaining"], 198)
        self.assertEqual(portal["accounts"][0]["rateLimitPercent"], 99)

    def test_admin_can_reset_rate_limit_for_username_from_admin_portal(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "adamsrealm1", "password": "strong-password"},
            )
            for index in range(3):
                server.post_json(
                    "/api/ask",
                    {"message": f"admin user reset setup {index}", "chatId": "admin-user-reset"},
                )
            before_reset = server.get_json("/api/admin/portal")["adminPortal"]["accounts"][0]
            reset = server.post_json(
                "/api/admin/rate-limit/reset",
                {"username": "adamsrealm1"},
            )
            after_reset = reset["adminPortal"]["accounts"][0]

        self.assertEqual(before_reset["rateLimit"]["remaining"], 197)
        self.assertGreaterEqual(reset["deleted"], 3)
        self.assertEqual(reset["resetRateLimit"]["remaining"], 200)
        self.assertEqual(after_reset["rateLimit"]["remaining"], 200)
        self.assertEqual(after_reset["rateLimitPercent"], 100)

    def test_non_admin_cannot_open_admin_portal_or_make_admin_changes(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "regular_portal_user", "password": "strong-password"},
            )
            portal = server.get_json_status("/api/admin/portal")
            platform_change = server.post_json_status("/api/admin/platform", {"available": False})
            rate_limit_reset = server.post_json_status(
                "/api/admin/rate-limit/reset",
                {"username": "regular_portal_user"},
            )
            role_change = server.post_json_status(
                "/api/admin/role",
                {"username": "regular_portal_user", "admin": True},
            )

        self.assertEqual(portal["status"], 403)
        self.assertEqual(platform_change["status"], 403)
        self.assertEqual(rate_limit_reset["status"], 403)
        self.assertEqual(role_change["status"], 403)

    def test_owner_admin_can_grant_admin_portal_access(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "portal_user", "password": "strong-password"},
            )
            server.post_json("/api/accounts/sign-out", {})
            server.post_json(
                "/api/accounts/create",
                {"username": "adamsrealm1", "password": "strong-password"},
            )
            promoted = server.post_json(
                "/api/admin/role",
                {"username": "portal_user", "admin": True},
            )
            server.post_json("/api/accounts/sign-out", {})
            login = server.post_json(
                "/api/accounts/sign-in",
                {"username": "portal_user", "password": "strong-password"},
            )
            portal = server.get_json("/api/admin/portal")

        self.assertTrue(promoted["updatedAccount"]["isAdmin"])
        self.assertTrue(login["account"]["isAdmin"])
        self.assertIn("adminPortal", portal)

    def test_non_owner_admin_cannot_add_or_remove_admins(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "portal_user", "password": "strong-password"},
            )
            server.post_json("/api/accounts/sign-out", {})
            server.post_json(
                "/api/accounts/create",
                {"username": "target_user", "password": "strong-password"},
            )
            server.post_json("/api/accounts/sign-out", {})
            server.post_json(
                "/api/accounts/create",
                {"username": "adamsrealm1", "password": "strong-password"},
            )
            server.post_json(
                "/api/admin/role",
                {"username": "portal_user", "admin": True},
            )
            server.post_json("/api/accounts/sign-out", {})
            server.post_json(
                "/api/accounts/sign-in",
                {"username": "portal_user", "password": "strong-password"},
            )

            add_admin = server.post_json_status(
                "/api/admin/role",
                {"username": "target_user", "admin": True},
            )
            remove_admin = server.post_json_status(
                "/api/admin/role",
                {"username": "portal_user", "admin": False},
            )
            portal = server.get_json("/api/admin/portal")["adminPortal"]

        self.assertEqual(add_admin["status"], 403)
        self.assertEqual(remove_admin["status"], 403)
        self.assertCountEqual(
            [account["username"] for account in portal["admins"]],
            ["adamsrealm1", "portal_user"],
        )

    def test_admin_can_make_learny_unavailable_without_calling_generator(self) -> None:
        CountingAnswerGenerator.calls = 0
        with run_account_server(CountingAnswerGenerator) as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "adamsrealm1", "password": "strong-password"},
            )
            portal = server.post_json("/api/admin/platform", {"available": False})["adminPortal"]
            blocked = server.post_json_status(
                "/api/ask",
                {"message": "hello", "chatId": "down-chat", "sessionId": "down-session"},
            )

        self.assertFalse(portal["platform"]["available"])
        self.assertEqual(blocked["status"], 503)
        self.assertFalse(blocked["data"]["platform"]["available"])
        self.assertEqual(CountingAnswerGenerator.calls, 0)

    def test_admin_username_ban_blocks_existing_account(self) -> None:
        admin_profile_picture = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
            "AAAADUlEQVR42mP8z8BQDwAFgwJ/lF4Q2wAAAABJRU5ErkJggg=="
        )
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "ban_target", "password": "strong-password"},
            )
            server.post_json("/api/accounts/sign-out", {})
            server.post_json(
                "/api/accounts/create",
                {"username": "adamsrealm1", "password": "strong-password"},
            )
            server.post_json(
                "/api/account/profile-picture",
                {"profilePicture": admin_profile_picture},
            )
            portal = server.post_json(
                "/api/admin/ban",
                {
                    "kind": "username",
                    "target": "ban_target",
                    "reason": "Testing the moderation lock.",
                },
            )["adminPortal"]
            server.post_json("/api/accounts/sign-out", {})
            blocked = server.post_json_status(
                "/api/accounts/sign-in",
                {"username": "ban_target", "password": "strong-password"},
            )

        self.assertEqual(len(portal["bans"]), 1)
        self.assertEqual(blocked["status"], 403)
        self.assertEqual(blocked["data"]["ban"]["target"], "ban_target")
        self.assertEqual(blocked["data"]["ban"]["reason"], "Testing the moderation lock.")
        self.assertEqual(blocked["data"]["ban"]["createdBy"], "adamsrealm1")
        self.assertEqual(blocked["data"]["ban"]["createdByAccount"]["username"], "adamsrealm1")
        self.assertEqual(
            blocked["data"]["ban"]["createdByAccount"]["profilePicture"],
            admin_profile_picture,
        )

    def test_admin_ip_ban_blocks_matching_forwarded_address(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "adamsrealm1", "password": "strong-password"},
            )
            portal = server.post_json(
                "/api/admin/ban",
                {
                    "kind": "ip",
                    "target": "203.0.113.77",
                    "reason": "Blocked network test.",
                },
            )["adminPortal"]
            blocked = server.post_json_status(
                "/api/ask",
                {"message": "hello", "chatId": "ip-ban-chat", "sessionId": "ip-ban-session"},
                {"X-Forwarded-For": "203.0.113.77"},
            )

        self.assertEqual(len(portal["bans"]), 1)
        self.assertEqual(blocked["status"], 403)
        self.assertEqual(blocked["data"]["ban"]["kind"], "ip")
        self.assertEqual(blocked["data"]["ban"]["target"], "203.0.113.77")
        self.assertEqual(blocked["data"]["ban"]["reason"], "Blocked network test.")

    def test_admin_can_delete_account_by_username(self) -> None:
        with run_account_server() as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "remove_me", "password": "strong-password"},
            )
            server.post_json("/api/accounts/sign-out", {})
            server.post_json(
                "/api/accounts/create",
                {"username": "adamsrealm1", "password": "strong-password"},
            )
            deleted = server.post_json(
                "/api/admin/delete-account",
                {"username": "remove_me"},
            )
            portal = deleted["adminPortal"]

        self.assertTrue(deleted["deleted"])
        self.assertNotIn("remove_me", [account["username"] for account in portal["accounts"]])

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

    def test_captcha_config_reports_enabled_site_key(self) -> None:
        with run_account_server(captcha_site_key="test-site", captcha_verifier=lambda token, ip: token == "ok") as server:
            config = server.get_json("/api/captcha/config")

        self.assertTrue(config["captcha"]["enabled"])
        self.assertEqual(config["captcha"]["siteKey"], "test-site")

    def test_captcha_protects_auth_and_delete_account(self) -> None:
        with run_account_server(captcha_site_key="test-site", captcha_verifier=lambda token, ip: token == "ok") as server:
            blocked_create = server.post_json_status(
                "/api/accounts/create",
                {"username": "captcha_user", "password": "strong-password"},
            )
            created = server.post_json(
                "/api/accounts/create",
                {"username": "captcha_user", "password": "strong-password", "captchaToken": "ok"},
            )
            server.post_json("/api/accounts/sign-out", {})
            blocked_sign_in = server.post_json_status(
                "/api/accounts/sign-in",
                {"username": "captcha_user", "password": "strong-password"},
            )
            signed_in = server.post_json(
                "/api/accounts/sign-in",
                {"username": "captcha_user", "password": "strong-password", "captchaToken": "ok"},
            )
            blocked_delete = server.post_json_status("/api/accounts/delete", {})
            deleted = server.post_json("/api/accounts/delete", {"captchaToken": "ok"})

        self.assertEqual(blocked_create["status"], 403)
        self.assertTrue(created["authenticated"])
        self.assertEqual(blocked_sign_in["status"], 403)
        self.assertTrue(signed_in["authenticated"])
        self.assertEqual(blocked_delete["status"], 403)
        self.assertTrue(deleted["deleted"])

    def test_attachment_upload_requires_password_captcha_and_verification_token(self) -> None:
        with run_account_server(captcha_site_key="test-site", captcha_verifier=lambda token, ip: token == "ok") as server:
            server.post_json(
                "/api/accounts/create",
                {"username": "attach_user", "password": "strong-password", "captchaToken": "ok"},
            )
            blocked_captcha = server.post_json_status(
                "/api/attachments/verify",
                {"password": "strong-password"},
            )
            blocked_password = server.post_json_status(
                "/api/attachments/verify",
                {"password": "wrong-password", "captchaToken": "ok"},
            )
            verification = server.post_json(
                "/api/attachments/verify",
                {"password": "strong-password", "captchaToken": "ok"},
            )
            blocked_upload = server.post_multipart_status(
                "/api/ask",
                fields={"message": "read this", "chatId": "attach-chat", "sessionId": "attach-session"},
                filename="note.txt",
                content_type="text/plain",
                content=b"hello from file",
            )
            allowed_upload = server.post_multipart(
                "/api/ask",
                fields={
                    "message": "read this",
                    "chatId": "attach-chat",
                    "sessionId": "attach-session",
                    "attachmentVerificationToken": verification["attachmentVerification"]["token"],
                },
                filename="note.txt",
                content_type="text/plain",
                content=b"hello from file",
            )

        self.assertEqual(blocked_captcha["status"], 403)
        self.assertEqual(blocked_password["status"], 401)
        self.assertTrue(verification["ok"])
        self.assertEqual(blocked_upload["status"], 403)
        self.assertEqual(allowed_upload["answer"], "Stored answer.")


class run_account_server:
    def __init__(
        self,
        generator_factory: Any = StaticAnswerGenerator,
        *,
        captcha_site_key: str = "",
        captcha_verifier: Any = None,
    ) -> None:
        self.temp_dir = TemporaryDirectory()
        self.generator_factory = generator_factory
        self.captcha_site_key = captcha_site_key
        self.captcha_verifier = captcha_verifier
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
            captcha_site_key=self.captcha_site_key,
            captcha_verifier=self.captcha_verifier,
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

    def get_json_status(self, path: str) -> dict[str, Any]:
        try:
            with self.opener.open(f"{self.base_url}{path}", timeout=10) as response:
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

    def post_multipart(
        self,
        path: str,
        *,
        fields: dict[str, str],
        filename: str,
        content_type: str,
        content: bytes,
    ) -> dict[str, Any]:
        boundary = "----LearnyAccountTestBoundary"
        chunks: list[bytes] = []
        for name, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode("utf-8"),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                    value.encode("utf-8"),
                    b"\r\n",
                ]
            )
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    'Content-Disposition: form-data; name="attachments"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                content,
                b"\r\n",
                f"--{boundary}--\r\n".encode("utf-8"),
            ]
        )
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=b"".join(chunks),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with self.opener.open(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_multipart_status(
        self,
        path: str,
        *,
        fields: dict[str, str],
        filename: str,
        content_type: str,
        content: bytes,
    ) -> dict[str, Any]:
        boundary = "----LearnyAccountTestBoundary"
        chunks: list[bytes] = []
        for name, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode("utf-8"),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                    value.encode("utf-8"),
                    b"\r\n",
                ]
            )
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    'Content-Disposition: form-data; name="attachments"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                content,
                b"\r\n",
                f"--{boundary}--\r\n".encode("utf-8"),
            ]
        )
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=b"".join(chunks),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
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

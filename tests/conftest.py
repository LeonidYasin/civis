import os
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import pytest

# Set mock BOT_TOKEN before importing civis_bot modules
os.environ.setdefault("BOT_TOKEN", "123456789:TEST_BOT_TOKEN_FOR_UNIT_TESTS")

# Ensure civis_bot directory is in sys.path
CIVIS_BOT_DIR = Path(__file__).parent.parent / "civis_bot"
if str(CIVIS_BOT_DIR) not in sys.path:
    sys.path.insert(0, str(CIVIS_BOT_DIR))

import telebot
from telebot import TeleBot
from telebot.types import Update, Message, User, Chat, CallbackQuery

import database
import handlers
import mcp_client


@dataclass
class OutgoingMessageRecord:
    method: str
    chat_id: Any
    text: Optional[str] = None
    reply_markup: Any = None
    kwargs: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class TelegramRecorder:
    """
    Captures all outgoing Telegram Bot API calls made by the bot.
    """
    def __init__(self, bot: TeleBot, monkeypatch: pytest.MonkeyPatch):
        self.bot = bot
        self.monkeypatch = monkeypatch
        self.records: List[OutgoingMessageRecord] = []
        self._next_message_id = 1000
        self._patch_all_sending_methods()

    def _generate_message_id(self) -> int:
        self._next_message_id += 1
        return self._next_message_id

    def _make_mock_message(self, chat_id: Any, text: Optional[str], reply_markup: Any = None) -> Message:
        msg_id = self._generate_message_id()
        msg_json = {
            "message_id": msg_id,
            "date": int(time.time()),
            "chat": {"id": chat_id, "type": "private"},
            "text": text or "",
        }
        return Message.de_json(msg_json)

    def _patch_all_sending_methods(self):
        # 1. send_message
        def mock_send_message(chat_id, text, disable_web_page_preview=None, reply_to_message_id=None,
                              reply_markup=None, parse_mode=None, disable_notification=None, timeout=None, **kwargs):
            record = OutgoingMessageRecord(
                method="send_message",
                chat_id=chat_id,
                text=str(text) if text is not None else None,
                reply_markup=reply_markup,
                kwargs={"reply_to_message_id": reply_to_message_id, "parse_mode": parse_mode, **kwargs}
            )
            self.records.append(record)
            return self._make_mock_message(chat_id, text, reply_markup)

        # 2. reply_to
        def mock_reply_to(message, text, **kwargs):
            chat_id = message.chat.id if hasattr(message, "chat") else message.from_user.id
            reply_markup = kwargs.get("reply_markup")
            record = OutgoingMessageRecord(
                method="reply_to",
                chat_id=chat_id,
                text=str(text) if text is not None else None,
                reply_markup=reply_markup,
                kwargs={"reply_to_message_id": getattr(message, "message_id", None), **kwargs}
            )
            self.records.append(record)
            return self._make_mock_message(chat_id, text, reply_markup)

        # 3. edit_message_text
        def mock_edit_message_text(text, chat_id=None, message_id=None, inline_message_id=None,
                                   parse_mode=None, reply_markup=None, **kwargs):
            record = OutgoingMessageRecord(
                method="edit_message_text",
                chat_id=chat_id,
                text=str(text) if text is not None else None,
                reply_markup=reply_markup,
                kwargs={"message_id": message_id, "inline_message_id": inline_message_id, **kwargs}
            )
            self.records.append(record)
            return self._make_mock_message(chat_id or 0, text, reply_markup)

        # 4. edit_message_reply_markup
        def mock_edit_message_reply_markup(chat_id=None, message_id=None, inline_message_id=None,
                                           reply_markup=None, **kwargs):
            record = OutgoingMessageRecord(
                method="edit_message_reply_markup",
                chat_id=chat_id,
                text=None,
                reply_markup=reply_markup,
                kwargs={"message_id": message_id, **kwargs}
            )
            self.records.append(record)
            return True

        # 5. send_photo
        def mock_send_photo(chat_id, photo, caption=None, reply_markup=None, **kwargs):
            record = OutgoingMessageRecord(
                method="send_photo",
                chat_id=chat_id,
                text=str(caption) if caption is not None else "[Photo]",
                reply_markup=reply_markup,
                kwargs=kwargs
            )
            self.records.append(record)
            return self._make_mock_message(chat_id, caption, reply_markup)

        # 6. answer_callback_query
        def mock_answer_callback_query(callback_query_id, text=None, show_alert=None, url=None, cache_time=None):
            record = OutgoingMessageRecord(
                method="answer_callback_query",
                chat_id=None,
                text=text,
                kwargs={"callback_query_id": callback_query_id, "show_alert": show_alert, "url": url}
            )
            self.records.append(record)
            return True

        # 7. delete_message
        def mock_delete_message(chat_id, message_id, **kwargs):
            record = OutgoingMessageRecord(
                method="delete_message",
                chat_id=chat_id,
                kwargs={"message_id": message_id, **kwargs}
            )
            self.records.append(record)
            return True

        # 8. get_me
        def mock_get_me():
            return User.de_json({
                "id": 123456789,
                "is_bot": True,
                "first_name": "Civis Bot",
                "username": "civis_matcher_bot"
            })

        self.monkeypatch.setattr(self.bot, "send_message", mock_send_message)
        self.monkeypatch.setattr(self.bot, "reply_to", mock_reply_to)
        self.monkeypatch.setattr(self.bot, "edit_message_text", mock_edit_message_text)
        self.monkeypatch.setattr(self.bot, "edit_message_reply_markup", mock_edit_message_reply_markup)
        self.monkeypatch.setattr(self.bot, "send_photo", mock_send_photo)
        self.monkeypatch.setattr(self.bot, "answer_callback_query", mock_answer_callback_query)
        self.monkeypatch.setattr(self.bot, "delete_message", mock_delete_message)
        self.monkeypatch.setattr(self.bot, "get_me", mock_get_me)

    @property
    def last_text(self) -> Optional[str]:
        return self.records[-1].text if self.records else None

    @property
    def all_texts(self) -> List[str]:
        return [r.text for r in self.records if r.text is not None]

    def clear(self):
        self.records.clear()


class TelegramTestDriver:
    """
    Simulates user interactions by generating telebot Updates and dispatching them
    synchronously via bot.process_new_updates.
    """
    def __init__(self, bot: TeleBot, recorder: TelegramRecorder):
        self.bot = bot
        self.recorder = recorder
        self._update_counter = 1
        self._message_counter = 100

    def send_text(self, tg_id: int, text: str, username: str = "testuser", first_name: str = "TestCitizen") -> Message:
        self._update_counter += 1
        self._message_counter += 1
        update_json = {
            "update_id": self._update_counter,
            "message": {
                "message_id": self._message_counter,
                "from": {
                    "id": tg_id,
                    "is_bot": False,
                    "first_name": first_name,
                    "username": username
                },
                "chat": {
                    "id": tg_id,
                    "type": "private",
                    "first_name": first_name,
                    "username": username
                },
                "date": int(time.time()),
                "text": text
            }
        }
        update = Update.de_json(update_json)
        self.bot.process_new_updates([update])
        return update.message

    def click_button(self, tg_id: int, callback_data: str, message_id: int = 1,
                     username: str = "testuser", first_name: str = "TestCitizen"):
        self._update_counter += 1
        update_json = {
            "update_id": self._update_counter,
            "callback_query": {
                "id": f"cb_{self._update_counter}",
                "from": {
                    "id": tg_id,
                    "is_bot": False,
                    "first_name": first_name,
                    "username": username
                },
                "message": {
                    "message_id": message_id,
                    "chat": {"id": tg_id, "type": "private"},
                    "date": int(time.time()),
                    "text": "menu"
                },
                "data": callback_data
            }
        }
        update = Update.de_json(update_json)
        self.bot.process_new_updates([update])


class MCPMockQueue:
    """
    Mock MCP gateway interceptor preventing all real network calls while verifying
    payload structures and returning compliant responses.
    """
    def __init__(self, monkeypatch: pytest.MonkeyPatch):
        self.monkeypatch = monkeypatch
        self.calls: List[Dict[str, Any]] = []
        self._patch_mcp_transport()

    def _patch_mcp_transport(self):
        def mock_http_post(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 30):
            self.calls.append({
                "url": url,
                "payload": payload,
                "headers": headers,
                "timestamp": time.time()
            })
            if "register-user" in url:
                tg_id = payload.get("tg_id", 0)
                return 201, {
                    "status": "ok",
                    "key": f"mcr_mock_key_for_tg_{tg_id}",
                    "principal": f"user:tg-{tg_id}"
                }
            elif "/mcp" in url:
                params = payload.get("params", {})
                tool_name = params.get("name")
                req_id = payload.get("id", 1)
                
                if tool_name == "create_listing":
                    return 200, {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "created_listing": {
                                "id": f"lst_mock_{int(time.time())}",
                                "revision": 1,
                                "status": "draft"
                            }
                        }
                    }
                elif tool_name == "preview_listing":
                    return 200, {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "ready": True,
                            "consent_token": "mock_consent_token_xyz_123",
                            "missing_fields": []
                        }
                    }
                elif tool_name == "publish_listing":
                    return 200, {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "status": "active"
                        }
                    }
                return 200, {"jsonrpc": "2.0", "id": req_id, "result": {"status": "ok"}}
            return 200, {"status": "ok"}

        self.monkeypatch.setattr(mcp_client, "_http_post_json", mock_http_post)


@pytest.fixture
def bot_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Provides a fully isolated test bot environment:
    - threaded=False on TeleBot instance
    - Guaranteed bot.stop_polling() in teardown
    - tmp_path SQLite database
    - Complete Telegram outbound API patching
    - Local MCP mock with zero network requests
    """
    # 1. Isolate Database via tmp_path
    test_db_path = tmp_path / "civis_test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db_path)
    monkeypatch.setattr(mcp_client, "DB_PATH", test_db_path)
    
    # Also patch submodules if they imported DB_PATH directly
    for mod_name in ["handlers.marketplace", "handlers.core", "handlers.dialogs"]:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if hasattr(mod, "DB_PATH"):
                monkeypatch.setattr(mod, "DB_PATH", test_db_path)
    
    database.init_db()
    mcp_client.ensure_mcp_tables()

    # 2. Synchronous TeleBot (threaded=False)
    test_bot = TeleBot("123456789:MOCK_TOKEN_FOR_TESTS", threaded=False)
    
    # 3. Recorder patching all sending methods
    recorder = TelegramRecorder(test_bot, monkeypatch)
    driver = TelegramTestDriver(test_bot, recorder)

    # 4. MCP Mock queue & secret
    monkeypatch.setenv("BOT_SHARED_SECRET", "test_bot_secret")
    monkeypatch.setattr(mcp_client, "BOT_SHARED_SECRET", "test_bot_secret")
    mcp_mock = MCPMockQueue(monkeypatch)

    # 5. Wire into handlers
    handlers.set_bot(test_bot)
    # Clear any previous handlers to avoid duplicate execution
    test_bot.message_handlers.clear()
    test_bot.callback_query_handlers.clear()
    handlers.register_handlers()

    yield driver, recorder, mcp_mock, test_db_path

    # Teardown
    try:
        test_bot.stop_polling()
    except Exception:
        pass

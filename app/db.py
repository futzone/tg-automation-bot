"""SQLite ombori: qoidalar, bilimlar, chat tarixi, pauzalar, ulanishlar."""
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    role TEXT NOT NULL,          -- 'user' (suhbatdosh) yoki 'assistant' (siz / bot)
    content TEXT NOT NULL,
    ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_chat ON history(chat_id, id);
CREATE TABLE IF NOT EXISTS chat_pause (
    chat_id INTEGER PRIMARY KEY,
    until_ts INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS connections (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    enabled INTEGER NOT NULL,
    can_reply INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS presets (
    name TEXT PRIMARY KEY,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS llm_calls (
    chat_id INTEGER NOT NULL,
    ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_chat ON llm_calls(chat_id, ts);
CREATE TABLE IF NOT EXISTS strikes (
    chat_id INTEGER PRIMARY KEY,
    count INTEGER NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------- qoidalar ----------
    def add_rule(self, text: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO rules(text, created_at) VALUES (?, ?)", (text, int(time.time()))
        )
        self.conn.commit()
        return cur.lastrowid

    def list_rules(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT id, text FROM rules ORDER BY id").fetchall()

    def delete_rule(self, rule_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # ---------- bilim bazasi ----------
    def add_knowledge(self, name: str, content: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO knowledge(name, content, created_at) VALUES (?, ?, ?)",
            (name, content, int(time.time())),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_knowledge(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT id, name, content FROM knowledge ORDER BY id"
        ).fetchall()

    def delete_knowledge(self, kid: int) -> bool:
        cur = self.conn.execute("DELETE FROM knowledge WHERE id = ?", (kid,))
        self.conn.commit()
        return cur.rowcount > 0

    # ---------- sozlamalar ----------
    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.conn.commit()

    # ---------- egasining hozirgi holati ----------
    def set_status(self, text: str, until_ts: int | None) -> None:
        self.set_setting("status_text", text)
        self.set_setting("status_until", str(until_ts or ""))

    def get_status(self) -> tuple[str, int | None] | None:
        """(matn, tugash vaqti) yoki holat o'rnatilmagan / muddati o'tgan bo'lsa None."""
        text = self.get_setting("status_text")
        if not text:
            return None
        until = self.get_setting("status_until")
        if until and int(until) <= time.time():
            self.clear_status()
            return None
        return text, int(until) if until else None

    def clear_status(self) -> None:
        self.set_status("", None)

    def save_preset(self, name: str, text: str) -> None:
        self.conn.execute(
            "INSERT INTO presets(name, text) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET text = excluded.text",
            (name, text),
        )
        self.conn.commit()

    def delete_preset(self, name: str) -> bool:
        cur = self.conn.execute("DELETE FROM presets WHERE name = ?", (name,))
        self.conn.commit()
        return cur.rowcount > 0

    def list_presets(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT name, text FROM presets ORDER BY name").fetchall()
        return {r["name"]: r["text"] for r in rows}

    # ---------- tarix ----------
    def add_history(self, chat_id: int, role: str, content: str) -> None:
        self.conn.execute(
            "INSERT INTO history(chat_id, role, content, ts) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, int(time.time())),
        )
        self.conn.commit()

    def get_history(self, chat_id: int, limit: int) -> list[tuple[str, str]]:
        rows = self.conn.execute(
            "SELECT role, content FROM history WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
        return [(r["role"], r["content"]) for r in reversed(rows)]

    def clear_history(self, chat_id: int | None = None) -> None:
        if chat_id is None:
            self.conn.execute("DELETE FROM history")
        else:
            self.conn.execute("DELETE FROM history WHERE chat_id = ?", (chat_id,))
        self.conn.commit()

    # ---------- chat pauzasi ----------
    def pause_chat(self, chat_id: int, seconds: int) -> None:
        self.conn.execute(
            "INSERT INTO chat_pause(chat_id, until_ts) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET until_ts = excluded.until_ts",
            (chat_id, int(time.time()) + seconds),
        )
        self.conn.commit()

    def is_chat_paused(self, chat_id: int) -> bool:
        row = self.conn.execute(
            "SELECT until_ts FROM chat_pause WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return bool(row and row["until_ts"] > time.time())

    def clear_pauses(self) -> None:
        self.conn.execute("DELETE FROM chat_pause")
        self.conn.commit()

    # ---------- AI javoblar limiti ----------
    def add_llm_call(self, chat_id: int) -> None:
        now = int(time.time())
        self.conn.execute("DELETE FROM llm_calls WHERE ts < ?", (now - 86400,))
        self.conn.execute("INSERT INTO llm_calls(chat_id, ts) VALUES (?, ?)", (chat_id, now))
        self.conn.commit()

    def count_llm_calls(self, chat_id: int, seconds: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM llm_calls WHERE chat_id = ? AND ts > ?",
            (chat_id, int(time.time()) - seconds),
        ).fetchone()
        return row["n"]

    def clear_llm_calls(self) -> None:
        self.conn.execute("DELETE FROM llm_calls")
        self.conn.commit()

    # ---------- so'kinish uchun ogohlantirishlar ----------
    def add_strike(self, chat_id: int) -> int:
        self.conn.execute(
            "INSERT INTO strikes(chat_id, count) VALUES (?, 1) "
            "ON CONFLICT(chat_id) DO UPDATE SET count = count + 1",
            (chat_id,),
        )
        self.conn.commit()
        return self.get_strikes(chat_id)

    def get_strikes(self, chat_id: int) -> int:
        row = self.conn.execute("SELECT count FROM strikes WHERE chat_id = ?", (chat_id,)).fetchone()
        return row["count"] if row else 0

    def count_blocked(self, limit: int) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM strikes WHERE count >= ?", (limit,)).fetchone()
        return row["n"]

    def clear_strikes(self, chat_id: int | None = None) -> None:
        if chat_id is None:
            self.conn.execute("DELETE FROM strikes")
        else:
            self.conn.execute("DELETE FROM strikes WHERE chat_id = ?", (chat_id,))
        self.conn.commit()

    # ---------- business ulanishlar ----------
    def save_connection(self, conn_id: str, user_id: int, enabled: bool, can_reply: bool) -> None:
        self.conn.execute(
            "INSERT INTO connections(id, user_id, enabled, can_reply) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET user_id = excluded.user_id, "
            "enabled = excluded.enabled, can_reply = excluded.can_reply",
            (conn_id, user_id, int(enabled), int(can_reply)),
        )
        self.conn.commit()

    def get_connection(self, conn_id: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM connections WHERE id = ?", (conn_id,)).fetchone()

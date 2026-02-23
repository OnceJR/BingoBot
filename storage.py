import json
import sqlite3
from typing import Dict, Any

from config import DB_PATH

SCHEMA = """CREATE TABLE IF NOT EXISTS state (
  chat_id INTEGER PRIMARY KEY,
  data TEXT NOT NULL
);
"""

DEFAULT_STATE = {
    "cards": [ [] ],
    "active": 0,
    "called": [],
    "cards_page": 0,
    "last": None,
    "clean_mode": True,     # nuevo
    "last_msg_id": None     # nuevo
}

class Store:
    def __init__(self, db_path: str = DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def get(self, chat_id: int) -> Dict[str, Any]:
        cur = self.conn.execute("SELECT data FROM state WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        if row:
            try:
                st = json.loads(row[0])
            except Exception:
                st = DEFAULT_STATE.copy()
        else:
            st = DEFAULT_STATE.copy()
        # saneo y compat
        for k,v in DEFAULT_STATE.items():
            st.setdefault(k, v)
        if not isinstance(st.get("cards"), list) or len(st["cards"]) == 0:
            st["cards"] = [[]]
        if not isinstance(st.get("active"), int) or st["active"] >= len(st["cards"]):
            st["active"] = 0
        if not isinstance(st.get("called"), list):
            st["called"] = []
        if not isinstance(st.get("cards_page"), int):
            st["cards_page"] = 0
        return st

    def set(self, chat_id: int, state: Dict[str, Any]):
        data = json.dumps(state, separators=(",", ":"))
        self.conn.execute(
            "INSERT INTO state(chat_id, data) VALUES(?, ?) ON CONFLICT(chat_id) DO UPDATE SET data=excluded.data",
            (chat_id, data)
        )
        self.conn.commit()

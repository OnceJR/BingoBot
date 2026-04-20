import json
import aiosqlite
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
    "clean_mode": True,
    "last_msg_id": None
}

class Store:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(SCHEMA)
            await db.commit()

    async def get(self, chat_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT data FROM state WHERE chat_id = ?", (chat_id,)) as cursor:
                row = await cursor.fetchone()
                
        if row:
            try:
                st = json.loads(row[0])
            except Exception:
                st = DEFAULT_STATE.copy()
        else:
            st = DEFAULT_STATE.copy()
            
        # saneo y compatibilidad
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

    async def set(self, chat_id: int, state: Dict[str, Any]):
        data = json.dumps(state, separators=(",", ":"))
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO state(chat_id, data) VALUES(?, ?) ON CONFLICT(chat_id) DO UPDATE SET data=excluded.data",
                (chat_id, data)
            )
            await db.commit()
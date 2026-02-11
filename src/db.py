import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import DB_PATH


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_state (
                user_id INTEGER PRIMARY KEY,
                state TEXT NOT NULL,
                data TEXT NOT NULL,
                context TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.commit()


def get_state(user_id: int) -> Optional[Dict[str, Any]]:
    with connect() as conn:
        row = conn.execute(
            "SELECT user_id, state, data, context, updated_at FROM player_state WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "user_id": row["user_id"],
            "state": row["state"],
            "data": json.loads(row["data"]),
            "context": json.loads(row["context"]),
            "updated_at": row["updated_at"],
        }


def set_state(user_id: int, state: str, data: Dict[str, Any], context: List[Dict[str, str]]) -> None:
    payload = json.dumps(data, ensure_ascii=False)
    context_payload = json.dumps(context, ensure_ascii=False)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO player_state (user_id, state, data, context, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                state = excluded.state,
                data = excluded.data,
                context = excluded.context,
                updated_at = excluded.updated_at;
            """,
            (user_id, state, payload, context_payload, _now()),
        )
        conn.commit()


def clear_state(user_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM player_state WHERE user_id = ?", (user_id,))
        conn.commit()

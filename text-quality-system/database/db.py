"""
SQLite-шар: підключення, ініціалізація, CRUD + рейтинг.

Зберігає результати аналізу, дозволяє отримати всі записи, відсортовані
за Q (за замовчуванням — спадання), видаляти та чистити таблицю.

Всі функції намагаються відкривати/закривати з'єднання локально, щоб
безпечно викликатися з Streamlit (який часто рестартує скрипт).
"""
import os
import sys
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from config import DB  # type: ignore
from database.models import SCHEMA_SQL, TextRecord


# Низькорівневий доступ
def _ensure_db_dir() -> None:
    """Створює каталог для файла БД, якщо ще не існує."""
    db_dir = os.path.dirname(DB["path"])
    if db_dir and not os.path.isdir(db_dir):
        os.makedirs(db_dir, exist_ok=True)


@contextmanager
def _connect():
    _ensure_db_dir()
    conn = sqlite3.connect(
        DB["path"],
        check_same_thread=DB.get("check_same_thread", False),
    )
    conn.row_factory = sqlite3.Row
    # прагми для сумісності зі змонтованими/мережевими файловими системами
    try:
        conn.execute("PRAGMA journal_mode = MEMORY")
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("PRAGMA locking_mode = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
    except Exception:
        pass
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# Ініціалізація та загальні утиліти
def init_db() -> None:
    """Створює таблицю/індекси, якщо їх нема."""
    with _connect() as conn:
        conn.executescript(SCHEMA_SQL)


def clear_all() -> int:
    """Видаляє всі записи. Повертає кількість видалених."""
    init_db()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM texts")
        return cur.rowcount


# Операції CRUD
def save_result(result: dict) -> int:
    """
    Записує результат аналізу (той, що повертає analyze_text) у таблицю texts.
    Повертає згенерований id.
    """
    init_db()

    # формуємо JSON з метриками і похідними
    metrics_bundle = {
        "metrics":    result.get("metrics", {}),
        "normalized": result.get("normalized", {}),
        "weights":    result.get("weights", {}),
        "breakdown":  result.get("breakdown", {}),
        "tokens_preview": result.get("tokens_preview", {}),
        "duration_ms": result.get("duration_ms", 0),
    }
    metrics_json = json.dumps(metrics_bundle, ensure_ascii=False)
    n_words = (
        result.get("tokens_preview", {}).get("n_words", 0)
        if isinstance(result.get("tokens_preview"), dict)
        else 0
    )

    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO texts
                (title, text, q_score, label, level, metrics_json, n_words, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.get("title") or "Без назви",
                result.get("text", ""),
                float(result.get("Q", 0.0)),
                result.get("label", ""),
                result.get("level", ""),
                metrics_json,
                int(n_words),
                result.get("created_at") or datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return cur.lastrowid


def _row_to_record(row) -> TextRecord:
    return TextRecord(
        id=row["id"],
        title=row["title"],
        text=row["text"],
        q_score=row["q_score"],
        label=row["label"],
        level=row["level"],
        metrics_json=row["metrics_json"],
        n_words=row["n_words"],
        created_at=row["created_at"],
    )


def get_by_id(record_id: int) -> Optional[dict]:
    """Повертає повну версію запису (з розпакованим metrics_json) або None."""
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM texts WHERE id = ?", (record_id,)).fetchone()
        if not row:
            return None
        rec = _row_to_record(row).to_dict()
        try:
            rec["metrics_bundle"] = json.loads(rec.pop("metrics_json"))
        except Exception:
            rec["metrics_bundle"] = {}
        return rec


def delete_by_id(record_id: int) -> bool:
    """Видаляє запис. Повертає True, якщо щось було видалено."""
    init_db()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM texts WHERE id = ?", (record_id,))
        return cur.rowcount > 0


def get_all(order_by: str = "q_score", descending: bool = True) -> List[dict]:
    """
    Повертає всі записи. За замовчуванням — сортування за Q (спадно).

    Допустимі order_by: q_score, created_at, n_words, title, label, id.
    """
    ALLOWED = {"q_score", "created_at", "n_words", "title", "label", "id"}
    if order_by not in ALLOWED:
        order_by = "q_score"
    direction = "DESC" if descending else "ASC"

    init_db()
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT id, title, q_score, label, level, n_words, created_at "
            f"FROM texts ORDER BY {order_by} {direction}"
        ).fetchall()
        return [dict(r) for r in rows]


def get_ranking() -> List[dict]:
    """
    Повертає рейтинг — відсортований за Q спадно список словників:
        [{"rank": 1, "id": 7, "title": "...", "q_score": 0.83, "label": "Відмінно", ...}, ...]
    """
    items = get_all(order_by="q_score", descending=True)
    ranked = []
    for i, it in enumerate(items, start=1):
        ranked.append({
            "rank": i,
            **it,
        })
    return ranked

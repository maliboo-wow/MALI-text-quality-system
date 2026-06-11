"""
Моделі (dataclass-рівень) та SQL-схема для SQLite.

Таблиця `texts`:
    id           INTEGER PRIMARY KEY AUTOINCREMENT
    title        TEXT        — людська назва тексту
    text         TEXT        — оригінальний текст
    q_score      REAL        — інтегральна оцінка Q (0..1)
    label        TEXT        — "Відмінно"/"Добре"/...
    level        TEXT        — "excellent"/"good"/"average"/"poor"
    metrics_json TEXT        — JSON з усіма метриками та нормалізованими балами
    n_words      INTEGER     — кількість слів (для швидких сортувань)
    created_at   TEXT        — ISO-дата створення
"""
from dataclasses import dataclass, asdict
from typing import Optional

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS texts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    text         TEXT    NOT NULL,
    q_score      REAL    NOT NULL,
    label        TEXT    NOT NULL,
    level        TEXT    NOT NULL,
    metrics_json TEXT    NOT NULL,
    n_words      INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_texts_q_score   ON texts (q_score DESC);
CREATE INDEX IF NOT EXISTS idx_texts_created   ON texts (created_at DESC);
"""


@dataclass
class TextRecord:
    """DTO для одного запису аналізу."""
    id: Optional[int]
    title: str
    text: str
    q_score: float
    label: str
    level: str
    metrics_json: str
    n_words: int
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)

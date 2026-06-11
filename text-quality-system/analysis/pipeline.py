"""
Пайплайн аналізу тексту — єдина точка входу для UI (Streamlit).

Проходить усі етапи:
    1. Перевірка довжини (config.APP)
    2. Очищення (cleaner)
    3. Токенізація / видалення стоп-слів  (tokenizer)
    4. Обчислення метрик  (metrics/*)
    5. Нормалізація       (normalizer)
    6. Обчислення Q       (scoring)
    7. Інтерпретація результату
    8. (Опційно) збереження у БД

Повертає повний словник результату, придатний для відображення у UI.
"""
import sys
import os
import time
from datetime import datetime

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from config import APP, WEIGHTS  # type: ignore
from preprocessing.cleaner import clean_text, clean_for_metrics
from preprocessing.tokenizer import (
    tokenize_words,
    tokenize_sentences,
    tokenize_paragraphs,
    get_content_words,
)
from metrics import METRIC_FUNCTIONS
from analysis.normalizer import normalize_metrics
from analysis.scoring import compute_q_from_scores, interpret, weighted_breakdown


class TextTooShortError(ValueError):
    pass


class TextTooLongError(ValueError):
    pass


def validate_text_length(text: str) -> None:
    n = len(text.strip())
    if n < APP["min_text_len"]:
        raise TextTooShortError(
            f"Текст замалий ({n} симв.) — мінімум {APP['min_text_len']}"
        )
    if n > APP["max_text_len"]:
        raise TextTooLongError(
            f"Текст завеликий ({n} симв.) — максимум {APP['max_text_len']}"
        )


def analyze_text(
    text: str,
    title: str = None,
    save_to_db: bool = False,
) -> dict:
    """
    Виконує повний аналіз тексту. Параметри:
        text       : str  — початковий текст.
        title      : str  — назва/ідентифікатор тексту (для БД).
        save_to_db : bool — якщо True, записати результат у SQLite.

    Повертає dict:
        {
            "title": str,
            "created_at": str (ISO),
            "duration_ms": int,
            "text": str,                # оригінал (очищений мінімально)
            "cleaned_text": str,        # текст для метрик
            "tokens_preview": {
                "words": [...до 30...],
                "content_words": [...до 30...],
                "n_words": int, "n_sentences": int, "n_paragraphs": int
            },
            "metrics": {
                "basic_stats":      {"score": ..., "raw": {...}},
                "lexical_diversity": {...},
                "readability":       {...},
                "structure":         {...},
                "tfidf":             {...},
                "water_content":     {...}
            },
            "normalized": {metric: score},
            "weights": {metric: weight},
            "breakdown": {metric: {"score":..,"weight":..,"contribution":..}},
            "Q": float,
            "label": str,                # "Відмінно"/"Добре"/...
            "level": str,                # "excellent"/"good"/"average"/"poor"
            "db_id": int | None          # якщо збережено у БД
        }
    """
    t0 = time.time()

    if text is None:
        raise ValueError("Передано None замість тексту")
    validate_text_length(text)

    # 1-2. Очищення
    cleaned = clean_for_metrics(text)

    # 3. Токенізація (preview для UI)
    words = tokenize_words(cleaned)
    content_words = get_content_words(cleaned)
    sentences = tokenize_sentences(cleaned)
    paragraphs = tokenize_paragraphs(cleaned)

    tokens_preview = {
        "words": words[:30],
        "content_words": content_words[:30],
        "n_words": len(words),
        "n_content_words": len(content_words),
        "n_sentences": len(sentences),
        "n_paragraphs": len(paragraphs),
    }

    # 4. Метрики
    metrics = {}
    for name, fn in METRIC_FUNCTIONS.items():
        try:
            metrics[name] = fn(cleaned)
        except Exception as e:
            metrics[name] = {"score": 0.0, "raw": {"error": str(e)}}

    # 5. Нормалізація
    normalized = normalize_metrics(metrics)

    # 6. Q
    q = compute_q_from_scores(normalized)

    # 7. Інтерпретація
    interpretation = interpret(q)
    breakdown = weighted_breakdown(normalized)

    duration_ms = int((time.time() - t0) * 1000)

    result = {
        "title": title or f"Текст {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "duration_ms": duration_ms,
        "text": text,
        "cleaned_text": cleaned,
        "tokens_preview": tokens_preview,
        "metrics": metrics,
        "normalized": normalized,
        "weights": dict(WEIGHTS),
        "breakdown": breakdown,
        "Q": interpretation["q"],
        "label": interpretation["label"],
        "level": interpretation["level"],
        "db_id": None,
    }

    # 8. Збереження у БД
    if save_to_db:
        from database.db import save_result
        result["db_id"] = save_result(result)

    return result


def reanalyze_from_text(text: str, title: str = None) -> dict:
    """Псевдонім: переобчислити без запису."""
    return analyze_text(text, title=title, save_to_db=False)

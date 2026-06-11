"""
Нормалізація балів метрик у спільний діапазон [0, 1].

Кожна метрика вже повертає свій score у межах [0, 1] (це домовленість на рівні
модулів metrics/*). Цей модуль виконує:
    - безпечне обмеження (clamp) у випадку числових похибок;
    - формування єдиного словника {metric_name: normalized_score}
      у тому порядку, який задано у config.WEIGHTS.
"""
import sys, os

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from config import WEIGHTS  # type: ignore


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Обмежує значення межами [lo, hi]."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return lo
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def normalize_metrics(metric_results: dict) -> dict:
    """
    Отримує dict виду:
        {
          "basic_stats": {"score": 0.8, "raw": {...}},
          "lexical_diversity": {"score": 0.6, ...},
          ...
        }
    Повертає словник нормалізованих score-ів для кожної метрики з WEIGHTS:
        {"basic_stats": 0.8, "lexical_diversity": 0.6, ...}
    Якщо якої-небудь метрики нема у вході — вона отримує 0.0.
    """
    normalized = {}
    for metric_name in WEIGHTS.keys():
        entry = metric_results.get(metric_name) or {}
        score = entry.get("score", 0.0) if isinstance(entry, dict) else 0.0
        normalized[metric_name] = round(clamp(score), 4)
    return normalized

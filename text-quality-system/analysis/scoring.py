"""
Обчислення інтегральної оцінки Q та її інтерпретація.

Формула:
    Q = Σ (metric_score_i * weight_i)    де Σ weight_i = 1
    Q ∈ [0, 1]

Інтерпретація — через config.get_score_label().
"""
import sys, os

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from config import WEIGHTS, get_score_label, SCORE_THRESHOLDS, SCORE_LABELS  # type: ignore


def compute_q_from_scores(scores: dict) -> float:
    """Приймає {metric_name: normalized_score} і повертає Q ∈ [0, 1]."""
    total_weight = sum(WEIGHTS.values())
    if total_weight <= 0:
        return 0.0
    q = 0.0
    for name, weight in WEIGHTS.items():
        s = float(scores.get(name, 0.0))
        if s < 0:
            s = 0.0
        if s > 1:
            s = 1.0
        q += s * weight
    # нормалізуємо на випадок, якщо сума ваг трохи не = 1.0
    q = q / total_weight
    if q < 0:
        return 0.0
    if q > 1:
        return 1.0
    return q


def compute_q(metric_results: dict) -> float:
    """Компактний варіант: приймає повні результати метрик (з score та raw)."""
    scores = {
        name: (metric_results.get(name) or {}).get("score", 0.0)
        for name in WEIGHTS.keys()
    }
    return compute_q_from_scores(scores)


def interpret(q: float) -> dict:
    """Повертає структуру з інтерпретацією Q:
        {"q": 0.73, "label": "Добре", "level": "good"}
    """
    label = get_score_label(q)
    # зворотнє мапування label -> ключ рівня
    level = None
    for key, lbl in SCORE_LABELS.items():
        if lbl == label:
            level = key
            break
    return {
        "q": round(float(q), 4),
        "label": label,
        "level": level,
    }


def weighted_breakdown(scores: dict) -> dict:
    """Повертає внесок кожної метрики в Q — зручно показати в UI."""
    total_weight = sum(WEIGHTS.values()) or 1.0
    breakdown = {}
    for name, w in WEIGHTS.items():
        s = float(scores.get(name, 0.0))
        s = max(0.0, min(1.0, s))
        contrib = s * w / total_weight
        breakdown[name] = {
            "score": round(s, 4),
            "weight": round(w, 4),
            "contribution": round(contrib, 4),
        }
    return breakdown

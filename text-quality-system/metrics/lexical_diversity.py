"""
Метрика: лексична різноманітність.

Рахує:
- TTR (Type-Token Ratio) — відношення унікальних слів до загальної кількості;
- частка hapax legomena — слів, що зустрілися рівно один раз;
- MATTR (Moving-Average TTR) — стабільніша оцінка TTR у вікні 50 слів.

Бал (score ∈ [0, 1]):
Порівнюється TTR та hapax_ratio з ідеалами з config.LEXICAL.
"""
import sys, os
from collections import Counter

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from config import LEXICAL  # type: ignore
from preprocessing.cleaner import clean_for_metrics
from preprocessing.tokenizer import (
    tokenize_words_alpha,
    get_content_words,
    get_unique_words,
    get_hapax_legomena,
)


def _mattr(tokens, window: int = 50) -> float:
    """Moving-Average TTR: для кожного вікна з N підряд слів
    рахуємо TTR, потім беремо середнє. Якщо слів менше window —
    повертаємо звичайний TTR."""
    if len(tokens) < window:
        return (len(set(tokens)) / len(tokens)) if tokens else 0.0

    total = 0.0
    n_windows = len(tokens) - window + 1
    for i in range(n_windows):
        chunk = tokens[i:i + window]
        total += len(set(chunk)) / window
    return total / n_windows


def _linear_score(value: float, ideal: float, minimum: float) -> float:
    """Лінійно відображає value у [0,1]:
    - >= ideal   -> 1.0
    - <= minimum -> 0.0
    - між ними   -> лінійно
    """
    if value >= ideal:
        return 1.0
    if value <= minimum:
        return 0.0
    return (value - minimum) / (ideal - minimum)


def compute(text: str) -> dict:
    cleaned = clean_for_metrics(text)

    all_tokens = tokenize_words_alpha(cleaned)
    content_tokens = get_content_words(cleaned)

    n_all = len(all_tokens)
    n_content = len(content_tokens)
    unique_all = get_unique_words(all_tokens)
    unique_content = get_unique_words(content_tokens)
    hapax_all = get_hapax_legomena(all_tokens)
    hapax_content = get_hapax_legomena(content_tokens)

    # TTR рахуємо на всіх словах (стандартний підхід)
    ttr = (len(unique_all) / n_all) if n_all else 0.0

    # Частка hapax — по унікальним (інакше при малих текстах неінформативно)
    hapax_ratio = (len(hapax_all) / len(unique_all)) if unique_all else 0.0

    mattr = _mattr(all_tokens, window=50)

    # скорінг
    ttr_score = _linear_score(ttr, LEXICAL["ttr_ideal"], LEXICAL["ttr_min"])
    hapax_score = _linear_score(
        hapax_ratio, LEXICAL["hapax_ideal_ratio"], LEXICAL["hapax_ideal_ratio"] * 0.5
    )

    # TTR — головний (60%), hapax (25%), MATTR як стабілізатор (15%)
    mattr_score = _linear_score(mattr, LEXICAL["ttr_ideal"], LEXICAL["ttr_min"])
    score = 0.60 * ttr_score + 0.25 * hapax_score + 0.15 * mattr_score
    score = max(0.0, min(1.0, score))

    return {
        "score": round(score, 4),
        "raw": {
            "n_tokens": n_all,
            "n_unique": len(unique_all),
            "n_content_tokens": n_content,
            "n_unique_content": len(unique_content),
            "n_hapax": len(hapax_all),
            "n_hapax_content": len(hapax_content),
            "ttr": round(ttr, 4),
            "hapax_ratio": round(hapax_ratio, 4),
            "mattr": round(mattr, 4),
            "ttr_score": round(ttr_score, 3),
            "hapax_score": round(hapax_score, 3),
            "mattr_score": round(mattr_score, 3),
        },
    }

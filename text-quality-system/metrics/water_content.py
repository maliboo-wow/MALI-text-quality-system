"""
Метрика: «водність» тексту (скільки слів-паразитів, кліше, шуму).

Вхідні дані:
- BAD_WORDS з dictionary/bad_words.py (категорії: filler, noise, repetition,
  slang, profanity, spam);
- STOP_WORDS з dictionary/stop_words.py (для довідки, не штрафуємо).

Основний показник — ratio:
    water_ratio = count(filler + noise + repetition + slang + spam) / total_words

Бал (score ∈ [0, 1]):
- 1.0, якщо water_ratio <= WATER["ideal_max_ratio"] (0.15);
- 0.0, якщо water_ratio >= WATER["poor_ratio"] (0.40);
- лінійно між ними.

Додатково рахуємо кількість слів з GOOD_WORDS (як позитивний показник
і показуємо у raw для інтерпретації).
"""
import sys, os
from collections import Counter

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from config import WATER  # type: ignore
from preprocessing.cleaner import clean_for_metrics
from preprocessing.tokenizer import tokenize_words_alpha, tokenize_words

# підключаємо dictionary/
_DICT_PATH = os.path.abspath(os.path.join(_BASE, "..", "dictionary"))
if _DICT_PATH not in sys.path:
    sys.path.insert(0, _DICT_PATH)
from bad_words import BAD_CATEGORIES  # type: ignore
from good_words import GOOD_WORDS, GOOD_CATEGORIES, LEVEL_WEIGHTS  # type: ignore
from stop_words import STOP_WORDS  # type: ignore


# категорії, які вважаємо «водою» (знижують якість тексту)
WATER_CATEGORIES = ("filler", "noise", "repetition", "slang", "spam")


def _build_water_set():
    s = set()
    for cat in WATER_CATEGORIES:
        s |= BAD_CATEGORIES.get(cat, set())
    return s


_WATER_WORDS = _build_water_set()
_PROFANITY = BAD_CATEGORIES.get("profanity", set())


def compute(text: str) -> dict:
    cleaned = clean_for_metrics(text)
    tokens = tokenize_words(cleaned)
    n_tokens = len(tokens)

    if n_tokens == 0:
        return {
            "score": 0.0,
            "raw": {
                "n_tokens": 0,
                "water_ratio": 0.0,
                "stopword_ratio": 0.0,
                "profanity_count": 0,
                "good_ratio": 0.0,
                "per_category": {},
            },
        }

    # рахунок за категоріями
    counter = Counter(tokens)

    per_category = {}
    for cat in WATER_CATEGORIES:
        words = BAD_CATEGORIES.get(cat, set())
        cnt = sum(counter[w] for w in words if w in counter)
        per_category[cat] = cnt

    water_count = sum(per_category.values())
    profanity_count = sum(counter[w] for w in _PROFANITY if w in counter)
    stopword_count = sum(counter[w] for w in STOP_WORDS if w in counter)

    # кількість «хороших» слів
    good_count = sum(counter[w] for w in GOOD_WORDS if w in counter)

    # Ratios
    water_ratio = water_count / n_tokens
    stopword_ratio = stopword_count / n_tokens
    good_ratio = good_count / n_tokens

    # «Хороший» зважений скор — за категоріями з good_words з вагами
    weighted_good = 0.0
    for cat, words in GOOD_CATEGORIES.items():
        w_cat = LEVEL_WEIGHTS.get(cat, 1.0)
        cnt = sum(counter[w] for w in words if w in counter)
        weighted_good += cnt * w_cat
    # нормуємо на кількість слів
    good_weighted_ratio = weighted_good / n_tokens

    # scoring
    ideal = WATER["ideal_max_ratio"]
    poor = WATER["poor_ratio"]
    if water_ratio <= ideal:
        water_score = 1.0
    elif water_ratio >= poor:
        water_score = 0.0
    else:
        water_score = 1.0 - (water_ratio - ideal) / (poor - ideal)

    # штраф за лайку (profanity) — академічний текст не може містити лайки
    if profanity_count > 0:
        profanity_penalty = min(1.0, profanity_count / max(n_tokens, 1) * 20)
        water_score *= (1.0 - profanity_penalty)

    # невеликий позитивний бонус за якісну лексику
    bonus = min(0.15, good_weighted_ratio / 0.5)
    score = water_score + bonus
    score = max(0.0, min(1.0, score))

    return {
        "score": round(score, 4),
        "raw": {
            "n_tokens": n_tokens,
            "water_count": water_count,
            "water_ratio": round(water_ratio, 4),
            "stopword_count": stopword_count,
            "stopword_ratio": round(stopword_ratio, 4),
            "profanity_count": profanity_count,
            "good_count": good_count,
            "good_ratio": round(good_ratio, 4),
            "good_weighted_ratio": round(good_weighted_ratio, 4),
            "water_score": round(water_score, 3),
            "good_bonus": round(bonus, 3),
            "per_category": per_category,
        },
    }

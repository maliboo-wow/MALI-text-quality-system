"""
Метрика: «водність» тексту (скільки слів-паразитів, кліше, шуму).

Вхідні дані:
- BAD_WORDS з dictionary/bad_words.py (категорії: filler, noise, repetition,
  slang, profanity, spam);
- STOP_WORDS з dictionary/stop_words.py (для довідки, не штрафуємо).

Основний показник — ratio:
    water_ratio = count(filler + noise + repetition + slang + spam) / total_words

Бал (score ∈ [0, 1]):
- 1.0, якщо water_ratio <= WATER["ideal_max_ratio"] (0.03);
- 0.0, якщо water_ratio >= WATER["poor_ratio"] (0.20);
- лінійно між ними.

Додатково рахуємо кількість слів з GOOD_WORDS (як позитивний показник
і показуємо у raw для інтерпретації).

Слова шукаються з урахуванням словоформ (лематизація pymorphy3) і фраз —
див. preprocessing/dictionary_index.py.
"""
import sys, os

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from config import WATER  # type: ignore
from preprocessing.cleaner import clean_for_metrics
from preprocessing.tokenizer import tokenize_words
from preprocessing.lemmatizer import lemmatize
from preprocessing.dictionary_index import DictionaryIndex

# підключаємо dictionary/
_DICT_PATH = os.path.abspath(os.path.join(_BASE, "..", "dictionary"))
if _DICT_PATH not in sys.path:
    sys.path.insert(0, _DICT_PATH)
from bad_words import BAD_CATEGORIES  # type: ignore
from good_words import GOOD_CATEGORIES, LEVEL_WEIGHTS  # type: ignore
from stop_words import STOP_WORDS  # type: ignore


# категорії, які вважаємо «водою» (знижують якість тексту)
WATER_CATEGORIES = ("filler", "noise", "repetition", "slang", "spam")

# службові категорії шукаємо за точною формою слова, решту — за лемою
EXACT_MATCH_CATEGORIES = {"filler", "noise", "repetition"}

# індекси будуються один раз при імпорті модуля
_BAD_INDEX = {
    cat: DictionaryIndex(words, use_lemmas=cat not in EXACT_MATCH_CATEGORIES)
    for cat, words in BAD_CATEGORIES.items()
}
_GOOD_INDEX = {cat: DictionaryIndex(words) for cat, words in GOOD_CATEGORIES.items()}


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

    # леми рахуємо один раз для всього тексту
    lemmas = lemmatize(tokens)

    # рахунок за категоріями
    per_category = {}
    found_words = {}
    for cat in WATER_CATEGORIES:
        found = _BAD_INDEX[cat].find(tokens, lemmas)
        per_category[cat] = len(found)
        found_words[cat] = sorted(set(found))

    water_count = sum(per_category.values())
    profanity_found = _BAD_INDEX["profanity"].find(tokens, lemmas)
    profanity_count = len(profanity_found)
    found_words["profanity"] = sorted(set(profanity_found))
    stopword_count = sum(1 for t in tokens if t in STOP_WORDS)

    # «Хороші» слова — за категоріями, із вагами рівнів
    good_count = 0
    weighted_good = 0.0
    good_per_category = {}
    for cat, index in _GOOD_INDEX.items():
        cnt = index.count(tokens, lemmas)
        good_per_category[cat] = cnt
        good_count += cnt
        weighted_good += cnt * LEVEL_WEIGHTS.get(cat, 1.0)

    # Ratios
    water_ratio = water_count / n_tokens
    stopword_ratio = stopword_count / n_tokens
    good_ratio = good_count / n_tokens
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
            "good_per_category": good_per_category,
            "found_words": found_words,   # які саме «погані» слова знайдено
        },
    }

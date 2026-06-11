"""
Метрика: базова статистика тексту.

Що рахує:
- кількість символів, слів, речень, абзаців;
- середня довжина слова (у символах);
- середня довжина речення (у словах);
- середня кількість речень у абзаці.

Як виставляє бал (score ∈ [0, 1]):
Оцінюється насамперед відхилення середньої довжини речення та середньої
довжини слова від ідеальних значень (з config.STATS). Занадто короткий
текст (менше STATS["min_words"]) отримує штраф.
"""
import sys, os

# робимо батьківську директорію видимою, щоб імпортувати config
_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from config import STATS  # type: ignore
from preprocessing.cleaner import clean_for_metrics
from preprocessing.tokenizer import (
    tokenize_words,
    tokenize_sentences,
    tokenize_paragraphs,
)


def _triangular_score(value: float, ideal: float, tolerance: float) -> float:
    """Повертає значення у [0, 1]: 1 коли value = ideal,
    спадає лінійно до 0 на відстані tolerance від ideal."""
    if tolerance <= 0:
        return 1.0 if value == ideal else 0.0
    deviation = abs(value - ideal)
    score = 1.0 - (deviation / tolerance)
    return max(0.0, min(1.0, score))


def compute(text: str) -> dict:
    """Обчислює basic_stats. Повертає:
        {
            "score": float,   # [0, 1]
            "raw": {...}      # всі підрахунки
        }
    """
    cleaned = clean_for_metrics(text)

    words = tokenize_words(cleaned)
    sentences = tokenize_sentences(cleaned)
    paragraphs = tokenize_paragraphs(cleaned)

    n_chars = len(cleaned)
    n_words = len(words)
    n_sentences = max(len(sentences), 1)      # щоб не ділити на 0
    n_paragraphs = max(len(paragraphs), 1)

    avg_word_len = (sum(len(w) for w in words) / n_words) if n_words else 0.0
    avg_sentence_len = n_words / n_sentences
    avg_paragraph_sentences = n_sentences / n_paragraphs

    # скорінг
    # 1. Довжина речення: ідеал ~ STATS["ideal_sentence_len"],
    #    допуск ~ (max_sentence_len - ideal_sentence_len) * 2
    sent_tolerance = max(STATS["max_sentence_len"] - STATS["ideal_sentence_len"], 1) * 2
    sent_score = _triangular_score(
        avg_sentence_len,
        STATS["ideal_sentence_len"],
        sent_tolerance,
    )

    # 2. Довжина слова: ідеал ~ STATS["ideal_word_len"], допуск 3 симв.
    word_score = _triangular_score(avg_word_len, STATS["ideal_word_len"], 3.0)

    # 3. Штраф за надто короткий текст
    if n_words >= STATS["min_words"]:
        length_score = 1.0
    else:
        # лінійно від 0 до 1 при наближенні до мінімуму
        length_score = n_words / STATS["min_words"]

    # Підсумковий score метрики — середнє зважене
    score = (sent_score * 0.45) + (word_score * 0.30) + (length_score * 0.25)
    score = max(0.0, min(1.0, score))

    return {
        "score": round(score, 4),
        "raw": {
            "n_chars": n_chars,
            "n_words": n_words,
            "n_sentences": n_sentences,
            "n_paragraphs": n_paragraphs,
            "avg_word_len": round(avg_word_len, 2),
            "avg_sentence_len": round(avg_sentence_len, 2),
            "avg_paragraph_sentences": round(avg_paragraph_sentences, 2),
            "sent_score": round(sent_score, 3),
            "word_score": round(word_score, 3),
            "length_score": round(length_score, 3),
        },
    }

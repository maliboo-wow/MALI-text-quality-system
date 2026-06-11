"""
Метрика: структурованість тексту.

Рахує:
- наявність «вступних» маркерів (intro_keywords з config.STRUCTURE);
- наявність «висновкових» маркерів (conclusion_keywords);
- кількість абзаців (>= min_sections — добре);
- довжина абзаців (дуже короткі/дуже довгі — гірше).

Бал (score ∈ [0, 1]):
Зважена сума прапорців та показників.
"""
import sys, os

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from config import STRUCTURE  # type: ignore
from preprocessing.cleaner import clean_for_metrics
from preprocessing.tokenizer import (
    tokenize_paragraphs,
    tokenize_words,
    tokenize_sentences,
)


def _contains_any(text_lower: str, keywords) -> bool:
    return any(kw in text_lower for kw in keywords)


def compute(text: str) -> dict:
    cleaned = clean_for_metrics(text)
    low = cleaned.lower()

    paragraphs = tokenize_paragraphs(cleaned)
    n_paragraphs = len(paragraphs)

    # Дивимось на перші 20 % тексту як на потенційний вступ,
    # та на останні 20 % як на потенційні висновки.
    cut = max(100, len(low) // 5)
    head = low[:cut]
    tail = low[-cut:]

    has_intro = _contains_any(head, STRUCTURE["intro_keywords"])
    has_conclusion = _contains_any(tail, STRUCTURE["conclusion_keywords"])

    # Якщо маркери не знайшли у «головах/хвостах», перевіряємо весь текст
    # (трохи поступаємось — бо маркер може бути не в очікуваній зоні)
    has_intro_any = has_intro or _contains_any(low, STRUCTURE["intro_keywords"])
    has_conclusion_any = has_conclusion or _contains_any(
        low, STRUCTURE["conclusion_keywords"]
    )

    # Бали за наявність у правильній позиції — 1.0,
    # десь у тексті — 0.5, немає зовсім — 0.
    intro_score = 1.0 if has_intro else (0.5 if has_intro_any else 0.0)
    conclusion_score = 1.0 if has_conclusion else (0.5 if has_conclusion_any else 0.0)

    # кількість розділів/абзаців
    min_sections = STRUCTURE["min_sections"]
    if n_paragraphs >= min_sections:
        sections_score = 1.0
    elif n_paragraphs == 0:
        sections_score = 0.0
    else:
        sections_score = n_paragraphs / min_sections

    # рівномірність абзаців (довжина у словах)
    paragraph_sizes = [len(tokenize_words(p)) for p in paragraphs] if paragraphs else []
    if paragraph_sizes:
        mean = sum(paragraph_sizes) / len(paragraph_sizes)
        # коефіцієнт варіації
        if mean > 0:
            variance = sum((s - mean) ** 2 for s in paragraph_sizes) / len(paragraph_sizes)
            cv = (variance ** 0.5) / mean
            uniformity_score = max(0.0, 1.0 - min(cv, 1.0))
        else:
            uniformity_score = 0.0
    else:
        uniformity_score = 0.0

    # Зважена сума
    score = (
        0.30 * intro_score
        + 0.30 * conclusion_score
        + 0.25 * sections_score
        + 0.15 * uniformity_score
    )
    score = max(0.0, min(1.0, score))

    return {
        "score": round(score, 4),
        "raw": {
            "n_paragraphs": n_paragraphs,
            "n_sentences": len(tokenize_sentences(cleaned)),
            "has_intro": has_intro,
            "has_intro_any": has_intro_any,
            "has_conclusion": has_conclusion,
            "has_conclusion_any": has_conclusion_any,
            "intro_score": round(intro_score, 3),
            "conclusion_score": round(conclusion_score, 3),
            "sections_score": round(sections_score, 3),
            "uniformity_score": round(uniformity_score, 3),
            "paragraph_sizes": paragraph_sizes,
        },
    }

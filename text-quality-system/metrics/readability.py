"""
Метрика: читабельність.

Використовується Coleman-Liau Index (CLI):
    CLI = 0.0588 * L - 0.296 * S - 15.8
де
    L = середня кількість букв у 100 словах,
    S = середнє число речень у 100 словах.

CLI відповідає приблизному класу складності тексту (рівень шкільного класу).

Додатково рахуємо Flesch-подібну оцінку для укр. мови на складах:
    FRE_uk = 206.835 - 1.3 * ASL - 60.1 * ASW
де ASL — середня довжина речення у словах,
   ASW — середня кількість складів на слово.

Бал (score ∈ [0, 1]):
Близькість CLI до config.READABILITY["ideal_cli"] з допусками min/max.
"""
import sys, os

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from config import READABILITY  # type: ignore
from preprocessing.cleaner import clean_for_metrics
from preprocessing.tokenizer import (
    tokenize_words,
    tokenize_sentences,
    count_syllables_uk,
)


def _coleman_liau(text: str, n_words: int, n_sentences: int) -> float:
    """Coleman-Liau Index. Повертає ~0 якщо тексту замало."""
    if n_words < 1 or n_sentences < 1:
        return 0.0
    # L — букв на 100 слів (рахуємо тільки літери, без цифр/розділових)
    letters = sum(1 for ch in text if ch.isalpha())
    L = (letters / n_words) * 100
    S = (n_sentences / n_words) * 100
    return 0.0588 * L - 0.296 * S - 15.8


def _flesch_uk(words, n_sentences: int) -> float:
    """Адаптований Flesch Reading Ease для української (по складах)."""
    n_words = len(words)
    if n_words < 1 or n_sentences < 1:
        return 0.0
    total_syl = sum(count_syllables_uk(w) for w in words)
    ASL = n_words / n_sentences
    ASW = total_syl / n_words
    return 206.835 - 1.3 * ASL - 60.1 * ASW


def _cli_score(cli: float) -> float:
    """Переводить CLI в score 0..1:
    - ідеал -> 1.0
    - виходить за max_cli або min_cli -> 0.0
    - між ними -> лінійно (трикутник).
    """
    ideal = READABILITY["ideal_cli"]
    mx = READABILITY["max_cli"]
    mn = READABILITY["min_cli"]

    if cli >= ideal:
        # погіршення вправо
        if cli >= mx:
            return 0.0
        return 1.0 - (cli - ideal) / (mx - ideal)
    else:
        # погіршення вліво (надто просто)
        if cli <= mn:
            return 0.0
        return 1.0 - (ideal - cli) / (ideal - mn)


def compute(text: str) -> dict:
    cleaned = clean_for_metrics(text)
    words = tokenize_words(cleaned)
    sentences = tokenize_sentences(cleaned)

    n_words = len(words)
    n_sentences = max(len(sentences), 1)

    cli = _coleman_liau(cleaned, n_words, n_sentences)
    fre = _flesch_uk(words, n_sentences)

    cli_score = _cli_score(cli)
    # FRE лежить у ~[0, 100]; вважаємо ідеалом ~60 (комфортно читається)
    fre_score = max(0.0, 1.0 - abs(fre - 60.0) / 60.0)
    fre_score = min(1.0, fre_score)

    # основну вагу віддаємо CLI (як описано в конфігу), FRE — додатково
    score = 0.75 * cli_score + 0.25 * fre_score
    score = max(0.0, min(1.0, score))

    return {
        "score": round(score, 4),
        "raw": {
            "coleman_liau": round(cli, 2),
            "flesch_uk": round(fre, 2),
            "cli_score": round(cli_score, 3),
            "fre_score": round(fre_score, 3),
            "n_words": n_words,
            "n_sentences": n_sentences,
        },
    }

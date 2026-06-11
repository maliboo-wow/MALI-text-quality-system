"""
Метрика: TF-IDF аналіз тексту.

Реалізація без зовнішніх бібліотек (власний обчислювач TF-IDF).
Текст розбивається на «документи» (абзаци, або речення — якщо абзаців мало).
Для кожного токена (без стоп-слів) рахуємо:
    tf(t, d)       = частота t у документі d / довжина d
    idf(t)         = log(N / df(t))  (з +1 у df для згладжування)
    tfidf(t, d)    = tf * idf
Для всього тексту беремо максимальний tfidf слова серед усіх документів.

Повертає:
- top_keywords — top-N ключових слів (з config.TFIDF["top_n_keywords"]);
- score ∈ [0, 1] — «інформативність» тексту:
    чим більша частка змістовних слів із високим TF-IDF,
    тим більша тематична концентрація тексту.
"""
import math
import sys, os
from collections import Counter, defaultdict

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from config import TFIDF  # type: ignore
from preprocessing.cleaner import clean_for_metrics
from preprocessing.tokenizer import (
    tokenize_paragraphs,
    tokenize_sentences,
    tokenize_words_alpha,
    remove_stopwords,
)


def _split_into_documents(text: str):
    """Повертає список документів для TF-IDF: абзаци, або речення
    (якщо абзаців 1-2). Кожен документ — список токенів (без стоп-слів)."""
    paragraphs = tokenize_paragraphs(text)
    if len(paragraphs) >= 3:
        chunks = paragraphs
    else:
        chunks = tokenize_sentences(text)

    docs = []
    for ch in chunks:
        tokens = remove_stopwords(tokenize_words_alpha(ch))
        if tokens:
            docs.append(tokens)
    return docs


def _compute_tfidf(docs):
    """Повертає:
        term_best_tfidf: {word: max_tfidf_across_docs}
        term_total_tfidf: {word: sum_tfidf_across_docs}
        df: {word: кількість документів, де зустрічається}
    """
    n_docs = len(docs)
    if n_docs == 0:
        return {}, {}, {}

    # document frequency
    df = defaultdict(int)
    for d in docs:
        for w in set(d):
            df[w] += 1

    # idf зі згладжуванням
    idf = {w: math.log((1 + n_docs) / (1 + c)) + 1 for w, c in df.items()}

    best = {}
    total = defaultdict(float)
    for d in docs:
        length = len(d)
        if length == 0:
            continue
        tf_counts = Counter(d)
        for w, cnt in tf_counts.items():
            tf = cnt / length
            val = tf * idf[w]
            total[w] += val
            if val > best.get(w, 0.0):
                best[w] = val

    return best, dict(total), dict(df)


def compute(text: str) -> dict:
    cleaned = clean_for_metrics(text)
    docs = _split_into_documents(cleaned)

    best, total, df = _compute_tfidf(docs)

    top_n = TFIDF["top_n_keywords"]
    min_df_filter = TFIDF["min_df"]
    max_features = TFIDF["max_features"]

    # фільтр за мінімальним document frequency
    filtered = {w: v for w, v in best.items() if df.get(w, 0) >= min_df_filter}

    # топ-N ключових слів за максимальним tfidf
    top = sorted(filtered.items(), key=lambda kv: kv[1], reverse=True)[:top_n]

    # SCORE
    # Ідея: хороший текст має невеличке «ядро» слів з відчутно вищим tfidf за середнє.
    # Рахуємо частку унікальних змістовних слів, у яких
    # максимальний tfidf >= медіани. Також рахуємо концентрацію top-N.
    if not filtered:
        score = 0.0
        concentration = 0.0
        above_median_ratio = 0.0
    else:
        values = sorted(filtered.values())
        median = values[len(values) // 2]
        above_median = sum(1 for v in values if v >= median)
        above_median_ratio = above_median / len(values)

        # Частка ваги top-N від усього
        total_sum = sum(total.values()) or 1.0
        top_sum = sum(total.get(w, 0.0) for w, _ in top)
        concentration = top_sum / total_sum

        # помірна концентрація (20-60%) вважається хорошою
        if concentration < 0.2:
            conc_score = concentration / 0.2
        elif concentration <= 0.6:
            conc_score = 1.0
        else:
            conc_score = max(0.0, 1.0 - (concentration - 0.6) / 0.4)

        score = 0.5 * above_median_ratio + 0.5 * conc_score

    # обмежуємо кількість ознак у відповіді (не все потрібно зберігати)
    limited_best = dict(
        sorted(filtered.items(), key=lambda kv: kv[1], reverse=True)[:max_features]
    )

    score = max(0.0, min(1.0, score))

    return {
        "score": round(score, 4),
        "raw": {
            "n_documents": len(docs),
            "n_unique_terms": len(filtered),
            "concentration_top_n": round(concentration, 4) if filtered else 0.0,
            "above_median_ratio": round(above_median_ratio, 4) if filtered else 0.0,
            "top_keywords": [(w, round(v, 4)) for w, v in top],
            "tfidf_best": {w: round(v, 4) for w, v in limited_best.items()},
        },
    }

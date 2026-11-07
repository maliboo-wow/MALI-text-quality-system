"""
Лематизація українських слів (pymorphy3 + словник ВЕСУМ).

Потрібна, щоб слово зі словника знаходилось у тексті в будь-якій формі:
«аналітичний» -> «аналітичну», «аналітичних», «аналітичною».

Ключ слова (однаковий для словника і для тексту):
- слово відоме pymorphy3 — його лема;
- невідоме (сленг, суржик, «ааа») — саме слово.

Якщо pymorphy3 не встановлено — ключем завжди є саме слово.
"""
from functools import lru_cache

try:
    import pymorphy3
    _MORPH = pymorphy3.MorphAnalyzer(lang="uk")
    _HAS_MORPH = True
except Exception:  # pragma: no cover
    _MORPH = None
    _HAS_MORPH = False


def is_available() -> bool:
    """Чи працює лематизація (встановлено pymorphy3 з українським словником)."""
    return _HAS_MORPH


@lru_cache(maxsize=200_000)
def lemma(word: str) -> str:
    """Повертає лему відомого слова або саме слово, якщо воно невідоме."""
    w = _normalize(word)
    if not _HAS_MORPH or not _MORPH.word_is_known(w):
        return w
    return _MORPH.parse(w)[0].normal_form


def lemmatize(tokens):
    """Список токенів -> список лем."""
    return [lemma(t) for t in tokens]


def is_imperative(word: str) -> bool:
    """Чи є слово наказовою формою дієслова («натисни», «підпишись»)."""
    if not _HAS_MORPH:
        return False
    w = _normalize(word)
    return _MORPH.word_is_known(w) and "impr" in _MORPH.parse(w)[0].tag


# Внутрішні утиліти
def _normalize(word: str) -> str:
    """Нижній регістр + звичайний апостроф."""
    return word.lower().replace("’", "'").replace("ʼ", "'").replace("`", "'")

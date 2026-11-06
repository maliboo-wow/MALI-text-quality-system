"""
Лематизація українських слів (pymorphy3 + словник ВЕСУМ).

Навіщо: словники зберігають слово в одній формі («аналітичний»), а в тексті
воно трапляється в будь-якому відмінку («аналітичну», «аналітичних»).
Тому і слова словника, і слова тексту зводимо до спільного ключа — леми.

Правило побудови ключа (однакове для словника і для тексту):
    - слово відоме словнику pymorphy3  -> його нормальна форма (лема);
    - слово невідоме (сленг, суржик, «ааа») -> саме слово без змін.

Якщо pymorphy3 не встановлено, ключем завжди є саме слово — система
продовжує працювати, просто без лематизації.
"""
from functools import lru_cache

try:
    import pymorphy3
    _MORPH = pymorphy3.MorphAnalyzer(lang="uk")
except Exception:  # бібліотеки або словника немає — працюємо без лематизації
    _MORPH = None

# різні варіанти апострофа зводимо до одного
_APOSTROPHES = str.maketrans({"’": "'", "ʼ": "'", "`": "'", "ʹ": "'"})


def is_available() -> bool:
    """Чи доступна лематизація (встановлено pymorphy3 з українським словником)."""
    return _MORPH is not None


def normalize_word(word: str) -> str:
    """Нижній регістр + єдиний апостроф."""
    return word.lower().translate(_APOSTROPHES)


@lru_cache(maxsize=200_000)
def lemma(word: str) -> str:
    """Повертає ключ слова: лему для відомих слів, саме слово — для невідомих."""
    w = normalize_word(word)
    if _MORPH is None or not _MORPH.word_is_known(w):
        return w
    return _MORPH.parse(w)[0].normal_form


def is_imperative(word: str) -> bool:
    """Чи є слово формою наказового способу («натисни», «підпишись»)."""
    if _MORPH is None:
        return False
    w = normalize_word(word)
    return _MORPH.word_is_known(w) and "impr" in _MORPH.parse(w)[0].tag


def lemmatize(tokens):
    """Список токенів -> список лем (ключів)."""
    return [lemma(t) for t in tokens]

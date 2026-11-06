"""
Перевірки цілісності словників:
    - жодна лема не повторюється між категоріями;
    - «хороші» і «погані» слова не перетинаються;
    - загальний розмір словника — не менше 5000 унікальних лем.

Запуск (з папки text-quality-system):  python -m pytest
"""
import os
import sys
from collections import defaultdict

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "..", "dictionary"))

from bad_words import BAD_CATEGORIES  # type: ignore  # noqa: E402
from good_words import GOOD_CATEGORIES  # type: ignore  # noqa: E402
from metrics.water_content import _BAD_INDEX, _GOOD_INDEX  # noqa: E402


def _keys(index):
    """Усі ключі індексу: леми, точні форми та фрази."""
    return index.words | index.exact | {" ".join(p) for p in index.phrases}


def _owners():
    owners = defaultdict(list)
    for prefix, indexes in (("good", _GOOD_INDEX), ("bad", _BAD_INDEX)):
        for cat, index in indexes.items():
            for k in _keys(index):
                owners[k].append(f"{prefix}.{cat}")
    return owners


def test_no_lemma_in_two_categories():
    dupes = {k: cats for k, cats in _owners().items() if len(cats) > 1}
    assert not dupes, f"Леми в кількох категоріях: {sorted(dupes.items())[:20]}"


def test_good_and_bad_do_not_overlap():
    good = set().union(*(_keys(i) for i in _GOOD_INDEX.values()))
    bad = set().union(*(_keys(i) for i in _BAD_INDEX.values()))
    assert not good & bad, f"Слова одночасно хороші й погані: {sorted(good & bad)[:20]}"


def test_dictionary_size():
    assert len(_owners()) >= 5000


def test_entries_are_lowercase_strings():
    for cats in (GOOD_CATEGORIES, BAD_CATEGORIES):
        for cat, words in cats.items():
            bad = [w for w in words if not isinstance(w, str) or w != w.lower() or not w.strip()]
            assert not bad, f"{cat}: некоректні записи {bad[:10]}"

"""
Тести словників.

Перевіряє:
- жодна лема не повторюється в кількох категоріях;
- «хороші» і «погані» слова не перетинаються;
- у словниках не менше 5000 унікальних лем;
- усі записи — непорожні рядки в нижньому регістрі.

Запуск (з папки text-quality-system): python -m pytest
"""
import sys, os
from collections import defaultdict

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from preprocessing.dictionary_index import all_keys
from metrics.water_content import _BAD_INDEX, _GOOD_INDEX, BAD_CATEGORIES, GOOD_CATEGORIES


def _owners():
    """{ключ: [категорії, де він зустрічається]}"""
    owners = defaultdict(list)
    for cat, index in _GOOD_INDEX.items():
        for key in all_keys(index):
            owners[key].append("good." + cat)
    for cat, index in _BAD_INDEX.items():
        for key in all_keys(index):
            owners[key].append("bad." + cat)
    return owners


def test_no_lemma_in_two_categories():
    dupes = {k: cats for k, cats in _owners().items() if len(cats) > 1}
    assert not dupes, f"Леми в кількох категоріях: {sorted(dupes.items())[:20]}"


def test_good_and_bad_do_not_overlap():
    good = set().union(*(all_keys(i) for i in _GOOD_INDEX.values()))
    bad = set().union(*(all_keys(i) for i in _BAD_INDEX.values()))
    assert not good & bad, f"Слова одночасно хороші й погані: {sorted(good & bad)[:20]}"


def test_dictionary_size():
    assert len(_owners()) >= 5000


def test_entries_are_lowercase():
    for categories in (GOOD_CATEGORIES, BAD_CATEGORIES):
        for cat, words in categories.items():
            wrong = [w for w in words if not w.strip() or w != w.lower()]
            assert not wrong, f"{cat}: некоректні записи {wrong[:10]}"

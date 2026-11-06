"""Перевірки метрики «водності»: словоформи, фрази, точний збіг для паразитів."""
import os
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE)

from metrics.water_content import compute  # noqa: E402
from preprocessing.lemmatizer import is_available  # noqa: E402
from preprocessing.tokenizer import tokenize_words  # noqa: E402


def test_apostrophe_is_part_of_word():
    assert tokenize_words("Об’єктивний п'ятий") == ["об'єктивний", "п'ятий"]


def test_inflected_good_words_are_found():
    if not is_available():
        return  # без pymorphy3 словоформи не розпізнаються — це очікувано
    raw = compute("Аналітичну роботу провели науковці з експериментальної лабораторії.")["raw"]
    assert raw["good_count"] >= 3


def test_filler_matched_by_exact_form_only():
    # «типу» як паразит рахується, а «тип» (іменник) — ні
    assert compute("Короче, я типу не знаю.")["raw"]["per_category"]["filler"] == 2
    assert compute("Цей тип даних описано в розділі.")["raw"]["per_category"]["filler"] == 0


def test_phrases_are_counted_once():
    found = compute("Ну типу так.")["raw"]["found_words"]["filler"]
    assert "ну типу" in found
    assert "ну" not in found and "типу" not in found


def test_imperative_spam_is_exact():
    raw = compute("Компанія поділилася результатами. Підпишись і поділись!")["raw"]
    assert sorted(raw["found_words"]["spam"]) == ["поділись", "підпишись"]


def test_neutral_words_are_not_water():
    text = "Батько десь колись казав, що тут і там щось ніби змінилося."
    assert compute(text)["raw"]["water_count"] == 0

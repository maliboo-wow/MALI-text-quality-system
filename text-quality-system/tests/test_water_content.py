"""
Тести метрики «водності».

Перевіряє:
- апостроф не розриває слово;
- словоформи «хороших» слів знаходяться через лематизацію;
- слова-паразити рахуються лише за точною формою;
- фрази рахуються один раз;
- наказові форми в спамі шукаються точно;
- нейтральні слова не вважаються «водою».
"""
import sys, os

_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from metrics.water_content import compute
from preprocessing.lemmatizer import is_available
from preprocessing.tokenizer import tokenize_words


def test_apostrophe_is_part_of_word():
    assert tokenize_words("Об’єктивний п'ятий") == ["об'єктивний", "п'ятий"]


def test_inflected_good_words_are_found():
    # без pymorphy3 словоформи не розпізнаються — це очікувано
    if not is_available():
        return
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

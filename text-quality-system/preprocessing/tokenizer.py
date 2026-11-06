import re
import sys
import os
from collections import Counter

_dictionary_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dictionary"))
sys.path.insert(0, _dictionary_path)
from stop_words import STOP_WORDS  # type: ignore


# слова

def tokenize_words(text):
    """Розбиває текст на слова (з цифрами). Апостроф усередині слова не розриває його."""
    text = _normalize_apostrophes(text.lower())
    return re.findall(r"[а-яіїєґa-z0-9]+(?:'[а-яіїєґa-z0-9]+)*", text)


def tokenize_words_alpha(text):
    """Розбиває текст на слова (тільки букви, без цифр)."""
    text = _normalize_apostrophes(text.lower())
    return re.findall(r"[а-яіїєґa-z]+(?:'[а-яіїєґa-z]+)*", text)


def remove_stopwords(tokens):
    """Прибирає стоп-слова зі списку."""
    return [t for t in tokens if t not in STOP_WORDS]


def get_content_words(text):
    """Повертає змістовні слова (без стоп-слів)."""
    tokens = tokenize_words_alpha(text)
    return remove_stopwords(tokens)


# речення і абзаци

def tokenize_sentences(text):
    """Розбиває текст на речення (по крапці, знаку оклику, питання)."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in parts if s.strip()]


def tokenize_paragraphs(text):
    """Розбиває текст на абзаци (по порожньому рядку)."""
    parts = text.split('\n\n')
    return [p.strip() for p in parts if p.strip()]


# допоміжні

def count_syllables_uk(word):
    """Рахує склади в слові — по кількості голосних."""
    vowels = 'аеєиіїоуюя'
    return sum(1 for ch in word.lower() if ch in vowels)


def get_unique_words(tokens):
    """Множина унікальних слів."""
    return set(tokens)


def get_hapax_legomena(tokens):
    """Слова що зустрічаються рівно 1 раз — показник багатства лексики."""
    counts = Counter(tokens)
    return [word for word, freq in counts.items() if freq == 1]


def _normalize_apostrophes(text):
    """Зводить різні апострофи (’ ʼ `) до звичайного '."""
    return text.replace("’", "'").replace("ʼ", "'").replace("`", "'")
import re
import unicodedata

# Інтерфейс

def clean_text(text: str) -> str:
    text = _normalize_unicode(text)
    text = _remove_html(text)
    text = _remove_urls(text)
    text = _remove_junk_chars(text)
    text = _normalize_whitespace(text)
    return text.strip()


def clean_for_metrics(text: str) -> str:
    """Полегшене очищення — зберігає розділові знаки та структуру(потрібно для підрахунку речень і абзаців)."""
    text = _normalize_unicode(text)
    text = _remove_html(text)
    text = _remove_urls(text)
    text = _normalize_whitespace(text)
    return text.strip()

# Внутрішні функції

def _normalize_unicode(text: str) -> str:
    """NFC-нормалізація: 'й' як одна кодова точка, а не 'и' + '̆'."""
    return unicodedata.normalize("NFC", text)


def _remove_html(text: str) -> str:
    """Видаляє HTML-теги (<b>, <p>, &nbsp; тощо)."""
    text = re.sub(r'<[^>]+>', ' ', text)          # теги
    text = re.sub(r'&[a-z]+;', ' ', text)          # HTML-ентіті (&nbsp; &amp; ...)
    return text


def _remove_urls(text: str) -> str:
    """Видаляє http/https посилання та www-адреси."""
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    return text


def _remove_junk_chars(text: str) -> str:
    """Залишає:
      - українські та латинські літери
      - цифри
      - базові розділові знаки: . , ! ? ; : ( ) - — « »
      - пробіли та переноси рядків
    """
    return re.sub(r'[^\w\s.,!?;:()\-—«»\n]', '', text)


def _normalize_whitespace(text: str) -> str:
    """ - Стискає кілька пробілів в один
    - Стискає більше двох переносів рядка у два (зберігає абзаци)
    """
    text = re.sub(r'[^\S\n]+', ' ', text)       # пробіли (але не \n)
    text = re.sub(r'\n{3,}', '\n\n', text)       # зайві порожні рядки
    return text

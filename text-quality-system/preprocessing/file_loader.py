"""
Завантаження тексту з файлів (DOCX, TXT) та з довільних джерел.

Підтримує:
- шляхи до файлів;
- file-like об'єкти (наприклад, UploadedFile зі Streamlit);
- bytes / str.

Функція load_any() визначає формат автоматично за розширенням або MIME.
"""
import io
import os
from typing import Union

try:
    import docx  # python-docx
    _HAS_DOCX = True
except Exception:  # pragma: no cover
    _HAS_DOCX = False


class UnsupportedFileError(ValueError):
    pass


# TXT
def load_txt(source) -> str:
    """Читає TXT з шляху/bytes/file-like. Автовизначення кодування."""
    data = _read_bytes(source)
    # типові кодування для української
    for enc in ("utf-8", "utf-8-sig", "cp1251", "koi8-u"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    # остання спроба — з заміною
    return data.decode("utf-8", errors="replace")


# DOCX
def load_docx(source) -> str:
    """Читає DOCX з шляху/bytes/file-like. Потребує python-docx."""
    if not _HAS_DOCX:
        raise UnsupportedFileError(
            "Для читання DOCX потрібна бібліотека python-docx. "
            "Встановіть: pip install python-docx"
        )
    if isinstance(source, (str, os.PathLike)):
        document = docx.Document(source)
    else:
        data = _read_bytes(source)
        document = docx.Document(io.BytesIO(data))

    parts = []
    for para in document.paragraphs:
        txt = para.text
        if txt:
            parts.append(txt)

    # Таблиці — витягуємо як додаткові рядки
    for table in document.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text)
            if row_text:
                parts.append(row_text)

    return "\n\n".join(parts).strip()


# Універсальний завантажувач
def load_any(source, filename: str = None) -> str:
    """
    Визначає формат за розширенням (або за параметром filename) та завантажує.
    source: path / bytes / file-like (із .name)
    filename: опційно — щоб явно вказати ім'я/розширення
    """
    name = filename
    if name is None:
        if isinstance(source, (str, os.PathLike)):
            name = str(source)
        elif hasattr(source, "name"):
            name = source.name

    ext = ""
    if name:
        ext = os.path.splitext(name)[1].lower()

    if ext in (".docx",):
        return load_docx(source)
    if ext in (".txt", ".text", ".md", ""):
        # дефолт — текст
        return load_txt(source)

    # невідоме розширення — пробуємо як текст
    try:
        return load_txt(source)
    except Exception as e:
        raise UnsupportedFileError(
            f"Невідомий формат файлу: {ext or '—'}. Причина: {e}"
        )


# Внутрішні утиліти
def _read_bytes(source) -> bytes:
    """Уніфіковано читає bytes зі всіх типів джерел."""
    if isinstance(source, bytes):
        return source
    if isinstance(source, str) and os.path.exists(source):
        with open(source, "rb") as f:
            return f.read()
    if isinstance(source, str):
        # вже готовий текст
        return source.encode("utf-8")
    if hasattr(source, "read"):
        data = source.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        # Streamlit uploaded file потім може бути використаний повторно — спробуємо seek(0)
        try:
            source.seek(0)
        except Exception:
            pass
        return data
    raise TypeError(f"Непідтримуваний тип джерела: {type(source).__name__}")

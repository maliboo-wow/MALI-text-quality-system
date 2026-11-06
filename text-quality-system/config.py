import os


# 1. ШЛЯХИ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "texts.db")
DICTIONARY_DIR = os.path.join(BASE_DIR, "..", "dictionary")
SAMPLE_TEXTS_DIR = os.path.join(BASE_DIR, "tests", "sample_texts")

# 2. ВАГИ МЕТРИК  (сума повинна = 1.0)
WEIGHTS = {
    "lexical_diversity": 0.20,   # різноманітність лексики (TTR, hapax)
    "readability":       0.25,   # читабельність (ARI / Coleman-Liau)
    "water_content":     0.20,   # водність (стоп-слова, кліше)
    "basic_stats":       0.15,   # базова статистика (довжини, кількості)
    "structure":         0.20,   # наявність структурних елементів
}

# Перевірка суми ваг при імпорті
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, (
    f"Сума ваг WEIGHTS має дорівнювати 1.0, зараз = {sum(WEIGHTS.values())}"
)

# 3. ПОРОГИ ІНТЕГРАЛЬНОЇ ОЦІНКИ  (Q від 0 до 1)

SCORE_THRESHOLDS = {
    "excellent": 0.80,   # відмінно
    "good":      0.60,   # добре
    "average":   0.40,   # задовільно
    # нижче 0.40 - незадовільно
}

SCORE_LABELS = {
    "excellent": "Відмінно",
    "good":      "Добре",
    "average":   "Задовільно",
    "poor":      "Незадовільно",
}

def get_score_label(score: float) -> str:
    """Повертає текстову оцінку за числовим значенням Q."""
    if score >= SCORE_THRESHOLDS["excellent"]:
        return SCORE_LABELS["excellent"]
    elif score >= SCORE_THRESHOLDS["good"]:
        return SCORE_LABELS["good"]
    elif score >= SCORE_THRESHOLDS["average"]:
        return SCORE_LABELS["average"]
    else:
        return SCORE_LABELS["poor"]


# 4. ПАРАМЕТРИ МЕТРИК

# Базова статистика
STATS = {
    "min_words":          50,    # мінімальна кількість слів для аналізу
    "ideal_sentence_len": 15,    # ідеальна середня довжина речення (слів)
    "max_sentence_len":   30,    # речення довші за це вважаються складними
    "ideal_word_len":     6,     # ідеальна середня довжина слова (символів)
}

# Лексична різноманітність
LEXICAL = {
    "ttr_ideal":          0.70,  # ідеальний Type-Token Ratio
    "ttr_min":            0.40,  # мінімально прийнятний TTR
    "hapax_ideal_ratio":  0.50,  # ідеальна частка hapax legomena
}

# Читабельність (Coleman-Liau Index)
READABILITY = {
    "ideal_cli":          10.0,  # ідеальний рівень
    "max_cli":            16.0,  # вище — надто складно
    "min_cli":            5.0,   # нижче — надто просто
}

# Водність тексту
WATER = {
    "ideal_max_ratio":    0.03,  # ≤3 % водних слів — добре
    "poor_ratio":         0.20,  # ≥20 % — незадовільно
}

# Структура
STRUCTURE = {
    # Ключові слова для визначення вступу (нижній регістр)
    "intro_keywords": [
        "вступ", "введення", "мета", "актуальність",
        "у цій роботі", "розглянемо", "дана робота",
    ],
    # Ключові слова для визначення висновків
    "conclusion_keywords": [
        "висновок", "висновки", "підсумок", "підсумовуючи",
        "таким чином", "отже", "підведемо підсумки",
        "в результаті", "підсумовуючи вищесказане",
    ],
    # Мінімальна кількість розділів/абзаців для «структурованого» тексту
    "min_sections": 3,
}

# TF-IDF
TFIDF = {
    "top_n_keywords":     10,    # скільки ключових слів виводити
    "min_df":             1,     # мінімальна частота документа
    "max_features":       500,   # максимум фіч для векторизатора
}

# 5. ПАРАМЕТРИ БАЗИ ДАНИХ

DB = {
    "path": DB_PATH,              # де зберігається файл texts.db
    "echo": False,                # якщо True — в консоль друкуватиметься кожен SQL-запит
    "check_same_thread": False,   # потрібно при багатопотоковому доступі до SQLite
}

# 6. ПАРАМЕТРИ ЗАСТОСУНКУ (Streamlit)

APP = {
    "title":        "Система оцінки якості тексту",  # назва у вкладці браузера
    "max_text_len": 100_000,   # обмеження: якщо вставили занадто великий текст — відхиляємо
    "min_text_len": 50,        # якщо текст надто короткий — теж відхиляємо
}

# 7. ЛОГУВАННЯ

LOGGING = {
    "level":   "INFO",     # що писати в лог: INFO = звичайні події, DEBUG = все підряд
    "format":  "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "to_file": False,      # False = виводити в консоль, True = писати у файл app.log
    "log_file": "app.log", # шлях до файлу (якщо to_file = True)
}
import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import config
from analysis.pipeline import analyze_text, TextTooShortError, TextTooLongError
from preprocessing.file_loader import load_any, UnsupportedFileError
from database import db as db_layer

# словники
sys.path.insert(0, os.path.abspath(os.path.join(BASE, "..", "dictionary")))
from bad_words import BAD_CATEGORIES   # type: ignore
from good_words import GOOD_CATEGORIES  # type: ignore
from stop_words import STOP_WORDS       # type: ignore


METRIC_NAMES = {
    "basic_stats": "Базова статистика",
    "lexical_diversity": "Лексична різноманітність",
    "readability": "Читабельність",
    "structure": "Структурованість",
    "water_content": "Водність",
    "tfidf": "TF-IDF",
}

DEMO_TEXT = """Вступ. У цій роботі розглянемо проблему автоматизованої оцінки якості письмового тексту. Актуальність дослідження обумовлена зростанням обсягів електронного контенту та потребою у швидких інструментах перевірки.

Основна частина. Запропоновано систему обчислення інтегральної оцінки Q на основі шести метрик: базова статистика, лексична різноманітність, читабельність за Coleman-Liau, водність, структурованість та TF-IDF-аналіз. Кожна метрика приведена до спільної шкали [0, 1], після чого обчислюється зважена сума.

Висновок. Підведемо підсумки: розроблена система МАЛІ дозволяє швидко оцінювати якість україномовного тексту й може бути інтегрована у редактори, освітні сервіси та засоби автоматичної перевірки робіт."""


st.set_page_config(page_title="МАЛІ · Mali", layout="wide")

# стилі
st.markdown("""
<style>
.stApp { background: #FFFFFF; color: #0F0F14; }
#MainMenu, footer, header { visibility: hidden; }

section[data-testid="stSidebar"] {
    background: #F5F1FA !important;
    border-right: 1px solid #E5DFEF;
}
section[data-testid="stSidebar"] *,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p {
    color: #0F0F14 !important;
}

h1, h2, h3, h4, h5 { color: #0F0F14; }

.stButton > button {
    background: #5B21B6;
    color: #FFFFFF !important;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 500;
}
.stButton > button:hover {
    background: #2C0F47;
    color: #FFFFFF !important;
}

textarea, input[type="text"] {
    color: #0F0F14 !important;
    background: #FAFAFC !important;
}

.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #6B6B7A;
    padding: 8px 14px;
}
.stTabs [aria-selected="true"] { color: #5B21B6; }

.card {
    background: #FFFFFF;
    border: 1px solid #E5DFEF;
    border-radius: 8px;
    padding: 18px;
    margin-bottom: 12px;
}
.q-block {
    background: #F5F1FA;
    border: 1px solid #DDD0F0;
    border-radius: 10px;
    padding: 24px;
}
.q-cap { font-size: 11px; letter-spacing: 1px; text-transform: uppercase; color: #6B6B7A; }
.q-value { font-size: 54px; font-weight: 600; color: #2C0F47; line-height: 1; }
.q-label { font-size: 18px; font-weight: 500; color: #5B21B6; margin-top: 6px; }

.bar { width: 100%; height: 6px; background: #ECEAF5; border-radius: 4px; overflow: hidden; }
.bar > span { display: block; height: 100%; background: #5B21B6; }

.kw {
    display: inline-block;
    background: #F5F1FA;
    color: #2C0F47;
    border: 1px solid #E0D6F0;
    padding: 4px 10px;
    border-radius: 999px;
    margin: 3px 4px 3px 0;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


# шапка
st.markdown("""
<div style="border-bottom: 1px solid #E5DFEF; padding-bottom: 14px; margin-bottom: 22px;">
  <h1 style="margin:0; font-size:34px; color:#2C0F47;">МАЛІ</h1>
  <div style="color:#6B6B7A; font-size:14px;">Maliboo · академічна оцінка якості тексту</div>
</div>
""", unsafe_allow_html=True)


# sidebar: статус БД 
with st.sidebar:
    st.markdown("### МАЛІ")
    st.caption("Mali · text quality")

    try:
        n_saved = len(db_layer.get_all())
        db_ok = True
    except Exception as e:
        n_saved = 0
        db_ok = False
        db_err = str(e)

    st.markdown("**База даних**")
    if db_ok:
        st.write(f"Збережено записів: **{n_saved}**")
    else:
        st.error(db_err)
    st.caption(f"Файл БД:\n`{config.DB['path']}`")

    if st.button("Оновити", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.caption(
        "**МАЛІ** — Метричний Аналіз\n"
        "Лексики та Інформативності.\n\n"
        "Скорочена назва — *Maliboo*."
    )


# вкладки
tab_a, tab_h, tab_d, tab_w, tab_about = st.tabs(
    ["Аналіз", "Історія", "Словники", "Налаштування", "Про"]
)


# 1. АНАЛІЗ
with tab_a:
    src = st.radio(
        "Джерело",
        ("Вставити текст", "Завантажити файл", "Демо-текст"),
        horizontal=True,
        label_visibility="collapsed",
    )

    text = ""
    title = ""

    if src == "Вставити текст":
        title = st.text_input("Назва тексту", placeholder="наприклад, Реферат №1")
        text = st.text_area(
            "Текст для аналізу",
            height=400,
            placeholder="Вставте сюди ваш текст…",
        )

    elif src == "Завантажити файл":
        up = st.file_uploader("TXT, DOCX або MD", type=["txt", "docx", "md"])
        if up is not None:
            try:
                text = load_any(up, filename=up.name)
                title = os.path.splitext(up.name)[0]
                st.success(f"Файл прочитано · {len(text)} симв.")
                with st.expander("Переглянути текст"):
                    st.text(text[:5000] + ("…" if len(text) > 5000 else ""))
            except UnsupportedFileError as e:
                st.error(str(e))

    else:
        title = "Демо-текст"
        text = DEMO_TEXT
        st.info(f"Завантажено демо-текст ({len(text)} симв.)")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.caption(f"Готово до аналізу: **{len(text)}** символів")
    with c2:
        save_to_db = st.checkbox("Зберегти у БД")
    with c3:
        run = st.button("Аналізувати", type="primary", use_container_width=True)

    if run:
        if not text.strip():
            st.warning("Спочатку додайте текст.")
        else:
            try:
                with st.spinner("Обчислюю метрики…"):
                    result = analyze_text(
                        text,
                        title=title or None,
                        save_to_db=save_to_db,
                    )
                st.session_state["last_result"] = result
                if save_to_db:
                    if result.get("db_id"):
                        st.success(f"Збережено у БД · id #{result['db_id']}")
                    else:
                        st.warning("Не вдалося отримати id запису.")
            except TextTooShortError as e:
                st.error(f"Текст замалий: {e}")
            except TextTooLongError as e:
                st.error(f"Текст завеликий: {e}")
            except Exception as e:
                st.error(f"Помилка під час аналізу: {e}")

    result = st.session_state.get("last_result")
    if result is not None:
        st.markdown("---")

        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown(
                f"""
                <div class="q-block">
                  <div class="q-cap">Інтегральна оцінка Q</div>
                  <div class="q-value">{result['Q']:.2f}</div>
                  <div class="q-label">{result['label']}</div>
                  <div style="color:#6B6B7A; font-size:13px; margin-top:8px;">
                    Q ∈ [0, 1] · {result['duration_ms']} мс ·
                    {result['tokens_preview']['n_words']} слів
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            tp = result["tokens_preview"]
            st.markdown(
                f"""
                <div class="card" style="padding:20px;">
                  <table style="width:100%; border-collapse:collapse;">
                    <tr><td style="padding:6px 0;">Слова</td>
                        <td style="text-align:right; font-weight:500;">{tp['n_words']}</td></tr>
                    <tr><td style="padding:6px 0;">Змістовні слова</td>
                        <td style="text-align:right; font-weight:500;">{tp['n_content_words']}</td></tr>
                    <tr><td style="padding:6px 0;">Речення</td>
                        <td style="text-align:right; font-weight:500;">{tp['n_sentences']}</td></tr>
                    <tr><td style="padding:6px 0;">Абзаци</td>
                        <td style="text-align:right; font-weight:500;">{tp['n_paragraphs']}</td></tr>
                  </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("##### Розклад метрик")
        for name, w in config.WEIGHTS.items():
            entry = result["breakdown"].get(name, {"score": 0, "contribution": 0})
            sc = entry["score"]
            label = METRIC_NAMES.get(name, name)
            st.markdown(
                f"""
                <div style="margin-bottom:12px;">
                  <div style="display:flex; justify-content:space-between; font-size:14px;">
                    <span>{label}</span>
                    <span style="color:#6B6B7A;">
                      {sc:.2f} · вага {w:.2f} · внесок {entry['contribution']:.3f}
                    </span>
                  </div>
                  <div class="bar"><span style="width:{sc*100:.0f}%;"></span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        top = (result["metrics"].get("tfidf") or {}).get("raw", {}).get("top_keywords", [])
        if top:
            st.markdown("##### Ключові слова (TF-IDF)")
            chips = "".join(
                f'<span class="kw">{w} <span style="opacity:.55;">{v:.2f}</span></span>'
                for w, v in top
            )
            st.markdown(f"<div>{chips}</div>", unsafe_allow_html=True)

        st.markdown("##### Деталі по метриках")
        for name in list(config.WEIGHTS.keys()) + ["tfidf"]:
            if name not in result["metrics"]:
                continue
            label = METRIC_NAMES.get(name, name)
            sc = result["metrics"][name].get("score", 0)
            with st.expander(f"{label} — {sc:.2f}"):
                raw = result["metrics"][name].get("raw", {})
                simple = {k: v for k, v in raw.items() if not isinstance(v, (list, dict))}
                if simple:
                    df = pd.DataFrame(
                        [{"показник": k, "значення": v} for k, v in simple.items()]
                    )
                    st.dataframe(df, use_container_width=True, hide_index=True)
                for k, v in raw.items():
                    if isinstance(v, (list, dict)):
                        st.markdown(f"**{k}**")
                        st.json(v, expanded=False)


# 2. ІСТОРІЯ
with tab_h:
    st.markdown("##### Збережені тексти")
    items = db_layer.get_ranking()

    if not items:
        st.info(
            "Поки що порожньо. Поставте галочку **«Зберегти у БД»** "
            "у вкладці «Аналіз» перед натисканням кнопки."
        )
    else:
        df = pd.DataFrame(items).rename(columns={
            "rank": "№",
            "id": "ID",
            "title": "Назва",
            "q_score": "Q",
            "label": "Оцінка",
            "n_words": "Слова",
            "created_at": "Дата",
        })[["№", "ID", "Назва", "Q", "Оцінка", "Слова", "Дата"]]
        df["Q"] = df["Q"].map(lambda v: f"{v:.3f}")
        st.dataframe(df, use_container_width=True, hide_index=True)

        ids = [it["id"] for it in items]
        c1, c2 = st.columns([3, 1])
        sel = c1.selectbox("Запис для перегляду", ids, format_func=lambda i: f"#{i}")
        if c2.button("Видалити", use_container_width=True):
            if db_layer.delete_by_id(sel):
                st.success(f"Видалено #{sel}")
                st.rerun()

        rec = db_layer.get_by_id(sel)
        if rec:
            st.markdown(
                f"**{rec['title']}** · Q = {rec['q_score']:.3f} · {rec['label']} · "
                f"{rec['n_words']} слів · {rec['created_at']}"
            )
            with st.expander("Текст"):
                st.text(rec["text"][:3000] + ("…" if len(rec["text"]) > 3000 else ""))


# 3. СЛОВНИКИ
with tab_d:
    st.markdown("##### Перегляд словників")

    kind = st.radio(
        "Категорія",
        ("Хороша лексика (GOOD)", "Вода / шум (BAD)", "Стоп-слова"),
        horizontal=True,
    )

    if kind.startswith("Хороша"):
        cat = st.selectbox("Підкатегорія", list(GOOD_CATEGORIES.keys()))
        words = sorted(GOOD_CATEGORIES[cat])
    elif kind.startswith("Вода"):
        cat = st.selectbox("Підкатегорія", list(BAD_CATEGORIES.keys()))
        words = sorted(BAD_CATEGORIES[cat])
    else:
        words = sorted(STOP_WORDS)

    q = st.text_input("Пошук", placeholder="введіть фрагмент слова…")
    if q:
        q = q.lower()
        words = [w for w in words if q in w]

    st.caption(f"Знайдено: **{len(words)}**")
    if words:
        # компактна сітка з 4 колонок
        cols = st.columns(4)
        chunk = (len(words) + 3) // 4
        for i, col in enumerate(cols):
            with col:
                part = words[i * chunk:(i + 1) * chunk]
                if part:
                    st.markdown(
                        " ".join(f'<span class="kw">{w}</span>' for w in part),
                        unsafe_allow_html=True,
                    )


# 4. НАЛАШТУВАННЯ (ваги метрик)
with tab_w:
    st.markdown("##### Ваги метрик")
    st.caption(
        "Сума ваг має дорівнювати 1.0. Зміни застосовуються до поточної сесії — "
        "наступний аналіз використає нові ваги."
    )

    if "weights_draft" not in st.session_state:
        st.session_state["weights_draft"] = dict(config.WEIGHTS)

    draft = st.session_state["weights_draft"]

    new_vals = {}
    for name in config.WEIGHTS.keys():
        new_vals[name] = st.slider(
            METRIC_NAMES.get(name, name),
            min_value=0.0,
            max_value=1.0,
            value=float(draft.get(name, config.WEIGHTS[name])),
            step=0.05,
            key=f"w_{name}",
        )

    total = sum(new_vals.values())
    st.markdown(f"**Сума ваг:** {total:.2f}")
    if abs(total - 1.0) > 0.01:
        st.warning("Сума не дорівнює 1.0 — буде нормалізовано автоматично.")

    c1, c2 = st.columns(2)
    if c1.button("Застосувати", use_container_width=True):
        if total <= 0:
            st.error("Сума ваг має бути більше нуля.")
        else:
            for name in config.WEIGHTS:
                config.WEIGHTS[name] = new_vals[name] / total
            st.session_state["weights_draft"] = dict(config.WEIGHTS)
            st.success("Ваги оновлено.")

    if c2.button("Скинути до стандартних", use_container_width=True):
        defaults = {
            "lexical_diversity": 0.20,
            "readability":       0.25,
            "water_content":     0.20,
            "basic_stats":       0.15,
            "structure":         0.20,
        }
        for k, v in defaults.items():
            config.WEIGHTS[k] = v
        st.session_state["weights_draft"] = dict(config.WEIGHTS)
        st.rerun()

    st.markdown("---")
    st.markdown("##### Поточні значення")
    cur = pd.DataFrame(
        [{"метрика": METRIC_NAMES.get(k, k), "вага": round(v, 3)}
         for k, v in config.WEIGHTS.items()]
    )
    st.dataframe(cur, use_container_width=True, hide_index=True)


# 5. ПРО
with tab_about:
    st.markdown("""
##### Що таке МАЛІ

**МАЛІ** — **М**етричний **А**наліз **Л**ексики та **І**нформативності.
Скорочена міжнародна назва — *Mali*.

Система оцінює якість україномовного тексту за шістьма метриками:

- **Базова статистика** — довжина слів, речень, абзаців.
- **Лексична різноманітність** — TTR, MATTR, hapax legomena.
- **Читабельність** — Coleman-Liau та адаптований Flesch.
- **Водність** — частка слів-паразитів, кліше, шуму.
- **Структурованість** — наявність вступу, висновку, абзаців.
- **TF-IDF** — концентрація ключових слів.

Інтегральна оцінка обчислюється як зважена сума:
**Q = Σ (score · weight)**, де Σ weight = 1, Q ∈ [0, 1].
""")
    st.caption(f"© {datetime.now().year} · МАЛІ · demo build")

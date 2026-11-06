"""
Пошук слів словника в тексті з урахуванням словоформ і фраз.

Кожна категорія словника перетворюється на індекс (dict):
- words   — леми окремих слів («аналітичний» знайде «аналітичну»);
- exact   — слова, які шукаємо лише за точною формою;
- phrases — фрази з кількох слів («ну типу», «тільки сьогодні»).

За точною формою шукаємо:
- слова-паразити і шум (use_lemmas=False): «типу» лематизатор звів би до «тип»,
  «короче» — до «короткий»;
- наказові форми дієслів: «поділись» — спам, а «поділилася» в новині — ні.
"""
from .tokenizer import tokenize_words
from .lemmatizer import lemma, is_imperative


def build_index(words, use_lemmas: bool = True) -> dict:
    """Будує індекс для однієї категорії словника."""
    index = {"words": set(), "exact": set(), "phrases": set(), "use_lemmas": use_lemmas}
    for entry in words:
        tokens = tokenize_words(entry)
        if len(tokens) > 1:
            index["phrases"].add(tuple(tokens))
        elif tokens:
            word = tokens[0]
            if use_lemmas and not is_imperative(word):
                index["words"].add(lemma(word))
            else:
                index["exact"].add(word)
    index["max_phrase_len"] = max((len(p) for p in index["phrases"]), default=0)
    return index


def find_words(index: dict, tokens, lemmas) -> list:
    """Повертає знайдені слова та фрази (у тому вигляді, як вони стоять у тексті).
    Слова, що вже увійшли у фразу, окремо не рахуються."""
    found = []
    used = set()
    n = len(tokens)

    # спочатку фрази — від найдовших
    for size in range(index["max_phrase_len"], 1, -1):
        for i in range(n - size + 1):
            if any(j in used for j in range(i, i + size)):
                continue
            if tuple(tokens[i:i + size]) in index["phrases"]:
                found.append(" ".join(tokens[i:i + size]))
                used.update(range(i, i + size))

    # потім окремі слова
    keys = lemmas if index["use_lemmas"] else tokens
    for i in range(n):
        if i in used:
            continue
        if keys[i] in index["words"] or tokens[i] in index["exact"]:
            found.append(tokens[i])
    return found


def all_keys(index: dict) -> set:
    """Усі ключі індексу — для перевірки дублів між категоріями."""
    return index["words"] | index["exact"] | {" ".join(p) for p in index["phrases"]}

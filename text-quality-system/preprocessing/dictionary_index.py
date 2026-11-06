"""
Пошук слів словника в тексті з урахуванням словоформ і фраз.

Кожна категорія словника перетворюється на індекс:
    - окремі слова  -> множина ключів (лема або саме слово, див. lemmatizer.lemma);
    - фрази («ну типу», «бла-бла-бла») -> кортежі токенів, шукаються як n-грами.

Режими зіставлення:
    use_lemmas=True  — «аналітичний» знайде «аналітичну», «аналітичних» тощо;
    use_lemmas=False — точний збіг форми. Потрібен для слів-паразитів і «шуму»:
                       «типу» чи «короче» лематизатор звів би до «тип» і «короткий»,
                       і тоді штрафувалося б кожне «тип» у науковому тексті.

Дієслова в наказовому способі («підпишись», «встигни») завжди шукаються за точною
формою: заклик «поділись» — спам, а «поділилася» в новині — ні.
"""
from .tokenizer import tokenize_words
from .lemmatizer import lemma, is_imperative


class DictionaryIndex:
    def __init__(self, words, use_lemmas: bool = True):
        self.use_lemmas = use_lemmas
        self.words = set()     # ключі (леми або точні форми — залежно від режиму)
        self.exact = set()     # слова, що шукаються лише за точною формою
        self.phrases = set()
        for entry in words:
            toks = tokenize_words(entry)
            if len(toks) == 1:
                if use_lemmas and not is_imperative(toks[0]):
                    self.words.add(lemma(toks[0]))
                else:
                    self.exact.add(toks[0])
            elif len(toks) > 1:
                self.phrases.add(tuple(toks))
        self.max_phrase_len = max((len(p) for p in self.phrases), default=0)

    def find(self, tokens, lemmas=None):
        """
        Повертає список знайдених входжень (слово або фраза у тому вигляді,
        в якому вони стоять у тексті). Токени, що увійшли у фразу, повторно
        як окремі слова не рахуються.
        """
        keys = lemmas if (self.use_lemmas and lemmas is not None) else tokens
        if self.use_lemmas and lemmas is None:
            keys = [lemma(t) for t in tokens]
        found, used = [], set()
        n = len(tokens)
        # спочатку фрази — від найдовших
        for size in range(self.max_phrase_len, 1, -1):
            for i in range(n - size + 1):
                if any(j in used for j in range(i, i + size)):
                    continue
                if tuple(tokens[i:i + size]) in self.phrases:
                    found.append(" ".join(tokens[i:i + size]))
                    used.update(range(i, i + size))
        # потім окремі слова
        for i in range(n):
            if i not in used and (keys[i] in self.words or tokens[i] in self.exact):
                found.append(tokens[i])
        return found

    def count(self, tokens, lemmas=None) -> int:
        return len(self.find(tokens, lemmas))

"""So'kinish filtri: xabarda taqiqlangan so'z yoki ibora bor-yo'qligini tekshiradi."""
import re
from pathlib import Path

_APOSTROPHES = "'ʻʼ’‘`´"
_DROP_APOSTROPHES = str.maketrans("", "", _APOSTROPHES)
_UNIFY_APOSTROPHES = str.maketrans(_APOSTROPHES, "'" * len(_APOSTROPHES))
_CYRILLIC = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "s", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h",
}
_TOKEN_RE = re.compile(r"[a-z0-9']+")
_REPEAT_RE = re.compile(r"(.)\1+")


def normalize(text: str, keep_apostrophes: bool = False) -> list[str]:
    """Kichik harf, kirill → lotin, apostrofsiz, takror harflar bittaga ('suuuka' → 'suka')."""
    text = "".join(_CYRILLIC.get(ch, ch) for ch in text.lower())
    text = text.translate(_UNIFY_APOSTROPHES if keep_apostrophes else _DROP_APOSTROPHES)
    tokens = (_REPEAT_RE.sub(r"\1", token.strip("'")) for token in _TOKEN_RE.findall(text))
    return [token for token in tokens if token]


class BadWords:
    """Ro'yxat fayli: har qatorda bitta so'z yoki ibora, '#' bilan boshlangan qatorlar izoh.
    Faqat butun so'zlar mos keladi ('ker' so'zi 'kerak' ichida topilmaydi).
    '=' bilan boshlangan so'z apostrofi bilan aynan yozilgandagina mos keladi ("=o'l" 'ol' ga mos kelmaydi)."""

    def __init__(self, path: Path):
        self.words: set[str] = set()
        self.phrases: set[str] = set()
        self.exact: set[str] = set()
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.partition("#")[0].strip()
            if line.startswith("="):
                self.exact.update(normalize(line[1:], keep_apostrophes=True))
                continue
            tokens = normalize(line)
            if len(tokens) == 1:
                self.words.add(tokens[0])
            elif tokens:
                self.phrases.add(f" {' '.join(tokens)} ")

    def __len__(self) -> int:
        return len(self.words) + len(self.phrases) + len(self.exact)

    def contains(self, text: str) -> bool:
        tokens = normalize(text)
        if not self.words.isdisjoint(tokens):
            return True
        if self.exact and not self.exact.isdisjoint(normalize(text, keep_apostrophes=True)):
            return True
        padded = f" {' '.join(tokens)} "
        return any(phrase in padded for phrase in self.phrases)

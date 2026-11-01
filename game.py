"""Lógica pura del juego (sin red): normalizar respuestas, máscara de letras,
pistas y puntos."""
import random
import re
import unicodedata

from config import MAX_HINTS, STREAK_BONUS

STOPWORDS = {"el", "la", "los", "las", "un", "una", "unos", "unas",
             "the", "a", "an", "y", "and", "e"}
WORD_GAP = "  "  # espacio largo entre palabras (no se colapsa en HTML)

# Letras reveladas por día de pista (se limitan a 1/3 de las letras distintas)
LETTER_REVEALS = {1: 0, 2: 1, 3: 2, 4: 2, 5: 3, 6: 4, 7: 5}


# ---------------------------------------------------------------- texto
def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))


def base_char(ch):
    b = strip_accents(ch).lower()
    return b[:1] if b else ch.lower()


def is_alnum(ch):
    return base_char(ch).isalnum()


def tokens(text, drop_stopwords=True):
    t = strip_accents(text).lower().replace("&", " and ")
    words = re.sub(r"[\W_]+", " ", t).split()
    if drop_stopwords:
        kept = [w for w in words if w not in STOPWORDS]
        if kept:
            return kept
    return words


def close_token(a, b):
    """Palabras iguales o con una errata pequeña. Números y palabras cortas,
    siempre exactos (para no confundir 'Rocky II' con 'Rocky III')."""
    if a == b:
        return True
    if min(len(a), len(b)) < 5:
        return False
    import difflib
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    if len(a) == len(b):
        return ratio >= 0.8
    if abs(len(a) - len(b)) == 1 and min(len(a), len(b)) >= 7:
        return ratio >= 0.9
    return False


def is_match(guess, aliases):
    g = tokens(guess)
    if not g:
        return False
    gj = "".join(g)
    for alias in aliases:
        a = tokens(alias)
        if not a:
            continue
        if g == a or gj == "".join(a):
            return True
        if len(g) == len(a) and all(close_token(x, y) for x, y in zip(g, a)):
            return True
    return False


# ------------------------------------------------------------- máscara
def unique_letters(title):
    seen = []
    for ch in title:
        if is_alnum(ch):
            b = base_char(ch)
            if b not in seen:
                seen.append(b)
    return seen


def reveal_set(title, seed, day):
    letters = sorted(unique_letters(title))
    random.Random(seed).shuffle(letters)
    n = min(LETTER_REVEALS.get(day, 0), len(letters) // 3)
    return set(letters[:n])


def render_mask(title, revealed):
    words = []
    for word in title.split():
        out = []
        for ch in word:
            if not is_alnum(ch):
                out.append(ch)
            elif base_char(ch) in revealed:
                out.append(ch.upper())
            else:
                out.append("_")
        words.append(" ".join(out))
    return WORD_GAP.join(words)


def count_letters(title):
    return sum(1 for ch in title if is_alnum(ch))


def count_words(title):
    return sum(1 for w in title.split() if any(is_alnum(c) for c in w))


# -------------------------------------------------------------- pistas
COUNTRIES = {
    "US": "EE. UU.", "ES": "España", "GB": "Reino Unido", "FR": "Francia",
    "IT": "Italia", "DE": "Alemania", "JP": "Japón", "KR": "Corea del Sur",
    "MX": "México", "AR": "Argentina", "CA": "Canadá", "AU": "Australia",
    "NZ": "Nueva Zelanda", "IN": "India", "CN": "China", "HK": "Hong Kong",
    "SE": "Suecia", "DK": "Dinamarca", "BR": "Brasil", "IE": "Irlanda",
    "RU": "Rusia", "PL": "Polonia", "CL": "Chile", "CO": "Colombia",
    "BE": "Bélgica", "NL": "Países Bajos", "AT": "Austria", "CH": "Suiza",
    "NO": "Noruega", "FI": "Finlandia", "IR": "Irán", "TH": "Tailandia",
}
LANGUAGES = {
    "en": "inglés", "es": "español", "fr": "francés", "it": "italiano",
    "de": "alemán", "ja": "japonés", "ko": "coreano", "zh": "chino",
    "cn": "cantonés", "pt": "portugués", "ru": "ruso", "sv": "sueco",
    "da": "danés", "hi": "hindi", "pl": "polaco", "fa": "persa", "th": "tailandés",
}


def cut(text, n):
    text = " ".join(text.split())
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip(" ,.;:") + "…"


def redact(text, aliases):
    """Tapa el título (y sus variantes) dentro de un texto."""
    out = text
    for a in sorted(aliases, key=len, reverse=True):
        if len(a.strip()) >= 3:
            out = re.sub(re.escape(a), "▮▮▮", out, flags=re.IGNORECASE)
    return out


def _join_es(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]


def build_hints(movie, aliases):
    """Devuelve las 6 pistas de texto (días 2 a 7) como dicts icon/label/value."""
    syn = redact(movie.get("overview", ""), aliases)
    tagline = movie.get("tagline") or ""
    tagline_ok = bool(tagline) and redact(tagline, aliases) == tagline

    def genre():
        g = movie.get("genres") or []
        return ("🎭", "Género", ", ".join(g[:3])) if g else None

    def decade():
        y = movie.get("year")
        if not y:
            return None
        dec = y // 10 * 10
        txt = f"década de {dec}" if dec >= 2000 else f"años {dec % 100}"
        c = movie.get("countries") or []
        if c:
            txt += f" · {c[0]}"
        return ("📅", "Época y país", txt)

    def director():
        d = movie.get("directors") or []
        return ("🎬", "Dirección", _join_es(d[:2])) if d else None

    def cast():
        c = movie.get("cast") or []
        return ("👥", "Reparto", _join_es(c[:2])) if len(c) >= 1 else None

    def tag():
        return ("💬", "Eslogan", f"«{cut(tagline, 80)}»") if tagline_ok else None

    def synopsis():
        return ("📝", "Sinopsis", syn) if syn else None

    def runtime():
        r = movie.get("runtime")
        return ("⏱️", "Duración", f"{r} min") if r else None

    def rating():
        v = movie.get("vote_average")
        return ("⭐", "Nota media", f"{v:.1f}/10") if v else None

    def language():
        l = movie.get("language")
        return ("🗣️", "Idioma original", l) if l else None

    def company():
        c = movie.get("companies") or []
        return ("🏢", "Productora", c[0]) if c else None

    slots = [genre, decade, director, cast, tag, synopsis]
    extras = [runtime, rating, language, company]
    hints = []
    for slot in slots:
        h = slot()
        while h is None and extras:
            h = extras.pop(0)()
        if h is not None:
            hints.append({"icon": h[0], "label": h[1], "value": h[2]})
    # Garantizamos 6 pistas
    while len(hints) < MAX_HINTS - 1:
        hints.append({"icon": "🍿", "label": "Pista", "value": "¡mucha suerte!"})
    return hints


# --------------------------------------------------------------- puntos
def points_for_day(day, theme_bonus=0):
    return (MAX_HINTS + 1 - day) + theme_bonus


def streak_bonus(streak):
    for need, extra in STREAK_BONUS:
        if streak >= need:
            return extra
    return 0

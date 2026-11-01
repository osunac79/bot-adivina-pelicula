"""Temáticas de las rondas y cómo se eligen.

Cada temática define una búsqueda en TMDB (discover). `bonus` son puntos extra
que se suman al acertar (modo difícil).
"""

THEMES = {
    "general": {
        "label": "Cine para todos", "emoji": "🍿", "bonus": 0,
        "params": {"sort_by": "vote_count.desc", "vote_count.gte": 6000}, "pages": 12,
    },
    "clasicos": {
        "label": "Clásicos", "emoji": "🎞️", "bonus": 0,
        "params": {"sort_by": "vote_count.desc", "primary_release_date.lte": "1979-12-31",
                   "vote_count.gte": 1500}, "pages": 6,
    },
    "espanol": {
        "label": "Cine español", "emoji": "🇪🇸", "bonus": 0,
        "params": {"sort_by": "vote_count.desc", "with_origin_country": "ES",
                   "vote_count.gte": 400}, "pages": 5,
    },
    "ciencia-ficcion": {
        "label": "Ciencia ficción", "emoji": "🚀", "bonus": 0,
        "params": {"sort_by": "vote_count.desc", "with_genres": "878",
                   "vote_count.gte": 4000}, "pages": 6,
    },
    "animacion": {
        "label": "Animación", "emoji": "🎨", "bonus": 0,
        "params": {"sort_by": "vote_count.desc", "with_genres": "16",
                   "vote_count.gte": 4000}, "pages": 5,
    },
    "dificil": {
        "label": "MODO DIFÍCIL", "emoji": "🔥", "bonus": 2,
        "params": {"sort_by": "vote_count.desc", "primary_release_date.lte": "2005-12-31",
                   "vote_count.gte": 800, "vote_count.lte": 3500}, "pages": 8,
    },
    # Temporada
    "terror": {
        "label": "Especial terror", "emoji": "🎃", "bonus": 0,
        "params": {"sort_by": "vote_count.desc", "with_genres": "27",
                   "vote_count.gte": 2500}, "pages": 6,
    },
    "monstruos": {
        "label": "Monstruos clásicos", "emoji": "🧛", "bonus": 1,
        "params": {"sort_by": "vote_count.desc", "with_genres": "27",
                   "primary_release_date.lte": "1964-12-31", "vote_count.gte": 250}, "pages": 3,
    },
    "navidad": {
        "label": "Especial Navidad", "emoji": "🎄", "bonus": 0,
        "params": {"sort_by": "vote_count.desc", "with_keywords": "207317",
                   "vote_count.gte": 800}, "pages": 3,
    },
}

# Rotación normal: cada ronda usa la siguiente temática de la lista.
ROTATION = [
    "general", "general", "clasicos", "general", "espanol",
    "general", "dificil", "ciencia-ficcion", "general", "animacion",
]


def choose_theme(today, round_number):
    """Elige la temática. Las de temporada tienen prioridad."""
    m, d = today.month, today.day
    if (m == 10 and d >= 24) or (m == 11 and d == 1):
        return "terror" if round_number % 2 else "monstruos"
    if (m == 12 and d >= 18) or (m == 1 and d <= 6):
        return "navidad"
    return ROTATION[(round_number - 1) % len(ROTATION)]

"""Todos los textos del bot (con emoticonos) y su ajuste al límite de caracteres."""
import random

from config import HASHTAGS, MAX_CHARS, MAX_GUESSES_PER_DAY, MAX_HINTS
from game import (count_letters, count_words, cut, points_for_day, render_mask,
                   reveal_set)
from themes import THEMES

MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

WRONG = [
    "❌ ¡Uy! Esa no es. ¡Sigue intentándolo! 🎬",
    "🙈 Frío, frío… no es esa película.",
    "🤔 Mmm, no. ¡Vuelve a probar!",
    "🚫 Esa no es. ¡Que no decaiga el cine! 🍿",
    "😅 Casi… bueno, no. ¡Otra vez!",
]


def handle(acct, at=True):
    return f"@{acct}" if at else acct


def hint_line(h, short=False):
    if short:
        return f"{h['icon']} {h['value']}"
    return f"{h['icon']} {h['label']}: {h['value']}"


# ------------------------------------------------------------ pistas
def day_toot(rnd, day, limit=None, tags=True):
    """Toot del día con todas las pistas liberadas hasta ahora."""
    limit = limit or MAX_CHARS
    m = rnd["movie"]
    theme = THEMES[rnd["theme"]]
    mask = render_mask(m["title"], reveal_set(m["title"], m["tmdb_id"], day))
    bar = "🟩" * day + "⬜" * (MAX_HINTS - day)
    pts = points_for_day(day, theme["bonus"])
    hints = rnd["hints"][: day - 1]

    if day == 1:
        footer_full = ("✍️ Responde a este toot con tu respuesta (¡mejor en mención "
                       "privada! 🤫). Cada día, una pista nueva 🗓️")
    elif day == MAX_HINTS:
        footer_full = "⚠️ ¡ÚLTIMA PISTA! Mañana se revela la solución 🎞️"
    else:
        footer_full = "✍️ Responde con tu respuesta (mejor en privado 🤫)"
    footer_short = "✍️ Responde con tu respuesta 🤫"

    def build(short_old, syn_max, with_pts, footer):
        lines = [f"🎬 ADIVINA LA PELÍCULA #{rnd['n']} · {theme['emoji']} {theme['label']}",
                 f"🔍 Pista {day}/{MAX_HINTS} {bar}", "",
                 f"🔤 {mask}",
                 f"({count_letters(m['title'])} letras · {count_words(m['title'])} palabras)"]
        if hints:
            lines.append("")
            for i, h in enumerate(hints):
                h = dict(h)
                if h["label"] == "Sinopsis" and syn_max:
                    h["value"] = cut(h["value"], syn_max)
                is_new = i == len(hints) - 1
                lines.append(hint_line(h, short=short_old and not is_new))
        if with_pts:
            lines += ["", f"💰 Hoy vale {pts} {'punto' if pts == 1 else 'puntos'}"]
        if footer:
            lines += ["", footer]
        if tags:
            lines += ["", HASHTAGS]
        return "\n".join(lines)

    attempts = [
        (False, None, True, footer_full), (True, None, True, footer_full),
        (True, 120, True, footer_full), (True, 90, True, footer_short),
        (True, 60, False, footer_short), (True, 40, False, ""),
    ]
    text = ""
    for a in attempts:
        text = build(*a)
        if len(text) <= limit - 15:
            return text
    return text[: limit - 1]


# ----------------------------------------------------- respuestas directas
def wrong_reply(acct, attempts_left):
    left = (f"\n🎟️ Te quedan {attempts_left} intentos con esta pista."
            if attempts_left > 0 else "\n⏳ Sin intentos por hoy: ¡espera a la siguiente pista!")
    return f"@{acct} {random.choice(WRONG)}{left}"


def limit_reply(acct):
    return (f"@{acct} 🚫 Ya usaste tus {MAX_GUESSES_PER_DAY} intentos con esta pista. "
            "⏳ ¡Mañana habrá una nueva! 🎬")


def correct_reply(acct, entry):
    lines = [f"@{acct} ✅ ¡ACERTASTE! 🎉🍿",
             f"💰 +{entry['points']} {'punto' if entry['points'] == 1 else 'puntos'} (pista {entry['day']}/{MAX_HINTS})"]
    if entry["streak_bonus"]:
        lines.append(f"🔥 Bonus de racha: +{entry['streak_bonus']}")
    if entry["theme_bonus"]:
        lines.append(f"🔥 Bonus de temática: +{entry['theme_bonus']}")
    lines.append(f"📈 Racha actual: {entry['streak']} 🔥" if entry["streak"] > 1
                 else "📈 ¡Empieza tu racha!")
    return "\n".join(lines)


def no_round_reply(acct):
    return f"@{acct} 🌙 Ahora mismo no hay ronda activa. ¡Mañana hay película nueva! 🎬"


def help_text(acct):
    return (f"@{acct} 🎬 ¿CÓMO SE JUEGA?\n"
            f"🔍 Cada día una pista nueva (máx. {MAX_HINTS}) de la película misteriosa.\n"
            "✍️ Responde con el título (mejor en mención privada 🤫).\n"
            f"💰 Antes aciertas, más puntos: de {MAX_HINTS} a 1.\n"
            "🔥 Acierta rondas seguidas para ganar bonus de racha.\n"
            "🤖 Comandos: !pista · !ranking · !racha · !ayuda")


def clues_reply(acct, rnd, day):
    text = day_toot(rnd, day, limit=MAX_CHARS - len(acct) - 2, tags=False)
    return f"@{acct}\n{text}"


# --------------------------------------------------------- rankings
def top(scores, k=5):
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:k]


def ranking_lines(entries, at=False, k=5):
    if not entries:
        return ["   (aún nadie… ¡sé el primero! 🚀)"]
    return [f"{MEDALS[i]} {handle(a, at)} · {p} pts" for i, (a, p) in enumerate(entries[:k])]


def ranking_reply(acct, state, month_key):
    weekly = state["scores"]["weekly"]
    monthly = state["scores"]["monthly"].get(month_key, {})
    lines = [f"@{acct} 🏆 RANKING", "", "📅 Semana"]
    lines += ranking_lines(top(weekly, 3))
    lines += ["", "🗓️ Mes"] + ranking_lines(top(monthly, 3))
    lines += ["", f"👤 Tus puntos: {weekly.get(acct, 0)} esta semana · "
              f"{monthly.get(acct, 0)} este mes · {state['scores']['alltime'].get(acct, 0)} en total"]
    return "\n".join(lines)


def streak_reply(acct, current, best, solved):
    if current > 1:
        head = f"🔥 ¡Llevas {current} rondas acertadas seguidas!"
    elif current == 1:
        head = "🔥 Llevas 1 acierto. ¡A por la racha!"
    else:
        head = "🧊 Ahora mismo no tienes racha. ¡Acierta la próxima!"
    return f"@{acct} {head}\n🏅 Mejor racha: {best} · 🎯 Películas acertadas: {solved}"


# ------------------------------------------------------------ reveal
def reveal_toot(rnd, winners, timeout=False, limit=None):
    limit = limit or MAX_CHARS
    m = rnd["movie"]
    theme = THEMES[rnd["theme"]]
    head = (f"⏰ ¡SE ACABÓ EL TIEMPO! Solución de la ronda #{rnd['n']} 🎬" if timeout
            else f"🎉 ¡SOLUCIÓN de la ronda #{rnd['n']}! 🎬")
    title = m["title"]
    if m.get("original_title") and m["original_title"].lower() != title.lower():
        title += f" ({m['original_title']})"
    body = [head, "", f"🏆 {title} · {m['year']}"]
    if m.get("directors"):
        body.append(f"🎥 Dirección: {', '.join(m['directors'][:2])}")
    if m.get("cast"):
        body.append(f"👥 Reparto: {', '.join(m['cast'][:4])}")
    extra = []
    if m.get("genres"):
        extra.append(f"🎭 {', '.join(m['genres'][:3])}")
    if m.get("runtime"):
        extra.append(f"⏱️ {m['runtime']} min")
    if m.get("vote_average"):
        extra.append(f"⭐ {m['vote_average']:.1f}")
    if extra:
        body.append(" · ".join(extra))
    if winners:
        names = ", ".join(f"@{w['acct']} (+{w['points']})" for w in winners[:3])
        if len(winners) > 3:
            names += f" y {len(winners) - 3} más"
        result = f"🥳 ¡Acertaron! {names}"
    else:
        result = "😅 Esta vez nadie la adivinó. ¡Mañana, otra!"
    tail = [f"{theme['emoji']} {theme['label']}", HASHTAGS]

    def compose(syn):
        parts = list(body)
        if syn:
            parts += ["", f"📝 {syn}"]
        parts += ["", result, ""] + tail
        return "\n".join(parts)

    base = compose("")
    room = limit - 15 - len(base) - len("\n\n📝 ")
    if room >= 60 and m.get("overview"):
        return compose(cut(m["overview"], room))
    return base[:limit]


# ----------------------------------------------------------- resúmenes
def weekly_toot(state, week_rounds, best_streak):
    lines = ["📊 RESUMEN SEMANAL · Adivina la Película 🎬", ""]
    lines += ranking_lines(top(state["scores"]["weekly"], 3), at=True, k=3)
    if not state["scores"]["weekly"]:
        lines = ["📊 RESUMEN SEMANAL · Adivina la Película 🎬", "",
                 "😴 Semana tranquila: nadie puntuó. ¡Esta semana a por todas! 🚀"]
    solved = sum(1 for r in week_rounds if r["solved"])
    lines += ["", f"🎯 Rondas: {len(week_rounds)} · Acertadas: {solved}"]
    if week_rounds:
        titles = "; ".join(r["title"] for r in week_rounds[-4:])
        lines.append(f"🎞️ Películas: {cut(titles, 140)}")
    if best_streak and best_streak[1] > 1:
        lines.append(f"🔥 Mejor racha: {best_streak[0]} ({best_streak[1]})")
    lines += ["", "🗓️ ¡Nueva semana, nuevo ranking!", HASHTAGS]
    return "\n".join(lines)[: MAX_CHARS - 5]


def monthly_toot(label, scores):
    lines = [f"🏅 CAMPEONES DE {label.upper()} 🎬", ""]
    lines += ranking_lines(top(scores, 5), at=True)
    lines += ["", "👏 ¡Enhorabuena y gracias por jugar! 🍿", HASHTAGS]
    return "\n".join(lines)[: MAX_CHARS - 5]

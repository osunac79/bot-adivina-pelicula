"""Bot "Adivina la Película" para Mastodon.

Uso:
    python bot.py daily      # publica la pista del día (o abre ronda nueva)
    python bot.py replies    # lee menciones: respuestas y comandos
    python bot.py weekly     # resumen semanal y reinicio del ranking semanal
    python bot.py status     # muestra el estado actual (no publica nada)

Opciones: --dry-run (no publica, solo imprime) · --force · --theme NOMBRE
"""
import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from html import unescape

import config
import game
import messages as msg
from storage import ensure_defaults, load_state, save_state
from themes import THEMES, choose_theme

MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ------------------------------------------------------------ utilidades
def month_key(d):
    return f"{d.year}-{d.month:02d}"


def clean_text(html):
    t = re.sub(r"<br\s*/?>", "\n", html or "")
    t = re.sub(r"</p>", "\n", t)
    t = unescape(re.sub(r"<[^>]+>", "", t))
    t = re.sub(r"(?<!\w)@[\w.-]+(@[\w.-]+)?", "", t)
    return " ".join(t.split())


def day_at(rnd, when):
    """Pista vigente en el momento `when` (según cuándo se publicó cada pista)."""
    n = sum(1 for t in rnd["hint_times"] if datetime.fromisoformat(t) <= when)
    return max(1, min(n, config.MAX_HINTS))


def streak_info(state, acct):
    s = state["streaks"].get(acct, {"current": 0, "best": 0, "last_round": 0})
    n = state["round_counter"]
    rnd = state.get("round")
    active = bool(rnd and rnd["status"] == "active")
    alive = s["last_round"] == n or (active and s["last_round"] == n - 1)
    return (s["current"] if alive else 0), s["best"]


# ------------------------------------------------------------ ronda diaria
def start_round(state, social, tmdb, now, theme_name=None):
    n = state["round_counter"] + 1
    theme_name = theme_name or choose_theme(now.date(), n)
    movie = tmdb.pick_movie(THEMES[theme_name], set(state["used_tmdb_ids"]))
    if movie is None and theme_name != "general":
        theme_name = "general"
        movie = tmdb.pick_movie(THEMES["general"], set(state["used_tmdb_ids"]))
    if movie is None:
        raise RuntimeError("No se pudo elegir ninguna película en TMDB")
    aliases = sorted({a for a in (movie["title"], movie["original_title"], movie["title_en"]) if a})
    rnd = {
        "n": n, "theme": theme_name, "movie": movie, "aliases": aliases,
        "hints": game.build_hints(movie, aliases), "hint_day": 1,
        "hint_times": [now.isoformat()], "toot_ids": [], "status": "active",
        "winners": [], "attempts": {},
    }
    state["round_counter"] = n
    state["used_tmdb_ids"].append(movie["tmdb_id"])
    state["round"] = rnd
    tid = social.post(msg.day_toot(rnd, 1), visibility=config.VISIBILITY)
    rnd["toot_ids"].append(tid)
    return rnd


def finish_round(state, social, tmdb, winners, timeout=False):
    rnd = state["round"]
    m = rnd["movie"]
    media = None
    try:
        data = tmdb.poster(m["poster_path"])
        media = [social.upload(data, f"Póster de la película {m['title']} ({m['year']})")]
    except Exception as exc:  # la portada es un extra: si falla, se publica igual
        print(f"No se pudo subir la portada: {exc}", file=sys.stderr)
    text = msg.reveal_toot(rnd, winners, timeout=timeout)
    tid = social.post(text, visibility=config.VISIBILITY, media_ids=media)
    rnd["toot_ids"].append(tid)
    rnd["status"] = "finished"
    state["week_rounds"].append({
        "n": rnd["n"], "title": m["title"], "solved": bool(winners),
        "day": winners[0]["day"] if winners else None,
    })


def maybe_monthly_summary(state, social, today):
    prev = (today.replace(day=1) - timedelta(days=1))
    key = month_key(prev)
    scores = state["scores"]["monthly"].get(key)
    if today.day == 1 and scores and state.get("monthly_posted") != key:
        label = f"{MONTHS_ES[prev.month - 1]} {prev.year}"
        social.post(msg.monthly_toot(label, scores), visibility=config.VISIBILITY)
        state["monthly_posted"] = key
        # Conservamos solo los 3 últimos meses para que el archivo no crezca
        for old in sorted(state["scores"]["monthly"])[:-3]:
            del state["scores"]["monthly"][old]


def run_daily(state, social, tmdb, now=None, force=False, theme=None, on_save=None):
    ensure_defaults(state)
    now = now or datetime.now(config.TZ)
    today = now.date().isoformat()
    save = on_save or (lambda: None)
    if state["last_daily"] == today and not force:
        return "skip"
    maybe_monthly_summary(state, social, now.date())
    rnd = state.get("round")
    if rnd and rnd["status"] == "active":
        if rnd["hint_day"] < config.MAX_HINTS:
            rnd["hint_day"] += 1
            rnd["hint_times"].append(now.isoformat())
            tid = social.post(msg.day_toot(rnd, rnd["hint_day"]), visibility=config.VISIBILITY)
            rnd["toot_ids"].append(tid)
            state["last_daily"] = today
            save()
            return f"pista {rnd['hint_day']}"
        finish_round(state, social, tmdb, [], timeout=True)
        save()
    start_round(state, social, tmdb, now, theme)
    state["last_daily"] = today
    save()
    return "ronda nueva"


# ------------------------------------------------------------- menciones
def award(state, rnd, acct, day, now):
    theme_bonus = THEMES[rnd["theme"]]["bonus"]
    s = state["streaks"].setdefault(acct, {"current": 0, "best": 0, "last_round": 0})
    s["current"] = s["current"] + 1 if s["last_round"] == rnd["n"] - 1 else 1
    s["last_round"] = rnd["n"]
    s["best"] = max(s["best"], s["current"])
    bonus = game.streak_bonus(s["current"])
    base = game.points_for_day(day)
    pts = base + theme_bonus + bonus
    mk = month_key(now)
    for bucket in (state["scores"]["weekly"], state["scores"]["monthly"].setdefault(mk, {}),
                   state["scores"]["alltime"]):
        bucket[acct] = bucket.get(acct, 0) + pts
    state["solved_counts"][acct] = state["solved_counts"].get(acct, 0) + 1
    return {"acct": acct, "day": day, "points": pts, "streak": s["current"],
            "streak_bonus": bonus, "theme_bonus": theme_bonus}


def reply(social, text, to_id, visibility="direct"):
    social.post(text, reply_to=to_id, visibility=visibility)


def handle_command(state, social, acct, sid, text, now):
    cmd = text.split()[0].lower()
    rnd = state.get("round")
    if cmd in ("!pista", "!pistas"):
        if rnd and rnd["status"] == "active":
            day = max(1, min(rnd["hint_day"], config.MAX_HINTS))
            reply(social, msg.clues_reply(acct, rnd, day), sid)
        else:
            reply(social, msg.no_round_reply(acct), sid)
    elif cmd in ("!ranking", "!top"):
        reply(social, msg.ranking_reply(acct, state, month_key(now)), sid)
    elif cmd == "!racha":
        cur, best = streak_info(state, acct)
        reply(social, msg.streak_reply(acct, cur, best, state["solved_counts"].get(acct, 0)), sid)
    else:
        reply(social, msg.help_text(acct), sid)


def handle_guess(state, social, acct, sid, text, created, now):
    rnd = state.get("round")
    if not rnd or rnd["status"] != "active":
        reply(social, msg.no_round_reply(acct), sid)
        return None
    if not text or len(text) > config.MAX_GUESS_LENGTH:
        return None
    if created < datetime.fromisoformat(rnd["hint_times"][0]):
        return None  # respuesta antigua, de antes de esta ronda
    if any(w["acct"] == acct for w in rnd["winners"]):
        return None
    day = day_at(rnd, created)
    used = rnd["attempts"].setdefault(acct, {})
    done = used.get(str(day), 0)
    if done >= config.MAX_GUESSES_PER_DAY:
        reply(social, msg.limit_reply(acct), sid)
        return None
    used[str(day)] = done + 1
    if game.is_match(text, rnd["aliases"]):
        entry = award(state, rnd, acct, day, now)
        rnd["winners"].append(entry)
        reply(social, msg.correct_reply(acct, entry), sid)
        return entry
    if config.REPLY_TO_WRONG:
        reply(social, msg.wrong_reply(acct, config.MAX_GUESSES_PER_DAY - used[str(day)]), sid)
    return None


def run_replies(state, social, tmdb, now=None, on_save=None):
    ensure_defaults(state)
    now = now or datetime.now(config.TZ)
    save = on_save or (lambda: None)
    last = state["last_notification_id"]
    if last is None:  # primera vez: ignoramos el histórico
        state["last_notification_id"] = social.latest_notification_id() or 0
        save()
        return "inicializado"
    mentions, seen_max = social.new_mentions(last)
    if not mentions:
        state["last_notification_id"] = max(seen_max, last)
        save()
        return "sin menciones"
    me = social.me_id()
    solved_now = []
    for n in mentions:
        if n["account"]["id"] == me:
            continue
        status = n["status"]
        acct = n["account"]["acct"]
        text = clean_text(status.get("content"))
        if not text:
            continue
        if text.startswith("!"):
            handle_command(state, social, acct, status["id"], text, now)
        else:
            entry = handle_guess(state, social, acct, status["id"], text, status["created_at"], now)
            if entry:
                solved_now.append(entry)
        state["last_notification_id"] = int(n["id"])
        save()
    state["last_notification_id"] = max(seen_max, state["last_notification_id"])
    if solved_now:
        finish_round(state, social, tmdb, state["round"]["winners"])
    save()
    return f"{len(mentions)} menciones"


# ---------------------------------------------------------------- semanal
def run_weekly(state, social, now=None, on_save=None):
    ensure_defaults(state)
    now = now or datetime.now(config.TZ)
    best = max(((a, s["best"]) for a, s in state["streaks"].items()),
               key=lambda kv: kv[1], default=None)
    social.post(msg.weekly_toot(state, state["week_rounds"], best), visibility=config.VISIBILITY)
    state["history"].append({"week_end": now.date().isoformat(),
                             "top": msg.top(state["scores"]["weekly"], 3),
                             "rounds": len(state["week_rounds"])})
    state["history"] = state["history"][-12:]
    state["scores"]["weekly"] = {}
    state["week_rounds"] = []
    if on_save:
        on_save()
    return "resumen publicado"


# -------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["daily", "replies", "weekly", "status"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--theme", choices=list(THEMES))
    args = ap.parse_args(argv)

    state = load_state()
    if args.command == "status":
        rnd = state["round"]
        print(f"Rondas: {state['round_counter']} · última pista publicada: {state['last_daily']}")
        if rnd:
            print(f"Ronda #{rnd['n']} ({rnd['status']}), pista {rnd['hint_day']}/{config.MAX_HINTS}, "
                  f"película: {rnd['movie']['title']}")
        print("Ranking semanal:", msg.top(state["scores"]["weekly"], 5))
        return 0

    from social import Social
    social = Social(os.environ.get("MASTODON_API_BASE_URL", ""),
                    os.environ.get("MASTODON_ACCESS_TOKEN", ""), dry_run=args.dry_run)
    save = (lambda: None) if args.dry_run else (lambda: save_state(state))

    if args.command in ("daily", "replies"):
        from tmdb import TMDB
        key = os.environ.get("TMDB_API_KEY", "")
        if not key:
            sys.exit("Falta la variable TMDB_API_KEY")
        tmdb = TMDB(key)

    if args.command == "daily":
        print(run_daily(state, social, tmdb, force=args.force, theme=args.theme, on_save=save))
    elif args.command == "replies":
        print(run_replies(state, social, tmdb, on_save=save))
    elif args.command == "weekly":
        print(run_weekly(state, social, on_save=save))
    save()
    return 0


if __name__ == "__main__":
    sys.exit(main())

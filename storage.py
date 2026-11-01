"""Guardado del estado del juego en state.json (se versiona en el propio repo)."""
import copy
import json
import os
from pathlib import Path

STATE_PATH = Path(os.environ.get("STATE_FILE", Path(__file__).parent / "state.json"))

DEFAULT_STATE = {
    "round_counter": 0,
    "round": None,
    "last_daily": None,
    "last_notification_id": None,
    "used_tmdb_ids": [],
    "scores": {"weekly": {}, "monthly": {}, "alltime": {}},
    "streaks": {},
    "solved_counts": {},
    "week_rounds": [],
    "history": [],
    "monthly_posted": None,
}


def ensure_defaults(state):
    for key, value in DEFAULT_STATE.items():
        if key not in state:
            state[key] = copy.deepcopy(value)
    for key in ("weekly", "monthly", "alltime"):
        state["scores"].setdefault(key, {})
    return state


def load_state(path=None):
    path = Path(path or STATE_PATH)
    state = {}
    if path.exists() and path.read_text(encoding="utf-8").strip():
        state = json.loads(path.read_text(encoding="utf-8"))
    return ensure_defaults(state)


def save_state(state, path=None):
    path = Path(path or STATE_PATH)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)

"""Ajustes generales del bot. Casi todo se puede cambiar con variables de entorno."""
import os
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.environ.get("BOT_TZ", "Europe/Madrid"))

MAX_HINTS = 7                  # pistas por ronda (1 pista por día)
MAX_GUESSES_PER_DAY = 5        # intentos por persona y por pista
MAX_GUESS_LENGTH = 80          # mensajes más largos no se consideran respuestas
MAX_CHARS = int(os.environ.get("MAX_CHARS", "500"))  # límite de caracteres de tu instancia
VISIBILITY = os.environ.get("VISIBILITY", "public")  # public | unlisted
REPLY_TO_WRONG = os.environ.get("REPLY_TO_WRONG", "1") == "1"
LANGUAGE = "es"
HASHTAGS = "#CineAdivina #Cine #Películas"

# Puntos extra por racha de rondas acertadas seguidas
STREAK_BONUS = [(5, 2), (3, 1)]   # (racha mínima, puntos extra)

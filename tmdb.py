"""Cliente mínimo de TMDB (themoviedb.org) para elegir películas y bajar la portada."""
import random

import requests

from game import COUNTRIES, LANGUAGES

BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w780"


class TMDB:
    def __init__(self, api_key, session=None):
        self.session = session or requests.Session()
        self.headers = {}
        self.params = {}
        # Acepta tanto la "clave API" (v3) como el "token de lectura" (v4)
        if len(api_key) > 40:
            self.headers["Authorization"] = f"Bearer {api_key}"
        else:
            self.params["api_key"] = api_key

    def _get(self, path, **params):
        q = dict(self.params)
        q.update(params)
        r = self.session.get(f"{BASE}{path}", params=q, headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json()

    def poster(self, poster_path):
        r = self.session.get(IMG + poster_path, timeout=60)
        r.raise_for_status()
        return r.content

    def _details(self, movie_id):
        d = self._get(f"/movie/{movie_id}", language="es-ES", append_to_response="credits")
        en = self._get(f"/movie/{movie_id}", language="en-US")
        credits = d.get("credits") or {}
        release = d.get("release_date") or ""
        year = int(release[:4]) if release[:4].isdigit() else None
        return {
            "tmdb_id": d["id"],
            "title": (d.get("title") or "").strip(),
            "original_title": (d.get("original_title") or "").strip(),
            "title_en": (en.get("title") or "").strip(),
            "year": year,
            "overview": (d.get("overview") or "").strip(),
            "tagline": (d.get("tagline") or "").strip(),
            "runtime": d.get("runtime") or 0,
            "vote_average": d.get("vote_average") or 0,
            "genres": [g["name"].capitalize() for g in d.get("genres", [])],
            "directors": [c["name"] for c in credits.get("crew", [])
                          if c.get("job") == "Director"],
            "cast": [c["name"] for c in credits.get("cast", [])[:6]],
            "countries": [COUNTRIES.get(c["iso_3166_1"], c["name"])
                          for c in d.get("production_countries", [])],
            "language": LANGUAGES.get(d.get("original_language"), d.get("original_language")),
            "companies": [c["name"] for c in d.get("production_companies", [])],
            "poster_path": d.get("poster_path"),
        }

    @staticmethod
    def valid(movie):
        return bool(movie["title"] and movie["overview"] and movie["poster_path"]
                    and movie["year"] and movie["directors"] and len(movie["cast"]) >= 2)

    def pick_movie(self, theme, exclude, rng=None):
        """Elige una película de la temática que no se haya usado ya."""
        rng = rng or random.Random()
        params = dict(theme["params"])
        params.update({"language": "es-ES", "include_adult": "false"})
        pages = list(range(1, theme.get("pages", 5) + 1))
        rng.shuffle(pages)
        for page in pages[:6]:
            data = self._get("/discover/movie", page=page, **params)
            results = [r for r in data.get("results", []) if r["id"] not in exclude]
            rng.shuffle(results)
            for r in results[:8]:
                movie = self._details(r["id"])
                if self.valid(movie):
                    return movie
        return None

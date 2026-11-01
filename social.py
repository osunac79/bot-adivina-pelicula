"""Pequeña capa sobre Mastodon.py. Con dry_run=True solo imprime lo que haría."""
import itertools


class Social:
    def __init__(self, base_url, token, dry_run=False):
        self.dry_run = dry_run
        self._fake_ids = itertools.count(1000)
        self._me = None
        if dry_run and not token:
            self.api = None
        else:
            from mastodon import Mastodon
            self.api = Mastodon(access_token=token, api_base_url=base_url)

    def me_id(self):
        if self._me is None:
            self._me = self.api.account_verify_credentials()["id"] if self.api else 0
        return self._me

    def post(self, text, reply_to=None, visibility="public", media_ids=None):
        if self.dry_run:
            fid = next(self._fake_ids)
            print(f"\n--- [DRY RUN] toot #{fid} ({visibility}, responde a {reply_to}) ---\n{text}\n")
            return fid
        status = self.api.status_post(
            text, in_reply_to_id=reply_to, visibility=visibility,
            media_ids=media_ids, language="es")
        return status["id"]

    def upload(self, data, alt):
        if self.dry_run:
            print(f"[DRY RUN] imagen subida ({len(data)} bytes) alt={alt!r}")
            return next(self._fake_ids)
        media = self.api.media_post(data, mime_type="image/jpeg",
                                    description=alt, file_name="portada.jpg")
        return media["id"]

    def latest_notification_id(self):
        if not self.api:
            return None
        batch = self.api.notifications(limit=1)
        return int(batch[0]["id"]) if batch else None

    def new_mentions(self, min_id):
        """Menciones nuevas (de la más antigua a la más reciente) y el último id visto."""
        mentions, seen_max = [], int(min_id or 0)
        if not self.api:
            return mentions, seen_max
        while True:
            batch = self.api.notifications(min_id=seen_max, limit=40)
            if not batch:
                break
            ids = [int(n["id"]) for n in batch]
            if max(ids) <= seen_max:
                break
            seen_max = max(ids)
            mentions.extend(n for n in batch if n["type"] == "mention" and n.get("status"))
        mentions.sort(key=lambda n: int(n["id"]))
        return mentions, seen_max

import re
import hashlib
from datetime import datetime, timezone
from dateutil import parser as date_parser
from django.conf import settings
from django.core.cache import cache
import feedparser
import requests

# =========================
# Helpers / infrastructure
# =========================

def _clean_html(text: str) -> str:
    """Просте очищення HTML + нормалізація пробілів."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _ua_headers():
    return {
        "User-Agent": "AthleticManager/1.0 (+https://example.com) Python-requests",
        "Accept": "application/json, text/xml, application/xml, */*;q=0.8",
    }

def _cache_get_or_set(key: str, fetch_fn, ttl_seconds: int):
    data = cache.get(key)
    if data is not None:
        return data
    data = fetch_fn()
    cache.set(key, data, ttl_seconds)
    return data


# =========================
# News (RSS) — ONLY
# =========================
def fetch_sport_news(limit: int = 9, feeds=None, ttl_seconds: int = 60 * 30):
    """
    Повертає список новин з RSS:
      {title, link, summary, image, date, source}
    """
    feed_urls = feeds if feeds else getattr(settings, "SPORT_NEWS_FEEDS", [])
    cache_key = "sport_news__" + hashlib.md5(("|".join(feed_urls) + f"|{limit}").encode()).hexdigest()

    def _fetch():
        items = []
        for url in feed_urls:
            try:
                # спочатку пробуємо завантажити з нашими headers
                try:
                    resp = requests.get(url, timeout=10, headers=_ua_headers())
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.content)
                except Exception:
                    # fallback — нехай feedparser сам сходить
                    feed = feedparser.parse(url)

                source_title = (getattr(feed, "feed", {}) or {}).get("title", "Source")

                for e in getattr(feed, "entries", []):
                    title = (getattr(e, "title", "") or "").strip()
                    link = (getattr(e, "link", "") or "").strip()
                    summary = _clean_html(getattr(e, "summary", ""))[:220] if hasattr(e, "summary") else ""

                    # дата
                    dt = None
                    for field in ("published", "updated", "created"):
                        if hasattr(e, field):
                            try:
                                dt = date_parser.parse(getattr(e, field))
                                break
                            except Exception:
                                pass
                    if not dt:
                        dt = datetime.now(timezone.utc)

                    # картинка
                    image = None
                    media = getattr(e, "media_content", None)
                    if media and isinstance(media, list):
                        for m in media:
                            if m.get("url"):
                                image = m["url"]
                                break
                    if not image:
                        thumbs = getattr(e, "media_thumbnail", None)
                        if thumbs and isinstance(thumbs, list):
                            for t in thumbs:
                                if t.get("url"):
                                    image = t["url"]
                                    break
                    if not image:
                        for l in getattr(e, "links", []) or []:
                            if l.get("rel") == "enclosure" and "image" in (l.get("type") or ""):
                                image = l.get("href")
                                break

                    items.append({
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "image": image,
                        "date": dt,
                        "source": source_title,
                    })
            except Exception:
                # якщо помилка з конкретним фідом — пропускаємо
                continue

        # свіже вище
        items.sort(key=lambda x: x["date"], reverse=True)
        return items[:limit]

    return _cache_get_or_set(cache_key, _fetch, ttl_seconds)

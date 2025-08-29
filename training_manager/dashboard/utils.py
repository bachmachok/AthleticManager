# training_manager/dashboard/utils.py
import re
import hashlib
from datetime import datetime, timezone
from dateutil import parser as date_parser

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import get_language, gettext as _

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


def _ua_headers(lang: str | None = None):
    """
    Заголовки запиту з урахуванням мови інтерфейсу (Accept-Language),
    щоб фіди, що підтримують мультимову, віддавали локалізований контент.
    """
    # нормалізуємо, напр. "uk-ua" -> "uk-UA"
    if not lang:
        lang = get_language() or getattr(settings, "LANGUAGE_CODE", "en")
    lang = lang.replace("_", "-")
    # базовий fallback, щоб сервер міг вибрати найближчу мову
    # приклад: "uk-UA,uk;q=0.9,en;q=0.8"
    lang_fallback = f"{lang},{lang.split('-')[0]};q=0.9,en;q=0.8"

    return {
        "User-Agent": "AthleticManager/1.0 (+https://example.com) Python-requests",
        "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.7",
        "Accept-Language": lang_fallback,
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
def fetch_sport_news(
    limit: int = 9,
    feeds=None,
    ttl_seconds: int = 60 * 30,
    lang: str | None = None,
):
    """
    Повертає список новин з RSS:
      {title, link, summary, image, date, source}

    :param limit: к-сть новин
    :param feeds: список URL фідів; якщо None — візьмемо з settings.SPORT_NEWS_FEEDS
                  (у views.index уже підставляється мапа за мовою)
    :param ttl_seconds: TTL кешу
    :param lang: примусова локаль (якщо None — поточна мова інтерфейсу)
    """
    # Визначаємо мову
    lang = lang or get_language() or getattr(settings, "LANGUAGE_CODE", "en")
    feed_urls = feeds if feeds else getattr(settings, "SPORT_NEWS_FEEDS", [])

    # Кеш розділяємо по мові та набору фідів
    cache_fingerprint = f"{lang}|{ '|'.join(feed_urls) }|{limit}"
    cache_key = "sport_news__" + hashlib.md5(cache_fingerprint.encode()).hexdigest()

    def _fetch():
        items = []
        for url in feed_urls:
            try:
                # спочатку пробуємо завантажити з нашими headers (вкл. Accept-Language)
                try:
                    resp = requests.get(url, timeout=10, headers=_ua_headers(lang))
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.content)
                except Exception:
                    # fallback — нехай feedparser сам сходить
                    feed = feedparser.parse(url)

                source_title = (getattr(feed, "feed", {}) or {}).get("title") or _("Джерело")

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
                        for l in (getattr(e, "links", []) or []):
                            if l.get("rel") == "enclosure" and "image" in (l.get("type") or ""):
                                image = l.get("href")
                                break

                    items.append(
                        {
                            "title": title,
                            "link": link,
                            "summary": summary,
                            "image": image,
                            "date": dt,          # форматування дати робиться у шаблоні відповідно до мови
                            "source": source_title,
                        }
                    )
            except Exception:
                # якщо помилка з конкретним фідом — пропускаємо
                continue

        # свіже вище
        items.sort(key=lambda x: x["date"], reverse=True)
        return items[:limit]

    return _cache_get_or_set(cache_key, _fetch, ttl_seconds)

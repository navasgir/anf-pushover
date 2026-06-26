import os
import sys
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

FEED_URL = "https://anf-news2.com/feed.rss"
STATE_FILE = Path("last_seen.txt")


def log(*args):
    print(*args, flush=True)


def fail(msg):
    log("HATA:", msg)
    sys.exit(1)


def main():
    try:
        req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=20).read()
    except Exception as e:
        fail(f"RSS indirilemedi: {e}")

    try:
        root = ET.fromstring(raw)
    except Exception as e:
        fail(f"RSS parse edilemedi: {e}")

    item = root.find("./channel/item")
    if item is None:
        fail("Feed icinde haber bulunamadi.")

    title = (item.findtext("title") or "").strip()
    link = (item.findtext("link") or "").strip()

    if not title or not link:
        fail("Baslik veya link bos geldi.")

    old = STATE_FILE.read_text().strip() if STATE_FILE.exists() else ""

    log("Bulunan baslik:", title)
    log("Bulunan link:", link)
    log("Kayitli eski link:", old or "(yok)")

    if link == old:
        log("Yeni haber yok, cikiliyor.")
        sys.exit(0)

    token = os.environ.get("PUSHOVER_TOKEN")
    user = os.environ.get("PUSHOVER_USER")

    if not token or not user:
        fail("PUSHOVER_TOKEN veya PUSHOVER_USER bos. GitHub Secrets'i kontrol et.")

    data = urllib.parse.urlencode({
        "token": token,
        "user": user,
        "title": "ANF",
        "message": title,
        "url": link,
        "url_title": "Haberi ac",
    }).encode()

    try:
        resp = urllib.request.urlopen(
            urllib.request.Request(
                "https://api.pushover.net/1/messages.json",
                data=data,
                method="POST",
            ),
            timeout=20,
        )
        body = resp.read().decode("utf-8", errors="ignore")
        log("Pushover yaniti:", resp.status, body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        fail(f"Pushover istegi basarisiz: {e.code} {err_body}")
    except Exception as e:
        fail(f"Pushover istegine baglanilamadi: {e}")

    STATE_FILE.write_text(link)
    log("Gonderildi:", title)


if __name__ == "__main__":
    main()

import argparse
import asyncio
import json
import os
import sys

import aiohttp

INDEX_FILE = "data/madrid/sessions_index.json"
LEGISLATURAS = ["XIII", "XII", "XI", "X"]
URL_TEMPLATE = "https://www.asambleamadrid.es/static/doc/publicaciones/{leg}-DS-{idx}.pdf"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
# Diaries are numbered consecutively; this many misses in a row means we've
# reached the latest one.
STOP_AFTER_MISSES = 25
BATCH_SIZE = 5  # the site sits behind a WAF: keep concurrency low
RETRIES = 3

FOUND, MISSING, BLOCKED = "found", "missing", "blocked"


async def probe(session, leg, idx):
    """HEAD a diary URL. 404 means it doesn't exist; anything else after
    retries (403/429/5xx/timeouts) means we couldn't tell."""
    url = URL_TEMPLATE.format(leg=leg, idx=idx)
    for attempt in range(1, RETRIES + 1):
        try:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=20), allow_redirects=True) as resp:
                if resp.status == 200:
                    return FOUND
                if resp.status == 404:
                    return MISSING
        except (aiohttp.ClientError, asyncio.TimeoutError):
            pass
        await asyncio.sleep(2 * attempt)
    return BLOCKED


def session_entry(leg, idx):
    return {"id": f"{leg}-{idx}", "url": URL_TEMPLATE.format(leg=leg, idx=idx), "legis_id": leg, "text": f"DS {idx}"}


def load_index():
    if not os.path.exists(INDEX_FILE):
        return []
    with open(INDEX_FILE, encoding="utf-8") as f:
        return json.load(f)


async def scan_legislature(session, leg, known):
    """Probe diaries after the highest known one until enough consecutive misses."""
    idx = max(known) + 1 if known else 1
    found, blocked, probed, misses = [], 0, 0, 0
    while misses < STOP_AFTER_MISSES:
        batch = list(range(idx, idx + BATCH_SIZE))
        results = await asyncio.gather(*(probe(session, leg, i) for i in batch))
        probed += len(batch)
        for i, status in zip(batch, results):
            if status == FOUND:
                found.append(i)
                misses = 0
            elif status == MISSING:
                misses += 1
            else:
                blocked += 1
                misses += 1
        idx += BATCH_SIZE
    return found, blocked, probed


def parse_legislaturas(value):
    if not value:
        return list(LEGISLATURAS)
    requested = [v.strip().upper() for v in str(value).split(",") if v.strip()]
    missing = [leg for leg in requested if leg not in LEGISLATURAS]
    if missing:
        raise ValueError(f"Legislaturas desconocidas: {', '.join(missing)}")
    return requested


async def main():
    parser = argparse.ArgumentParser(description="Scrapea índices de diarios de sesiones de Madrid.")
    parser.add_argument(
        "--legislaturas",
        help="Lista de legislaturas separadas por coma (ej: XIII,XII). Por defecto: XIII,XII,XI,X.",
    )
    args = parser.parse_args()
    legislaturas = parse_legislaturas(args.legislaturas)
    os.makedirs("data/madrid", exist_ok=True)

    # Incremental: keep every known diary and only look for newer ones.
    sessions = {s["id"]: s for s in load_index()}
    total_new = 0
    total_blocked = 0
    total_probed = 0
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for leg in legislaturas:
            known = [int(s["id"].split("-")[1]) for s in sessions.values() if s.get("legis_id") == leg]
            found, blocked, probed = await scan_legislature(session, leg, known)
            for idx in found:
                sessions[f"{leg}-{idx}"] = session_entry(leg, idx)
            total_new += len(found)
            total_blocked += blocked
            total_probed += probed
            print(f"{leg}: {len(known)} conocidos, {len(found)} nuevos, {blocked} sin respuesta válida")

    ordered = sorted(sessions.values(), key=lambda s: (LEGISLATURAS.index(s["legis_id"]) if s["legis_id"] in LEGISLATURAS else 99, int(s["id"].split("-")[1])))
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(ordered, f, indent=2, ensure_ascii=False)
    print(f"Found {len(ordered)} valid session diaries ({total_new} new).")

    if total_blocked * 2 > total_probed:
        # Previously this silently produced an empty index for months.
        print(
            f"::error title=Madrid::asambleamadrid.es no respondió ({total_blocked} peticiones bloqueadas o fallidas).",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

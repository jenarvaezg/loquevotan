#!/usr/bin/env python3
"""
Scraper de votaciones del Congreso de los Diputados de España.
Descarga los JSON de datos abiertos de congreso.es/opendata/votaciones.
Soporta múltiples legislaturas (X a XV).
"""

import json
import os
import re
import sys
import time
import urllib.request

BASE_URL = "https://www.congreso.es"
VOTACIONES_PAGE = f"{BASE_URL}/es/opendata/votaciones"
PORTLET_PARAMS = "p_p_id=votaciones&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw")
STATE_DIR = os.path.join(SCRIPT_DIR, "..", "data", "state", "national")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

DELAY_BETWEEN_DATES = 1.5
DELAY_BETWEEN_FILES = 0.5

# Legislatures with opendata available
LEGISLATURES = ["X", "XI", "XII", "XIII", "XIV", "XV"]


def fetch(url):
    """Fetch URL content with browser User-Agent."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def get_voting_dates(legislatura):
    """Extract the diasVotaciones array for a given legislature."""
    url = (
        f"{VOTACIONES_PAGE}?{PORTLET_PARAMS}"
        f"&targetLegislatura={legislatura}&currentLegislatura=XV"
    )
    html = fetch(url)
    match = re.search(r"diasVotaciones\s*=\s*\[([^\]]+)\]", html)
    if not match:
        return []
    return sorted(int(d.strip()) for d in match.group(1).split(",") if d.strip())


def int_to_date_param(date_int):
    """Convert 20230919 to '19/09/2023' (DD/MM/YYYY for the Liferay portlet)."""
    s = str(date_int)
    return f"{s[6:8]}/{s[4:6]}/{s[:4]}"


def get_json_urls(date_int, legislatura):
    """Fetch the votaciones page for a date and extract all JSON download URLs."""
    param = int_to_date_param(date_int)
    url = (
        f"{VOTACIONES_PAGE}?{PORTLET_PARAMS}"
        f"&targetLegislatura={legislatura}&targetDate={param}"
    )
    html = fetch(url)
    hrefs = re.findall(
        r'href="(/webpublica/opendata/votaciones/[^"]+\.json)"', html
    )
    return [f"{BASE_URL}{h}" for h in hrefs]


def download_json(url, date_int, legislatura):
    """Download a single voting JSON and save it to data/raw/."""
    match = re.search(r"Sesion(\d+)/\d+/Votacion(\d+)/", url)
    if not match:
        print(f"  WARN: URL no reconocida: {url}", file=sys.stderr)
        return None

    sesion = match.group(1)
    votacion = match.group(2)
    filename = f"L{legislatura}_{date_int}_S{sesion}_V{votacion}.json"
    filepath = os.path.join(RAW_DIR, filename)

    if os.path.exists(filepath):
        return filepath

    data = fetch(url)
    json.loads(data)  # validate JSON

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(data)
    return filepath


def state_file(legislatura):
    """Path to the state file tracking last fetched date per legislature."""
    return os.path.join(STATE_DIR, f"last_fetch_{legislatura}.txt")


def get_last_date(legislatura):
    """Read the last successfully processed date for a legislature."""
    path = state_file(legislatura)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            content = f.read().strip()
            return int(content) if content else 0
    return 0


def save_last_date(legislatura, date_int):
    """Persist the last successfully processed date for a legislature."""
    with open(state_file(legislatura), "w", encoding="utf-8") as f:
        f.write(str(date_int))


def process_legislature(legislatura, limit=None):
    """Download all voting data for a single legislature."""
    print(f"\n{'='*60}")
    print(f"  LEGISLATURA {legislatura}")
    print(f"{'='*60}")

    dates = get_voting_dates(legislatura)
    if not dates:
        print(f"  No hay datos para la legislatura {legislatura}")
        return 0

    last = get_last_date(legislatura)
    pending = [d for d in dates if d > last]

    if not pending:
        print(f"  {len(dates)} fechas - todas ya descargadas")
        return 0

    if limit:
        pending = pending[:limit]

    print(f"  {len(dates)} fechas totales, {len(pending)} pendientes")
    total_downloaded = 0

    for i, date_int in enumerate(pending):
        s = str(date_int)
        label = f"{s[:4]}-{s[4:6]}-{s[6:]}"
        print(f"  [{i + 1}/{len(pending)}] {label}...", end=" ", flush=True)

        try:
            urls = get_json_urls(date_int, legislatura)
            if not urls:
                print("0 votaciones")
                time.sleep(DELAY_BETWEEN_DATES)
                continue

            print(f"{len(urls)} votaciones")

            for url in urls:
                try:
                    result = download_json(url, date_int, legislatura)
                    if result:
                        total_downloaded += 1
                except Exception as e:
                    print(f"    ERROR descargando: {e}", file=sys.stderr)
                time.sleep(DELAY_BETWEEN_FILES)

            save_last_date(legislatura, date_int)

        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)

        time.sleep(DELAY_BETWEEN_DATES)

    return total_downloaded


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(STATE_DIR, exist_ok=True)

    # Parse arguments
    limit = None
    target_legs = LEGISLATURES

    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    if "--legislatura" in sys.argv:
        idx = sys.argv.index("--legislatura")
        if idx + 1 < len(sys.argv):
            target_legs = [sys.argv[idx + 1]]

    # Migrate old state file (from single-legislature version)
    old_state = os.path.join(RAW_DIR, "last_fetch.txt")
    new_state = state_file("XV")
    if os.path.exists(old_state) and not os.path.exists(new_state):
        os.rename(old_state, new_state)

    # Migrate legacy per-legislature state files from data/raw/
    for leg in LEGISLATURES:
        legacy_state = os.path.join(RAW_DIR, f"last_fetch_{leg}.txt")
        migrated_state = state_file(leg)
        if os.path.exists(legacy_state) and not os.path.exists(migrated_state):
            os.rename(legacy_state, migrated_state)

    # Migrate old filenames without legislature prefix
    for f in os.listdir(RAW_DIR):
        if re.match(r"^\d{8}_S\d+_V\d+\.json$", f):
            old_path = os.path.join(RAW_DIR, f)
            new_name = f"LXV_{f}"
            new_path = os.path.join(RAW_DIR, new_name)
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)

    grand_total = 0
    for leg in target_legs:
        grand_total += process_legislature(leg, limit)

    print(f"\n{'='*60}")
    print(f"  DESCARGA COMPLETADA: {grand_total} archivos nuevos")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

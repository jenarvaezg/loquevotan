#!/usr/bin/env python3
"""
Scraper de votaciones del Congreso de los Diputados de España.
Descarga los JSON de datos abiertos de congreso.es/opendata/votaciones.

Las legislaturas disponibles se descubren desde la propia web (selector de
legislatura), así que una legislatura nueva (XVI, XVII...) se recoge sola.

Estado por legislatura en data/state/national/dates_<LEG>.json:
    {"20260930": 21, ...}  -> nº de votaciones publicadas ese día.
Una fecha se considera completa solo si data/raw tiene al menos ese nº de
ficheros para ella. Si data/raw se pierde (cache de CI expirada, etc.), las
fechas sin ficheros vuelven a quedar pendientes y se re-descargan: el scraper
se repara solo en lugar de dar por descargado algo que no está en disco.
"""

import io
import json
import os
import re
import sys
import time
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone

BASE_URL = "https://www.congreso.es"
VOTACIONES_PAGE = f"{BASE_URL}/es/opendata/votaciones"
PORTLET_PARAMS = "p_p_id=votaciones&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.environ.get("LQV_NATIONAL_RAW_DIR") or os.path.join(SCRIPT_DIR, "..", "data", "raw")
STATE_DIR = os.environ.get("LQV_NATIONAL_STATE_DIR") or os.path.join(
    SCRIPT_DIR, "..", "data", "state", "national"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

DELAY_BETWEEN_DATES = float(os.environ.get("LQV_SCRAPER_DELAY_DATES", "1.5"))
DELAY_BETWEEN_FILES = float(os.environ.get("LQV_SCRAPER_DELAY_FILES", "0.5"))
FETCH_RETRIES = 3
# Date pages of long sessions (budget debates with 400+ votes) take 40s+ to
# render; a 30s timeout made the old scraper skip exactly those days.
PAGE_TIMEOUT = 120
ZIP_TIMEOUT = 300
FETCH_RETRY_BACKOFF = 5

# Fallback if the legislature selector can't be parsed. Discovery from the web
# takes precedence, so new legislatures don't need a code change.
LEGISLATURES = ["X", "XI", "XII", "XIII", "XIV", "XV", "XVI"]

ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
RAW_FILE_RE = re.compile(r"^L([IVXLC]+)_(\d{8})_S\d+_V\d+\.json$")


def roman_to_int(roman):
    total = 0
    prev = 0
    for ch in reversed(roman.upper()):
        value = ROMAN_VALUES[ch]
        total = total - value if value < prev else total + value
        prev = max(prev, value)
    return total


def fetch_bytes(url, timeout=PAGE_TIMEOUT):
    """Fetch URL with browser User-Agent, retrying transient errors."""
    last_error = None
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001 - network errors are varied
            last_error = e
            if attempt < FETCH_RETRIES:
                time.sleep(FETCH_RETRY_BACKOFF * attempt)
    raise last_error


def fetch(url, timeout=PAGE_TIMEOUT):
    return fetch_bytes(url, timeout).decode("utf-8")


def legislature_page_url(legislatura):
    return f"{VOTACIONES_PAGE}?{PORTLET_PARAMS}&targetLegislatura={legislatura}"


def parse_legislatures(html):
    """Extract legislature ids (roman numerals) from the legislature <select>."""
    start = html.find('id="_votaciones_legislatura"')
    if start == -1:
        return []
    end = html.find("</select>", start)
    segment = html[start:end if end != -1 else start + 5000]
    legs = re.findall(r"<option[^>]*>\s*([IVXLC]+)\s+Legislatura", segment)
    return sorted(set(legs), key=roman_to_int)


def parse_voting_dates(html):
    match = re.search(r"diasVotaciones\s*=\s*\[([^\]]*)\]", html)
    if not match:
        return []
    return sorted(int(d.strip()) for d in match.group(1).split(",") if d.strip())


def discover_legislatures():
    """Legislatures listed on the opendata page, falling back to LEGISLATURES."""
    try:
        legs = parse_legislatures(fetch(f"{VOTACIONES_PAGE}?{PORTLET_PARAMS}"))
    except Exception as e:  # noqa: BLE001
        print(f"  WARN: no se pudo descubrir legislaturas ({e}); uso lista fija", file=sys.stderr)
        legs = []
    return legs or list(LEGISLATURES)


def get_voting_dates(legislatura):
    """Extract the diasVotaciones array for a given legislature."""
    return parse_voting_dates(fetch(legislature_page_url(legislatura)))


def int_to_date_param(date_int):
    """Convert 20230919 to '19/09/2023' (DD/MM/YYYY for the Liferay portlet)."""
    s = str(date_int)
    return f"{s[6:8]}/{s[4:6]}/{s[:4]}"


def parse_date_links(html):
    """JSON download URLs (one per vote) and the day's ZIP with all of them."""
    hrefs = re.findall(r'href="(/webpublica/opendata/votaciones/[^"]+\.json)"', html)
    zips = re.findall(r'href="(/webpublica/opendata/votaciones/[^"]+\.zip)"', html)
    # Preserve order, drop duplicates.
    json_urls = [f"{BASE_URL}{h}" for h in dict.fromkeys(hrefs)]
    return json_urls, (f"{BASE_URL}{zips[0]}" if zips else None)


def get_date_links(date_int, legislatura):
    """Fetch the votaciones page for a date: (json_urls, zip_url or None)."""
    param = int_to_date_param(date_int)
    return parse_date_links(fetch(f"{legislature_page_url(legislatura)}&targetDate={param}"))


def vote_key_from_url(url):
    match = re.search(r"Sesion(\d+)/\d+/Votacion(\d+)/", url)
    return (int(match.group(1)), int(match.group(2))) if match else None


def zip_entry_key(name):
    """'sesion202votacion9.json' -> (202, 9)."""
    match = re.search(r"sesion(\d+)votacion(\d+)\.json$", os.path.basename(name), re.IGNORECASE)
    return (int(match.group(1)), int(match.group(2))) if match else None


def raw_filename(url, date_int, legislatura):
    match = re.search(r"Sesion(\d+)/\d+/Votacion(\d+)/", url)
    if not match:
        return None
    return f"L{legislatura}_{date_int}_S{match.group(1)}_V{match.group(2)}.json"


def write_raw(filepath, text):
    json.loads(text)  # validate JSON before persisting
    tmp_path = f"{filepath}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp_path, filepath)


def extract_from_zip(zip_bytes, wanted):
    """Write the JSONs in `wanted` ({(sesion, votacion): filepath}) from the
    day's ZIP. Returns the keys written. The ZIP's JSONs are byte-for-byte the
    same documents as the per-vote downloads."""
    written = set()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            key = zip_entry_key(name)
            if key in wanted and key not in written:
                write_raw(wanted[key], archive.read(name).decode("utf-8"))
                written.add(key)
    return written


def download_json(url, date_int, legislatura):
    """Download a single voting JSON into data/raw/. Returns (path, is_new)."""
    filename = raw_filename(url, date_int, legislatura)
    if not filename:
        raise ValueError(f"URL no reconocida: {url}")
    filepath = os.path.join(RAW_DIR, filename)

    if os.path.exists(filepath):
        return filepath, False

    write_raw(filepath, fetch(url))
    return filepath, True


def raw_counts_by_date(legislatura, raw_dir=None):
    """Number of raw files on disk per date for a legislature."""
    counts = Counter()
    for name in os.listdir(raw_dir or RAW_DIR):
        match = RAW_FILE_RE.match(name)
        if match and match.group(1) == legislatura:
            counts[int(match.group(2))] += 1
    return counts


def manifest_file(legislatura, state_dir=None):
    return os.path.join(state_dir or STATE_DIR, f"dates_{legislatura}.json")


def legacy_state_file(legislatura, state_dir=None):
    return os.path.join(state_dir or STATE_DIR, f"last_fetch_{legislatura}.txt")


def load_manifest(legislatura, raw_counts, state_dir=None):
    """Load {date_int: expected_count}, migrating from the legacy last_fetch file.

    Legacy state only stored the last processed date. Dates up to it that have
    files on disk are trusted with the count present; dates with no files are
    left out so they get downloaded again.
    """
    path = manifest_file(legislatura, state_dir)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return {int(k): int(v) for k, v in json.load(f).items()}

    legacy = legacy_state_file(legislatura, state_dir)
    last = 0
    if os.path.exists(legacy):
        with open(legacy, encoding="utf-8") as f:
            content = f.read().strip()
            last = int(content) if content else 0
    return {d: n for d, n in raw_counts.items() if d <= last and n > 0}


def save_manifest(legislatura, manifest, state_dir=None):
    path = manifest_file(legislatura, state_dir)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump({str(k): manifest[k] for k in sorted(manifest)}, f, indent=0)
        f.write("\n")
    os.replace(tmp_path, path)


def is_settled(date_int, now=None):
    """A voting day is final once it's at least two days old.

    A run during (or right after) a plenary session may see only part of the
    day's votes, so recent dates are never recorded as complete.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = int((now - timedelta(days=2)).strftime("%Y%m%d"))
    return date_int <= cutoff


def pending_dates(dates, manifest, raw_counts):
    """Dates not yet fully downloaded: unknown, or fewer files than expected."""
    return [d for d in dates if d not in manifest or raw_counts.get(d, 0) < manifest[d]]


def process_legislature(legislatura, limit=None):
    """Download all missing voting data for a single legislature.

    Returns (new_files, failed_dates).
    """
    print(f"\n{'='*60}")
    print(f"  LEGISLATURA {legislatura}")
    print(f"{'='*60}")

    dates = get_voting_dates(legislatura)
    if not dates:
        print(f"  No hay datos para la legislatura {legislatura}")
        return 0, []

    raw_counts = raw_counts_by_date(legislatura)
    manifest = load_manifest(legislatura, raw_counts)
    pending = pending_dates(dates, manifest, raw_counts)

    if not pending:
        print(f"  {len(dates)} fechas - todas ya descargadas")
        save_manifest(legislatura, manifest)
        return 0, []

    if limit:
        pending = pending[:limit]

    print(f"  {len(dates)} fechas totales, {len(pending)} pendientes")
    total_downloaded = 0
    failed_dates = []

    for i, date_int in enumerate(pending):
        s = str(date_int)
        label = f"{s[:4]}-{s[4:6]}-{s[6:]}"
        print(f"  [{i + 1}/{len(pending)}] {label}...", end=" ", flush=True)

        try:
            urls, zip_url = get_date_links(date_int, legislatura)
            if not urls:
                # Listed as a voting day but no files yet: retry next run.
                print("0 votaciones (se reintentará)")
                time.sleep(DELAY_BETWEEN_DATES)
                continue

            print(f"{len(urls)} votaciones")
            errors = 0
            missing = {}
            for url in urls:
                key, filename = vote_key_from_url(url), raw_filename(url, date_int, legislatura)
                if key and filename and not os.path.exists(os.path.join(RAW_DIR, filename)):
                    missing[key] = os.path.join(RAW_DIR, filename)

            # One request for the whole day instead of one per vote (a lost
            # cache means ~14k votes); per-vote downloads cover any gap.
            if zip_url and len(missing) > 1:
                try:
                    written = extract_from_zip(fetch_bytes(zip_url, ZIP_TIMEOUT), missing)
                    total_downloaded += len(written)
                except Exception as e:  # noqa: BLE001
                    print(f"    WARN: ZIP del día no utilizable ({e}); descarga por votación", file=sys.stderr)

            for url in urls:
                try:
                    _, is_new = download_json(url, date_int, legislatura)
                    if is_new:
                        total_downloaded += 1
                        time.sleep(DELAY_BETWEEN_FILES)
                except Exception as e:  # noqa: BLE001
                    errors += 1
                    print(f"    ERROR descargando {url}: {e}", file=sys.stderr)

            if errors:
                failed_dates.append(date_int)
            elif is_settled(date_int):
                manifest[date_int] = len(urls)
                save_manifest(legislatura, manifest)

        except Exception as e:  # noqa: BLE001
            failed_dates.append(date_int)
            print(f"  ERROR: {e}", file=sys.stderr)

        time.sleep(DELAY_BETWEEN_DATES)

    return total_downloaded, failed_dates


def remove_legacy_state(legislatura):
    """Drop last_fetch_<LEG>.txt once dates_<LEG>.json supersedes it."""
    legacy = legacy_state_file(legislatura)
    if os.path.exists(legacy) and os.path.exists(manifest_file(legislatura)):
        os.remove(legacy)


def migrate_legacy_layout():
    """Move state/filenames from older scraper versions into the current layout."""
    old_state = os.path.join(RAW_DIR, "last_fetch.txt")
    if os.path.exists(old_state) and not os.path.exists(legacy_state_file("XV")):
        os.rename(old_state, legacy_state_file("XV"))

    for leg in LEGISLATURES:
        legacy_raw_state = os.path.join(RAW_DIR, f"last_fetch_{leg}.txt")
        if not os.path.exists(legacy_raw_state):
            continue
        if os.path.exists(manifest_file(leg)) or os.path.exists(legacy_state_file(leg)):
            os.remove(legacy_raw_state)  # superseded
        else:
            os.rename(legacy_raw_state, legacy_state_file(leg))

    for f in os.listdir(RAW_DIR):
        if re.match(r"^\d{8}_S\d+_V\d+\.json$", f):
            new_path = os.path.join(RAW_DIR, f"LXV_{f}")
            if not os.path.exists(new_path):
                os.rename(os.path.join(RAW_DIR, f), new_path)


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(STATE_DIR, exist_ok=True)

    limit = None
    target_legs = None

    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    if "--legislatura" in sys.argv:
        idx = sys.argv.index("--legislatura")
        if idx + 1 < len(sys.argv):
            target_legs = [sys.argv[idx + 1]]

    migrate_legacy_layout()

    if target_legs is None:
        target_legs = discover_legislatures()
    print(f"Legislaturas: {', '.join(target_legs)}")

    grand_total = 0
    failures = {}
    for leg in target_legs:
        downloaded, failed = process_legislature(leg, limit)
        grand_total += downloaded
        if failed:
            failures[leg] = failed
        remove_legacy_state(leg)

    print(f"\n{'='*60}")
    print(f"  DESCARGA COMPLETADA: {grand_total} archivos nuevos")
    print(f"{'='*60}")

    if failures:
        detail = "; ".join(f"{leg}: {', '.join(map(str, d))}" for leg, d in failures.items())
        # GitHub annotation; dates stay pending and are retried next run.
        print(f"::warning title=Scraper nacional::Fechas con errores (se reintentarán): {detail}")


if __name__ == "__main__":
    main()

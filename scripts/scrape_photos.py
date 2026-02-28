#!/usr/bin/env python3
"""
Scrapes congreso.es to build a mapping of diputado names to codParlamentario IDs.
This enables displaying official photos via:
  https://www.congreso.es/docu/imgweb/diputados/{codParlamentario}_{leg_number}.jpg

Output: data/foto_map.json
  {
    "Apellidos, Nombre": { "X": 123, "XIV": 45, ... },
    ...
  }
"""

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "data", "foto_map.json")

LEGISLATURAS = ["X", "XI", "XII", "XIII", "XIV", "XV"]
LEG_TO_NUM = {"X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15}

# Max codParlamentario to scan per legislatura (with margin)
MAX_ID = 450

BASE_URL = (
    "https://www.congreso.es/es/busqueda-de-diputados"
    "?p_p_id=diputadomodule&p_p_lifecycle=0&p_p_state=normal"
    "&p_p_mode=view&_diputadomodule_mostrarFicha=true"
    "&codParlamentario={cod}&idLegislatura={leg}"
)

TITLE_RE = re.compile(r"<title>\s*(.+?)\s*-\s*[XIVL]+\s*Legislatura")

HEADERS = {"User-Agent": "Mozilla/5.0 (loquevotan.es photo mapper)"}


def fetch_name_and_prov(cod, leg):
    """Fetch the diputado name and province for a given codParlamentario and legislatura."""
    url = BASE_URL.format(cod=cod, leg=leg)
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            m_title = TITLE_RE.search(html)
            if not m_title:
                return None, None
                
            name = m_title.group(1).strip()
            # "Búsqueda" means no diputado found
            if name.startswith("Búsqueda"):
                return None, None
                
            prov = None
            m_prov = re.search(r'Diputad[ao] por\s+([^<]+)', html)
            if m_prov:
                prov = m_prov.group(1).strip()
                
            return name, prov
    except (HTTPError, URLError, TimeoutError):
        pass
    return None, None


def name_to_apellidos_nombre(full_name):
    """Convert 'Nombre1 Nombre2 Apellido1 Apellido2' to 'Apellido1 Apellido2, Nombre1 Nombre2'.
    
    Very rough heuristic for Spanish names.
    """
    parts = full_name.strip().split()
    if len(parts) >= 3:
        # Typical case: 1 name, 2 surnames -> Surnames, Name
        return f"{' '.join(parts[1:])}, {parts[0]}"
    elif len(parts) == 2:
        return f"{parts[1]}, {parts[0]}"
    return full_name


def scrape_legislatura(leg):
    """Scrape all codParlamentario → (name, prov) mappings for a legislatura."""
    results = {}  # full_name -> {cod, prov}
    consecutive_misses = 0

    def process_id(cod):
        name, prov = fetch_name_and_prov(cod, leg)
        return cod, name, prov

    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit in chunks to allow early stopping
        chunk_size = 50
        for start in range(1, MAX_ID + 1, chunk_size):
            end = min(start + chunk_size, MAX_ID + 1)
            futures = {
                executor.submit(process_id, cod): cod
                for cod in range(start, end)
            }

            chunk_results = {}
            for future in as_completed(futures):
                cod, name, prov = future.result()
                chunk_results[cod] = (name, prov)

            # Process in order
            for cod in range(start, end):
                name, prov = chunk_results.get(cod, (None, None))
                if name:
                    results[name] = {"cod": cod, "provincia": prov}
                    consecutive_misses = 0
                else:
                    consecutive_misses += 1

            # Stop early if we've seen 40 consecutive misses
            if consecutive_misses >= 40:
                break

    return results


def load_existing():
    """Load existing foto_map if it exists."""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_existing_prov():
    prov_file = os.path.join(SCRIPT_DIR, "..", "data", "provincia_map.json")
    if os.path.exists(prov_file):
        with open(prov_file, encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    only_legs = [l for l in sys.argv[1:] if l in LEGISLATURAS]
    if not only_legs:
        only_legs = LEGISLATURAS

    print(f"Scraping fotos y provincias para legislaturas: {', '.join(only_legs)}")

    # Load existing map (full_name -> {leg: cod})
    foto_map = load_existing()
    prov_map = load_existing_prov()
    prov_file = os.path.join(SCRIPT_DIR, "..", "data", "provincia_map.json")

    for leg in only_legs:
        print(f"\n{'='*50}")
        print(f"Legislatura {leg} (IDs 1-{MAX_ID})...")
        print(f"{'='*50}")

        leg_results = scrape_legislatura(leg)

        found = 0
        for full_name, data in sorted(leg_results.items()):
            # Convert "Nombre Apellidos" to "Apellidos, Nombre" for matching with votes
            clean_name = name_to_apellidos_nombre(full_name)
            
            if clean_name not in foto_map:
                foto_map[clean_name] = {}
            foto_map[clean_name][leg] = data["cod"]
            
            if data["provincia"]:
                if clean_name not in prov_map:
                    prov_map[clean_name] = {}
                prov_map[clean_name][leg] = data["provincia"]
                
            found += 1
            print(f"  [{data['cod']:3d}] {clean_name} ({data['provincia']})")

        print(f"  → {found} diputados encontrados")

        # Save after each legislatura
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(foto_map, f, ensure_ascii=False, indent=2, sort_keys=True)
            
        with open(prov_file, "w", encoding="utf-8") as f:
            json.dump(prov_map, f, ensure_ascii=False, indent=2, sort_keys=True)
            
        print(f"  → Guardado en {OUTPUT_FILE} y {prov_file}")

    print(f"\nTotal nombres únicos: {len(foto_map)}")
    print(f"Fichero: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

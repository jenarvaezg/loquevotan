import requests
from bs4 import BeautifulSoup
import json
import re
import os
import argparse
from datetime import datetime

DEFAULT_LEGISLATURAS = ["11", "10", "9", "8", "7"]


def parse_legislaturas(value):
    if not value:
        return DEFAULT_LEGISLATURAS
    return [v.strip() for v in str(value).split(",") if v.strip()]


def get_cyl_session_links(legislaturas=None):
    base_url = "https://www.ccyl.es/RecursosInformacion/DiarioDeSesiones?SeriePublicacion=DS(P)"
    legislaturas = legislaturas or DEFAULT_LEGISLATURAS
    all_sessions = []
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for legis in legislaturas:
        print(f"--- Processing CyL Legislatura {legis} ---")
        url = f"{base_url}&Legislatura={legis}"
        response = requests.get(url, headers=headers)
        
        # Extract the JSON from the 'var model = [...];' line
        match = re.search(r'var model = (\[.*?\]);', response.text)
        if match:
            model_json = match.group(1)
            try:
                data = json.loads(model_json)
                for item in data:
                    # Filter for Plenary sessions (DS(P))
                    if item.get("SeriePublicacion") != "DS(P)":
                        continue
                        
                    pub_num = item.get("NumeroPublicacion")
                    
                    # Convert ASP.NET date format /Date(1765926000000)/ to string
                    date_val = item.get("FechaPublicacion")
                    date_str = "Unknown"
                    if date_val:
                        ts_match = re.search(r'(\d+)', date_val)
                        if ts_match:
                            ts = int(ts_match.group(1)) / 1000
                            date_str = datetime.fromtimestamp(ts).strftime('%d/%m/%Y')
                    
                    all_sessions.append({
                        "pub_num": str(pub_num),
                        "legis_id": legis,
                        "date": date_str,
                        "title": item.get("EventosEnPublicacion", ""),
                        "url": f"https://www.ccyl.es/Publicaciones/TextoEntradaDiario?Legislatura={legis}&SeriePublicacion=DS(P)&NumeroPublicacion={pub_num}",
                        "pdf_url": f"https://www.ccyl.es/Publicaciones/PdfPublicacion?Legislatura={legis}&SeriePublicacion=DS(P)&NumeroPublicacion={pub_num}"
                    })
            except Exception as e:
                print(f"  Error parsing JSON for Legis {legis}: {e}")
        else:
            print(f"  Could not find model JSON for Legis {legis}")
            
    return all_sessions

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrapea índice de sesiones de CyL.")
    parser.add_argument(
        "--legislaturas",
        help="Lista de legislaturas separadas por coma (ej: 11,10). Por defecto: 11,10,9,8,7.",
    )
    args = parser.parse_args()

    os.makedirs("data/cyl", exist_ok=True)
    target_legs = parse_legislaturas(args.legislaturas)
    sessions = get_cyl_session_links(target_legs)
    print(f"Found {len(sessions)} session documents for CyL")
    with open("data/cyl/sessions_index.json", "w") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

import requests
from bs4 import BeautifulSoup
import json
import re
import os
from datetime import datetime

def get_cyl_session_links():
    base_url = "https://www.ccyl.es/RecursosInformacion/DiarioDeSesiones?SeriePublicacion=DS(P)"
    legislaturas = ["11", "10"]
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
    os.makedirs("data/cyl", exist_ok=True)
    sessions = get_cyl_session_links()
    print(f"Found {len(sessions)} session documents for CyL")
    with open("data/cyl/sessions_index.json", "w") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

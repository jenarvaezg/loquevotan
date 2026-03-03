import requests
from bs4 import BeautifulSoup
import json
import re
import os
import argparse
from urllib.parse import urljoin

DEFAULT_LEGISLATURAS = ["12", "11", "10", "9"]


def parse_legislaturas(value):
    if not value:
        return DEFAULT_LEGISLATURAS
    return [v.strip() for v in str(value).split(",") if v.strip()]


def get_session_links(legislaturas=None):
    base_url = "https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento/composicionyfuncionamiento/resultadosvotaciones.do?seleccion=publicadosen&desderango=&hastarango=&desdemes=&desdeanyo=&hastames=&hastaanyo=&terminos=&accion=Ver+Sentido+del+voto"
    legislaturas = legislaturas or DEFAULT_LEGISLATURAS
    all_sessions = []
    
    index_file = "data/andalucia/sessions_index.json"
    if os.path.exists(index_file):
        with open(index_file, "r") as f:
            all_sessions = json.load(f)
            
    existing_doc_ids = {s['doc_id'] for s in all_sessions}
    new_sessions = []
    
    for legis in legislaturas:
        print(f"--- Processing Legislatura {legis} ---")
        # Most legislatures won't have more than 100 sessions, so 0, 15, 30, 45, 60, 75, 90 should cover most
        for indice in range(0, 150, 15):
            url = f"{base_url}&legislatura={legis}&indice={indice}"
            print(f"Fetching page with index {indice}...")
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = soup.find_all('a', href=re.compile(r'tipodoc=diario'))
            if not links:
                break
                
            found_new = False
            for link in links:
                text = link.get_text().strip()
                href = link.get('href')
                full_url = urljoin(url, href)
                
                id_match = re.search(r'id=(\d+)', href)
                if id_match:
                    doc_id = id_match.group(1)
                    
                    if doc_id in existing_doc_ids:
                        continue
                    
                    found_new = True
                    existing_doc_ids.add(doc_id)
                    session_match = re.search(r'sesión número (\d+)', text)
                    doc_num_match = re.search(r'Documento número (\d+)', text)
                    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
                    
                    new_sessions.append({
                        "doc_id": doc_id,
                        "legis_id": legis,
                        "session": session_match.group(1) if session_match else "Unknown",
                        "doc_num": doc_num_match.group(1) if doc_num_match else "Unknown",
                        "date": date_match.group(1) if date_match else "Unknown",
                        "url": full_url
                    })
            
            # If all links on this page were already known, we don't need to check older pages for this legislatura
            if not found_new:
                print("No new sessions found on this page, stopping for this legislatura.")
                break
            
    return all_sessions + new_sessions

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrapea índice de sesiones de Andalucía.")
    parser.add_argument(
        "--legislaturas",
        help="Lista de legislaturas separadas por coma (ej: 12,11). Por defecto: 12,11,10,9.",
    )
    args = parser.parse_args()

    target_legs = parse_legislaturas(args.legislaturas)
    sessions = get_session_links(target_legs)
    print(f"Found {len(sessions)} session documents")
    os.makedirs("data/andalucia/raw/pdf", exist_ok=True)
    with open("data/andalucia/sessions_index.json", "w") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

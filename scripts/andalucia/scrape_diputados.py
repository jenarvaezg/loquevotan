import requests
from bs4 import BeautifulSoup
import json
import re
import os
import time
from urllib.parse import urljoin

def scrape_andalucia_all_diputados():
    base_url = "https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento/composicionyfuncionamiento/diputados/buscadoravanzadodiputados.do"
    legislaturas = ["12", "11", "10", "9"]
    all_diputados = []
    
    for legis in legislaturas:
        print(f"--- Scraping Diputados for Legislatura {legis} ---")
        url = f"{base_url}?legislatura={legis}&cirele=0&nombre=&apellidos=&accion=Buscar&sinpaginacion=1"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all article tags
        articles = soup.find_all('article')
        
        if not articles:
            # Fallback for older layouts if any
            links = soup.find_all('a', href=re.compile(r'codmie='))
            seen_codmies = set()
            for l in links:
                href = l.get('href')
                m = re.search(r'codmie=(\d+)', href)
                if m and m.group(1) not in seen_codmies:
                    seen_codmies.add(m.group(1))
                    name = l.get_text().strip()
                    all_diputados.append({
                        "id": f"AND-{legis}-{m.group(1)}",
                        "nombre": name,
                        "grupo": "Unknown", # To be filled by PDF parser
                        "codmie": m.group(1),
                        "nlegis": legis,
                        "foto": None
                    })
            continue

        for art in articles:
            link = art.find('a', href=re.compile(r'codmie='))
            if not link: continue
            
            name = link.get_text().strip()
            href = link.get('href')
            
            codmie_match = re.search(r'codmie=(\d+)', href)
            if not codmie_match: continue
            codmie = codmie_match.group(1)
            
            img_tag = art.find('img')
            img_url = None
            if img_tag:
                src = img_tag.get('src')
                if src:
                    img_url = urljoin(url, src)
            
            all_diputados.append({
                "id": f"AND-{legis}-{codmie}",
                "nombre": name,
                "grupo": "Unknown", 
                "codmie": codmie,
                "nlegis": legis,
                "foto": img_url
            })
            
    return all_diputados

if __name__ == "__main__":
    os.makedirs("data/andalucia", exist_ok=True)
    diputados = scrape_andalucia_all_diputados()
    print(f"Found {len(diputados)} total historical diputados")
    with open("data/andalucia/diputados_raw.json", "w") as f:
        json.dump(diputados, f, indent=2, ensure_ascii=False)

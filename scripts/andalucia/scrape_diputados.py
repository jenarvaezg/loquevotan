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
        
        # Find all card tags or links
        links = soup.find_all('a', href=re.compile(r'codmie='))
        seen_codmies = set()
        for link in links:
            href = link.get('href')
            codmie_match = re.search(r'codmie=(\d+)', href)
            if not codmie_match: continue
            codmie = codmie_match.group(1)
            
            if codmie in seen_codmies:
                continue
            seen_codmies.add(codmie)
            
            name = link.get_text().strip()
            
            # Find the photo by looking at the parent containers
            img_url = None
            parent = link.parent
            while parent and parent.name != 'body':
                img_tag = parent.find('img')
                if img_tag and img_tag.get('src'):
                    img_url = urljoin(url, img_tag.get('src'))
                    break
                parent = parent.parent
            
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

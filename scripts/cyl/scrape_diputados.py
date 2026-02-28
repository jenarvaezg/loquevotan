import requests
from bs4 import BeautifulSoup
import json
import re
import os
from urllib.parse import urljoin

def scrape_cyl_diputados():
    base_url = "https://www.ccyl.es/Organizacion/PlenoAlfabetico"
    legislaturas = ["11", "10"]
    all_diputados = []
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for legis in legislaturas:
        print(f"--- Scraping CyL Diputados for Legislatura {legis} ---")
        url = f"{base_url}?Legislatura={legis}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # The deputies are in div.list-group-item
        items = soup.find_all('div', class_='list-group-item')
        
        for item in items:
            link = item.find('a', href=re.compile(r'CodigoPersona='))
            if not link: continue
            
            href = link.get('href')
            id_match = re.search(r'CodigoPersona=([A-Z0-9]+)', href)
            if not id_match: continue
            p_id = id_match.group(1)
            
            # Name extraction
            # Structure: Carlos Javier Amando <span class="..."><strong>Fernández Carriedo</strong></span>
            p_tag = item.find('p', class_='cc_org_Procurador')
            if p_tag:
                # Get the whole text, cleaning extra spaces
                name = " ".join(p_tag.get_text().strip().split())
            else:
                name = "Unknown"
                
            # Group extraction
            group_tag = item.find('span', class_='cc_org_ProcuradorGrupoParlamentario')
            group = group_tag.get_text().strip() if group_tag else "Unknown"
            
            # Province extraction
            prov_tag = item.find('span', class_='cc_org_ProcuradorGrupoProvincia')
            provincia = prov_tag.get_text().strip() if prov_tag else "Unknown"
            
            # Photo extraction
            img_tag = item.find('img', class_='img-responsive')
            photo = urljoin(url, img_tag.get('src')) if img_tag else None
            
            all_diputados.append({
                "id": f"CYL-{legis}-{p_id}",
                "nombre": name,
                "grupo": group,
                "provincia": provincia,
                "p_id": p_id,
                "nlegis": legis,
                "url": urljoin(url, href),
                "foto": photo
            })
            
    return all_diputados

if __name__ == "__main__":
    os.makedirs("data/cyl", exist_ok=True)
    diputados = scrape_cyl_diputados()
    print(f"Found {len(diputados)} total historical diputados for CyL")
    with open("data/cyl/diputados_raw.json", "w") as f:
        json.dump(diputados, f, indent=2, ensure_ascii=False)

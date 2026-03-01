import requests
from bs4 import BeautifulSoup
import json
import re
import os
from urllib.parse import urljoin

def scrape_catalunya_diputados():
    url = "https://www.parlament.cat/web/composicio/ple-parlament/index.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    print(f"Fetching deputies from {url}...")
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    diputados = []
    # Find all links to deputy files
    links = soup.find_all('a', href=re.compile(r'diputats-fitxa'))
    
    seen_ids = set()
    for link in links:
        name = link.get_text().strip()
        if not name: continue
        
        # Clean title like "M. H. Sr."
        name = re.sub(r'^(?:M\.\s*H\.\s*|I\.\s*|H\.\s*)?(?:Sr\.|Sra\.)\s*', '', name).strip()
        
        href = link.get('href')
        p_codi_match = re.search(r'p_codi=(\d+)', href)
        if not p_codi_match: continue
        p_codi = p_codi_match.group(1)
        
        if p_codi in seen_ids: continue
        seen_ids.add(p_codi)
        
        # Find group
        # The group is usually in a paragraph following the name or in the same listitem
        parent_li = link.find_parent('li')
        grupo = "Desconegut"
        if parent_li:
            paragraphs = parent_li.find_all('p')
            for p in paragraphs:
                txt = p.get_text().strip()
                if "Grup Parlamentari" in txt or "Grup Mixt" in txt:
                    grupo = txt
                    break
        
        # Find photo
        photo = None
        if parent_li:
            img = parent_li.find('img')
            if img:
                photo = urljoin(url, img.get('src'))
        
        diputados.append({
            "id": f"CAT-15-{p_codi}",
            "nombre": name,
            "grupo": grupo,
            "p_codi": p_codi,
            "nlegis": "15",
            "foto": photo,
            "provincia": "Barcelona" # Default, will refine if possible
        })
        
    return diputados

if __name__ == "__main__":
    deps = scrape_catalunya_diputados()
    print(f"Found {len(deps)} deputies")
    os.makedirs("data/catalunya", exist_ok=True)
    with open("data/catalunya/diputados_raw.json", "w") as f:
        json.dump(deps, f, indent=2, ensure_ascii=False)

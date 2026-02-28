import requests
from bs4 import BeautifulSoup
import json
import re
import time
from urllib.parse import urljoin

def enrich_cyl_diputados():
    with open("data/cyl/diputados_raw.json", "r") as f:
        diputados = json.load(f)
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for i, d in enumerate(diputados):
        if d["grupo"] != "Unknown": continue
        
        print(f"Enriching {d['nombre']} ({d['p_id']})...")
        try:
            response = requests.get(d["url"], headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for group in the profile
            group_tag = soup.find('a', href=re.compile(r'CodigoGrupoParlamentario='))
            if group_tag:
                d["grupo"] = group_tag.get_text().strip()
            
            # Find province
            prov_tag = soup.find(string=re.compile(r'Provincia:'))
            if prov_tag:
                d["provincia"] = prov_tag.parent.parent.get_text().replace('Provincia:', '').strip()
            
            # Find photo if missing
            if not d.get("foto"):
                # Try specific selector for CyL profile
                img_tag = soup.find('img', src=re.compile(r'/Content/img/procuradores/'))
                if not img_tag:
                    img_tag = soup.find('img', src=re.compile(r'Fotos/'))
                if img_tag:
                    d["foto"] = urljoin(d["url"], img_tag.get('src'))
            
            time.sleep(0.1)
        except Exception as e:
            print(f"  Error enriching {d['nombre']}: {e}")
            
        if (i+1) % 20 == 0:
            with open("data/cyl/diputados_raw.json", "w") as f:
                json.dump(diputados, f, indent=2, ensure_ascii=False)
                
    with open("data/cyl/diputados_raw.json", "w") as f:
        json.dump(diputados, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    enrich_cyl_diputados()

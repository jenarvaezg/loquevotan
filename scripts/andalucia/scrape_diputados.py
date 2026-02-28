import requests
from bs4 import BeautifulSoup
import json
import re

def scrape_diputados_andalucia():
    url = "https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento/composicionyfuncionamiento/diputadosysenadores.do"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    diputados = []
    
    # Looking for containers
    items = soup.find_all('div', class_='diputado') or soup.find_all('div', style=re.compile(r'float:\s*left'))
    
    # If no specific containers, try to find all links and go up
    if not items:
        links = soup.find_all('a', href=re.compile(r'codmie='))
        # Use parent of parent as container typically
        items = [l.find_parent('div') for l in links]

    for item in items:
        if not item: continue
        link = item.find('a', href=re.compile(r'codmie='))
        if not link: continue
        
        name = link.get_text().strip()
        href = link.get('href')
        
        codmie_match = re.search(r'codmie=(\d+)', href)
        nlegis_match = re.search(r'nlegis=(\d+)', href)
        
        if codmie_match:
            codmie = codmie_match.group(1)
            nlegis = nlegis_match.group(1) if nlegis_match else "12"
            
            # Find group
            text = item.get_text()
            group_match = re.search(r'\((.*?)\)|\[(.*?)\]', text)
            group = group_match.group(1) or group_match.group(2) if group_match else "Unknown"
            
            # Find photo
            img_tag = item.find('img')
            img_url = None
            if img_tag:
                src = img_tag.get('src')
                if src:
                    if src.startswith('http'):
                        img_url = src
                    else:
                        img_url = f"https://www.parlamentodeandalucia.es{src}"
            
            diputados.append({
                "id": f"AND-{nlegis}-{codmie}",
                "nombre": name,
                "grupo": group.strip(),
                "codmie": codmie,
                "nlegis": nlegis,
                "url": f"https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento/composicionyfuncionamiento/{href}",
                "foto": img_url
            })
            
    return diputados

if __name__ == "__main__":
    diputados = scrape_diputados_andalucia()
    print(f"Found {len(diputados)} diputados")
    os.makedirs("data/andalucia", exist_ok=True)
    with open("data/andalucia/diputados_raw.json", "w") as f:
        json.dump(diputados, f, indent=2, ensure_ascii=False)

import requests
from bs4 import BeautifulSoup
import json
import re
import os
from urllib.parse import urljoin

def scrape_madrid_diputados():
    # Attempt to reach the deputies page with realistic headers
    url = "https://www.asambleamadrid.es/composicion/diputados"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.asambleamadrid.es/"
    }
    
    print(f"Connecting to {url}...")
    try:
        session = requests.Session()
        # First request to get cookies
        r1 = session.get("https://www.asambleamadrid.es/", headers=headers, timeout=15)
        print(f"Home status: {r1.status_code}")
        
        # Now the deputies page
        response = session.get(url, headers=headers, timeout=15)
        print(f"Deputies page status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Failed to fetch. Body length: {len(response.text)}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Looking for deputy cards
        # Based on typical layouts, they might be in articles or divs with specific classes
        items = soup.find_all('div', class_=re.compile(r'diputado|card|item'))
        print(f"Found {len(items)} potential deputy items")
        
        diputados = []
        # If no items found, try to find all links with 'diputado' in URL
        if not items:
            links = soup.find_all('a', href=re.compile(r'/diputados/'))
            print(f"Found {len(links)} links with /diputados/")
            for link in links:
                href = link.get('href')
                name = link.get_text().strip()
                if name and len(name) > 5:
                    diputados.append({
                        "nombre": name,
                        "url": urljoin(url, href)
                    })
        
        return diputados
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    deps = scrape_madrid_diputados()
    print(f"Extracted {len(deps)} deputies")
    if deps:
        print(f"Sample: {deps[0]}")

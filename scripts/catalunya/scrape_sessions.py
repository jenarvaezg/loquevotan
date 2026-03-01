import requests
from bs4 import BeautifulSoup
import json
import re
import os
from urllib.parse import urljoin

def get_catalunya_session_links():
    base_url = "https://www.parlament.cat/web/documentacio/publicacions/diari-ple/index.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    all_sessions = []
    
    # We'll scrape the first 5 pages
    for page in range(1, 6):
        url = f"{base_url}?p_pagina={page}"
        print(f"Fetching sessions from {url}...")
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for PDF links
        # They look like <a href="/document/dspcp/442479389.pdf"> DSPC-P 080/15</a>
        rows = soup.find_all('tr')
        for row in rows:
            link = row.find('a', href=re.compile(r'/document/dspcp/'))
            if not link: continue
            
            href = link.get('href')
            text = link.get_text().strip()
            
            # Extract DS number from text like "DSPC-P 080/15"
            ds_match = re.search(r'(\d+)/(\d+)', text)
            if not ds_match: continue
            
            ds_num, legis = ds_match.groups()
            
            # Find date in cells
            cells = row.find_all('td')
            date_str = "Desconeguda"
            if len(cells) >= 3:
                date_str = cells[2].get_text().strip()
            
            # Find session info
            session_info = ""
            if len(cells) >= 2:
                session_info = cells[1].get_text().strip()

            all_sessions.append({
                "doc_id": ds_num,
                "legis_id": legis,
                "date": date_str,
                "session_info": session_info,
                "url": urljoin("https://www.parlament.cat", href)
            })
            
    return all_sessions

if __name__ == "__main__":
    os.makedirs("data/catalunya", exist_ok=True)
    sessions = get_catalunya_session_links()
    print(f"Found {len(sessions)} session documents for Catalonia")
    with open("data/catalunya/sessions_index.json", "w") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

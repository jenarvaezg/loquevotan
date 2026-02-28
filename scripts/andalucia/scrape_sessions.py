import requests
from bs4 import BeautifulSoup
import json
import re
import os
from urllib.parse import urljoin

def get_session_links():
    base_url = "https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento/composicionyfuncionamiento/resultadosvotaciones.do?seleccion=publicadosen&legislatura=12&desderango=&hastarango=&desdemes=&desdeanyo=&hastames=&hastaanyo=&terminos=&accion=Ver+Sentido+del+voto"
    
    sessions = []
    indices = [0, 15, 30, 45, 60] # Based on the 69 results found
    
    for indice in indices:
        url = f"{base_url}&indice={indice}"
        print(f"Fetching page with index {indice}...")
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Looking for links with tipodoc=diario
        links = soup.find_all('a', href=re.compile(r'tipodoc=diario'))
        
        for link in links:
            text = link.get_text().strip()
            href = link.get('href')
            full_url = urljoin(url, href)
            
            # Extract id
            id_match = re.search(r'id=(\d+)', href)
            if id_match:
                doc_id = id_match.group(1)
                
                # Extract session and document number from text
                session_match = re.search(r'sesión número (\d+)', text)
                doc_num_match = re.search(r'Documento número (\d+)', text)
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
                
                sessions.append({
                    "doc_id": doc_id,
                    "session": session_match.group(1) if session_match else "Unknown",
                    "doc_num": doc_num_match.group(1) if doc_num_match else "Unknown",
                    "date": date_match.group(1) if date_match else "Unknown",
                    "url": full_url
                })
            
    return sessions

if __name__ == "__main__":
    sessions = get_session_links()
    print(f"Found {len(sessions)} session documents")
    os.makedirs("data/andalucia/raw/pdf", exist_ok=True)
    with open("data/andalucia/sessions_index.json", "w") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

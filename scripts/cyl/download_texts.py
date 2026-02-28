import json
import os
import requests
import time
from bs4 import BeautifulSoup

def download_cyl_texts():
    with open("data/cyl/sessions_index.json", "r") as f:
        sessions = json.load(f)
    
    os.makedirs("data/cyl/raw/html", exist_ok=True)
    os.makedirs("data/cyl/raw/txt", exist_ok=True)
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Prioritize investiture and recent ones
    sessions.sort(key=lambda x: int(x['pub_num']) if x['pub_num'].isdigit() else 0)
    
    for session in sessions:
        legis = session['legis_id']
        pub_num = session['pub_num']
        doc_id = f"{legis}-{pub_num}"
        html_path = f"data/cyl/raw/html/{doc_id}.html"
        txt_path = f"data/cyl/raw/txt/{doc_id}.txt"
        
        if os.path.exists(txt_path):
            continue
            
        print(f"Downloading CyL Session {doc_id}...")
        try:
            response = requests.get(session['url'], headers=headers)
            if response.status_code == 200:
                with open(html_path, 'w') as f:
                    f.write(response.text)
                
                # Extract text
                soup = BeautifulSoup(response.text, 'html.parser')
                # Find the main text container
                # Based on my observation, it might be inside div.cc_pub_Texto
                text_container = soup.find('div', class_='cc_pub_Texto') or soup.find('body')
                if text_container:
                    with open(txt_path, 'w') as f:
                        f.write(text_container.get_text())
                
                print(f"  Saved {txt_path}")
            else:
                print(f"  Failed to download {doc_id}: Status {response.status_code}")
            
            time.sleep(0.2)
        except Exception as e:
            print(f"  Error downloading {doc_id}: {e}")

if __name__ == "__main__":
    download_cyl_texts()

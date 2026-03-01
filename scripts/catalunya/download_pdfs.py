import json
import os
import requests
import time

def download_catalunya_pdfs():
    with open("data/catalunya/sessions_index.json", "r") as f:
        sessions = json.load(f)
    
    os.makedirs("data/catalunya/raw/pdf", exist_ok=True)
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    downloaded = 0
    for session in sessions:
        # Only XV legislatura
        if session['legis_id'] != '15': continue
        
        doc_id = session['doc_id']
        url = session['url']
        filename = f"DS-{doc_id}.pdf"
        dest_path = os.path.join("data/catalunya/raw/pdf", filename)
        
        if os.path.exists(dest_path):
            continue
            
        print(f"Downloading {filename}...")
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(dest_path, 'wb') as f:
                    f.write(response.content)
                downloaded += 1
                time.sleep(0.5)
            else:
                print(f"  Failed to download {doc_id}: Status {response.status_code}")
        except Exception as e:
            print(f"  Error downloading {doc_id}: {e}")
            
    print(f"Successfully downloaded {downloaded} new PDF documents for Catalonia")

if __name__ == "__main__":
    download_catalunya_pdfs()

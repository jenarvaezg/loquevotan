import json
import os
import requests
import time

def download_madrid_pdfs():
    index_file = "data/madrid/sessions_index.json"
    if not os.path.exists(index_file):
        print(f"Error: {index_file} not found")
        return
        
    with open(index_file, "r") as f:
        sessions = json.load(f)
    
    os.makedirs("data/madrid/raw/pdf", exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    downloaded = 0
    for session in sessions:
        doc_id = session['id']
        url = session['url']
        filename = f"DS-{doc_id}.pdf"
        dest_path = os.path.join("data/madrid/raw/pdf", filename)
        
        if os.path.exists(dest_path):
            print(f"Skipping {filename}, already exists")
            continue
            
        print(f"Downloading {filename} from {url}...")
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(dest_path, 'wb') as f:
                    f.write(response.content)
                downloaded += 1
                print(f"  Saved {filename} ({len(response.content)} bytes)")
                time.sleep(1)
            else:
                print(f"  Failed to download {filename}: Status {response.status_code}")
        except Exception as e:
            print(f"  Error downloading {filename}: {e}")
            
    print(f"Successfully downloaded {downloaded} new PDF documents")

if __name__ == "__main__":
    download_madrid_pdfs()

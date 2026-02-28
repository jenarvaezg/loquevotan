import json
import os
import requests
import time

def download_pdfs():
    with open("data/andalucia/sessions_index.json", "r") as f:
        sessions = json.load(f)
    
    os.makedirs("data/andalucia/raw/pdf", exist_ok=True)
    
    for session in sessions:
        doc_id = session['doc_id']
        output_path = f"data/andalucia/raw/pdf/{doc_id}.pdf"
        
        if os.path.exists(output_path):
            print(f"Skipping {doc_id}, already exists")
            continue
            
        print(f"Downloading {doc_id} from {session['url']}...")
        try:
            response = requests.get(session['url'], stream=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Saved {output_path}")
            else:
                print(f"Failed to download {doc_id}: Status {response.status_code}")
            
            # Be nice to the server
            time.sleep(0.5)
        except Exception as e:
            print(f"Error downloading {doc_id}: {e}")

if __name__ == "__main__":
    download_pdfs()

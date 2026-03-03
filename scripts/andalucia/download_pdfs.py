import json
import os
import requests
import time
import argparse


def parse_legislaturas(value):
    if not value:
        return None
    return {v.strip() for v in str(value).split(",") if v.strip()}


def download_pdfs(legislaturas=None):
    with open("data/andalucia/sessions_index.json", "r") as f:
        sessions = json.load(f)
    
    os.makedirs("data/andalucia/raw/pdf", exist_ok=True)
    
    for session in sessions:
        if legislaturas and str(session.get("legis_id")) not in legislaturas:
            continue

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
    parser = argparse.ArgumentParser(description="Descarga PDFs de votaciones de Andalucía.")
    parser.add_argument(
        "--legislaturas",
        help="Lista de legislaturas separadas por coma (ej: 12,11).",
    )
    args = parser.parse_args()
    target_legs = parse_legislaturas(args.legislaturas)
    download_pdfs(target_legs)

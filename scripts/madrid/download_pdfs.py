import os
import requests
import time

def download_madrid_pdfs(legis="XIII", start_session=1, end_session=100):
    base_url = "https://www.asambleamadrid.es/static/doc/publicaciones/{}-DS-{}.pdf"
    output_dir = f"data/madrid/raw/pdf"
    os.makedirs(output_dir, exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"--- Downloading Madrid PDFs for Legislature {legis} ---")
    consecutive_errors = 0
    
    for session in range(start_session, end_session + 1):
        filename = f"{legis}-DS-{session}.pdf"
        output_path = os.path.join(output_dir, filename)
        
        if os.path.exists(output_path):
            print(f"Skipping {filename}, already exists")
            continue
            
        url = base_url.format(legis, session)
        print(f"Downloading session {session} from {url}...")
        
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=15)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"  Saved {filename} ({os.path.getsize(output_path)} bytes)")
                consecutive_errors = 0
            elif response.status_code == 404:
                print(f"  Session {session} not found (404). Stopping.")
                break
            else:
                print(f"  Error {response.status_code} for session {session}")
                consecutive_errors += 1
            
            # Be nice to the static server
            time.sleep(0.5)
            
            if consecutive_errors >= 3:
                print("Too many consecutive errors. Stopping.")
                break
                
        except Exception as e:
            print(f"  Error downloading session {session}: {e}")
            break

if __name__ == "__main__":
    # Let's test with the first 30 sessions of the current legislature
    download_madrid_pdfs(legis="XIII", start_session=1, end_session=30)

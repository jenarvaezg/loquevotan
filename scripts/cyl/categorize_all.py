import json
import os
import sys
import subprocess
import re

# Add root dir to path to import ai_utils
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import ai_utils

# Configuration
AMBITO = "cyl"
CACHE_FILE = "data/cyl/cache_categorias.json"
RAW_VOTES_FILES = [
    "data/cyl/votos_XI_raw.json",
    "data/cyl/votos_X_raw.json",
    "data/cyl/votos_IX_raw.json",
    "data/cyl/votos_VIII_raw.json",
    "data/cyl/votos_VII_raw.json"
]
PROMPT_FILE = "scripts/prompt_categorizacion.txt"

def main():
    if not os.path.exists(CACHE_FILE):
        cache = {}
    else:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)

    # 1. Collect all unique titles that need categorization
    titles_to_process = []
    seen_titles = set()

    for file_path in RAW_VOTES_FILES:
        if not os.path.exists(file_path):
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            votes = json.load(f)
            for v in votes:
                title = v["titulo"]
                # Skip already cached with valid results
                if title in cache and cache[title].get("titulo_ciudadano") != "Asunto parlamentario sin clasificar":
                    continue
                if title in seen_titles:
                    continue
                if title in ["Votación nominal", "Votación ordinaria", ""]:
                    continue
                
                seen_titles.add(title)
                titles_to_process.append((title, title))

    if not titles_to_process:
        print("No new titles to categorize for CyL.")
        return

    print(f"Total unique titles to categorize for CyL: {len(titles_to_process)}")

    with open(PROMPT_FILE, "r") as f:
        prompt_text = f.read()

    # 2. Process in batches using gemini-cli
    BATCH_SIZE = 25 # Smaller batch for stability
    
    for i in range(0, len(titles_to_process), BATCH_SIZE):
        batch = titles_to_process[i:i+BATCH_SIZE]
        print(f"Processing batch {i//BATCH_SIZE + 1}/{(len(titles_to_process)-1)//BATCH_SIZE + 1} ({len(batch)} titles)...")
        
        results = ai_utils._categorize_batch_cli(batch, prompt_text)
        
        # Update cache and save periodically
        cache.update(results)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        
        print(f"  Done. Total cached: {len(cache)}")

    print("Categorization complete.")

if __name__ == "__main__":
    main()

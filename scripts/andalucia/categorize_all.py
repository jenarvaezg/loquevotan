import json
import os
import sys
from google import genai
from google.genai import types

# Add root dir to path to import ai_utils
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import ai_utils

AMBITO = "andalucia"
CACHE_FILE = f"data/{AMBITO}/cache_categorias.json"
RAW_DIR = f"data/{AMBITO}"
PROMPT_FILE = "scripts/prompt_categorizacion.txt"
LEGISLATURAS = ["XII", "XI", "X", "IX"]

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY no configurada.")
        return

    # 1. Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    print(f"Caché cargada con {len(cache)} entradas.")

    # 2. Collect all unique titles from raw votes
    all_titles = set()
    for leg in LEGISLATURAS:
        raw_file = f"{RAW_DIR}/votos_{leg}_raw.json"
        if os.path.exists(raw_file):
            print(f"Cargando títulos de {raw_file}...")
            with open(raw_file, "r") as f:
                votes = json.load(f)
                for v in votes:
                    all_titles.add(v["titulo"])

    # 3. Filter titles needing categorization
    to_categorize = []
    for title in all_titles:
        entry = cache.get(title)
        if not entry or entry.get("titulo_ciudadano") == "Asunto parlamentario sin clasificar":
            to_categorize.append((title, title))

    if not to_categorize:
        print("No hay nuevos títulos por categorizar.")
        return

    print(f"Se van a categorizar {len(to_categorize)} títulos...")

    # 4. Batch categorize
    with open(PROMPT_FILE, "r") as f:
        prompt_text = f.read()

    BATCH_SIZE = 30
    total_new = 0
    
    try:
        for i in range(0, len(to_categorize), BATCH_SIZE):
            batch = to_categorize[i:i+BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(to_categorize) - 1) // BATCH_SIZE + 1
            print(f"Procesando lote {batch_num}/{total_batches} ({len(batch)} textos)...")
            
            results = ai_utils.categorize_batch(batch, api_key, prompt_text)
            
            # Update cache
            for original_title, data in results.items():
                cache[original_title] = data
                total_new += 1
            
            # Save cache after each batch
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
                
            print(f"  Lote {batch_num} completado y guardado.")
            
    except Exception as e:
        print(f"Error durante el procesamiento: {e}")
    finally:
        print(f"Proceso finalizado. Total categorizados: {total_new}")

if __name__ == "__main__":
    main()

import json
import os

def populate_cache_all():
    legislaturas = ["XII", "XI", "X", "IX"]
    unique_titles = set()
    
    for leg in legislaturas:
        raw_file = f"data/andalucia/votos_{leg}_raw.json"
        if os.path.exists(raw_file):
            with open(raw_file, "r") as f:
                votes = json.load(f)
                for v in votes:
                    if v["titulo"] and v["titulo"] != "Votación sin título":
                        unique_titles.add(v["titulo"])
    
    print(f"Total unique titles found: {len(unique_titles)}")
    
    cache_file = "data/andalucia/cache_categorias.json"
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cache = json.load(f)
            
    for t in unique_titles:
        if t not in cache:
            cache[t] = {
                "categoria": "Otros",
                "etiquetas": ["andalucia"],
                "resumen": "Votación en el Parlamento de Andalucía",
                "titulo_ciudadano": t[:150]
            }
            
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    
    print(f"Cache updated with {len(cache)} entries")

if __name__ == "__main__":
    populate_cache_all()

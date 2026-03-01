import json
import os

TAGS_TO_REMOVE = {"cyl", "andalucia", "madrid", "nacional"}

def cleanup_json_file(file_path):
    if not os.path.exists(file_path):
        return
    
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error reading {file_path}")
            return

    modified = False
    
    # Handle cache_categorias.json structure
    if isinstance(data, dict):
        for key, entry in data.items():
            if isinstance(entry, dict) and "etiquetas" in entry:
                old_len = len(entry["etiquetas"])
                entry["etiquetas"] = [t for t in entry["etiquetas"] if t.lower() not in TAGS_TO_REMOVE]
                if len(entry["etiquetas"]) != old_len:
                    modified = True
    
    # Handle manifest_home.json and votaciones_meta.json structure
    # They have "latestVotes", "tightVotes", "featuredVotes" or "votaciones" list
    if isinstance(data, dict):
        # manifest_home
        for list_key in ["latestVotes", "tightVotes", "featuredVotes"]:
            if list_key in data:
                for v in data[list_key]:
                    if "etiquetas" in v:
                        old_len = len(v["etiquetas"])
                        v["etiquetas"] = [t for t in v["etiquetas"] if t.lower() not in TAGS_TO_REMOVE]
                        if len(v["etiquetas"]) != old_len:
                            modified = True
        
        # votaciones_meta
        if "votaciones" in data:
            for v in data["votaciones"]:
                if "etiquetas" in v:
                    old_len = len(v["etiquetas"])
                    v["etiquetas"] = [t for t in v["etiquetas"] if t.lower() not in TAGS_TO_REMOVE]
                    if len(v["etiquetas"]) != old_len:
                        modified = True

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Cleaned tags in {file_path}")

def main():
    # Cache files
    cleanup_json_file("data/cache_categorias.json")
    cleanup_json_file("data/andalucia/cache_categorias.json")
    cleanup_json_file("data/cyl/cache_categorias.json")
    cleanup_json_file("data/madrid/cache_categorias.json")
    
    # Public files (will be overwritten by transform but just in case)
    paths = [
        "public/data/manifest_home.json",
        "public/data/andalucia/manifest_home.json",
        "public/data/cyl/manifest_home.json",
        "public/data/votaciones_meta.json",
        "public/data/andalucia/votaciones_meta.json",
        "public/data/cyl/votaciones_meta.json"
    ]
    for p in paths:
        cleanup_json_file(p)

if __name__ == "__main__":
    main()

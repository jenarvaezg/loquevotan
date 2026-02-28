import json
import os

def build_global_index():
    public_data_dir = "public/data"
    ambitos_file = os.path.join(public_data_dir, "ambitos.json")
    
    if not os.path.exists(ambitos_file):
        print("No ambitos.json found.")
        return
        
    with open(ambitos_file, "r", encoding="utf-8") as f:
        ambitos = json.load(f).get("ambitos", [])
        
    global_index = {} # deputy_name -> [scope_ids]
    
    for ambito in ambitos:
        scope_id = ambito["id"]
        meta_path = os.path.join(public_data_dir, scope_id if scope_id != "nacional" else "", "votaciones_meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                for dip in meta.get("diputados", []):
                    if dip not in global_index:
                        global_index[dip] = []
                    global_index[dip].append(scope_id)
                    
    out_file = os.path.join(public_data_dir, "global_diputados.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(global_index, f, ensure_ascii=False, separators=(',', ':'))
        
    print(f"Generated global_diputados.json with {len(global_index)} unique deputies.")

if __name__ == "__main__":
    build_global_index()
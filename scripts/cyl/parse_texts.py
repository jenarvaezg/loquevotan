import json
import re
import os
import glob
import unicodedata

def normalize_text(text):
    if not text:
        return ""
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.lower()
    text = re.sub(r'[^a-z0-9 ]', '', text)
    return " ".join(text.split())

def parse_cyl_session(file_path, diputados_map, session_info):
    with open(file_path, 'r') as f:
        text = f.read()
        
    votes = []
    
    # Simple approach for Proof of Concept: focus on NOMINAL calls first
    calls = list(re.finditer(r'Votación [A-Z0-9/]+\s+.*?llamamiento', text, re.DOTALL | re.IGNORECASE))
    
    for i, match in enumerate(calls):
        start_idx = match.start()
        next_call = calls[i+1].start() if i+1 < len(calls) else len(text)
        end_match = re.search(r'El resultado de la votación es el siguiente', text[start_idx:], re.IGNORECASE)
        end_idx = start_idx + end_match.end() + 500 if end_match else next_call
        
        content = text[start_idx:end_idx]
        
        results = {
            "id": f"CYL-{session_info['legis_id']}-{session_info['pub_num']}-{i+1}",
            "fecha": session_info['date'],
            "titulo": session_info.get('title', 'Votación nominal'),
            "votos": [],
            "tipo": "nominal"
        }
        
        # Search for patterns like "EL SEÑOR ...:\nSí."
        # Using a more robust regex for names and votes
        vote_matches = re.finditer(r'(?:EL SEÑOR|LA SEÑORA)\s+([A-Z\sÁÉÍÓÚÑ\-]+):\s*\n\s*(Sí|No|Abstención)\.', content, re.IGNORECASE)
        
        found_any = False
        for v_m in vote_matches:
            found_any = True
            raw_name = v_m.group(1).strip()
            sense = v_m.group(2).strip().lower()
            
            norm_name = normalize_text(raw_name)
            found_deputy = None
            
            for d_norm, d_data in diputados_map.items():
                if d_norm in norm_name or norm_name in d_norm:
                    if d_data["nlegis"] == session_info['legis_id']:
                        found_deputy = d_data
                        break
            
            if found_deputy:
                results["votos"].append({
                    "diputado": found_deputy["nombre"],
                    "diputadoId": found_deputy["id"],
                    "grupo": found_deputy["grupo"],
                    "voto": sense
                })
            else:
                results["votos"].append({
                    "diputado": raw_name,
                    "diputadoId": f"CYL-UNK-{normalize_text(raw_name)[:10]}",
                    "grupo": "Unknown",
                    "voto": sense
                })
        
        if found_any:
            votes.append(results)
        
    return votes

def main():
    with open("data/cyl/diputados_raw.json", "r") as f:
        diputados_list = json.load(f)
    
    diputados_map = {normalize_text(d["nombre"]): d for d in diputados_list}
    
    with open("data/cyl/sessions_index.json", "r") as f:
        sessions = json.load(f)
        sessions_map = {f"{s['legis_id']}-{s['pub_num']}": s for s in sessions}
        
    all_votes = []
    txt_files = glob.glob("data/cyl/raw/txt/*.txt")
    
    for txt_path in sorted(txt_files):
        doc_id = os.path.basename(txt_path).replace('.txt', '')
        session_info = sessions_map.get(doc_id)
        if not session_info: continue
        
        print(f"Parsing {txt_path}...")
        try:
            votes = parse_cyl_session(txt_path, diputados_map, session_info)
            if votes:
                all_votes.extend(votes)
                print(f"  Found {len(votes)} nominal votes")
        except Exception as e:
            print(f"  Error parsing {txt_path}: {e}")
            
    os.makedirs("data/cyl", exist_ok=True)
    for legis in ["11", "10"]:
        leg_votes = [v for v in all_votes if v["id"].startswith(f"CYL-{legis}")]
        roman = "XI" if legis == "11" else "X"
        with open(f"data/cyl/votos_{roman}_raw.json", "w") as f:
            json.dump(leg_votes, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()

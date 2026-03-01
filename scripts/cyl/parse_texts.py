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

def clean_group(group):
    if not group: return "Unknown"
    g = group.lower()
    if "popular" in g: return "PP"
    if "socialista" in g: return "PSOE"
    if "vox" in g: return "VOX"
    if "upl" in g: return "UPL-SY"
    if "ciudadanos" in g: return "CS"
    if "podemos" in g: return "PODEMOS"
    if "mixto" in g: return "Mixto"
    if "adscrito" in g: return "No Adscrito"
    return group

def parse_cyl_session(file_path, diputados_map, session_info):
    with open(file_path, 'r') as f:
        text = f.read()
    
    # Pre-clean text from HTML noise
    text = text.replace('&nbsp;', ' ').replace('&nbsp', ' ')
    text = text.replace('**', '')
    # Remove excessive empty lines
    text = re.sub(r'\n\s*\n', '\n\n', text)
        
    votes = []
    
    # Simple approach for Proof of Concept: focus on NOMINAL calls first
    calls = list(re.finditer(r'(?:Votación|Votaciones)\s+.*?(?:llamamiento|sorteo)', text, re.DOTALL | re.IGNORECASE))
    
    for i, match in enumerate(calls):
        start_idx = match.start()
        # Search for title in a larger context before the vote (3000 chars)
        pre_text = text[max(0, start_idx-3000):start_idx]
        
        # Look for the sentence that describes the vote
        # Pattern: Someter a votación [X]
        title = "Votación nominal"
        # Try to find the most specific description
        # 1. Look for "somete a votación"
        title_match = re.search(r'somete a votación\s+(.*?)(?:\.|\n\n|\s{3,}|\[)', pre_text, re.DOTALL | re.IGNORECASE)
        if not title_match:
            # 2. Look for "proceder a la votación"
            title_match = re.search(r'proceder\s+.*?votación\s+(?:de|a|para)\s+(.*?)(?:\.|\n\n|\s{3,}|\[)', pre_text, re.DOTALL | re.IGNORECASE)
            
        if title_match:
            candidate = title_match.group(1).strip()
            # Remove common lead-ins
            candidate = re.sub(r'^(?:la|el|los|las|de|del|a|en)\s+', '', candidate, flags=re.IGNORECASE)
            # Remove trailing fragments
            candidate = re.sub(r'\s+en\s+los\s+términos.*$', '', candidate, flags=re.IGNORECASE)
            title = candidate.strip()
        else:
            # Fallback to session title but shorten it if it's too long
            s_title = session_info.get('title', 'Votación nominal')
            if len(s_title) > 100:
                # Try to take only the first point if it's a list
                s_title = s_title.split('--')[0].split(';')[0].strip()
            title = s_title
        
        # Ensure title is not empty
        if not title: title = "Votación nominal"
        # Capitalize first letter
        title = title[0].upper() + title[1:] if title else "Votación nominal"
        
        next_call = calls[i+1].start() if i+1 < len(calls) else len(text)
        end_match = re.search(r'El resultado de la votación es el siguiente', text[start_idx:], re.IGNORECASE)
        end_idx = start_idx + end_match.end() + 1000 if end_match else next_call
        
        content = text[start_idx:end_idx]
        
        results = {
            "id": f"CYL-{session_info['legis_id']}-{session_info['pub_num']}-{i+1}",
            "fecha": session_info['date'],
            "titulo": title[:200],
            "votos": [],
            "tipo": "nominal"
        }
        
        # Search for patterns like "EL SEÑOR ...:\nSí."
        # The name might include hyphens or spaces
        vote_matches = re.finditer(r'(?:EL SEÑOR|LA SEÑORA)\s+([A-Z\sÁÉÍÓÚÑ\-]+):\s*\n\s*(Sí|No|Abstención)\.', content, re.IGNORECASE)
        
        found_any = False
        for v_m in vote_matches:
            found_any = True
            raw_name = v_m.group(1).strip()
            sense = v_m.group(2).strip().lower()
            
            norm_name = normalize_text(raw_name)
            found_deputy = None
            
            # Fuzzy match in diputados_map
            for d_norm, d_data in diputados_map.items():
                if d_norm in norm_name or norm_name in d_norm:
                    if d_data["nlegis"] == session_info['legis_id']:
                        found_deputy = d_data
                        break
            
            if found_deputy:
                results["votos"].append({
                    "diputado": found_deputy["nombre"],
                    "diputadoId": found_deputy["id"],
                    "grupo": clean_group(found_deputy["grupo"]),
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
    for legis in ["11", "10", "9", "8", "7"]:
        leg_votes = [v for v in all_votes if v["id"].startswith(f"CYL-{legis}")]
        roman_map = {"11": "XI", "10": "X", "9": "IX", "8": "VIII", "7": "VII"}
        roman = roman_map.get(legis, legis)
        with open(f"data/cyl/votos_{roman}_raw.json", "w") as f:
            json.dump(leg_votes, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()

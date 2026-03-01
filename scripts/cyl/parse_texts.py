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

def spanish_to_int(text):
    if not text: return 0
    text = text.lower().strip()
    # Handle direct numbers
    if text.isdigit(): return int(text)
    
    units = {
        "cero": 0, "un": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
        "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciséis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
        "veintiuno": 21, "veintidós": 22, "veintitrés": 23, "veinticuatro": 24, "veinticinco": 25, "veintiséis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
        "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
        "una": 1, "ninguna": 0, "ninguno": 0
    }
    if text in units: return units[text]
    
    parts = text.split(" y ")
    if len(parts) == 2:
        return units.get(parts[0], 0) + units.get(parts[1], 0)
    
    return 0

def parse_cyl_session(file_path, diputados_by_leg, session_info):
    with open(file_path, 'r') as f:
        text = f.read()
    
    # Pre-clean text from HTML noise
    text = text.replace('&nbsp;', ' ').replace('&nbsp', ' ')
    text = text.replace('**', '')
    text = re.sub(r'\n\s*\n', '\n\n', text)
        
    leg_id = session_info['legis_id']
    all_votations = []
    
    # 1. Look for NOMINAL votes (llamamiento)
    calls = list(re.finditer(r'(?:Votación|Votaciones)\s+.*?(?:llamamiento|sorteo)', text, re.DOTALL | re.IGNORECASE))
    
    for i, match in enumerate(calls):
        start_idx = match.start()
        pre_text = text[max(0, start_idx-2000):start_idx]
        
        title = "Votación nominal"
        title_match = re.search(r'(?:somete a votación|proceder\s+.*?votación\s+(?:de|a|para))\s+(.*?)(?:\.|\n\n|\s{3,}|\[)', pre_text, re.DOTALL | re.IGNORECASE)
        if title_match:
            candidate = title_match.group(1).strip()
            candidate = re.sub(r'^(?:la|el|los|las|de|del|a|en)\s+', '', candidate, flags=re.IGNORECASE)
            title = candidate[0].upper() + candidate[1:]
        
        content_after = text[start_idx:start_idx+15000] # Large enough for names
        end_match = re.search(r'El resultado de la votación es el siguiente', content_after, re.IGNORECASE)
        end_idx = end_match.end() + 1000 if end_match else 5000
        content = content_after[:end_idx]
        
        results = {
            "id": f"CYL-{leg_id}-{session_info['pub_num']}-NOM-{i+1}",
            "fecha": session_info['date'],
            "titulo": title[:200],
            "votos": [],
            "tipo": "nominal"
        }
        
        vote_matches = re.finditer(r'(?:EL SEÑOR|LA SEÑORA)\s+([A-Z\sÁÉÍÓÚÑ\-]+):\s*\n\s*(Sí|No|Abstención)\.', content, re.IGNORECASE)
        found_any = False
        for v_m in vote_matches:
            found_any = True
            raw_name = v_m.group(1).strip()
            sense = v_m.group(2).strip().lower()
            norm_name = normalize_text(raw_name)
            
            found_deputy = None
            for d in diputados_by_leg.get(leg_id, []):
                if normalize_text(d["nombre"]) == norm_name or norm_name in normalize_text(d["nombre"]):
                    found_deputy = d
                    break
            
            results["votos"].append({
                "diputado": found_deputy["nombre"] if found_deputy else raw_name,
                "diputadoId": found_deputy["id"] if found_deputy else f"CYL-UNK-{normalize_text(raw_name)[:10]}",
                "grupo": clean_group(found_deputy["grupo"]) if found_deputy else "Unknown",
                "voto": "si" if sense == "sí" else sense
            })
        
        if found_any:
            all_votations.append(results)

    # 2. Look for ORDINARY votes with totals
    # Pattern: Votos emitidos: [X]. A favor: [Y]. En contra: [Z]. [Abstención: [W]]
    results_pattern = r'Votos emitidos:\s*(.*?)\.\s*A favor:\s*(.*?)\.(?:\s*En contra:\s*(.*?)\.)?(?:\s*Abstención:\s*(.*?)\.)?'
    res_matches = list(re.finditer(results_pattern, text, re.IGNORECASE))
    
    for i, match in enumerate(res_matches):
        start_idx = match.start()
        # Find the context/title BEFORE the results
        pre_context = text[max(0, start_idx-1500):start_idx]
        
        # Look for IDs like PNL/000089 or M/000003
        id_match = re.search(r'([A-Z]+/\d+)', pre_context)
        ref_id = id_match.group(1) if id_match else f"ORD-{i+1}"
        
        # Look for proponente
        proponente = ""
        prop_match = re.search(r'presentada por el (Grupo Parlamentario [^,]+)', pre_context, re.I)
        if prop_match:
            proponente = clean_group(prop_match.group(1))
            
        # Look for title
        title = "Votación ordinaria"
        title_match = re.search(r'(?:votamos|votación)\s+.*?\s+(?:la|el|los|las)\s+(.*?)(?:\.|admitida|publicada|consecuencia|\n\n)', pre_context, re.DOTALL | re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            title = title[0].upper() + title[1:]
        
        v_emit = spanish_to_int(match.group(1))
        v_favor = spanish_to_int(match.group(2))
        v_contra = spanish_to_int(match.group(3)) if match.group(3) else 0
        v_abst = spanish_to_int(match.group(4)) if match.group(4) else 0
        
        # If we have no numbers, skip
        if v_emit == 0 and v_favor == 0: continue
        
        # Check if already added via nominal (approx check)
        if any(v["fecha"] == session_info['date'] and abs(len(v["votos"]) - v_emit) < 2 for v in all_votations if v["tipo"] == "nominal"):
            continue

        results = {
            "id": f"CYL-{leg_id}-{session_info['pub_num']}-{ref_id.replace('/', '-')}",
            "fecha": session_info['date'],
            "titulo": title[:200],
            "votos": [],
            "tipo": "ordinaria",
            "totales": {"favor": v_favor, "contra": v_contra, "abstencion": v_abst, "total": v_emit},
            "proponente": proponente
        }
        
        # UNANIMOUS DEDUCTION: If A Favor == Votos Emitidos
        if v_favor == v_emit and v_emit > 0:
            for d in diputados_by_leg.get(leg_id, []):
                results["votos"].append({
                    "diputado": d["nombre"],
                    "diputadoId": d["id"],
                    "grupo": clean_group(d["grupo"]),
                    "voto": "si"
                })
            results["metadatos"] = {"tipo": "deduccion_grupal", "nota": "Voto unánime deducido por el resultado de la cámara."}
        
        all_votations.append(results)
        
    return all_votations

def main():
    with open("data/cyl/diputados_raw.json", "r") as f:
        diputados_list = json.load(f)
    
    diputados_by_leg = {}
    for d in diputados_list:
        leg = d["nlegis"]
        if leg not in diputados_by_leg: diputados_by_leg[leg] = []
        diputados_by_leg[leg].append(d)
    
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
            votes = parse_cyl_session(txt_path, diputados_by_leg, session_info)
            if votes:
                all_votes.extend(votes)
                print(f"  Found {len(votes)} votations")
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

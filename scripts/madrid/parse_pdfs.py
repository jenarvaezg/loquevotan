import pdfplumber
import json
import re
import os
import glob
import unicodedata
import itertools

LEGISLATURAS_GROUPS = {
    "XIII": {"PP": 70, "Más Madrid": 27, "PSOE-M": 27, "Vox": 11},
    "XII": {"PP": 65, "Más Madrid": 24, "PSOE-M": 24, "Vox": 13, "Unidas Podemos": 10},
    "XI": {"PSOE-M": 37, "PP": 30, "Ciudadanos": 26, "Más Madrid": 20, "Vox": 12, "Unidas Podemos": 7},
    "X": {"PP": 48, "PSOE-M": 37, "Podemos": 27, "Ciudadanos": 17}
}

def guess_group_votes(v_si, v_no, v_abs, group_sizes):
    options = ["si", "no", "abstencion"]
    best_combo = None
    min_dist = 999999
    
    group_names = list(group_sizes.keys())
    
    for combo in itertools.product(options, repeat=len(group_names)):
        theo_si = 0
        theo_no = 0
        theo_abs = 0
        for i, vote in enumerate(combo):
            size = group_sizes[group_names[i]]
            if vote == "si": theo_si += size
            elif vote == "no": theo_no += size
            elif vote == "abstencion": theo_abs += size
            
        dist = abs(theo_si - v_si) + abs(theo_no - v_no) + abs(theo_abs - v_abs)
        if dist < min_dist:
            min_dist = dist
            best_combo = combo
            
    if best_combo is None:
        return {}
        
    return {group_names[i]: best_combo[i] for i in range(len(group_names))}

def spanish_to_int(text):
    if not text: return 0
    text = text.lower().strip()
    if text == "cero": return 0
    if text == "uno" or text == "una": return 1
    m = re.search(r'\d+', text)
    if m: return int(m.group(0))
    return 0

def normalize_text(text):
    if not text: return ""
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.lower().strip()

def parse_madrid_ds(file_path):
    print(f"Parsing {file_path}...")
    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join([p.extract_text() or "" for p in pdf.pages])
    except Exception as e:
        print(f"  Error opening PDF: {e}")
        return []

    # Extract legislature from filename
    filename = os.path.basename(file_path)
    leg = "XIII"
    if "DS-XIII-" in filename or filename.startswith("XIII-"): leg = "XIII"
    elif "DS-XII-" in filename or filename.startswith("XII-"): leg = "XII"
    elif "DS-XI-" in filename or filename.startswith("XI-"): leg = "XI"
    elif "DS-X-" in filename or filename.startswith("X-"): leg = "X"
    
    if leg not in LEGISLATURAS_GROUPS:
        return []

    votations = []
    
    res_pattern = r'(?:El\s+)?resultado\s+de\s+la\s+votación\s+es\s+(?:el\s+siguiente|de)?[:\s]*(\d+|[a-z]+)\s+votos\s+emitidos[:\s]*(\d+|[a-z]+)\s+síes?,\s*(\d+|[a-z]+)\s+noes?\s+y\s+(\d+|[a-z]+)\s+abstenciones?'
    
    matches = list(re.finditer(res_pattern, text, re.IGNORECASE))
    
    # Check date
    date_match = re.search(r'(\d{1,2})\s+DE\s+([A-Z]+)\s+DE\s+(\d{4})', text[:2000], re.I)
    month_map = {"ENERO": "01", "FEBRERO": "02", "MARZO": "03", "ABRIL": "04", "MAYO": "05", "JUNIO": "06", 
                 "JULIO": "07", "AGOSTO": "08", "SEPTIEMBRE": "09", "OCTUBRE": "10", "NOVIEMBRE": "11", "DICIEMBRE": "12"}
    date_str = "Unknown"
    if date_match:
        d, m, y = date_match.groups()
        date_str = f"{d.zfill(2)}/{month_map.get(m.upper(), '01')}/{y}"

    ds_num = filename.replace('.pdf', '')
    
    for i, match in enumerate(matches):
        start_idx = match.start()
        pre_context = text[max(0, start_idx-2500):start_idx]
        
        title = "Votación ordinaria"
        
        lines = pre_context.split('\n')
        for line in reversed(lines):
            if any(k in line.lower() for k in ['votamos', 'votar', 'votación', 'somete', 'vota']):
                m = re.search(r'(?:votando|votamos|votación|votar|somete a votación|sometemos a votación|vota)\s+(?:la|el|los|las|de)?\s*(.*)', line, re.I)
                if m:
                    title = m.group(1).strip()
                    break
        
        v_emit = spanish_to_int(match.group(1))
        v_si = spanish_to_int(match.group(2))
        v_no = spanish_to_int(match.group(3))
        v_abs = spanish_to_int(match.group(4))
        
        post_text = text[match.end():match.end()+200]
        remote_match = re.search(r'añadimos\s+(\d+|[a-z]+)\s+(?:votos|síes|noes)?\s*(?:a\s+distancia)?', post_text, re.I)
        if remote_match:
            n_remote = spanish_to_int(remote_match.group(1))
            if 'sí' in remote_match.group(0).lower() or 'votos' in remote_match.group(0).lower():
                v_si += n_remote
                v_emit += n_remote
            elif 'no' in remote_match.group(0).lower():
                v_no += n_remote
                v_emit += n_remote
                
        title = re.sub(r'^[,\s]+', '', title)
        title = title.split('.')[0].strip()
        
        group_votes = guess_group_votes(v_si, v_no, v_abs, LEGISLATURAS_GROUPS[leg])

        votations.append({
            "id": f"MAD-{leg}-{ds_num}-{i+1}",
            "fecha": date_str,
            "titulo": title,
            "votos": [],
            "group_votes": group_votes,
            "totales": {
                "favor": v_si,
                "contra": v_no,
                "abstencion": v_abs,
                "total": v_emit
            },
            "metadatos": {
                "tipo": "deduccion_grupal",
                "nota": "Sentido del voto deducido por el resultado de la cámara y disciplina de grupo (estimado)."
            }
        })
        
    return votations

def main():
    files = glob.glob("data/madrid/raw/pdf/*.pdf")
    
    # Parse all
    all_votes = []
    for f in files:
        votes = parse_madrid_ds(f)
        all_votes.extend(votes)
        
    # Group by legislature to write
    by_leg = {}
    for v in all_votes:
        leg = v["id"].split("-")[1] # e.g. MAD-XIII-DS-688-1 -> XIII
        if leg not in by_leg:
            by_leg[leg] = []
        by_leg[leg].append(v)
        
    for leg, votes in by_leg.items():
        votes.sort(key=lambda x: x["fecha"], reverse=True)
        file_path = f"data/madrid/votos_{leg}_raw.json"
        
        # Merge if exists
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                existing = json.load(f)
                merged = {v["id"]: v for v in existing}
                for v in votes:
                    merged[v["id"]] = v
                unique_votes = list(merged.values())
        else:
            unique_votes = votes
            
        with open(file_path, "w") as f:
            json.dump(unique_votes, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(unique_votes)} votes to {file_path}")

if __name__ == "__main__":
    main()

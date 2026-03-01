import pdfplumber
import json
import re
import os
import glob
import unicodedata

# Madrid Groups XIII Legislature
# Approximate seat counts for verification
GROUPS = {
    "PP": 70,
    "Más Madrid": 27,
    "PSOE-M": 27,
    "Vox": 11
}

def spanish_to_int(text):
    if not text: return 0
    text = text.lower().strip()
    if text == "cero": return 0
    if text == "uno" or text == "una": return 1
    # Check if it's a number
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

    votations = []
    
    # Pattern for Madrid Assembly voting results
    # Example: El resultado de la votación es de 129 votos emitidos: 52 síes, 66 noes y 11 abstenciones
    # Optional: le añadimos 3 votos a distancia
    res_pattern = r'(?:El\s+)?resultado\s+de\s+la\s+votación\s+es\s+(?:el\s+siguiente|de)?[:\s]*(\d+|[a-z]+)\s+votos\s+emitidos[:\s]*(\d+|[a-z]+)\s+síes?,\s*(\d+|[a-z]+)\s+noes?\s+y\s+(\d+|[a-z]+)\s+abstenciones?'
    
    matches = list(re.finditer(res_pattern, text, re.IGNORECASE))
    
    for i, match in enumerate(matches):
        start_idx = match.start()
        # Find context BEFORE the match to get the title
        pre_context = text[max(0, start_idx-1000):start_idx]
        
        # Look for the sentence that starts the voting
        # Example: Empezamos votando la Proposición No de Ley 141/24
        # Example: Ahora, votamos la Proposición No de Ley 18/25
        # Example: sometemos a votación la ratificación del convenio...
        title = "Votación ordinaria"
        title_match = re.search(r'(?:votando|votamos|votación|votar)\s+(?:la|el|los|las)?\s*(.*?)(?:\.|\s{2,}|\n|:)', pre_context.split('\n')[-1] + text[start_idx:start_idx+100], re.IGNORECASE)
        
        # Better title search: look back for keywords
        lines = pre_context.split('\n')
        for line in reversed(lines):
            if any(k in line.lower() for k in ['votamos', 'votar', 'votación', 'somete']):
                m = re.search(r'(?:votando|votamos|votación|votar|somete a votación)\s+(?:la|el|los|las|de)?\s*(.*)', line, re.I)
                if m:
                    title = m.group(1).strip()
                    break
        
        v_emit = spanish_to_int(match.group(1))
        v_si = spanish_to_int(match.group(2))
        v_no = spanish_to_int(match.group(3))
        v_abs = spanish_to_int(match.group(4))
        
        # Look for remote votes addition immediately after
        post_text = text[match.end():match.end()+200]
        remote_match = re.search(r'añadimos\s+(\d+|[a-z]+)\s+(?:votos|síes|noes)?\s*(?:a\s+distancia)?', post_text, re.I)
        if remote_match:
            n_remote = spanish_to_int(remote_match.group(1))
            # Usually they specify what kind of votes they add, but often they are 'síes'
            if 'sí' in remote_match.group(0).lower() or 'votos' in remote_match.group(0).lower():
                v_si += n_remote
                v_emit += n_remote
            elif 'no' in remote_match.group(0).lower():
                v_no += n_remote
                v_emit += n_remote
        
        # Extract date from first page header
        date_match = re.search(r'(\d{1,2})\s+DE\s+([A-Z]+)\s+DE\s+(\d{4})', text[:2000], re.I)
        month_map = {"ENERO": "01", "FEBRERO": "02", "MARZO": "03", "ABRIL": "04", "MAYO": "05", "JUNIO": "06", 
                     "JULIO": "07", "AGOSTO": "08", "SEPTIEMBRE": "09", "OCTUBRE": "10", "NOVIEMBRE": "11", "DICIEMBRE": "12"}
        date_str = "Unknown"
        if date_match:
            d, m, y = date_match.groups()
            date_str = f"{d.zfill(2)}/{month_map.get(m.upper(), '01')}/{y}"

        # Clean title
        title = re.sub(r'^[,\s]+', '', title)
        title = title.split('.')[0].strip()

        ds_num = os.path.basename(file_path).replace('DS-', '').replace('.pdf', '')
        
        votations.append({
            "id": f"MAD-XIII-{ds_num}-{i+1}",
            "fecha": date_str,
            "titulo": title,
            "votos": [], # We don't have individual votes, will deduct from group
            "group_votes": {
                "PP": "si" if v_si > GROUPS["PP"] else ("no" if v_no > GROUPS["PP"] else "si"), # Placeholder logic
                "Más Madrid": "no" if v_no > GROUPS["PP"] else "si", # Very placeholder, needs real logic
                "PSOE-M": "no" if v_no > GROUPS["PP"] else "si",
                "Vox": "si" if v_si > 100 else "no"
            },
            # Real result totals
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
    all_votes = []
    for f in files:
        votes = parse_madrid_ds(f)
        all_votes.extend(votes)
        
    # Merge with existing if any
    existing_file = "data/madrid/votos_XIII_raw.json"
    if os.path.exists(existing_file):
        with open(existing_file, "r") as f:
            existing = json.load(f)
            # Create map by ID to avoid duplicates
            merged = {v["id"]: v for v in existing}
            for v in all_votes:
                merged[v["id"]] = v
            unique_votes = list(merged.values())
    else:
        unique_votes = all_votes
            
    unique_votes.sort(key=lambda x: x["id"])
    
    # Heuristic fix for group votes: 
    # Madrid has 135 deputies. PP 70, MM 27, PSOE 27, Vox 11.
    # We can try to guess group votes if the sum matches perfectly.
    for v in unique_votes:
        t = v.get("totales")
        if not t: continue
        
        # Guess logic: if PP + Vox = Favor, then both Si.
        if t["favor"] == (70 + 11):
            v["group_votes"] = {"PP": "si", "Vox": "si", "Más Madrid": "no", "PSOE-M": "no"}
        elif t["favor"] == 70:
            v["group_votes"] = {"PP": "si", "Vox": "no", "Más Madrid": "no", "PSOE-M": "no"}
        elif t["favor"] > 70 and t["favor"] < 81:
            # Maybe some abstain
            v["group_votes"] = {"PP": "si", "Vox": "abstencion", "Más Madrid": "no", "PSOE-M": "no"}
        elif t["favor"] == 135:
            v["group_votes"] = {"PP": "si", "Vox": "si", "Más Madrid": "si", "PSOE-M": "si"}
        elif t["favor"] == 0:
            v["group_votes"] = {"PP": "no", "Vox": "no", "Más Madrid": "no", "PSOE-M": "no"}
            
    with open("data/madrid/votos_XIII_raw.json", "w") as f:
        json.dump(unique_votes, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(unique_votes)} votes to data/madrid/votos_XIII_raw.json")

if __name__ == "__main__":
    main()

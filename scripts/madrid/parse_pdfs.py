import pdfplumber
import json
import re
import os
import glob
import unicodedata
import io

# Madrid Groups Seat Counts for Heuristics
SEATS = {
    "XIII": {"PP": 70, "Más Madrid": 27, "PSOE-M": 27, "Vox": 11},
    "XII":  {"PP": 65, "Más Madrid": 24, "PSOE-M": 24, "Vox": 13},
    "XI":   {"PP": 30, "PSOE-M": 37, "Más Madrid": 20, "Ciudadanos": 26, "Vox": 12, "Podemos": 7},
    "X":    {"PP": 48, "PSOE-M": 37, "Podemos": 27, "Ciudadanos": 17}
}

def spanish_to_int(text):
    if not text: return 0
    text = text.lower().strip()
    if text in ["cero", "cap", "ninguna", "ninguno"]: return 0
    if text in ["uno", "una", "un"]: return 1
    if text == "dos": return 2
    if text == "tres": return 3
    if text == "diez": return 10
    m = re.search(r'\d+', text)
    if m: return int(m.group(0))
    return 0

def normalize_text(text):
    if not text: return ""
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.lower().strip()

def parse_madrid_ds(file_path, legis_id):
    print(f"Parsing {file_path} (Legis {legis_id})...")
    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join([p.extract_text() or "" for p in pdf.pages])
    except Exception as e:
        print(f"  Error opening PDF: {e}")
        return []

    # Clean artifacts
    text = text.replace('-\n', '')
    text = re.sub(r'[ \t]+', ' ', text)

    # 1. Locate the start of the voting section (usually near the end)
    vote_section_match = re.search(r'(?:proceder a realizar las votaciones|llamo a votación)', text, re.I)
    search_text = text[vote_section_match.start():] if vote_section_match else text

    # 2. Extract votations
    res_pattern = r'resultado\s+(?:de\s+la\s+)?votación\s+es\s+(?:el\s+siguiente|de)?[:\s]*' \
                  r'(?:(?P<emitidos>\d+|[a-z]+)\s+votos\s+emitidos[:\s]*)?' \
                  r'(?:(?P<si1>\d+|[a-z]+)\s+síes?|votos\s+afirmativos\s+(?P<si2>\d+|[a-z]+))' \
                  r'(?:,\s*| y )' \
                  r'(?:(?P<no1>\d+|[a-z]+)\s+noes?|votos\s+negativos\s+(?P<no2>\d+|[a-z]+))' \
                  r'(?:[,\s]*y\s*|[,\s]+)?' \
                  r'(?:abstenciones\s+(?P<abs2>\d+|[a-z]+)|(?P<abs1>\d+|[a-z]+)\s+abstenciones?)?'
    
    matches = list(re.finditer(res_pattern, search_text, re.IGNORECASE))
    
    votations = []
    last_end = 0
    for i, match in enumerate(matches):
        block_start = max(0, last_end)
        votation_block = search_text[block_start:match.start()]
        
        # 3. Extract Title
        title = "Votación desconocida"
        entity_patterns = [
            r'(?:Proposición No de Ley|PNL)\s+\d+/\d+',
            r'Proposición de Ley\s+\d+/\d+',
            r'Proyecto de Ley\s+\d+/\d+',
            r'enmienda(?:s)?\s+(?:número\s+)?[\d, y a]+',
            r'ratificación del convenio\s+.*',
            r'texto del proyecto de ley',
            r'dictamen de la Comisión.*',
            r'confianza de la Asamblea',
            r'investidura'
        ]
        
        all_found = []
        for p in entity_patterns:
            for m in re.finditer(p, votation_block, re.I):
                all_found.append((m.start(), m.group(0).strip()))
        
        if all_found:
            all_found.sort(key=lambda x: x[0])
            title = all_found[-1][1]
        else:
            lines = [l.strip() for l in votation_block.split('\n') if l.strip()]
            for line in reversed(lines):
                if any(k in line.lower() for k in ['votamos', 'votar', 'votación', 'somete a']):
                    m = re.search(r'(?:votamos|votar|votación|somete a votación)\s+(?:la|el|los|las|de)?\s*(.*)', line, re.I)
                    if m:
                        candidate = m.group(1).strip()
                        if len(candidate) > 5:
                            title = candidate
                            break
        
        # 4. Extract Votes
        d = match.groupdict()
        v_si = spanish_to_int(d['si1'] or d['si2'])
        v_no = spanish_to_int(d['no1'] or d['no2'])
        v_abs = spanish_to_int(d['abs1'] or d['abs2'] or '0')
        v_emit = spanish_to_int(d['emitidos']) if d['emitidos'] else (v_si + v_no + v_abs)
        
        # Special case for Investiture
        if "confianza" in title.lower() or "investidura" in title.lower():
            title = "Investidura"

        # 5. Telematic additions (immediately after result)
        post_text = search_text[match.end():match.end()+300]
        remote_matches = re.finditer(r'(\d+|un|una|dos|tres)\s*(?:votos?\s+)?(sí|no|abstención|abstencions)', post_text, re.I)
        for rm in remote_matches:
            val = spanish_to_int(rm.group(1))
            sense = rm.group(2).lower()
            if 'sí' in sense: v_si += val
            elif 'no' in sense: v_no += val
            elif 'abstenc' in sense: v_abs += val
        
        v_emit = max(v_emit, v_si + v_no + v_abs)

        # 6. Extract Date
        date_match = re.search(r'(\d{1,2})\s+DE\s+([A-Z]+)\s+DE\s+(\d{4})', text[:2000], re.I)
        month_map = {"ENERO": "01", "FEBRERO": "02", "MARZO": "03", "ABRIL": "04", "MAYO": "05", "JUNIO": "06", 
                     "JULIO": "07", "AGOSTO": "08", "SEPTIEMBRE": "09", "OCTUBRE": "10", "NOVIEMBRE": "11", "DICIEMBRE": "12"}
        date_str = "Unknown"
        if date_match:
            d_d, m, y = date_match.groups()
            date_str = f"{d_d.zfill(2)}/{month_map.get(m.upper(), '01')}/{y}"

        ds_num = os.path.basename(file_path).replace('DS-', '').replace('.pdf', '').split('-')[-1]
        
        # Cleanup title
        title = re.sub(r'^(?:la|el|los|las|de|del)\s+', '', title, flags=re.I)
        title = title[0].upper() + title[1:]
        title = re.sub(r'[.:;,]+$', '', title).strip()

        votations.append({
            "id": f"MAD-{legis_id}-{ds_num}-{i+1}",
            "fecha": date_str,
            "titulo": title[:300],
            "votos": [],
            "totales": {
                "favor": v_si,
                "contra": v_no,
                "abstencion": v_abs,
                "total": v_emit
            },
            "metadatos": {
                "tipo": "deduccion_grupal",
                "note": "Sentido del voto deduït pel resultat de la cambra i disciplina de grup (estimat)."
            }
        })
        last_end = match.end() + 100
        
    return votations

def main():
    files = glob.glob("data/madrid/raw/pdf/*.pdf")
    all_votes = []
    processed_ids = set()
    
    for f in sorted(files):
        filename = os.path.basename(f)
        parts = filename.split('-')
        legis = parts[1] if len(parts) >= 3 else "XIII"
        
        votes = parse_madrid_ds(f, legis)
        for v in votes:
            if v["id"] not in processed_ids:
                all_votes.append(v)
                processed_ids.add(v["id"])
                
    all_votes.sort(key=lambda x: x["id"])
    
    # Deduct group votes
    for v in all_votes:
        leg = v["id"].split("-")[1]
        t = v["totales"]
        seats = SEATS.get(leg, SEATS["XIII"])
        gv = {}
        
        if leg in ["XIII", "XII"]:
            if t["favor"] >= seats["PP"] + seats.get("Vox", 0) - 2:
                gv["PP"] = "si"; gv["Vox"] = "si"
            elif t["favor"] >= seats["PP"] - 2:
                gv["PP"] = "si"; gv["Vox"] = "no"
            
            opp_total = seats.get("Más Madrid", 0) + seats.get("PSOE-M", 0)
            if t["contra"] >= opp_total - 2:
                gv["Más Madrid"] = "no"; gv["PSOE-M"] = "no"
            elif t["favor"] >= opp_total + seats["PP"] - 5:
                gv["Más Madrid"] = "si"; gv["PSOE-M"] = "si"
        
        v["group_votes"] = gv

    # Save by legislature
    for leg in ["X", "XI", "XII", "XIII"]:
        leg_votes = [v for v in all_votes if v["id"].startswith(f"MAD-{leg}")]
        if leg_votes:
            with open(f"data/madrid/votos_{leg}_raw.json", "w") as f:
                json.dump(leg_votes, f, indent=2, ensure_ascii=False)
    
    print(f"Extraction complete. Processed {len(all_votes)} total votations for Madrid.")

if __name__ == "__main__":
    main()

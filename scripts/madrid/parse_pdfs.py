import pdfplumber
import json
import re
import os
import glob
import unicodedata
import io
from multiprocessing import Pool

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

def extract_descriptions(text):
    """Find all PNL/Bill definitions and their objects in the text."""
    desc_map = {}
    pnl_pattern = r'(?P<code>(?:PNL|PCOP|PNLP|PL|Proyecto de Ley|Proposición No de Ley|Moción|Propuesta de Resolución)\s*-?\s*(?P<num>\d+)/(?P<year>\d+)).*?(?:objeto|finalidad):\s*(?P<desc>.*?)(?:\.\s+[A-Z\d]{3,}|\n\n\n|\Z|DIARIO DE SESIONES|Pregunta n|Interpelación)'
    
    for m in re.finditer(pnl_pattern, text, re.IGNORECASE | re.DOTALL):
        num = m.group('num')
        year = m.group('year')
        short_year = year[-2:]
        key = f"{num}/{short_year}"
        desc = m.group('desc').strip()
        desc = re.sub(r'\s+', ' ', desc)
        desc = re.sub(r'\d+\s+DIARIO DE SESIONES.*?\d{4}', '', desc, flags=re.I)
        if len(desc) > 10:
            if key not in desc_map or len(desc) > len(desc_map[key]):
                desc_map[key] = desc
    return desc_map

def parse_one_file(file_path):
    print(f"Parsing {file_path}...")
    try:
        with pdfplumber.open(file_path) as pdf:
            first_page_text = pdf.pages[0].extract_text() or ""
            # Quick check for voting sections
            has_votes = False
            for page in pdf.pages:
                p_text = (page.extract_text() or "").lower()
                if "resultado" in p_text and ("votación" in p_text or "votos" in p_text):
                    has_votes = True
                    break
            if not has_votes: return []
            
            full_text = "\n".join([p.extract_text() or "" for p in pdf.pages])
    except Exception as e:
        print(f"  Error opening PDF {file_path}: {e}")
        return []

    legis_match = re.search(r'(X|XI|XII|XIII)\s+legislatura', first_page_text, re.I)
    legis_id = legis_match.group(1).upper() if legis_match else "XIII"
    ds_match = re.search(r'NÚM\.\s*(\d+)', first_page_text, re.I)
    ds_num = ds_match.group(1) if ds_match else os.path.basename(file_path).split('-')[-1].split('.')[0]

    full_text = full_text.replace('-\n', '')
    full_text = re.sub(r'[ \t]+', ' ', full_text)
    desc_map = extract_descriptions(full_text)

    # RE-DESIGNED Result Pattern (More robust)
    # We look for "resultado ... votación" and then capture favor/contra/abs in any order/naming
    res_pattern = r'resultado\s+(?:de\s+la\s+)?votación\s+es\s+.*?' \
                  r'(?:(?P<emitidos>\d+|[a-z]+)\s+(?:votos\s+emitidos|diputados\s+presentes))?.*?' \
                  r'(?:(?P<si>\d+|[a-z]+)\s+(?:síes|votos?\s+(?:a\s+favor|afirmativos)))' \
                  r'.*?' \
                  r'(?:(?P<no>\d+|[a-z]+)\s+(?:noes|votos?\s+(?:en\s+contra|negativos)))' \
                  r'(?:.*?(?P<abs>\d+|[a-z]+)\s+abstenciones?)?'
    
    matches = list(re.finditer(res_pattern, full_text, re.IGNORECASE | re.DOTALL))
    votations = []
    last_end = 0
    for i, match in enumerate(matches):
        # We need to ensure we don't grab context from miles away
        block_start = max(last_end, match.start() - 2000)
        votation_block = full_text[block_start:match.start()]
        
        num_match = re.search(r'(\d+)/(\d{2,4})', votation_block)
        key_found = f"{num_match.group(1)}/{num_match.group(2)[-2:]}" if num_match else None
        
        base_title = "Votación desconocida"
        entity_patterns = [
            r'(?P<full>(?:Proposición No de Ley|PNL|PCOP|PNLP|Proposición de Ley|Proyecto de Ley|PL|Moción|Propuesta de Resolución)\s*(?:-)?\s*(?P<num>\d+)/(?P<year>\d+))',
            r'enmienda(?:s)?\s+(?:número\s+)?[\d, y a]+',
            r'ratificación del convenio\s+.*',
            r'texto del proyecto de ley',
            r'dictamen de la Comisión.*',
            r'investidura'
        ]
        
        all_found = []
        for p in entity_patterns:
            for em in re.finditer(p, votation_block, re.I):
                all_found.append((em.start(), em.group(0).strip()))
        
        if all_found:
            all_found.sort(key=lambda x: x[0])
            base_title = all_found[-1][1]
        elif key_found:
            base_title = f"Votación {key_found}"
        else:
            lines = [l.strip() for l in votation_block.split('\n') if l.strip()]
            for line in reversed(lines):
                if any(k in line.lower() for k in ['votamos', 'votar', 'votación', 'pasamos a']):
                    m = re.search(r'(?:votamos|votar|votación|pasamos a|somete a)\s+(?:la|el|los|las|de)?\s*(.*)', line, re.I)
                    if m:
                        base_title = m.group(1).strip()
                        if len(base_title) > 5: break
        
        if key_found and key_found in desc_map:
            if len(base_title) < 40:
                base_title = f"{base_title}: {desc_map[key_found]}"
            elif key_found not in base_title:
                base_title = f"{base_title} ({key_found}): {desc_map[key_found]}"

        d = match.groupdict()
        v_si = spanish_to_int(d['si'])
        v_no = spanish_to_int(d['no'])
        v_abs = spanish_to_int(d['abs'] or '0')
        v_emit = spanish_to_int(d['emitidos']) if d['emitidos'] else (v_si + v_no + v_abs)
        
        if "investidura" in base_title.lower() or "confianza" in base_title.lower():
            base_title = "Investidura de la Presidenta de la Comunidad"

        # Special handling for telematic/distance votes often found after the block
        post_text = full_text[match.end():match.end()+300]
        remote_matches = re.finditer(r'(\d+|un|una|dos|tres)\s*(?:votos?\s+)?(sí|no|abstención|abstencions)', post_text, re.I)
        for rm in remote_matches:
            val = spanish_to_int(rm.group(1))
            sense = rm.group(2).lower()
            if 'sí' in sense: v_si += val
            elif 'no' in sense: v_no += val
            elif 'abstenc' in sense: v_abs += val
        
        v_emit = max(v_emit, v_si + v_no + v_abs)
        date_match = re.search(r'(\d{1,2})\s+DE\s+([A-Z]+)\s+DE\s+(\d{4})', full_text[:2000], re.I)
        date_str = "Unknown"
        if date_match:
            d_d, m, y = date_match.groups()
            month_map = {"ENERO": "01", "FEBRERO": "02", "MARZO": "03", "ABRIL": "04", "MAYO": "05", "JUNIO": "06", 
                         "JULIO": "07", "AGOSTO": "08", "SEPTIEMBRE": "09", "OCTUBRE": "10", "NOVIEMBRE": "11", "DICIEMBRE": "12"}
            date_str = f"{d_d.zfill(2)}/{month_map.get(m.upper(), '01')}/{y}"

        base_title = re.sub(r'^(?:la|el|los|las|de|del)\s+', '', base_title, flags=re.I)
        base_title = base_title[0].upper() + base_title[1:]
        base_title = re.sub(r'[.:;,]+$', '', base_title).strip()

        votations.append({
            "id": f"MAD-{legis_id}-{ds_num}-{i+1}",
            "fecha": date_str,
            "titulo": base_title[:1000], 
            "votos": [],
            "totales": {"favor": v_si, "contra": v_no, "abstencion": v_abs, "total": v_emit},
            "metadatos": {"tipo": "deduccion_grupal", "nota": "Sentido del voto deducido por disciplina de grupo."}
        })
        last_end = match.end()
    return votations

def main():
    files = glob.glob("data/madrid/raw/pdf/*.pdf")
    all_votes_map = {}
    
    with Pool(processes=os.cpu_count()) as pool:
        results = pool.map(parse_one_file, sorted(files))
        for res in results:
            for v in res:
                all_votes_map[v["id"]] = v
                
    all_votes = sorted(list(all_votes_map.values()), key=lambda x: x["id"])
    
    for v in all_votes:
        leg = v["id"].split("-")[1]
        t = v["totales"]
        seats = SEATS.get(leg, SEATS["XIII"])
        gv = {}
        if leg in ["XIII", "XII", "XI", "X"]:
            if t["favor"] >= (seats["PP"] + seats.get("Vox", 0) + seats.get("Ciudadanos", 0)) * 0.9:
                gv["PP"] = "si"; gv["Vox"] = "si"; gv["Ciudadanos"] = "si"
            elif t["favor"] >= seats["PP"] * 0.9:
                gv["PP"] = "si"
            
            if t["contra"] >= (seats.get("Más Madrid", 0) + seats.get("PSOE-M", 0) + seats.get("Podemos", 0)) * 0.9:
                gv["Más Madrid"] = "no"; gv["PSOE-M"] = "no"; gv["Podemos"] = "no"
        v["group_votes"] = gv

    for leg in ["X", "XI", "XII", "XIII"]:
        path = f"data/madrid/votos_{leg}_raw.json"
        if os.path.exists(path): os.remove(path)
        prefix = f"MAD-{leg}-"
        leg_votes = [v for v in all_votes if v["id"].startswith(prefix)]
        if leg_votes:
            with open(path, "w") as f:
                json.dump(leg_votes, f, indent=2, ensure_ascii=False)
    
    print(f"Extraction complete. Processed {len(all_votes)} unique votations for Madrid.")

if __name__ == "__main__":
    main()

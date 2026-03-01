import pdfplumber
import json
import re
import os
import glob
import unicodedata

def normalize_text(text):
    if not text: return ""
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.lower().strip()

def spanish_to_int(text):
    if not text: return 0
    text = text.lower().strip()
    if "cap" in text: return 0
    m = re.search(r'\d+', text)
    if m: return int(m.group(0))
    return 0

def parse_catalunya_ds(file_path, session_info):
    print(f"Parsing {file_path}...")
    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join([p.extract_text() or "" for p in pdf.pages])
    except Exception as e:
        print(f"  Error opening PDF: {e}")
        return []

    votations = []
    
    # Pre-clean: sometimes line breaks break the patterns
    text = text.replace('-\n', '').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    
    # Pattern for results in Catalan
    # Aquesta proposta ha estat aprovada per 72 vots a favor, 37 vots en contra i 26 abstencions.
    # Aquests punts han estat aprovats per 124 vots a favor, cap vot en contra i 11 abstencions.
    res_pattern = r'Aquest[as]? (?:punt|proposta|propostes) ha(?:n)? estat (aprovad[as]|rebutjad[as]) per (?:unanimitat|(\d+|cap) vots? a favor, (\d+|cap) vots? en contra i (\d+|cap) abstencions?)'
    
    matches = list(re.finditer(res_pattern, text, re.IGNORECASE))
    
    current_mocio = ""
    
    for i, match in enumerate(matches):
        start_idx = match.start()
        # Look back for Moció or Proposta de resolució
        pre_context = text[max(0, start_idx-2000):start_idx]
        
        # Look for titles like "Moció subsegüent... (continuació)"
        mocio_match = re.search(r'(Moció subsegüent a la interpel·lació al Govern sobre .*?)(?:\(|\d{3}-)', pre_context, re.I)
        if mocio_match:
            current_mocio = mocio_match.group(1).strip()
            
        # Look for point number
        point = ""
        point_match = re.search(r'(?:votarem|votem|votar)\s+(?:el|els|els|les|la)?\s*(?:punt|punts|proposta|propostes)\s+([0-9., i y a]+)', pre_context[-200:], re.I)
        if point_match:
            point = point_match.group(1).strip()
            
        title = f"{current_mocio} - {point}" if current_mocio else f"Votació {point}"
        if not title.strip(): title = "Votació ordinària"
        
        v_si, v_no, v_abs = 0, 0, 0
        if "unanimitat" in match.group(0).lower():
            v_si = 135
        else:
            v_si = spanish_to_int(match.group(2))
            v_no = spanish_to_int(match.group(3))
            v_abs = spanish_to_int(match.group(4))
        
        votations.append({
            "id": f"CAT-15-{session_info['doc_id']}-{i+1}",
            "fecha": session_info['date'],
            "titulo": title[:300],
            "votos": [],
            "totales": {
                "favor": v_si,
                "contra": v_no,
                "abstencion": v_abs,
                "total": v_si + v_no + v_abs
            },
            "metadatos": {
                "tipo": "deduccion_grupal",
                "nota": "Sentit del vot deduït pel resultat de la cambra i disciplina de grup (estimat)."
            }
        })
        
    return votations

def main():
    with open("data/catalunya/sessions_index.json", "r") as f:
        sessions = json.load(f)
    sessions_map = {s['doc_id']: s for s in sessions}
    
    files = glob.glob("data/catalunya/raw/pdf/*.pdf")
    all_votes = []
    for f in sorted(files):
        doc_id = os.path.basename(f).replace('DS-', '').replace('.pdf', '')
        session_info = sessions_map.get(doc_id)
        if not session_info: continue
        
        votes = parse_catalunya_ds(f, session_info)
        all_votes.extend(votes)
            
    all_votes.sort(key=lambda x: x["id"])
    with open("data/catalunya/votos_XV_raw.json", "w") as f:
        json.dump(all_votes, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(all_votes)} votes to data/catalunya/votos_XV_raw.json")

if __name__ == "__main__":
    main()

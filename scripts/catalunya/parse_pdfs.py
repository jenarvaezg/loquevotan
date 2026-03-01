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
    
    # Patterns for Catalonia Parliament voting results (in Catalan)
    # Pattern 1: Standard result
    res_pattern = r'Aquest[as]? (?:punt|proposta|propostes) ha(?:n)? estat (aprovad[as]|rebutjad[as]) per (\d+|cap) vots? a favor, (\d+|cap) vots? en contra i (\d+|cap) abstencions?'
    
    # Pattern 2: Unanimous
    unanimous_pattern = r'Aquest[as]? (?:punt|proposta|propostes) ha(?:n)? estat aprovad[as] per unanimitat'
    
    matches = list(re.finditer(res_pattern, text, re.IGNORECASE))
    
    for i, match in enumerate(matches):
        start_idx = match.start()
        pre_context = text[max(0, start_idx-1500):start_idx]
        
        # Try to find the title
        title = "Votació ordinària"
        lines = pre_context.split('\n')
        for line in reversed(lines):
            if any(k in line.lower() for k in ['votem', 'votar', 'votació', 'passem a votar']):
                m = re.search(r'(?:votem|votar|votació|passem a votar)\s+(?:la|el|els|les|de)?\s*(.*)', line, re.I)
                if m:
                    title = m.group(1).strip()
                    if len(title) > 5: break
        
        status = match.group(1).lower()
        v_si = spanish_to_int(match.group(2))
        v_no = spanish_to_int(match.group(3))
        v_abs = spanish_to_int(match.group(4))
        
        title = title.split('.')[0].strip()
        
        votations.append({
            "id": f"CAT-15-{session_info['doc_id']}-{i+1}",
            "fecha": session_info['date'],
            "titulo": title[:250],
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

    # Unanimous matches
    u_matches = list(re.finditer(unanimous_pattern, text, re.IGNORECASE))
    for i, match in enumerate(u_matches):
        # Avoid duplicates with already found matches if they are close
        if any(abs(v.get('start_pos', 0) - match.start()) < 100 for v in votations): continue
        
        start_idx = match.start()
        pre_context = text[max(0, start_idx-1500):start_idx]
        title = "Votació unànime"
        lines = pre_context.split('\n')
        for line in reversed(lines):
            if any(k in line.lower() for k in ['votem', 'votar', 'votació', 'passem a votar']):
                m = re.search(r'(?:votem|votar|votació|passem a votar)\s+(?:la|el|els|les|de)?\s*(.*)', line, re.I)
                if m:
                    title = m.group(1).strip()
                    if len(title) > 5: break
        
        title = title.split('.')[0].strip()
        
        votations.append({
            "id": f"CAT-15-{session_info['doc_id']}-U-{i+1}",
            "fecha": session_info['date'],
            "titulo": title[:250],
            "votos": [],
            "totales": {
                "favor": 135, # Default for unanimous in Catalonia
                "contra": 0,
                "abstencion": 0,
                "total": 135
            },
            "metadatos": {
                "tipo": "deduccion_grupal",
                "nota": "Vot unànime."
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

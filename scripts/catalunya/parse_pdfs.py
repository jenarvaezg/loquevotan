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

def extract_catalunya_points(text):
    """Extract points and titles from TAULA DE CONTINGUT."""
    points = {}
    
    # TAULA DE CONTINGUT logic
    # Looking for blocks like:
    # Moció subsegüent a la interpel·lació al Govern sobre el sector primari
    # 302-00198/15 40
    
    # Split text into lines to process TOC
    lines = text.split('\n')
    for i in range(len(lines)):
        line = lines[i].strip()
        # Look for ref ID pattern: 302-00198/15
        ref_match = re.search(r'(\d{3}-\d{5}/\d{2})', line)
        if ref_match:
            ref_id = ref_match.group(1)
            # The title is likely in the previous 1-3 lines
            title_parts = []
            for j in range(1, 4):
                if i - j >= 0:
                    prev_line = lines[i-j].strip()
                    if prev_line and not re.search(r'^\d+$', prev_line) and "DSPC" not in prev_line:
                        title_parts.insert(0, prev_line)
                    else:
                        break
            
            title = " ".join(title_parts).strip()
            if title:
                points[ref_id] = title
                # Also short ID
                short_id = ref_id.split('-')[1].split('/')[0]
                points[short_id] = title

    return points

def parse_catalunya_ds(file_path, session_info):
    print(f"Parsing {file_path}...")
    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join([p.extract_text() or "" for p in pdf.pages])
    except Exception as e:
        print(f"  Error opening PDF: {e}")
        return []

    # Pre-extract points from TOC (check first 10 pages)
    toc_text = "\n".join([p.extract_text() or "" for p in pdfplumber.open(file_path).pages[:10]])
    points_map = extract_catalunya_points(toc_text)

    # Pre-clean for result matching
    clean_text = text.replace('-\n', '').replace('\n', ' ')
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    # Results pattern
    res_pattern = r'Aquest[as]? (?:punt|proposta|propostes) ha(?:n)? estat (?P<status>aprovad[as]|rebutjad[as]) per (?:unanimitat|(?P<si>\d+|cap) vots? a favor, (?P<no>\d+|cap) vots? en contra i (?P<abs>\d+|cap) abstencions?)'
    
    matches = list(re.finditer(res_pattern, clean_text, re.IGNORECASE))
    
    votations = []
    
    for i, match in enumerate(matches):
        match_str = match.group(0)
        original_idx = text.find(match_str[:50])
        if original_idx == -1: original_idx = 0
        
        pre_context = text[max(0, original_idx-2000):original_idx]
        
        title = "Votación ordinària"
        
        # Look for ref IDs: 302-00198/15
        refs = re.findall(r'(\d{3}-\d{5}/\d{2})', pre_context)
        if refs:
            last_ref = refs[-1]
            if last_ref in points_map:
                title = points_map[last_ref]
        else:
            # Try to find specific point number: "punt número 2"
            point_num_match = re.search(r'punt número (\d+)', pre_context[-300:], re.I)
            if point_num_match:
                title = f"Punt {point_num_match.group(1)}"
            else:
                # Common intro lines
                announcement = re.search(r'(?:votarem|votem|votar)\s+(?:la|el|els|les|la|de)?\s*(.*?)(?:\.|\s{2,}|\n|:)', pre_context.split('\n')[-1], re.I)
                if announcement:
                    title = announcement.group(1).strip()
        
        # 2. Extract Votes
        v_si, v_no, v_abs = 0, 0, 0
        if "unanimitat" in match.group(0).lower():
            v_si = 135
        else:
            v_si = spanish_to_int(match.group('si'))
            v_no = spanish_to_int(match.group('no'))
            v_abs = spanish_to_int(match.group('abs'))
        
        votations.append({
            "id": f"CAT-15-{session_info['doc_id']}-{i+1}",
            "fecha": session_info['date'],
            "titulo": title[:400],
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

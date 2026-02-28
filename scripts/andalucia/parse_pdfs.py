import pdfplumber
import json
import re
import os
import glob
import unicodedata

def normalize_text(text):
    if not text:
        return ""
    # Common abbreviations
    text = text.replace("Mª", "Maria")
    text = text.replace("Fco.", "Francisco")
    text = text.replace("D.", "Don")
    # Remove accents and convert to lowercase
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.lower()
    # Remove non-alphanumeric characters except spaces
    text = re.sub(r'[^a-z0-9 ]', '', text)
    # Remove extra spaces
    text = " ".join(text.split())
    return text

def parse_andalucia_voto_pdf(pdf_path, diputados_map, session_info):
    votes = []
    doc_id = os.path.basename(pdf_path).replace('.pdf', '')
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n---PAGE_BREAK---\n"
            
    # Split by vote
    vote_matches = list(re.finditer(r'VOTACIÓN Nº (\d+)', full_text))
    
    for i, match in enumerate(vote_matches):
        vote_num = match.group(1)
        start_idx = match.end()
        end_idx = vote_matches[i+1].start() if i+1 < len(vote_matches) else len(full_text)
        content = full_text[start_idx:end_idx]
        
        # Use session info from index as fallback
        session_num = session_info.get('session', 'Unknown')
        legis = "XII"
        date = session_info.get('date', 'Unknown')
        
        # Try to find better metadata in full_text
        s_match = re.search(r'SESIÓN (\d+)', full_text)
        if s_match: session_num = s_match.group(1)
        
        # Refined title extraction
        title = ""
        # Look for the line after the date/time timestamp
        ts_match = re.search(r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}', content)
        if ts_match:
            lines_after = content[ts_match.end():].split('\n')
            for line in lines_after:
                line = line.strip()
                if not line or 'VOTACIÓN' in line or 'PROTOCOLO' in line or 'SESIÓN' in line or 'PRESIDE' in line:
                    continue
                if 'TÍTULO' in line:
                    # Capture everything after TÍTULO ... DEBATE:
                    title_match = re.search(r'TÍTULO (?:GENERAL|PARTICULAR) DEL DEBATE:\s*(.*)', line)
                    if title_match:
                        title = title_match.group(1).strip()
                        break
                    continue
                if 'TOTAL' in line and 'PP' in line:
                    break
                title = line
                break

        if not title:
            # Look at the text BEFORE the vote number (sometimes title is there)
            prev_content = full_text[max(0, match.start()-200):match.start()]
            title_match = re.search(r'TÍTULO (?:GENERAL|PARTICULAR) DEL DEBATE:\s*(.*?)\n', prev_content, re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()

        results = {
            "id": f"AND-{legis}-{session_num}-{vote_num}",
            "fecha": date,
            "titulo": title if title else "Votación sin título",
            "sesion": session_num,
            "numero": vote_num,
            "votos": []
        }
        
        # Parse individual votes
        sections = re.split(r'\*\*\* (SI|NO|ABSTENCIONES|AUSENTE) \*\*\*', content)
        
        for j in range(1, len(sections), 2):
            sense = sections[j]
            names_text = sections[j+1]
            
            deputy_matches = re.finditer(r'(\d{3})\s+(.*?)(?=\s+\d{3}|$|\n)', names_text)
            
            for d_match in deputy_matches:
                local_id = d_match.group(1)
                full_name = d_match.group(2).strip()
                full_name = " ".join(full_name.split())
                
                norm_name = normalize_text(full_name)
                found_deputy = None
                
                if norm_name in diputados_map:
                    found_deputy = diputados_map[norm_name]
                else:
                    # Fuzzy match for names like "Mª Mercedes" -> "Maria Mercedes"
                    for d_norm, d_data in diputados_map.items():
                        if d_norm in norm_name or norm_name in d_norm:
                            found_deputy = d_data
                            break
                
                voto_sense = "abstencion"
                if sense == "SI": voto_sense = "si"
                elif sense == "NO": voto_sense = "no"
                elif sense == "AUSENTE": voto_sense = "no_vota"

                if found_deputy:
                    results["votos"].append({
                        "diputado": found_deputy["nombre"],
                        "diputadoId": found_deputy["id"],
                        "grupo": found_deputy["grupo"],
                        "voto": voto_sense
                    })
                else:
                    results["votos"].append({
                        "diputado": full_name,
                        "diputadoId": f"AND-UNK-{local_id}",
                        "grupo": "Unknown",
                        "voto": voto_sense
                    })
        
        votes.append(results)
        
    return votes

def main():
    # Load deputies map
    with open("data/andalucia/diputados_raw.json", "r") as f:
        diputados = json.load(f)
    
    # Load session index
    with open("data/andalucia/sessions_index.json", "r") as f:
        sessions_list = json.load(f)
        sessions_map = {s['doc_id']: s for s in sessions_list}
    
    diputados_map = {}
    for d in diputados:
        norm = normalize_text(d["nombre"])
        diputados_map[norm] = d
        
    all_votes = []
    pdf_files = glob.glob("data/andalucia/raw/pdf/*.pdf")
    
    for pdf_path in sorted(pdf_files):
        doc_id = os.path.basename(pdf_path).replace('.pdf', '')
        session_info = sessions_map.get(doc_id, {})
        
        print(f"Parsing {pdf_path}...")
        try:
            votes = parse_andalucia_voto_pdf(pdf_path, diputados_map, session_info)
            all_votes.extend(votes)
            print(f"  Found {len(votes)} votes")
        except Exception as e:
            print(f"  Error parsing {pdf_path}: {e}")
            
    with open("data/andalucia/votos_XII_raw.json", "w") as f:
        json.dump(all_votes, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()

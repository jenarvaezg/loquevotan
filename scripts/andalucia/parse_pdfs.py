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
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n---PAGE_BREAK---\n"
            
    vote_matches = list(re.finditer(r'VOTACIÓN Nº (\d+)', full_text))
    
    for i, match in enumerate(vote_matches):
        vote_num = match.group(1)
        start_idx = match.end()
        end_idx = vote_matches[i+1].start() if i+1 < len(vote_matches) else len(full_text)
        content = full_text[start_idx:end_idx]
        
        session_num = session_info.get('session', 'Unknown')
        legis_id = session_info.get('legis_id', '12')
        # Map legis_id to roman
        legis_map = {"12": "XII", "11": "XI", "10": "X", "9": "IX"}
        legis = legis_map.get(legis_id, "XII")
        date = session_info.get('date', 'Unknown')
        
        results = {
            "id": f"AND-{legis}-{session_num}-{vote_num}",
            "fecha": date,
            "titulo": "Votación sin título",
            "sesion": session_num,
            "numero": vote_num,
            "votos": []
        }
        
        # Title extraction
        ts_match = re.search(r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}', content)
        if ts_match:
            lines = content[ts_match.end():].split('\n')
            for line in lines:
                line = line.strip()
                if not line or any(x in line for x in ['VOTACIÓN', 'PROTOCOLO', 'SESIÓN', 'PRESIDE']): continue
                if 'TÍTULO' in line:
                    m = re.search(r'TÍTULO (?:GENERAL|PARTICULAR) DEL DEBATE:\s*(.*)', line)
                    if m: 
                        results["titulo"] = m.group(1).strip()
                        break
                    continue
                if 'PRESENTES' in line or 'TOTAL' in line: break
                results["titulo"] = line
                break

        current_group = "Unknown"
        lines = content.split('\n')
        current_sense = None
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Detect sense
            sense_match = re.search(r'\*\*\* (SI|NO|ABSTENCIONES|AUSENTE) \*\*\*', line)
            if sense_match:
                current_sense = sense_match.group(1)
                continue
                
            # Detect group
            if (line.startswith('G.P.') or line.startswith('GRUPO')) and '***' not in line:
                current_group = line.replace('G.P. ', '').replace('GRUPO ', '').strip()
                continue
            
            # Detect deputies
            if current_sense:
                dep_matches = re.finditer(r'(\d{3})\s+(.*?)(?=\s+\d{3}|$)', line)
                for d_m in dep_matches:
                    local_id = d_m.group(1)
                    full_name = " ".join(d_m.group(2).strip().split())
                    
                    norm_name = normalize_text(full_name)
                    found_deputy = None
                    
                    # Try to find deputy in map for this legislature
                    for d_norm, d_data in diputados_map.items():
                        if d_data["nlegis"] == legis_id and (d_norm in norm_name or norm_name in d_norm):
                            found_deputy = d_data
                            break
                    
                    voto_sense = "abstencion"
                    if current_sense == "SI": voto_sense = "si"
                    elif current_sense == "NO": voto_sense = "no"
                    elif current_sense == "AUSENTE": voto_sense = "no_vota"

                    if found_deputy:
                        if found_deputy["grupo"] == "Unknown":
                            found_deputy["grupo"] = current_group

                        results["votos"].append({
                            "diputado": found_deputy["nombre"],
                            "diputadoId": found_deputy["id"],
                            "grupo": current_group,
                            "voto": voto_sense
                        })
                    else:
                        results["votos"].append({
                            "diputado": full_name,
                            "diputadoId": f"AND-UNK-{local_id}",
                            "grupo": current_group,
                            "voto": voto_sense
                        })
        
        votes.append(results)
        
    return votes

def main():
    # Load deputies map
    with open("data/andalucia/diputados_raw.json", "r") as f:
        diputados_list = json.load(f)
    
    diputados_map = {normalize_text(d["nombre"]): d for d in diputados_list}
    
    # Load session index
    with open("data/andalucia/sessions_index.json", "r") as f:
        sessions_list = json.load(f)
        sessions_map = {s['doc_id']: s for s in sessions_list}
    
    votes_by_leg = {"12": [], "11": [], "10": [], "9": []}
    pdf_files = glob.glob("data/andalucia/raw/pdf/*.pdf")
    
    for pdf_path in sorted(pdf_files):
        doc_id = os.path.basename(pdf_path).replace('.pdf', '')
        session_info = sessions_map.get(doc_id)
        if not session_info: continue
        
        leg = session_info['legis_id']
        print(f"Parsing {pdf_path} (Leg {leg})...")
        try:
            votes = parse_andalucia_voto_pdf(pdf_path, diputados_map, session_info)
            votes_by_leg[leg].extend(votes)
            print(f"  Found {len(votes)} votes")
        except Exception as e:
            print(f"  Error parsing {pdf_path}: {e}")
            
    # Output structure
    leg_roman = {"12": "XII", "11": "XI", "10": "X", "9": "IX"}
    for leg_id, votes in votes_by_leg.items():
        if not votes: continue
        roman = leg_roman[leg_id]
        with open(f"data/andalucia/votos_{roman}_raw.json", "w") as f:
            json.dump(votes, f, indent=2, ensure_ascii=False)
            
    # Save updated diputados with groups
    with open("data/andalucia/diputados_raw.json", "w") as f:
        json.dump(list(diputados_map.values()), f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()

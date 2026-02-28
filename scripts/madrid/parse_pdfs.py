import pdfplumber
import json
import re
import os
import glob

# Madrid Groups XIII Legislature
GROUPS = {
    "PP": 70,
    "Más Madrid": 27,
    "PSOE-M": 27,
    "Vox": 11
}

def solve_group_votes(favor, contra, abstencion, present):
    results = {}
    remaining_groups = list(GROUPS.keys())
    
    # Heuristic for Madrid
    pp_sense = "si" if favor > contra else "no"
    results["PP"] = pp_sense
    remaining_groups.remove("PP")
    
    for g in remaining_groups[:]:
        count = GROUPS[g]
        if abs(count - abstencion) <= 3:
            results[g] = "abstencion"
            remaining_groups.remove(g)
            break
            
    for g in remaining_groups:
        if pp_sense == "no":
            results[g] = "si"
        else:
            results[g] = "no"
            
    return results

def parse_madrid_pdf(pdf_path):
    all_votes = []
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"
            
    # Extract Initiatives Index
    initiatives = {}
    pattern = r'(\d+)\.-\s+(PNL|PL|PPL|PRL)-(\d+)\(XIII\)/(\d{4}).*?objeto:\s*(.*?)(?=\.\s+Publicación|\.\s+\d+\.-|$)'
    matches = re.finditer(pattern, full_text, re.DOTALL)
    for m in matches:
        ref_short = f"{m.group(3)}/{m.group(4)[2:]}" # e.g. 4/23
        title = " ".join(m.group(5).strip().split())
        initiatives[ref_short] = title

    # Flexible pattern for results
    # Handles: "70 síes", "votos afirmativos 70", "54 noes", "votos negativos 54", etc.
    res_pattern = r'resultado de la votación.*?(\d+)?\s*(?:diputados presentes|votos emitidos)?;?\s*(?:votos afirmativos\s+)?(\d+)\s*(?:síes|sí|votos afirmativos|favor)?\s*,?\s*(?:votos negativos\s+)?(\d+)\s*(?:noes|no|votos negativos|contra)?\s+y\s+(\d+)\s+abstenciones'
    
    results_matches = re.finditer(res_pattern, full_text, re.DOTALL | re.IGNORECASE)
    
    doc_id = os.path.basename(pdf_path).replace('.pdf', '')
    date = "Unknown"
    date_match = re.search(r'Sesión celebrada el .*?(\d+ de .*? de \d{4})', full_text)
    if date_match:
        date = date_match.group(1)

    for rm in results_matches:
        context = full_text[max(0, rm.start()-1000):rm.end()+500]
        
        present_str = rm.group(1)
        present = int(present_str) if present_str else 135
        favor = int(rm.group(2))
        contra = int(rm.group(3))
        abstencion = int(rm.group(4))
        
        # Avoid garbage matches (0,0,0)
        if favor + contra + abstencion < 10: continue
        
        ref_match = re.search(r'(?:Proposición No de Ley|Proyecto de Ley|PNL|PL|PPL)\s+(\d+/\d+)', context, re.IGNORECASE)
        ref = ref_match.group(1) if ref_match else None
        
        title = "Votación sin título"
        vote_id_suffix = f"pos-{rm.start()}" # Unique enough
        
        if ref and ref in initiatives:
            title = initiatives[ref]
            vote_id_suffix = ref.replace('/', '-')
        elif "confianza" in context.lower() and "Presidenta" in context:
            title = "Sesión de Investidura de la Candidata a la Presidencia de la Comunidad de Madrid"
            vote_id_suffix = "investidura"
        else:
            # Try to find recent PNL text
            lines = context.split('\n')
            for line in reversed(lines[:len(lines)//2]):
                if len(line) > 20 and ("PNL" in line or "Proposición" in line):
                    title = line.strip()
                    break

        vote_id = f"MAD-XIII-{doc_id.split('-')[-1]}-{vote_id_suffix}"
        group_votes = solve_group_votes(favor, contra, abstencion, present)
        
        all_votes.append({
            "id": vote_id,
            "fecha": date,
            "titulo": title,
            "group_votes": group_votes,
            "results_raw": {"favor": favor, "contra": contra, "abstencion": abstencion, "present": present},
            "metadatos": {
                "tipo": "deduccion_grupal",
                "nota": "Sentido del voto deducido por disciplina de grupo (Asamblea de Madrid no publica votos individuales en actas ordinarias)."
            }
        })
        
    return all_votes

def main():
    pdf_files = glob.glob("data/madrid/raw/pdf/*.pdf")
    all_extracted = []
    
    for pdf_path in sorted(pdf_files, key=lambda x: int(re.search(r'DS-(\d+)', x).group(1))):
        print(f"Parsing {pdf_path}...")
        try:
            votes = parse_madrid_pdf(pdf_path)
            if votes:
                all_extracted.extend(votes)
                print(f"  Found {len(votes)} potential votes")
        except Exception as e:
            print(f"  Error parsing {pdf_path}: {e}")
            
    # Deduplicate by ID
    seen_ids = set()
    unique_votes = []
    for v in all_extracted:
        if v["id"] not in seen_ids:
            seen_ids.add(v["id"])
            unique_votes.append(v)
            
    unique_votes.sort(key=lambda x: x["id"])
    
    os.makedirs("data/madrid", exist_ok=True)
    with open("data/madrid/votos_XIII_raw.json", "w") as f:
        json.dump(unique_votes, f, indent=2, ensure_ascii=False)
    print(f"Total unique votes extracted for Madrid: {len(unique_votes)}")

if __name__ == "__main__":
    main()

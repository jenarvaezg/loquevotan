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
    pattern = r'(\d+)\.-\s+([A-Z]+)-(\d+)\(XIII\)/(\d{4}).*?objeto:\s*(.*?)(?=\.\s+Publicación|\.\s+\d+\.-|$)'
    matches = re.finditer(pattern, full_text[:100000], re.DOTALL)
    for m in matches:
        ref_short = f"{m.group(3)}/{m.group(4)[2:]}" # e.g. 4/23
        title = " ".join(m.group(5).strip().split())
        title = title.split('. Publicación')[0].strip()
        initiatives[ref_short] = title

    # Multiple patterns for results
    patterns = [
        r'resultado de la votación.*?:?\s*(\d+)?\s*(?:diputados presentes|votos emitidos)?;?\s*(\d+)\s+síes,?\s*(\d+)\s+noes\s+y\s+(\d+)\s+abstenciones',
        r'resultado de la votación.*?votos afirmativos\s+(\d+),?\s+votos negativos\s+(\d+)\s+y\s+abstenciones\s+(\d+)',
        r'resultado de la votación.*?(\d+)\s+votos a favor\s+y\s+(\d+)\s+en contra'
    ]
    
    doc_id = os.path.basename(pdf_path).replace('.pdf', '')
    date = "Unknown"
    date_match = re.search(r'Sesión celebrada el .*?(\d+ de .*? de \d{4})', full_text)
    if date_match:
        date = date_match.group(1)

    for p in patterns:
        results_matches = re.finditer(p, full_text, re.DOTALL | re.IGNORECASE)
        for rm in results_matches:
            groups = rm.groups()
            if len(groups) == 4: # Standard
                present = int(groups[0]) if (groups[0] and groups[0].isdigit()) else 135
                favor = int(groups[1])
                contra = int(groups[2])
                abstencion = int(groups[3])
            elif len(groups) == 3: # Investidura
                present = 135
                favor = int(groups[0])
                contra = int(groups[1])
                abstencion = int(groups[2])
            elif len(groups) == 2: # Simple
                present = 135
                favor = int(groups[0])
                contra = int(groups[1])
                abstencion = 0
            
            if favor + contra + abstencion < 10: continue
            
            context = full_text[max(0, rm.start()-1500):rm.end()+1000]
            
            # Find ID
            ref_match = re.search(r'(?:PNL|PL|PPL|PRL|Proposición No de Ley|Proyecto de Ley)\s+(\d+/\d+)', context, re.IGNORECASE)
            ref = ref_match.group(1) if ref_match else None
            
            title = "Votación sin título"
            vote_id_suffix = f"pos-{rm.start()}"
            
            if ref and ref in initiatives:
                title = initiatives[ref]
                vote_id_suffix = ref.replace('/', '-')
            elif "confianza" in context.lower() and "Presidenta" in context:
                title = "Sesión de Investidura de la Candidata a la Presidencia de la Comunidad de Madrid"
                vote_id_suffix = "investidura"
            else:
                # Look for lines before result
                lines = full_text[max(0, rm.start()-500):rm.start()].split('\n')
                for line in reversed(lines):
                    line = line.strip()
                    if len(line) > 40 and not line.isupper() and "votos" not in line.lower():
                        title = line
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
        votes = parse_madrid_pdf(pdf_path)
        if votes: all_extracted.extend(votes)
            
    seen_ids = set()
    unique_votes = []
    for v in all_extracted:
        if v["id"] not in seen_ids:
            seen_ids.add(v["id"])
            unique_votes.append(v)
            
    unique_votes.sort(key=lambda x: x["id"])
    with open("data/madrid/votos_XIII_raw.json", "w") as f:
        json.dump(unique_votes, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()

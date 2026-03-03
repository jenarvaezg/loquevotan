import argparse
import glob
import json
import os
import re
import subprocess


PDF_GLOB = "data/madrid/raw/pdf/*.pdf"
PARSE_STATE_FILE = "data/madrid/parse_state.json"
OUTPUT_PATTERN = "data/madrid/votos_{leg}_raw.json"
LEGISLATURAS = ["X", "XI", "XII", "XIII"]
PARSER_VERSION = 3

# Madrid Groups Seat Counts for Heuristics
SEATS = {
    "XIII": {"PP": 70, "Más Madrid": 27, "PSOE-M": 27, "Vox": 11},
    "XII": {"PP": 65, "Más Madrid": 24, "PSOE-M": 24, "Vox": 13},
    "XI": {"PP": 30, "PSOE-M": 37, "Más Madrid": 20, "Ciudadanos": 26, "Vox": 12, "Podemos": 7},
    "X": {"PP": 48, "PSOE-M": 37, "Podemos": 27, "Ciudadanos": 17},
}


def spanish_to_int(text):
    if not text:
        return 0
    text = text.lower().strip()
    if text in ["cero", "cap", "ninguna", "ninguno"]:
        return 0
    if text in ["uno", "una", "un"]:
        return 1
    if text == "dos":
        return 2
    if text == "tres":
        return 3
    if text == "diez":
        return 10
    m = re.search(r"\d+", text)
    if m:
        return int(m.group(0))
    return 0


def clean_madrid_title(title):
    if not title:
        return ""
    t = re.sub(r"\s+", " ", title).strip()

    boilerplate_patterns = [
        r"^la Asamblea de Madrid insta al (?:Gobierno|Consejo de Gobierno)(?: de la Comunidad de Madrid)? a[:\s]*(?:que )?(?:poner en marcha )?(?:las siguientes actuaciones|lo siguiente)?[:\s]*",
        r"^en el marco de sus competencias, qué medidas va a adoptar .*? con el siguiente objeto[:\s]*",
        r"^con el (?:siguiente )?objeto(?: de(?: lo siguiente)?)?[:\s]*",
        r"^¿?Qué valoración hace el Gobierno.*?sobre[:\s]*",
        r"^¿?Qué medidas va a adoptar el Gobierno.*?con respecto a[:\s]*",
        r"^¿?Qué planes tiene el Gobierno.*?con el siguiente objeto[:\s]*",
        r"^en relación a[:\s]*",
        r"^\d+[\.\)\-\s]+",
    ]

    last_len = -1
    while len(t) != last_len:
        last_len = len(t)
        for pattern in boilerplate_patterns:
            new_t = re.sub(pattern, "", t, flags=re.I).strip()
            if len(new_t) > 5:
                t = new_t

    if t:
        t = t[0].upper() + t[1:]

    t = re.sub(r"[.:;, ]+$", "", t).strip()
    return t


def extract_descriptions(text):
    desc_map = {}
    p_re = re.compile(
        r"(?P<code>(?:PNL|PCOP|PNLP|PL|Proyecto de Ley|Proposición No de Ley|Moción|Propuesta de Resolución|I|C)\s*-?\s*(?P<num>\d+)/(?P<year>\d+)).*?(?:objeto|finalidad|sobre|objeto de la misma)[:\s]+",
        re.I | re.DOTALL,
    )

    for m in p_re.finditer(text):
        num = m.group("num")
        year = m.group("year")
        short_year = year[-2:]
        key = f"{num}/{short_year}"

        start_desc = m.end()
        candidate = text[start_desc:start_desc + 1000].strip()

        stop_markers = ["Publicación BOAM", "DIARIO DE SESIONES", "\n\n\n"]
        desc = candidate
        for sm in stop_markers:
            if sm in desc:
                desc = desc.split(sm)[0].strip()

        cleaned = clean_madrid_title(desc)
        if len(cleaned) > 10:
            if key not in desc_map or len(cleaned) > len(desc_map[key]):
                desc_map[key] = cleaned
    return desc_map


def get_pdf_text(path):
    try:
        result = subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True, timeout=30)
        return result.stdout
    except Exception:
        return ""


def get_pdf_first_page_text(path):
    try:
        result = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "1", path, "-"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout
    except Exception:
        return ""


def parse_one_file(file_path):
    full_text = get_pdf_text(file_path)
    if not full_text:
        return None
    if "resultado" not in full_text.lower():
        return []

    first_page_text = get_pdf_first_page_text(file_path)

    legis_match = re.search(r"(X|XI|XII|XIII)\s+legislatura", first_page_text, re.I)
    legis_id = legis_match.group(1).upper() if legis_match else "XIII"
    ds_match = re.search(r"NÚM\.\s*(\d+)", first_page_text, re.I)
    ds_num = ds_match.group(1) if ds_match else os.path.basename(file_path).split("-")[-1].split(".")[0]

    desc_text = full_text.replace("-\n", "")
    desc_map = extract_descriptions(desc_text)

    votations = []
    last_end = 0
    last_known_title = None

    for i, m_anchor in enumerate(re.finditer(r"resultado\s+(?:de\s+la\s+)?votación\s+es", desc_text, re.I)):
        window = desc_text[m_anchor.end():m_anchor.end() + 1000]

        res_pattern = (
            r"(?:.*?(?P<emitidos>\d+|[a-z]+)\s+(?:votos\s+emitidos|diputados\s+presentes))?"
            r".*?(?P<si>\d+|[a-z]+)\s+(?:síes|votos?\s+(?:a\s+favor|afirmativos))"
            r".*?(?P<no>\d+|[a-z]+)\s+(?:noes|votos?\s+(?:en\s+contra|negativos))"
            r"(?:.*?(?P<abs>\d+|[a-z]+)\s+abstenciones?)?"
        )

        match = re.search(res_pattern, window, re.I | re.S)
        if not match:
            continue

        block_start = max(last_end, m_anchor.start() - 3000)
        votation_block = desc_text[block_start:m_anchor.start()]

        num_match = re.search(r"(\d+)/(\d{2,4})", votation_block)
        key_found = f"{num_match.group(1)}/{num_match.group(2)[-2:]}" if num_match else None

        base_title = "Votación desconocida"
        entity_patterns = [
            r"(?P<full>(?:Proposición No de Ley|PNL|PCOP|PNLP|Proposición de Ley|Proyecto de Ley|PL|Moción|Propuesta de Resolución)\s*(?:-)?\s*(?P<num>\d+)/(?P<year>\d+))",
            r"enmienda(?:s)?\s+(?:número\s+)?[\d, y a]+",
            r"ratificación del convenio\s+.*",
            r"texto del proyecto de ley",
            r"dictamen de la Comisión.*",
            r"investidura",
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
            lines = [l.strip() for l in votation_block.split("\n") if l.strip()]
            for line in reversed(lines):
                if any(k in line.lower() for k in ["votamos", "votar", "votación", "pasamos a"]):
                    m = re.search(r"(?:votamos|votar|votación|pasamos a|somete a)\s+(?:la|el|los|las|de)?\s*(.*)", line, re.I)
                    if m:
                        base_title = m.group(1).strip()
                        if len(base_title) > 5:
                            break

        if key_found and key_found in desc_map:
            desc = desc_map[key_found]
            prefix_match = re.search(
                r"^((?:PNL|PCOP|PNLP|PL|Proyecto de Ley|Proposición No de Ley|Moción)\s*(?:-)?\s*\d+/\d+)",
                base_title,
                re.I,
            )
            prefix = prefix_match.group(1) if prefix_match else base_title
            base_title = f"{prefix}: {desc}"

        d = match.groupdict()
        v_si = spanish_to_int(d["si"])
        v_no = spanish_to_int(d["no"])
        v_abs = spanish_to_int(d["abs"] or "0")
        v_emit = spanish_to_int(d["emitidos"]) if d["emitidos"] else (v_si + v_no + v_abs)

        if "investidura" in base_title.lower() or "confianza" in base_title.lower():
            base_title = "Investidura de la Presidenta de la Comunidad"

        post_text = desc_text[match.end():match.end() + 400]
        remote_matches = re.finditer(r"(\d+|un|una|dos|tres)\s*(?:votos?\s+)?(sí|no|abstención|abstencions)", post_text, re.I)
        for rm in remote_matches:
            val = spanish_to_int(rm.group(1))
            sense = rm.group(2).lower()
            if "sí" in sense:
                v_si += val
            elif "no" in sense:
                v_no += val
            elif "abstenc" in sense:
                v_abs += val

        v_emit = max(v_emit, v_si + v_no + v_abs)
        date_match = re.search(r"(\d{1,2})\s+DE\s+([A-Z]+)\s+DE\s+(\d{4})", desc_text[:3000], re.I)
        date_str = "Unknown"
        if date_match:
            d_d, m, y = date_match.groups()
            month_map = {
                "ENERO": "01",
                "FEBRERO": "02",
                "MARZO": "03",
                "ABRIL": "04",
                "MAYO": "05",
                "JUNIO": "06",
                "JULIO": "07",
                "AGOSTO": "08",
                "SEPTIEMBRE": "09",
                "OCTUBRE": "10",
                "NOVIEMBRE": "11",
                "DICIEMBRE": "12",
            }
            date_str = f"{d_d.zfill(2)}/{month_map.get(m.upper(), '01')}/{y}"

        base_title = re.sub(r"[.:;, ]+$", "", base_title).strip()

        normalized_lower = base_title.lower()
        is_low_signal_title = (
            normalized_lower in {
                "votación desconocida",
                "votación",
                "votación sin título",
                "votación de la",
                "(pausa.) el",
                "pausa. el",
                "el",
            }
            or re.fullmatch(r"\(?pausa\.?\)?\s*el", normalized_lower) is not None
        )
        if is_low_signal_title and last_known_title:
            base_title = f"Votación relacionada con: {last_known_title}"
        elif not is_low_signal_title:
            last_known_title = base_title

        votations.append(
            {
                "id": f"MAD-{legis_id}-{ds_num}-{i + 1}",
                "fecha": date_str,
                "titulo": base_title[:1500],
                "votos": [],
                "totales": {"favor": v_si, "contra": v_no, "abstencion": v_abs, "total": v_emit},
                "metadatos": {"tipo": "deduccion_grupal", "nota": "Sentido del voto deducido por disciplina de grupo."},
            }
        )
        last_end = m_anchor.end() + match.end()
    return votations


def file_signature(path):
    stat = os.stat(path)
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)


def load_parse_state():
    state = load_json(PARSE_STATE_FILE, {"version": PARSER_VERSION, "files": {}})
    if not isinstance(state, dict):
        return {"version": PARSER_VERSION, "files": {}}
    if state.get("version") != PARSER_VERSION:
        return {"version": PARSER_VERSION, "files": {}}
    if "files" not in state or not isinstance(state["files"], dict):
        state["files"] = {}
    state["version"] = PARSER_VERSION
    return state


def save_parse_state(state):
    state["version"] = PARSER_VERSION
    with open(PARSE_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_existing_votes_map():
    votes_by_id = {}
    for leg in LEGISLATURAS:
        path = OUTPUT_PATTERN.format(leg=leg)
        for vote in load_json(path, []):
            vote_id = vote.get("id")
            if vote_id:
                votes_by_id[vote_id] = vote
    return votes_by_id


def ensure_group_votes(votes_map, rebuild):
    for vote in votes_map.values():
        if not rebuild and vote.get("group_votes"):
            continue

        leg = vote.get("id", "").split("-")[1] if vote.get("id") else "XIII"
        totals = vote.get("totales", {})
        seats = SEATS.get(leg, SEATS["XIII"])
        group_votes = {}

        favor = totals.get("favor", 0)
        contra = totals.get("contra", 0)

        if leg in ["XIII", "XII", "XI", "X"]:
            if favor >= (seats.get("PP", 0) + seats.get("Vox", 0) + seats.get("Ciudadanos", 0)) * 0.9:
                group_votes["PP"] = "si"
                if "Vox" in seats:
                    group_votes["Vox"] = "si"
                if "Ciudadanos" in seats:
                    group_votes["Ciudadanos"] = "si"
            elif favor >= seats.get("PP", 0) * 0.9:
                group_votes["PP"] = "si"

            if contra >= (seats.get("Más Madrid", 0) + seats.get("PSOE-M", 0) + seats.get("Podemos", 0)) * 0.9:
                if "Más Madrid" in seats:
                    group_votes["Más Madrid"] = "no"
                if "PSOE-M" in seats:
                    group_votes["PSOE-M"] = "no"
                if "Podemos" in seats:
                    group_votes["Podemos"] = "no"

        vote["group_votes"] = group_votes


def split_votes_by_leg(votes_map):
    votes_by_leg = {leg: [] for leg in LEGISLATURAS}
    for vote in votes_map.values():
        parts = vote.get("id", "").split("-")
        if len(parts) < 2:
            continue
        leg = parts[1]
        if leg in votes_by_leg:
            votes_by_leg[leg].append(vote)
    for leg in votes_by_leg:
        votes_by_leg[leg].sort(key=lambda v: v.get("id", ""))
    return votes_by_leg


def main():
    parser = argparse.ArgumentParser(description="Parsea PDFs de Madrid con modo incremental.")
    parser.add_argument("--rebuild", action="store_true", help="Fuerza reprocesado completo de todos los PDFs.")
    args = parser.parse_args()

    files = sorted(glob.glob(PDF_GLOB))
    votes_by_id = {} if args.rebuild else load_existing_votes_map()
    state = {"version": PARSER_VERSION, "files": {}} if args.rebuild else load_parse_state()
    state_files = state["files"]

    seen_files = set()
    skipped = 0
    reparsed = 0

    print(f"Starting processing of {len(files)} files...")
    for i, file_path in enumerate(files):
        state_key = os.path.basename(file_path)
        seen_files.add(state_key)
        signature = file_signature(file_path)
        previous_entry = state_files.get(state_key, {})
        previous_vote_ids = previous_entry.get("vote_ids", [])

        unchanged = (
            not args.rebuild
            and previous_entry.get("signature") == signature
            and all(vote_id in votes_by_id for vote_id in previous_vote_ids)
        )
        if unchanged:
            skipped += 1
            continue

        print(f"[{i + 1}/{len(files)}] Parsing {file_path}...")
        parsed_votes = parse_one_file(file_path)
        if parsed_votes is None:
            print("  Parsing failed, preserving previous extracted votes for this file.")
            continue
        for old_vote_id in previous_vote_ids:
            votes_by_id.pop(old_vote_id, None)
        for vote in parsed_votes:
            vote_id = vote.get("id")
            if vote_id:
                votes_by_id[vote_id] = vote

        state_files[state_key] = {
            "signature": signature,
            "vote_ids": [v.get("id") for v in parsed_votes if v.get("id")],
        }
        reparsed += 1

    for stale_key in [k for k in list(state_files.keys()) if k not in seen_files]:
        for old_vote_id in state_files[stale_key].get("vote_ids", []):
            votes_by_id.pop(old_vote_id, None)
        del state_files[stale_key]

    ensure_group_votes(votes_by_id, args.rebuild)
    votes_by_leg = split_votes_by_leg(votes_by_id)

    for leg in LEGISLATURAS:
        path = OUTPUT_PATTERN.format(leg=leg)
        with open(path, "w") as f:
            json.dump(votes_by_leg[leg], f, indent=2, ensure_ascii=False)

    save_parse_state(state)
    print(
        f"Extraction complete. Processed {len(votes_by_id)} unique votations for Madrid "
        f"({reparsed} reprocesados, {skipped} reutilizados)."
    )


if __name__ == "__main__":
    main()

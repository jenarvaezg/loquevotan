import argparse
import glob
import json
import os
import re
import unicodedata

import pdfplumber


DIPUTADOS_FILE = "data/andalucia/diputados_raw.json"
SESSIONS_FILE = "data/andalucia/sessions_index.json"
PDF_GLOB = "data/andalucia/raw/pdf/*.pdf"
OUTPUT_PATTERN = "data/andalucia/votos_{leg}_raw.json"
PARSE_STATE_FILE = "data/andalucia/parse_state.json"

LEG_ID_TO_ROMAN = {"12": "XII", "11": "XI", "10": "X", "9": "IX"}
LEG_ROMAN_TO_ID = {v: k for k, v in LEG_ID_TO_ROMAN.items()}


def parse_legislaturas(value):
    if not value:
        return None
    return {v.strip() for v in str(value).split(",") if v.strip()}


def normalize_text(text):
    if not text:
        return ""
    # Common abbreviations
    text = text.replace("Mª", "Maria")
    text = text.replace("Fco.", "Francisco")
    text = text.replace("D.", "Don")
    # Remove accents and convert to lowercase
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = text.lower()
    # Remove non-alphanumeric characters except spaces
    text = re.sub(r"[^a-z0-9 ]", "", text)
    # Remove extra spaces
    text = " ".join(text.split())
    return text


def file_signature(path):
    stat = os.stat(path)
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)


def load_parse_state():
    state = load_json(PARSE_STATE_FILE, {"version": 1, "files": {}})
    if not isinstance(state, dict):
        return {"version": 1, "files": {}}
    if "files" not in state or not isinstance(state["files"], dict):
        state["files"] = {}
    state["version"] = 1
    return state


def save_parse_state(state):
    with open(PARSE_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_existing_votes_map():
    votes_by_id = {}
    for roman in LEG_ID_TO_ROMAN.values():
        path = OUTPUT_PATTERN.format(leg=roman)
        for vote in load_json(path, []):
            vote_id = vote.get("id")
            if vote_id:
                votes_by_id[vote_id] = vote
    return votes_by_id


def split_votes_by_leg(votes_by_id):
    votes_by_leg = {leg_id: [] for leg_id in LEG_ID_TO_ROMAN}
    for vote in votes_by_id.values():
        vote_id = vote.get("id", "")
        parts = vote_id.split("-")
        if len(parts) < 2:
            continue
        leg_id = LEG_ROMAN_TO_ID.get(parts[1])
        if leg_id in votes_by_leg:
            votes_by_leg[leg_id].append(vote)
    for leg_id in votes_by_leg:
        votes_by_leg[leg_id].sort(key=lambda v: v.get("id", ""))
    return votes_by_leg


def parse_andalucia_voto_pdf(pdf_path, diputados_map, session_info):
    votes = []

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n---PAGE_BREAK---\n"

    vote_matches = list(re.finditer(r"VOTACIÓN Nº (\d+)", full_text))

    for i, match in enumerate(vote_matches):
        vote_num = match.group(1)
        start_idx = match.end()
        end_idx = vote_matches[i + 1].start() if i + 1 < len(vote_matches) else len(full_text)
        content = full_text[start_idx:end_idx]

        # Look for title in the block BEFORE this vote (up to 1000 chars)
        pre_vote_text = full_text[max(0, match.start() - 1000):match.start()]

        session_num = session_info.get("session", "Unknown")
        legis_id = session_info.get("legis_id", "12")
        legis = LEG_ID_TO_ROMAN.get(legis_id, "XII")
        date = session_info.get("date", "Unknown")

        results = {
            "id": f"AND-{legis}-{session_num}-{vote_num}",
            "fecha": date,
            "titulo": "Votación sin título",
            "sesion": session_num,
            "numero": vote_num,
            "votos": [],
        }

        # Title extraction (looking backwards from the vote marker)
        tp_match = re.search(
            r"TÍTULO PARTICULAR DEL DEBATE:\s*(.*?)(?=\n[A-Z\s]+:|\nTOTAL|\n\d{2}/|$)",
            content,
            re.DOTALL,
        )
        if tp_match and tp_match.group(1).strip() and "PRESIDE" not in tp_match.group(1):
            results["titulo"] = " ".join(tp_match.group(1).strip().split())
        else:
            tg_match = re.search(
                r"TÍTULO GENERAL DEL DEBATE\s*\n(.*?)\n\d{2}/\d{2}/\d{4}",
                pre_vote_text,
                re.DOTALL,
            )
            if tg_match:
                results["titulo"] = " ".join(tg_match.group(1).strip().split())
            else:
                ts_match = list(re.finditer(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})", pre_vote_text))
                if ts_match:
                    last_ts = ts_match[-1]
                    lines = pre_vote_text[:last_ts.start()].strip().split("\n")
                    if lines:
                        candidate = lines[-1].strip()
                        if len(candidate) > 5 and "LEGISLATURA" not in candidate and "DEBATE" not in candidate:
                            results["titulo"] = candidate

        if "PRESIDE LA VOTACIÓN" in results["titulo"] or results["titulo"] == "Votación sin título":
            lines = pre_vote_text.strip().split("\n")
            for line in reversed(lines):
                line = line.strip()
                if not line or any(x in line for x in ["VOTACIÓN", "SESIÓN", "LEGISLATURA", "PROTOCOLO"]):
                    continue
                if len(line) > 10:
                    results["titulo"] = line
                    break

        current_group = "Unknown"
        lines = content.split("\n")
        current_sense = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            sense_match = re.search(r"\*\*\* (S[IÍ]|NO|ABSTENCIONES?|AUSENTE) \*\*\*", line)
            if sense_match:
                raw_sense = sense_match.group(1)
                if raw_sense in ["SI", "SÍ"]:
                    current_sense = "SI"
                elif raw_sense in ["ABSTENCION", "ABSTENCIONES"]:
                    current_sense = "ABSTENCIONES"
                else:
                    current_sense = raw_sense
                continue

            if (line.startswith("G.P.") or line.startswith("GRUPO")) and "***" not in line:
                current_group = line.replace("G.P. ", "").replace("GRUPO ", "").strip()
                continue

            if current_sense:
                dep_matches = re.finditer(r"(\d{3})\s+(.*?)(?=\s+\d{3}|$)", line)
                for d_m in dep_matches:
                    local_id = d_m.group(1)
                    full_name = " ".join(d_m.group(2).strip().split())

                    if (
                        not full_name
                        or re.match(r"^\d{2}:\d{2}:\d{2}", full_name)
                        or re.match(r"^[\d\s\:\.\/]+$", full_name)
                    ):
                        continue

                    norm_name = normalize_text(full_name)
                    found_deputy = None

                    for d_norm, d_data in diputados_map.items():
                        if d_data["nlegis"] == legis_id and (d_norm in norm_name or norm_name in d_norm):
                            found_deputy = d_data
                            break

                    voto_sense = "abstencion"
                    if current_sense == "SI":
                        voto_sense = "si"
                    elif current_sense == "NO":
                        voto_sense = "no"
                    elif current_sense == "AUSENTE":
                        voto_sense = "no_vota"

                    if found_deputy:
                        if found_deputy["grupo"] == "Unknown":
                            found_deputy["grupo"] = current_group

                        results["votos"].append(
                            {
                                "diputado": found_deputy["nombre"],
                                "diputadoId": found_deputy["id"],
                                "grupo": current_group,
                                "voto": voto_sense,
                            }
                        )
                    else:
                        results["votos"].append(
                            {
                                "diputado": full_name,
                                "diputadoId": f"AND-UNK-{local_id}",
                                "grupo": current_group,
                                "voto": voto_sense,
                            }
                        )

        votes.append(results)

    return votes


def main():
    parser = argparse.ArgumentParser(description="Parsea PDFs de Andalucía con modo incremental.")
    parser.add_argument("--rebuild", action="store_true", help="Fuerza reprocesado completo de todos los PDFs.")
    parser.add_argument(
        "--legislaturas",
        help="Lista de legislaturas separadas por coma (ej: 12,11).",
    )
    args = parser.parse_args()
    target_leg_ids = parse_legislaturas(args.legislaturas)

    diputados_list = load_json(DIPUTADOS_FILE, [])
    diputados_map = {normalize_text(d["nombre"]): d for d in diputados_list}

    sessions_list = load_json(SESSIONS_FILE, [])
    sessions_map = {s["doc_id"]: s for s in sessions_list}
    target_doc_ids = {
        str(s.get("doc_id"))
        for s in sessions_list
        if not target_leg_ids or str(s.get("legis_id")) in target_leg_ids
    }

    votes_by_id = {} if args.rebuild else load_existing_votes_map()
    state = {"version": 1, "files": {}} if args.rebuild else load_parse_state()
    state_files = state["files"]

    pdf_files = sorted(glob.glob(PDF_GLOB))
    seen_files = set()
    skipped = 0
    reparsed = 0

    for pdf_path in pdf_files:
        doc_id = os.path.basename(pdf_path).replace(".pdf", "")
        if target_doc_ids and doc_id not in target_doc_ids:
            continue

        session_info = sessions_map.get(doc_id)
        if not session_info:
            continue
        if target_leg_ids and str(session_info.get("legis_id")) not in target_leg_ids:
            continue

        state_key = os.path.basename(pdf_path)
        seen_files.add(state_key)
        signature = file_signature(pdf_path)
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

        leg = session_info["legis_id"]
        print(f"Parsing {pdf_path} (Leg {leg})...")
        try:
            parsed_votes = parse_andalucia_voto_pdf(pdf_path, diputados_map, session_info)
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
            print(f"  Found {len(parsed_votes)} votes")
        except Exception as e:
            print(f"  Error parsing {pdf_path}: {e}")

    stale_candidates = []
    for state_key in list(state_files.keys()):
        if state_key in seen_files:
            continue
        doc_id = state_key.replace(".pdf", "")
        if target_doc_ids and doc_id not in target_doc_ids:
            continue
        stale_candidates.append(state_key)

    for stale_key in stale_candidates:
        for old_vote_id in state_files[stale_key].get("vote_ids", []):
            votes_by_id.pop(old_vote_id, None)
        del state_files[stale_key]

    votes_by_leg = split_votes_by_leg(votes_by_id)
    for leg_id, roman in LEG_ID_TO_ROMAN.items():
        with open(OUTPUT_PATTERN.format(leg=roman), "w") as f:
            json.dump(votes_by_leg[leg_id], f, indent=2, ensure_ascii=False)

    with open(DIPUTADOS_FILE, "w") as f:
        diputados_out = sorted(diputados_map.values(), key=lambda d: d.get("id", ""))
        json.dump(diputados_out, f, indent=2, ensure_ascii=False)

    save_parse_state(state)
    print(
        f"Parse Andalucía completado: {len(votes_by_id)} votos totales, "
        f"{reparsed} PDFs reprocesados, {skipped} PDFs reutilizados."
    )


if __name__ == "__main__":
    main()

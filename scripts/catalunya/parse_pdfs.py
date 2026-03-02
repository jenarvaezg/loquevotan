import argparse
import glob
import json
import os
import re
import unicodedata

import pdfplumber


SESSIONS_FILE = "data/catalunya/sessions_index.json"
PDF_GLOB = "data/catalunya/raw/pdf/*.pdf"
OUTPUT_FILE = "data/catalunya/votos_XV_raw.json"
PARSE_STATE_FILE = "data/catalunya/parse_state.json"


def normalize_text(text):
    if not text:
        return ""
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return text.lower().strip()


def spanish_to_int(text):
    if not text:
        return 0
    text = text.lower().strip()
    if "cap" in text:
        return 0
    m = re.search(r"\d+", text)
    if m:
        return int(m.group(0))
    return 0


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
    for vote in load_json(OUTPUT_FILE, []):
        vote_id = vote.get("id")
        if vote_id:
            votes_by_id[vote_id] = vote
    return votes_by_id


def extract_catalunya_points(text):
    """Extract points and titles from TAULA DE CONTINGUT."""
    points = {}

    lines = text.split("\n")
    for i in range(len(lines)):
        line = lines[i].strip()
        ref_match = re.search(r"(\d{3}-\d{5}/\d{2})", line)
        if ref_match:
            ref_id = ref_match.group(1)
            title_parts = []
            for j in range(1, 4):
                if i - j >= 0:
                    prev_line = lines[i - j].strip()
                    if prev_line and not re.search(r"^\d+$", prev_line) and "DSPC" not in prev_line:
                        title_parts.insert(0, prev_line)
                    else:
                        break

            title = " ".join(title_parts).strip()
            if title:
                points[ref_id] = title
                short_id = ref_id.split("-")[1].split("/")[0]
                points[short_id] = title

    return points


def parse_catalunya_ds(file_path, session_info):
    print(f"Parsing {file_path}...")
    try:
        with pdfplumber.open(file_path) as pdf:
            pages = pdf.pages
            text = "\n".join([p.extract_text() or "" for p in pages])
            toc_text = "\n".join([p.extract_text() or "" for p in pages[:10]])
    except Exception as e:
        print(f"  Error opening PDF: {e}")
        return []

    points_map = extract_catalunya_points(toc_text)

    clean_text = text.replace("-\n", "").replace("\n", " ")
    clean_text = re.sub(r"\s+", " ", clean_text)

    res_pattern = (
        r"Aquest[as]? (?:punt|proposta|propostes) ha(?:n)? estat "
        r"(?P<status>aprovad[as]|rebutjad[as]) per "
        r"(?:unanimitat|(?P<si>\d+|cap) vots? a favor, (?P<no>\d+|cap) vots? en contra i (?P<abs>\d+|cap) abstencions?)"
    )

    matches = list(re.finditer(res_pattern, clean_text, re.IGNORECASE))
    votations = []

    for i, match in enumerate(matches):
        match_str = match.group(0)
        original_idx = text.find(match_str[:50])
        if original_idx == -1:
            original_idx = 0

        pre_context = text[max(0, original_idx - 2000):original_idx]
        title = "Votación ordinària"

        refs = re.findall(r"(\d{3}-\d{5}/\d{2})", pre_context)
        if refs:
            last_ref = refs[-1]
            if last_ref in points_map:
                title = points_map[last_ref]
        else:
            point_num_match = re.search(r"punt número (\d+)", pre_context[-300:], re.I)
            if point_num_match:
                title = f"Punt {point_num_match.group(1)}"
            else:
                announcement = re.search(
                    r"(?:votarem|votem|votar)\s+(?:la|el|els|les|la|de)?\s*(.*?)(?:\.|\s{2,}|\n|:)",
                    pre_context.split("\n")[-1],
                    re.I,
                )
                if announcement:
                    title = announcement.group(1).strip()

        if "unanimitat" in match.group(0).lower():
            v_si, v_no, v_abs = 135, 0, 0
        else:
            v_si = spanish_to_int(match.group("si"))
            v_no = spanish_to_int(match.group("no"))
            v_abs = spanish_to_int(match.group("abs"))

        votations.append(
            {
                "id": f"CAT-15-{session_info['doc_id']}-{i + 1}",
                "fecha": session_info["date"],
                "titulo": title[:400],
                "votos": [],
                "totales": {
                    "favor": v_si,
                    "contra": v_no,
                    "abstencion": v_abs,
                    "total": v_si + v_no + v_abs,
                },
                "metadatos": {
                    "tipo": "deduccion_grupal",
                    "nota": "Sentit del vot deduït pel resultat de la cambra i disciplina de grup (estimat).",
                },
            }
        )

    return votations


def main():
    parser = argparse.ArgumentParser(description="Parsea PDFs de Catalunya con modo incremental.")
    parser.add_argument("--rebuild", action="store_true", help="Fuerza reprocesado completo de todos los PDFs.")
    args = parser.parse_args()

    sessions = load_json(SESSIONS_FILE, [])
    sessions_map = {s["doc_id"]: s for s in sessions}

    votes_by_id = {} if args.rebuild else load_existing_votes_map()
    state = {"version": 1, "files": {}} if args.rebuild else load_parse_state()
    state_files = state["files"]

    files = sorted(glob.glob(PDF_GLOB))
    seen_files = set()
    skipped = 0
    reparsed = 0

    for file_path in files:
        doc_id = os.path.basename(file_path).replace("DS-", "").replace(".pdf", "")
        session_info = sessions_map.get(doc_id)
        if not session_info:
            continue

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

        parsed_votes = parse_catalunya_ds(file_path, session_info)
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

    all_votes = sorted(votes_by_id.values(), key=lambda x: x.get("id", ""))
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_votes, f, indent=2, ensure_ascii=False)

    save_parse_state(state)
    print(
        f"Saved {len(all_votes)} votes to {OUTPUT_FILE} "
        f"({reparsed} PDFs reprocesados, {skipped} reutilizados)."
    )


if __name__ == "__main__":
    main()

"""Build home_extras.json for every scope from the published data.

The home draws a featured vote as the chamber and answers "¿Votó [partido] a
favor de [tema]?" for the current legislature. Both need how each group voted,
which only lives in the large votos_<LEG>.json files, so this keeps the small
slice the home needs. Run it after the transforms, like build_global_index.py.
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from transform import group_majorities, is_non_partisan_group  # noqa: E402

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "data")
OUTPUT_NAME = "home_extras.json"
# Tags that describe the scope or the procedure, not a topic (same as the app).
BASE_HIDDEN_TAGS = {"nacional", "procedimiento_parlamentario"}
SPOTLIGHT_SIZE = 5
MIN_TOPIC_VOTES = 5
MAX_TOPICS = 60
RECENT_PER_TOPIC = 8
# A fallback spotlight vote needs both sides to have at least this share.
CONTESTED_SHARE = 0.15


def parse_date(fecha):
    """Accepts ISO dates (national) and D/M/YYYY dates (regional scopes)."""
    text = str(fecha or "").strip()
    try:
        if "-" in text:
            y, m, d = text.split("-")
        else:
            d, m, y = text.split("/")
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


def iso_date(fecha):
    parsed = parse_date(fecha)
    return parsed.isoformat() if parsed else str(fecha or "")


def scope_dir(public_dir, scope_id):
    return public_dir if scope_id == "nacional" else os.path.join(public_dir, scope_id)


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_votos(path_dir, leg):
    """Rows [votIdx, dipIdx, grupoIdx, voto] and the detail map of one legislature."""
    path = os.path.join(path_dir, f"votos_{leg}.json")
    if not os.path.exists(path):
        return [], {}
    data = read_json(path)
    if data.get("split"):
        rows, detail = [], {}
        for part in data.get("parts", []):
            part_data = read_json(os.path.join(path_dir, part))
            rows.extend(part_data.get("votos", []))
            detail.update(part_data.get("detail", {}))
        return rows, detail
    return data.get("votos", []), data.get("detail", {})


def tally_by_group(rows, grupos):
    """{votIdx: {group: [favor, contra, abstencion, no_vota]}}"""
    tallies = {}
    for vot_idx, _dip, grupo_idx, voto in rows:
        if not 1 <= voto <= 4:
            continue
        group = grupos[grupo_idx]
        counts = tallies.setdefault(vot_idx, {}).setdefault(group, [0, 0, 0, 0])
        counts[voto - 1] += 1
    return tallies


def positions(group_counts):
    return group_majorities({g: {1: c[0], 2: c[1], 3: c[2]} for g, c in group_counts.items()})


def vote_summary(vot, res):
    return {
        "id": vot["id"],
        "titulo": vot.get("titulo_ciudadano", ""),
        "fecha": iso_date(vot.get("fecha")),
        "result": res.get("result", ""),
        "favor": res.get("favor", 0),
        "contra": res.get("contra", 0),
        "abstencion": res.get("abstencion", 0),
        "total": res.get("total", 0),
        "margin": res.get("margin", 0),
    }


def is_contested(res):
    total = res.get("total") or 0
    return total > 0 and min(res.get("favor", 0), res.get("contra", 0)) >= total * CONTESTED_SHARE


def build_questions(votaciones, recent_leg_votes, tallies, hidden_tags, preferred_tags=()):
    """Per topic of the current legislature: each group's tally and its latest votes.

    The most voted topics are kept, plus the curated home examples
    (preferred_tags) when they have enough votes, since the home opens on them.
    """
    pos_by_vote = {i: positions(tallies[i]) for i in recent_leg_votes}
    groups = sorted({g for gm in pos_by_vote.values() for g in gm if not is_non_partisan_group(g)})

    topic_counts = Counter(
        tag
        for i in recent_leg_votes
        for tag in set(votaciones[i].get("etiquetas") or [])
        if tag not in hidden_tags
    )
    eligible = [(t, n) for t, n in topic_counts.most_common() if n >= MIN_TOPIC_VOTES]
    keep = {t for t, _ in eligible[:MAX_TOPICS]} | set(preferred_tags)
    topics = [(t, n) for t, n in eligible if t in keep]

    votes, row_of = [], {}
    out_topics = []
    for tag, n in topics:
        tally = {g: [0, 0, 0] for g in groups}
        recent = []
        for i in recent_leg_votes:
            if tag not in (votaciones[i].get("etiquetas") or []):
                continue
            for g, code in pos_by_vote[i].items():
                if g in tally:
                    tally[g][code - 1] += 1
            if len(recent) < RECENT_PER_TOPIC:
                if i not in row_of:
                    row_of[i] = len(votes)
                    votes.append({
                        "id": votaciones[i]["id"],
                        "titulo": votaciones[i].get("titulo_ciudadano", ""),
                        "fecha": iso_date(votaciones[i].get("fecha")),
                        "pos": {g: c for g, c in pos_by_vote[i].items() if g in tally},
                    })
                recent.append(row_of[i])
        out_topics.append({"tag": tag, "n": n, "tally": tally, "recent": recent})

    return {"groups": groups, "topics": out_topics, "votes": votes}


def build_scope(path_dir, hidden_tags):
    meta = read_json(os.path.join(path_dir, "votaciones_meta.json"))
    manifest_path = os.path.join(path_dir, "manifest_home.json")
    manifest = read_json(manifest_path) if os.path.exists(manifest_path) else {}

    votaciones = meta.get("votaciones", [])
    results = meta.get("votResults", [])
    grupos = meta.get("grupos", [])
    id_to_idx = {v["id"]: i for i, v in enumerate(votaciones)}
    # The published order sorts dates as text, which breaks D/M/YYYY dates.
    by_recency = sorted(
        range(len(votaciones)),
        key=lambda i: (parse_date(votaciones[i].get("fecha")) or date.min, i),
        reverse=True,
    )
    current_leg = votaciones[by_recency[0]]["legislatura"] if by_recency else None

    featured = [id_to_idx[v["id"]] for v in manifest.get("featuredVotes", []) if v.get("id") in id_to_idx]
    legs = {votaciones[i]["legislatura"] for i in featured} | ({current_leg} if current_leg else set())
    tallies, detail = {}, {}
    for leg in legs:
        rows, leg_detail = load_votos(path_dir, leg)
        tallies.update(tally_by_group(rows, grupos))
        detail.update(leg_detail)

    leg_votes = [i for i in by_recency if votaciones[i]["legislatura"] == current_leg]
    candidates = featured or [i for i in leg_votes if is_contested(results[i])]
    # Scopes without nominal votes still get a spotlight: the home then draws
    # the chamber from the totals alone ("groups": null).
    spotlight = [
        {**vote_summary(votaciones[i], results[i]),
         "resumen": (detail.get(str(i)) or {}).get("resumen", ""),
         "groups": tallies.get(i)}
        for i in candidates[:SPOTLIGHT_SIZE]
    ]
    nominal_leg_votes = [i for i in leg_votes if i in tallies]

    return {
        "legislatura": current_leg,
        "spotlight": spotlight,
        "questions": build_questions(
            votaciones, nominal_leg_votes, tallies, hidden_tags,
            preferred_tags=[tag for tag, _label in manifest.get("heroExamples", [])],
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-dir", default=PUBLIC_DIR)
    args = parser.parse_args(argv)

    ambitos = read_json(os.path.join(args.public_dir, "ambitos.json")).get("ambitos", [])
    hidden_tags = BASE_HIDDEN_TAGS | {a["id"] for a in ambitos}
    for ambito in ambitos:
        path_dir = scope_dir(args.public_dir, ambito["id"])
        if not os.path.exists(os.path.join(path_dir, "votaciones_meta.json")):
            continue
        extras = build_scope(path_dir, hidden_tags)
        with open(os.path.join(path_dir, OUTPUT_NAME), "w", encoding="utf-8") as f:
            json.dump(extras, f, ensure_ascii=False, separators=(",", ":"))
        q = extras["questions"]
        print(
            f"{ambito['id']}: legislatura {extras['legislatura']}, {len(extras['spotlight'])} destacadas, "
            f"{len(q['topics'])} temas, {len(q['votes'])} votaciones de ejemplo"
        )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
sys.path.append(str(SCRIPTS_DIR))
import ai_utils  # noqa: E402

AMBITOS_PATH = ROOT / "public" / "data" / "ambitos.json"
PROMPT_PATH = ROOT / "scripts" / "prompt_categorizacion.txt"

GENERIC_TITLE_PATTERNS = [
    re.compile(r"^asunto parlamentario sin clasificar$", re.I),
    re.compile(r"^votaci[oó]n(?:\s+desconocida|\s+sin\s+t[íi]tulo)?$", re.I),
    re.compile(r"^votaci[oó]n\s+sobre\s+un\s+asunto", re.I),
    re.compile(r"^votaci[oó]n\s+de\s+tr[aá]mite", re.I),
    re.compile(r"^votaci[oó]n\s+parlamentaria$", re.I),
    re.compile(r"^votaci[oó]n\s+ordinaria$", re.I),
    re.compile(r"^\(?pausa\.?\)?\s*el$", re.I),
    re.compile(r"^votaci[oó]n\s+de\s+la$", re.I),
]

LOW_SIGNAL_SOURCE_PATTERNS = [
    re.compile(r"^\s*(?:president[ea]|vicepresident[ea]|secretari[oa])\b", re.I),
    re.compile(r"^\s*(?:el\s+señor|la\s+señora)\b", re.I),
    re.compile(r"^\s*votaci[oó]n(?:\s|$)", re.I),
    re.compile(r"^\s*proposiciones?\s+no\s+de\s+ley\s+que\s+han\s+sido\s+debatidas", re.I),
    re.compile(r"^\s*proposiciones?\s+no\s+de\s+ley\s+en\s+el\s+orden", re.I),
    re.compile(r"^\s*intervenci[oó]n\s+de\s+la\s+presidencia", re.I),
]


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def words(text: str) -> int:
    return len([w for w in str(text or "").strip().split() if w])


def is_generic_title(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return True
    return any(pattern.search(value) for pattern in GENERIC_TITLE_PATTERNS)


def is_generic_summary(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return True
    return bool(re.search(r"^votaci[oó]n\s+(?:nominal|en|de)", value, re.I) or re.search(r"^asunto parlamentario", value, re.I))


def is_low_signal_source_title(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return True
    if any(pattern.search(value) for pattern in LOW_SIGNAL_SOURCE_PATTERNS):
        return True
    if words(value) <= 2:
        return True
    return False


def cache_entry_satisfies_reasons(entry: dict | None, reasons: list[str]) -> bool:
    if not isinstance(entry, dict):
        return False
    title = str(entry.get("titulo_ciudadano") or "").strip()
    category = str(entry.get("categoria_principal") or "").strip()
    summary = str(entry.get("resumen_sencillo") or "").strip()
    proponente = str(entry.get("proponente") or "").strip()

    checks = []
    for reason in reasons:
        if reason == "retitle":
            checks.append((not is_generic_title(title)) and words(title) <= 26)
        elif reason == "recategorize":
            checks.append(bool(category) and category != "Otros")
        elif reason == "summary":
            checks.append(not is_generic_summary(summary))
        elif reason == "proponente":
            checks.append(bool(proponente) and proponente.lower() != "desconocido")

    if not checks:
        return False
    return all(checks)


def scope_paths(scope_id: str):
    if scope_id == "nacional":
        return {
            "public_base": ROOT / "public" / "data",
            "cache": ROOT / "data" / "cache_categorias.json",
            "raw_base": ROOT / "data",
        }
    return {
        "public_base": ROOT / "public" / "data" / scope_id,
        "cache": ROOT / "data" / scope_id / "cache_categorias.json",
        "raw_base": ROOT / "data" / scope_id,
    }


def load_detail_by_leg(public_base: Path, legislaturas):
    by_leg = {}
    for leg in legislaturas:
        payload = load_json(public_base / f"votos_{leg}.json", {"votos": [], "detail": {}})
        by_leg[leg] = payload.get("detail", {})
    return by_leg


def load_raw_title_by_vote(scope_id: str, legislaturas):
    if scope_id == "nacional":
        return {}
    mapping = {}
    for leg in legislaturas:
        raw_path = ROOT / "data" / scope_id / f"votos_{leg}_raw.json"
        raw_votes = load_json(raw_path, [])
        for vote in raw_votes:
            vote_id = vote.get("id")
            title = str(vote.get("titulo") or "").strip()
            if vote_id and title:
                mapping[vote_id] = title
    return mapping


def collect_titles_for_scope(scope, max_titles: int | None):
    scope_id = scope["id"]
    legislaturas = scope.get("legislaturas", [])
    paths = scope_paths(scope_id)

    meta = load_json(paths["public_base"] / "votaciones_meta.json", None)
    if not meta:
        return {
            "scope": scope_id,
            "titles": [],
            "reasons": {},
            "error": "missing_votaciones_meta",
            "cache_path": paths["cache"],
        }

    detail_by_leg = load_detail_by_leg(paths["public_base"], legislaturas)
    raw_title_by_vote = load_raw_title_by_vote(scope_id, legislaturas)

    categories = meta.get("categorias", [])
    otros_idx = categories.index("Otros") if "Otros" in categories else -1
    votes = meta.get("votaciones", [])

    title_reasons = defaultdict(set)
    title_impact = Counter()

    for idx, vote in enumerate(votes):
        leg = vote.get("legislatura")
        detail = (detail_by_leg.get(leg) or {}).get(str(idx), {})
        title = str(vote.get("titulo_ciudadano") or "").strip()
        summary = str(detail.get("resumen") or "").strip()

        raw_title = ""
        if scope_id == "nacional":
            raw_title = str(detail.get("textoOficial") or "").strip()
        else:
            raw_title = str(raw_title_by_vote.get(vote.get("id")) or detail.get("textoOficial") or "").strip()
        if not raw_title:
            raw_title = title
        if not raw_title:
            continue

        low_signal_source = is_low_signal_source_title(raw_title)
        needs_retitle = is_generic_title(title) or words(title) > 26
        needs_recat = (
            (vote.get("categoria") == otros_idx)
            and (not is_generic_title(title))
            and words(title) >= 4
            and not low_signal_source
        )
        needs_summary = is_generic_summary(summary) and not low_signal_source
        needs_proponente = False
        if "proponente" in vote:
            prop = str(vote.get("proponente") or "").strip()
            needs_proponente = ((not prop) or (prop.lower() == "desconocido")) and not low_signal_source

        if not (needs_retitle or needs_recat or needs_summary or needs_proponente):
            continue

        if needs_retitle:
            title_reasons[raw_title].add("retitle")
        if needs_recat:
            title_reasons[raw_title].add("recategorize")
        if needs_summary:
            title_reasons[raw_title].add("summary")
        if needs_proponente:
            title_reasons[raw_title].add("proponente")
        title_impact[raw_title] += 1

    ordered_titles = sorted(
        title_reasons.keys(),
        key=lambda t: (title_impact[t], len(title_reasons[t]), len(t)),
        reverse=True,
    )
    if max_titles is not None:
        ordered_titles = ordered_titles[:max_titles]

    reasons = {title: sorted(title_reasons[title]) for title in ordered_titles}
    return {
        "scope": scope_id,
        "titles": ordered_titles,
        "reasons": reasons,
        "impact": {title: title_impact[title] for title in ordered_titles},
        "cache_path": paths["cache"],
        "error": None,
    }


def categorize_titles_with_cli(titles, prompt_text, batch_size, on_batch_done=None):
    updated = {}
    total_batches = (len(titles) - 1) // batch_size + 1 if titles else 0
    for i in range(0, len(titles), batch_size):
        batch = titles[i : i + batch_size]
        id_by_title = {title: f"tid_{ai_utils.text_hash(title)}" for title in batch}
        payload = [(id_by_title[title], title) for title in batch]
        print(
            f"    Batch {i // batch_size + 1}/{total_batches} ({len(batch)} títulos)",
            flush=True,
        )

        result = {}
        # Explicitly pass api_key=None to force gemini-cli path (OAuth local), never SDK/API key billing.
        for attempt in range(1, 4):
            result = ai_utils.categorize_batch(payload, None, prompt_text)
            if result:
                break
            print(f"      retry {attempt}/3 sin respuesta válida del CLI", flush=True)
        for title in batch:
            tid = id_by_title[title]
            if tid in result:
                updated[title] = result[tid]
        if on_batch_done:
            on_batch_done(updated, i // batch_size + 1, total_batches)
    return updated


def main():
    parser = argparse.ArgumentParser(description="Refresca cache de categorización usando gemini-cli (sin API key).")
    parser.add_argument(
        "--scopes",
        default="nacional,andalucia,cyl,madrid",
        help="Lista de ámbitos separados por coma. Ej: nacional,andalucia,cyl,madrid",
    )
    parser.add_argument("--batch-size", type=int, default=20, help="Tamaño de lote para llamadas al CLI.")
    parser.add_argument(
        "--prompt-file",
        default=str(PROMPT_PATH),
        help="Ruta al prompt para la categorización (por defecto prompt_categorizacion.txt).",
    )
    parser.add_argument(
        "--max-titles-per-scope",
        type=int,
        default=None,
        help="Límite opcional de títulos por ámbito (por impacto).",
    )
    parser.add_argument(
        "--skip-satisfied-cache",
        action="store_true",
        default=True,
        help="Saltar títulos que ya están bien cubiertos en cache para las razones detectadas (resume incremental).",
    )
    parser.add_argument(
        "--no-skip-satisfied-cache",
        action="store_false",
        dest="skip_satisfied_cache",
        help="No saltar entradas ya satisfechas en cache; recategorizar todo.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar candidatos, sin llamar a IA.")
    args = parser.parse_args()

    selected_scopes = {item.strip() for item in args.scopes.split(",") if item.strip()}
    ambitos = load_json(AMBITOS_PATH, {"ambitos": []}).get("ambitos", [])

    prompt_path = Path(args.prompt_file)
    if not prompt_path.is_absolute():
        prompt_path = ROOT / prompt_path
    with prompt_path.open("r", encoding="utf-8") as f:
        prompt_text = f.read()

    total_titles = 0
    total_updated = 0

    for scope in ambitos:
        scope_id = scope.get("id")
        if scope_id not in selected_scopes:
            continue

        plan = collect_titles_for_scope(scope, args.max_titles_per_scope)
        if plan["error"]:
            print(f"[{scope_id}] ERROR: {plan['error']}", flush=True)
            continue

        all_titles = plan["titles"]
        cache_path = plan["cache_path"]
        cache = load_json(cache_path, {})

        titles = all_titles
        if args.skip_satisfied_cache:
            titles = [
                title
                for title in all_titles
                if not cache_entry_satisfies_reasons(cache.get(title), plan["reasons"].get(title, []))
            ]

        total_titles += len(titles)
        skipped = len(all_titles) - len(titles)
        print(
            f"[{scope_id}] candidatos IA: {len(all_titles)} | pendientes: {len(titles)} | saltados(cache): {skipped}",
            flush=True,
        )
        if not titles:
            continue
        for sample in titles[:8]:
            reasons = ",".join(plan["reasons"].get(sample, []))
            print(f"  - ({plan['impact'].get(sample, 0)}x) [{reasons}] {sample[:140]}", flush=True)

        if args.dry_run:
            continue

        print(f"[{scope_id}] refrescando cache con gemini-cli en {cache_path}", flush=True)

        persisted = {"count": 0}

        def persist_checkpoint(updated_map, batch_no, total_batches):
            new_items = 0
            for k, v in updated_map.items():
                prev = cache.get(k)
                if prev != v:
                    cache[k] = v
                    new_items += 1
            if new_items:
                save_json(cache_path, cache)
                persisted["count"] += new_items
                print(
                    f"      checkpoint batch {batch_no}/{total_batches}: +{new_items} guardados (total_guardado={persisted['count']})",
                    flush=True,
                )

        updated_entries = categorize_titles_with_cli(
            titles,
            prompt_text,
            args.batch_size,
            on_batch_done=persist_checkpoint,
        )
        if not updated_entries:
            print(f"[{scope_id}] no se recibieron resultados válidos del CLI.", flush=True)
            continue
        # Ensure final state is persisted even if no diff was detected in last checkpoint.
        save_json(cache_path, cache)
        total_updated += len(updated_entries)
        print(
            f"[{scope_id}] actualizados {len(updated_entries)} títulos en cache (nuevos/actualizados guardados={persisted['count']}).",
            flush=True,
        )

    print(f"\nResumen: candidatos={total_titles}, actualizados={total_updated}, dry_run={args.dry_run}", flush=True)


if __name__ == "__main__":
    main()

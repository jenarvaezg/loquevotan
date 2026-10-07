// PROTOTYPE — desechable. Cuatro direcciones visuales para la portada sobre la
// ruta `/`, conmutables con `?variant=` (solo en dev). Datos reales; nada de
// esto debe llegar a main tal cual.
import { computed, watch } from "vue";
import { useData } from "../../composables/useData";
import { getGroupInfo, isNonPartisanGroup, majorityPosition, HIDDEN_TAGS } from "../../utils";

export const VARIANTS = [
  { key: "actual", name: "Diseño actual" },
  { key: "hemiciclo", name: "A — Hemiciclo" },
  { key: "pregunta", name: "B — La pregunta" },
  { key: "marcador", name: "C — Marcador" },
  { key: "orla", name: "D — La orla" },
  { key: "pregunta-hemiciclo", name: "E — Pregunta → hemiciclo" },
  { key: "hemiciclo-pregunta", name: "F — Hemiciclo → pregunta" },
];

// Rough left-to-right seating so the hemicycle reads like the real chamber.
const LEFT_TO_RIGHT = [
  "EH Bildu", "BNG", "CUP", "Podemos", "Podemos/IU", "UP", "PorA", "Adelante", "IU",
  "Sumar", "Comuns", "Más Madrid", "ERC", "PSOE", "PSC-PSOE", "PNV", "Junts", "Junts/Plu",
  "DL", "CiU", "CC", "UPL-SY", "Mixto", "Mixt", "No Adscrito", "Ciudadanos", "CS", "UPyD",
  "PP", "VOX",
];

export const VOTE_WORD = { 1: "A favor", 2: "En contra", 3: "Abstención", 4: "No vota" };

const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const MONTHS_LONG = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

export function shortDate(iso) {
  const [y, m, d] = String(iso || "").split("-");
  if (!d) return iso || "";
  return `${Number(d)} ${MONTHS[Number(m) - 1]} ${y}`;
}

export function longDate(iso) {
  const [y, m, d] = String(iso || "").split("-");
  if (!d) return iso || "";
  return `${Number(d)} de ${MONTHS_LONG[Number(m) - 1]} de ${y}`;
}

export function partyRank(label) {
  const i = LEFT_TO_RIGHT.indexOf(label);
  return i === -1 ? LEFT_TO_RIGHT.indexOf("Mixto") : i;
}

export function loadFonts(href) {
  if (document.querySelector(`link[data-proto-font="${href}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  link.dataset.protoFont = href;
  document.head.appendChild(link);
}

// "Apellido Apellido, Nombre" -> "Nombre Apellido Apellido"
export function displayName(raw) {
  const [last, first] = String(raw || "").split(",").map((s) => s.trim());
  return first ? `${first} ${last}` : last;
}

export function usePrototypeData() {
  const d = useData();

  const latestLeg = computed(() => {
    const idx = d.sortedVotIdxByDate.value[0];
    return idx == null ? null : d.votaciones.value[idx]?.legislatura || null;
  });

  watch(latestLeg, (leg) => { if (leg) d.loadVotosForLeg(leg); }, { immediate: true });

  const votosReady = computed(() => !!latestLeg.value && d.votosLoaded.value.has(latestLeg.value));

  const legVotIdx = computed(() =>
    d.sortedVotIdxByDate.value.filter((i) => d.votaciones.value[i]?.legislatura === latestLeg.value)
  );

  function votIdx(id) {
    const i = d.votIdById.value[id];
    return i == null ? null : i;
  }

  // One entry per deputy who has a record in that vote.
  function ballots(vIdx) {
    const rows = d.votosByVotacion.value[vIdx] || [];
    return rows.map((g) => {
      const v = d.votos.value[g];
      const info = getGroupInfo(d.grupos.value[v[2]]);
      return { dip: v[1], group: d.grupos.value[v[2]], label: info.label, color: info.color, voto: v[3] };
    });
  }

  function partyTally(vIdx) {
    const byLabel = new Map();
    for (const b of ballots(vIdx)) {
      if (!byLabel.has(b.label)) {
        byLabel.set(b.label, { label: b.label, color: b.color, counts: { 1: 0, 2: 0, 3: 0, 4: 0 }, total: 0 });
      }
      const t = byLabel.get(b.label);
      t.counts[b.voto] = (t.counts[b.voto] || 0) + 1;
      t.total += 1;
    }
    return [...byLabel.values()]
      .map((t) => ({ ...t, position: majorityPosition(t.counts) }))
      .sort((a, b) => partyRank(a.label) - partyRank(b.label));
  }

  // Deputies seated now: anyone with a record in the last few votes.
  const currentDips = computed(() => {
    if (!votosReady.value) return [];
    const seen = new Set();
    for (const v of legVotIdx.value.slice(0, 6)) {
      for (const b of ballots(v)) seen.add(b.dip);
    }
    return [...seen];
  });

  // Parties with a group line in the current legislature: label -> group codes.
  const legParties = computed(() => {
    if (!votosReady.value) return [];
    const codes = new Map();
    for (const v of legVotIdx.value.slice(0, 200)) {
      const gm = d.votacionDetail.value[v]?.group_majority || {};
      for (const code of Object.keys(gm)) {
        if (isNonPartisanGroup(code)) continue;
        const info = getGroupInfo(code);
        if (!codes.has(info.label)) codes.set(info.label, { label: info.label, color: info.color, codes: new Set() });
        codes.get(info.label).codes.add(code);
      }
    }
    return [...codes.values()].sort((a, b) => partyRank(a.label) - partyRank(b.label));
  });

  function partyPosition(vIdx, party) {
    const gm = d.votacionDetail.value[vIdx]?.group_majority || {};
    for (const code of party.codes) if (gm[code]) return gm[code];
    return null;
  }

  const legTopics = computed(() => {
    const counts = new Map();
    for (const v of legVotIdx.value) {
      for (const t of d.votaciones.value[v].etiquetas || []) {
        if (HIDDEN_TAGS.has(t) || t === "procedimiento_parlamentario") continue;
        counts.set(t, (counts.get(t) || 0) + 1);
      }
    }
    return [...counts.entries()].filter(([, n]) => n >= 4).sort((a, b) => b[1] - a[1]);
  });

  return {
    ...d,
    latestLeg,
    votosReady,
    legVotIdx,
    votIdx,
    ballots,
    partyTally,
    currentDips,
    legParties,
    partyPosition,
    legTopics,
  };
}

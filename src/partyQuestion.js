// "¿Votó [partido] a favor de [tema]?" over the home_extras.json questions.
import { getGroupInfo, isNonPartisanGroup, fmt } from "./utils";
import { partyRank } from "./hemicycle";

const ARTICLE = { PP: "el PP", PSOE: "el PSOE", PNV: "el PNV", "PSC-PSOE": "el PSC", VOX: "Vox", CS: "Ciudadanos" };

export function partyName(label) {
  return ARTICLE[label] || label;
}

/** Parties with a group line, merging group codes that share a label. */
export function questionParties(questions) {
  const byLabel = new Map();
  for (const code of questions?.groups || []) {
    if (isNonPartisanGroup(code)) continue;
    const { label, color } = getGroupInfo(code);
    if (!byLabel.has(label)) byLabel.set(label, { label, color, codes: [] });
    byLabel.get(label).codes.push(code);
  }
  return [...byLabel.values()].sort((a, b) => partyRank(a.label) - partyRank(b.label));
}

/** How often the party voted for, against and abstained on a topic. */
export function topicAnswer(topic, party) {
  const counts = { 1: 0, 2: 0, 3: 0 };
  for (const code of party?.codes || []) {
    const t = topic?.tally?.[code];
    if (!t) continue;
    counts[1] += t[0];
    counts[2] += t[1];
    counts[3] += t[2];
  }
  return { counts, n: counts[1] + counts[2] + counts[3] };
}

export function positionOf(vote, party) {
  for (const code of party?.codes || []) {
    if (vote?.pos?.[code]) return vote.pos[code];
  }
  return null;
}

export function answerLead({ counts, n }) {
  if (!n) return "No hay votaciones suficientes sobre este tema.";
  const share = counts[1] / n;
  if (share >= 0.85) return "Sí, casi siempre.";
  if (share >= 0.6) return "La mayoría de las veces.";
  if (share > 0.4) return "Depende de la votación.";
  if (share > 0.15) return "Pocas veces.";
  return "No, casi nunca.";
}

export function answerDetail({ counts, n }, tag, partyLabel) {
  if (!n) return "";
  const times = (k) => `${k} ${k === 1 ? "vez" : "veces"}`;
  const parts = [
    counts[1] && `votó a favor ${times(counts[1])}`,
    counts[2] && `${counts[1] ? "" : "votó "}en contra ${times(counts[2])}`,
    counts[3] && `se abstuvo ${times(counts[3])}`,
  ].filter(Boolean);
  const list = parts.length > 1 ? `${parts.slice(0, -1).join(", ")} y ${parts.at(-1)}` : parts[0];
  const votes = n === 1 ? "votación" : "votaciones";
  return `En ${n} ${votes} de esta legislatura sobre ${fmt(tag)}, ${partyName(partyLabel)} ${list}.`;
}

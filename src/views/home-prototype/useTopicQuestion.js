// PROTOTYPE — lógica de «¿Votó [partido] a favor de [tema]?» para las
// variantes E y F (misma que la variante B).
import { computed, ref, watch } from "vue";
import { fmt } from "../../utils";

const ARTICLE = { PP: "el PP", PSOE: "el PSOE", PNV: "el PNV", "PSC-PSOE": "el PSC", VOX: "Vox", CS: "Ciudadanos" };
export const named = (label) => ARTICLE[label] || label;

export function useTopicQuestion(data) {
  const { votaciones, legParties, legTopics, legVotIdx, partyPosition } = data;

  const partyKey = ref("PP");
  const topic = ref("subir_pensiones");
  watch(legParties, (list) => {
    if (list.length && !list.some((p) => p.label === partyKey.value)) {
      partyKey.value = (list.find((p) => p.label === "PP") || list[0]).label;
    }
  }, { immediate: true });
  watch(legTopics, (list) => {
    if (list.length && !list.some(([t]) => t === topic.value)) topic.value = list[0][0];
  }, { immediate: true });

  const party = computed(() => legParties.value.find((p) => p.label === partyKey.value) || null);
  const accent = computed(() => party.value?.color || "#000");
  const topicVotes = computed(() =>
    legVotIdx.value.filter((i) => (votaciones.value[i].etiquetas || []).includes(topic.value))
  );

  function tallyFor(p) {
    const counts = { 1: 0, 2: 0, 3: 0 };
    let n = 0;
    for (const i of topicVotes.value) {
      const pos = partyPosition(i, p);
      if (pos >= 1 && pos <= 3) { counts[pos]++; n++; }
    }
    return { counts, n };
  }

  const answer = computed(() => (party.value ? tallyFor(party.value) : null));
  const lead = computed(() => {
    const a = answer.value;
    if (!a?.n) return "No hay votaciones suficientes sobre este tema.";
    const f = a.counts[1] / a.n;
    if (f >= 0.85) return "Sí, casi siempre.";
    if (f >= 0.6) return "La mayoría de las veces.";
    if (f > 0.4) return "Depende de la votación.";
    if (f > 0.15) return "Pocas veces.";
    return "No, casi nunca.";
  });
  const detail = computed(() => {
    const a = answer.value;
    if (!a?.n) return "";
    const times = (k) => `${k} ${k === 1 ? "vez" : "veces"}`;
    const parts = [
      a.counts[1] && `votó a favor ${times(a.counts[1])}`,
      a.counts[2] && `${a.counts[1] ? "" : "votó "}en contra ${times(a.counts[2])}`,
      a.counts[3] && `se abstuvo ${times(a.counts[3])}`,
    ].filter(Boolean);
    const list = parts.length > 1 ? `${parts.slice(0, -1).join(", ")} y ${parts.at(-1)}` : parts[0];
    return `En ${a.n} votaciones de esta legislatura sobre ${fmt(topic.value)}, ${named(partyKey.value)} ${list}.`;
  });
  const others = computed(() =>
    legParties.value.map((p) => ({ p, ...tallyFor(p) })).filter((o) => o.n > 0)
  );
  const shortcuts = computed(() =>
    legTopics.value.slice(0, 7).map(([t]) => t).filter((t) => t !== topic.value).slice(0, 6)
  );

  return { partyKey, topic, party, accent, topicVotes, tallyFor, answer, lead, detail, others, shortcuts };
}

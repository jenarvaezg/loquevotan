export const LEGISLATURAS = [
  {
    id: "X",
    nombre: "X Legislatura",
    desde: "2012-01-01",
    hasta: "2015-10-27",
  },
  {
    id: "XI",
    nombre: "XI Legislatura",
    desde: "2016-01-13",
    hasta: "2016-05-03",
  },
  {
    id: "XII",
    nombre: "XII Legislatura",
    desde: "2016-07-19",
    hasta: "2019-02-13",
  },
  {
    id: "XIII",
    nombre: "XIII Legislatura",
    desde: "2019-05-21",
    hasta: "2019-09-24",
  },
  {
    id: "XIV",
    nombre: "XIV Legislatura",
    desde: "2020-01-03",
    hasta: "2023-05-29",
  },
  {
    id: "XV",
    nombre: "XV Legislatura",
    desde: "2023-08-17",
    // Cortes disueltas el 2026-10-06; la Diputación Permanente sigue en la XV
    // hasta la sesión constitutiva de la XVI.
    hasta: "2026-12-22",
  },
  {
    id: "XVI",
    nombre: "XVI Legislatura",
    desde: "2026-12-23",
    hasta: "2099-12-31",
  },
];

const ROMAN_VALUES = { I: 1, V: 5, X: 10, L: 50, C: 100 };

/** "XIV" -> 14. Unknown characters yield 0 so callers can sort safely. */
export function romanToInt(roman) {
  let total = 0;
  let prev = 0;
  const chars = String(roman || "").toUpperCase().split("").reverse();
  for (const ch of chars) {
    const value = ROMAN_VALUES[ch];
    if (!value) return 0;
    total = value < prev ? total - value : total + value;
    prev = Math.max(prev, value);
  }
  return total;
}

export const VOTO_LABELS = { 1: "A favor", 2: "En contra", 3: "Abstención", 4: "No vota" };

export const VOTES_PER_PAGE = 20;
export const DIPS_PER_PAGE = 30;

export const HIDDEN_TAGS = new Set(["nacional", "cyl", "andalucia", "madrid", "catalunya"]);

const VOTE_ID_SCOPE_PREFIXES = { AND: "andalucia", CYL: "cyl", MAD: "madrid", CAT: "catalunya" };

/** Scope a vote ID belongs to: regional IDs are prefixed, national ones are "XV-164-1". */
export function scopeFromVoteId(id) {
  const value = String(id || "").trim();
  const prefix = value.split("-")[0].toUpperCase();
  if (VOTE_ID_SCOPE_PREFIXES[prefix]) return VOTE_ID_SCOPE_PREFIXES[prefix];
  if (/^[IVXLC]+-\d+-\d+$/i.test(value)) return "nacional";
  return null;
}

/** Copy text; resolves to false when the clipboard is unavailable or denied. */
export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for insecure contexts / denied permission.
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }
}

export function displayTags(tags) {
  if (!Array.isArray(tags)) return [];
  return tags.filter(t => !HIDDEN_TAGS.has((t || '').toLowerCase()));
}

export function getLeg(fecha) {
  for (let i = LEGISLATURAS.length - 1; i >= 0; i--) {
    if (fecha >= LEGISLATURAS[i].desde && fecha <= LEGISLATURAS[i].hasta) {
      return LEGISLATURAS[i].id;
    }
  }
  return "";
}

export function fmt(s) {
  return (s || "").replace(/_/g, " ");
}

export function normalize(s) {
  if (!s) return "";
  return s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

export function matchSearch(query, target) {
  if (!query || !target) return false;
  const tokens = normalize(query).split(/\s+/).filter(Boolean);
  const normalizedTarget = normalize(target);
  return tokens.every(token => normalizedTarget.includes(token));
}

export function pct(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return (n * 100).toFixed(1) + "%";
}

// Groups that gather several parties (or none): there's no "group line", so
// loyalty and rebellion aren't measured against them.
const NON_PARTISAN_GROUP_RE = /mixto|^gmx$|plural|^gplu$|no adscrit|sin grupo|desconocido|unknown/i;

export function isNonPartisanGroup(name) {
  return NON_PARTISAN_GROUP_RE.test(String(name || ""));
}

/**
 * Group position from vote counts {1: favor, 2: contra, 3: abstención}: the
 * option with an absolute majority of the votes cast, or null if none.
 * Same rule as group_majority in the data pipeline.
 */
export function majorityPosition(counts) {
  const cast = (counts[1] || 0) + (counts[2] || 0) + (counts[3] || 0);
  for (const code of [1, 2, 3]) {
    if ((counts[code] || 0) * 2 > cast) return code;
  }
  return null;
}

export function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

export function avatarStyle(name) {
  const hue =
    Math.abs(name.split("").reduce((a, c) => a + c.charCodeAt(0), 0)) % 360;
  return { background: `hsl(${hue},55%,45%)` };
}

export function avatarInitials(name) {
  const parts = name.split(",");
  const apellido = (parts[0] || "").trim();
  const nombre = (parts[1] || "").trim();
  return ((nombre[0] || "") + (apellido[0] || "")).toUpperCase();
}

export function resultMarginText(r) {
  if (r.asentimiento) return "Aprobada por asentimiento";
  if (r.result === "Empate") return "Empate";
  return r.result + " por " + r.margin + " votos";
}

export function dipPhotoUrl(fotoEntry) {
  if (!fotoEntry) return null;
  // If it's already a full URL string (like for Andalucia), return it
  if (typeof fotoEntry === 'string') return fotoEntry;
  // Pick the most recent legislatura available
  const legs = Object.keys(fotoEntry);
  if (legs.length === 0) return null;
  const best = legs.reduce((a, b) => (romanToInt(a) >= romanToInt(b) ? a : b));
  const cod = fotoEntry[best];
  const num = romanToInt(best);
  return `https://www.congreso.es/docu/imgweb/diputados/${cod}_${num}.jpg`;
}

export const SUB_TIPO_LABELS = {
  final: "Votación final",
  totalidad: "Enmienda a la totalidad",
  transaccional: "Enmienda transaccional",
  particular: "Voto particular",
  enmienda: "Enmienda",
  separada: "Votación separada",
  dictamen: "Dictamen",
  propuesta: "Propuesta de resolución",
  otro: "Otro",
};

export function subTipoLabel(tipo) {
  return SUB_TIPO_LABELS[tipo] || tipo || "";
}

export function subTipoBadgeClass(tipo) {
  if (tipo === "final" || tipo === "dictamen") return "badge--final";
  if (tipo === "totalidad") return "badge--totalidad";
  if (tipo === "transaccional") return "badge--transaccional";
  return "badge--enmienda";
}

export function affinityColor(pct) {
  if (pct >= 0.8) return "#16a34a";
  if (pct >= 0.6) return "#86efac";
  if (pct >= 0.4) return "#fde047";
  if (pct >= 0.2) return "#fca5a5";
  return "#dc2626";
}

export function votoPillClass(code) {
  return code === 1
    ? "voto-pill--favor"
    : code === 2
      ? "voto-pill--contra"
      : code === 3
        ? "voto-pill--abstencion"
        : "voto-pill--no-vota";
}

const GROUP_MAP = {
  // National
  'GS': { label: 'PSOE', color: '#ef1c27' },
  'GP': { label: 'PP', color: '#0056a0' },
  'GVOX': { label: 'VOX', color: '#63be21' },
  'GSUMAR': { label: 'Sumar', color: '#e51c55' },
  'GCs': { label: 'Ciudadanos', color: '#eb6109' },
  'GEH Bildu': { label: 'EH Bildu', color: '#b5cf18' },
  'GER': { label: 'ERC', color: '#ffb232' },
  'GR': { label: 'ERC', color: '#ffb232' },
  'GJxCAT': { label: 'Junts', color: '#00c3b2' },
  'GPlu': { label: 'Junts/Plu', color: '#00c3b2' },
  'GV (EAJ-PNV)': { label: 'PNV', color: '#008000' },
  'GCUP-EC-EM': { label: 'Podemos', color: '#673ab7' },
  'GCUP-EC-GC': { label: 'Podemos', color: '#673ab7' },
  'GP-EC-EM': { label: 'Podemos', color: '#673ab7' },
  'GUPyD': { label: 'UPyD', color: '#ff00ff' },
  'GMx': { label: 'Mixto', color: '#64748b' },
  'GC-CiU': { label: 'CiU', color: '#0033a0' },
  'GC-DL': { label: 'DL', color: '#00c3b2' },
  'GIP': { label: 'Podemos/IU', color: '#673ab7' },

  // Andalucia
  'PSOE DE ANDALUCÍA': { label: 'PSOE', color: '#ef1c27' },
  'POPULAR ANDALUZ': { label: 'PP', color: '#0056a0' },
  'VOX EN ANDALUCÍA': { label: 'VOX', color: '#63be21' },
  'POR ANDALUCÍA': { label: 'PorA', color: '#673ab7' },
  'ADELANTE ANDALUCÍA': { label: 'Adelante', color: '#00a551' },
  'UNIDAS PODEMOS POR ANDALUCÍA': { label: 'UP', color: '#673ab7' },
  'CIUDADANOS': { label: 'CS', color: '#eb6109' },
  'PODEMOS ANDALUCIA': { label: 'Podemos', color: '#673ab7' },
  'IU-LV CONV. POR ANDALUCÍA': { label: 'IU', color: '#ef1c27' },
  'MIXTO-ADELANTE ANDALUCÍA': { label: 'Adelante', color: '#00a551' },

  // CyL
  'PSOE': { label: 'PSOE', color: '#ef1c27' },
  'PP': { label: 'PP', color: '#0056a0' },
  'VOX': { label: 'VOX', color: '#63be21' },
  'CS': { label: 'CS', color: '#eb6109' },
  'UPL-SY': { label: 'UPL-SY', color: '#7b1c34' },
  'Mixto': { label: 'Mixto', color: '#64748b' },

  // Madrid
  'PSOE-M': { label: 'PSOE', color: '#ef1c27' },
  'Más Madrid': { label: 'Más Madrid', color: '#00dec5' },

  // Catalunya
  'PSC': { label: 'PSC-PSOE', color: '#ef1c27' },
  'Junts': { label: 'Junts', color: '#00c3b2' },
  'ERC': { label: 'ERC', color: '#ffb232' },
  'Comuns': { label: 'Comuns', color: '#673ab7' },
  'CUP': { label: 'CUP', color: '#fff200' },
  'Mixt': { label: 'Mixt', color: '#64748b' },
};

export function getGroupInfo(groupName) {
  const g = groupName || '';
  const info = GROUP_MAP[g];
  if (info) return info;

  // Fallbacks for contains or clean matches
  const lower = g.toLowerCase();
  if (lower.includes('psoe') || lower.includes('socialista')) return { label: 'PSOE', color: '#ef1c27' };
  if (lower.includes('popular') || lower === 'pp') return { label: 'PP', color: '#0056a0' };
  if (lower.includes('vox')) return { label: 'VOX', color: '#63be21' };
  if (lower.includes('podemos') || lower.includes('unidas')) return { label: 'Podemos', color: '#673ab7' };
  if (lower.includes('sumar')) return { label: 'Sumar', color: '#e51c55' };
  if (lower.includes('ciudadanos') || lower === 'cs') return { label: 'CS', color: '#eb6109' };
  if (lower.includes('erc') || lower.includes('republicano')) return { label: 'ERC', color: '#ffb232' };
  if (lower.includes('junts')) return { label: 'Junts', color: '#00c3b2' };
  if (lower.includes('pnv') || lower.includes('vasco')) return { label: 'PNV', color: '#008000' };
  if (lower.includes('bildu')) return { label: 'EH Bildu', color: '#b5cf18' };

  return { label: g, color: '#64748b' };
}

export function sanitizeGroupName(groupName) {
  const g = String(groupName || '').trim();
  if (!g) return '';
  if (g.toLowerCase() === 'unknown') return '';
  return g;
}

export function isMeaningfulGroupName(groupName) {
  return sanitizeGroupName(groupName).length > 0;
}

export function appBasePath() {
  const raw = import.meta.env.BASE_URL || "/";
  const withLeading = raw.startsWith("/") ? raw : `/${raw}`;
  return withLeading.endsWith("/") ? withLeading : `${withLeading}/`;
}

export function buildAbsoluteAppUrl(path, origin = window.location.origin) {
  const cleanOrigin = String(origin || window.location.origin).replace(/\/+$/, "");
  const base = appBasePath();
  const cleanPath = String(path || "").replace(/^\/+/, "");
  return `${cleanOrigin}${base}${cleanPath}`;
}

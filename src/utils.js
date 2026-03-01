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
    hasta: "2099-12-31",
  },
];

export const VOTO_LABELS = { 1: "A favor", 2: "En contra", 3: "Abstención" };

export const VOTES_PER_PAGE = 20;
export const DIPS_PER_PAGE = 30;

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

export function pct(n) {
  return (n * 100).toFixed(1) + "%";
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
  if (r.result === "Empate") return "Empate";
  return r.result + " por " + r.margin + " votos";
}

const LEG_TO_NUM = { X: 10, XI: 11, XII: 12, XIII: 13, XIV: 14, XV: 15 };

export function dipPhotoUrl(fotoEntry) {
  if (!fotoEntry) return null;
  // If it's already a full URL string (like for Andalucia), return it
  if (typeof fotoEntry === 'string') return fotoEntry;
  // Pick the most recent legislatura available
  const legs = Object.keys(fotoEntry);
  if (legs.length === 0) return null;
  const best = legs.reduce((a, b) =>
    (LEG_TO_NUM[a] || 0) >= (LEG_TO_NUM[b] || 0) ? a : b,
  );
  const cod = fotoEntry[best];
  const num = LEG_TO_NUM[best];
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
      : "voto-pill--abstencion";
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

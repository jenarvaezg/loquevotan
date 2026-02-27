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

export const VOTO_LABELS = { 1: "A favor", 2: "En contra", 3: "Abstencion" };

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

export function affinityColor(pct) {
  if (pct >= 0.8) return "#16a34a";
  if (pct >= 0.6) return "#86efac";
  if (pct >= 0.4) return "#fde047";
  if (pct >= 0.2) return "#fca5a5";
  return "#dc2626";
}

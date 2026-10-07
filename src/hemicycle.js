// Seat layout for the hemicycle chart. Each seat is one deputy: its colour is
// the party and its fill is the vote (solid yes, hollow no, half abstention).
import { getGroupInfo } from "./utils";

// Rough left-to-right seating, so the chart reads like the real chamber.
const LEFT_TO_RIGHT = [
  "EH Bildu", "BNG", "CUP", "Podemos", "Podemos/IU", "UP", "PorA", "Adelante", "IU",
  "Sumar", "Comuns", "Más Madrid", "ERC", "PSOE", "PSC-PSOE", "PNV", "Junts", "Junts/Plu",
  "DL", "CiU", "CC", "UPL-SY", "Mixto", "Mixt", "No Adscrito", "Ciudadanos", "CS", "UPyD",
  "PP", "VOX",
];
const MIDDLE = LEFT_TO_RIGHT.indexOf("Mixto");

export function partyRank(label) {
  const i = LEFT_TO_RIGHT.indexOf(label);
  return i === -1 ? MIDDLE : i;
}

// Inner radius of the arc, as a share of the outer one. The gap holds the score.
const INNER = 0.46;
const layoutCache = new Map();

/**
 * Positions for n seats in concentric rows, ordered left to right so that
 * consecutive seats form wedges. Coordinates are in a unit half-disc:
 * x in [-1, 1], y in [-1, 0].
 */
export function seatLayout(n) {
  if (n <= 0) return { seats: [], radius: 0 };
  if (layoutCache.has(n)) return layoutCache.get(n);

  const capacity = (rows) => {
    const step = (1 - INNER) / (rows - 1);
    return Array.from({ length: rows }, (_, i) => Math.floor((Math.PI * (INNER + i * step)) / step) + 1);
  };
  let rows = 3;
  while (capacity(rows).reduce((a, b) => a + b, 0) < n) rows++;

  const step = (1 - INNER) / (rows - 1);
  const caps = capacity(rows);
  const capTotal = caps.reduce((a, b) => a + b, 0);
  const perRow = caps.map((c) => Math.floor((c * n) / capTotal));
  let left = n - perRow.reduce((a, b) => a + b, 0);
  for (let i = rows - 1; left > 0; i = (i - 1 + rows) % rows) {
    if (perRow[i] < caps[i]) {
      perRow[i]++;
      left--;
    }
  }

  const seats = [];
  perRow.forEach((count, i) => {
    const r = INNER + i * step;
    for (let j = 0; j < count; j++) {
      const angle = count === 1 ? Math.PI / 2 : Math.PI - (j * Math.PI) / (count - 1);
      seats.push({ x: r * Math.cos(angle), y: -r * Math.sin(angle), angle, r });
    }
  });
  seats.sort((a, b) => b.angle - a.angle || a.r - b.r);

  const layout = { seats: seats.map(({ x, y }) => ({ x, y })), radius: step * 0.4 };
  layoutCache.set(n, layout);
  return layout;
}

// Within a party: yes, abstention, no, absent.
const VOTE_ORDER = { 1: 0, 3: 1, 2: 2, 4: 3 };

function sortBallots(ballots) {
  return ballots.sort(
    (a, b) =>
      partyRank(a.label) - partyRank(b.label) ||
      a.label.localeCompare(b.label) ||
      VOTE_ORDER[a.voto] - VOTE_ORDER[b.voto]
  );
}

/** groups: { groupName: [favor, contra, abstencion, noVota] } */
export function ballotsFromGroups(groups) {
  const ballots = [];
  for (const [group, counts] of Object.entries(groups || {})) {
    const { label, color } = getGroupInfo(group);
    counts.forEach((n, k) => {
      for (let i = 0; i < n; i++) ballots.push({ label, color, voto: k + 1 });
    });
  }
  return sortBallots(ballots);
}

/** Without nominal votes only the totals are known: seats carry no party. */
export function ballotsFromTotals({ favor = 0, contra = 0, abstencion = 0 }) {
  const ballots = [];
  [favor, contra, abstencion].forEach((n, k) => {
    for (let i = 0; i < n; i++) ballots.push({ label: "", color: null, voto: k + 1 });
  });
  return sortBallots(ballots);
}

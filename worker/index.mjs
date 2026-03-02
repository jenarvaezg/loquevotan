const SITE_NAME = "Lo Que Votan";
const BRAND_TITLE = "LoQueVotan.es";
const JSON_CACHE_TTL_MS = 5 * 60 * 1000;
const LEG_TO_NUM = { X: 10, XI: 11, XII: 12, XIII: 13, XIV: 14, XV: 15 };
const OG_CANVAS = { width: 1200, height: 630 };
const OG_COLORS = {
  bgA: "#0b1220",
  bgB: "#111c33",
  panel: "#0e172a",
  text: "#f8fafc",
  muted: "#cbd5e1",
  favor: "#22c55e",
  contra: "#ef4444",
  abst: "#facc15",
  noVota: "#64748b",
  border: "#1e293b",
};

const scopeMetaCache = new Map();
let ambitosCache = { expiresAt: 0, data: null };
const imageDataUriCache = new Map();

function stripTrailingSlash(value) {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isHttpUrl(value) {
  return /^https?:\/\//i.test(value);
}

function asAbsoluteUrl(value, siteUrl) {
  if (!value || typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (isHttpUrl(trimmed)) return trimmed;
  if (trimmed.startsWith("/")) return `${siteUrl}${trimmed}`;
  return `${siteUrl}/${trimmed}`;
}

function decodeSegment(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function normalizeScope(scopeId) {
  if (!scopeId) return "nacional";
  return String(scopeId).trim().toLowerCase();
}

function scopeMetaPath(scopeId) {
  if (scopeId === "nacional") return "/data/votaciones_meta.json";
  return `/data/${scopeId}/votaciones_meta.json`;
}

async function fetchJsonAsset(env, requestUrl, path) {
  const url = new URL(path, requestUrl.origin).toString();
  const req = new Request(url, { method: "GET" });
  const resp = await env.ASSETS.fetch(req);
  if (!resp.ok) {
    throw new Error(`Asset fetch failed (${path}): HTTP ${resp.status}`);
  }
  return resp.json();
}

async function getAmbitos(env, requestUrl) {
  const now = Date.now();
  if (ambitosCache.data && ambitosCache.expiresAt > now) {
    return ambitosCache.data;
  }

  const payload = await fetchJsonAsset(env, requestUrl, "/data/ambitos.json");
  const ids = new Set((payload.ambitos || []).map((a) => String(a.id || "").toLowerCase()));
  ids.add("nacional");
  ambitosCache = {
    data: ids,
    expiresAt: now + JSON_CACHE_TTL_MS,
  };
  return ids;
}

async function getScopeMeta(env, requestUrl, scopeId) {
  const normalized = normalizeScope(scopeId);
  const now = Date.now();
  const cached = scopeMetaCache.get(normalized);
  if (cached && cached.expiresAt > now) return cached.data;

  const data = await fetchJsonAsset(env, requestUrl, scopeMetaPath(normalized));
  scopeMetaCache.set(normalized, {
    data,
    expiresAt: now + JSON_CACHE_TTL_MS,
  });
  return data;
}

function voteDescription(vote, result, categories) {
  const categoria = categories?.[vote?.categoria] || "Otros";
  const chunks = [];

  if (result?.result) chunks.push(`Resultado: ${result.result}`);
  if (
    Number.isFinite(result?.favor) &&
    Number.isFinite(result?.contra) &&
    Number.isFinite(result?.abstencion)
  ) {
    chunks.push(`${result.favor} sí · ${result.contra} no · ${result.abstencion} abstenciones`);
  }
  if (vote?.fecha) chunks.push(`Fecha: ${vote.fecha}`);
  chunks.push(`Tema: ${categoria}`);

  return `${chunks.join(" · ")} · ${BRAND_TITLE}`;
}

function diputadoDescription(name, groupName, stats) {
  const total = Number.isFinite(stats?.total) ? stats.total : 0;
  const loyal = Number.isFinite(stats?.loyalty) ? Math.round(stats.loyalty * 100) : null;
  const chunks = [];
  chunks.push(`${name} · ${groupName}`);
  if (total > 0) chunks.push(`${total} votaciones registradas`);
  if (loyal !== null) chunks.push(`${loyal}% de disciplina de voto`);
  return `${chunks.join(" · ")} · ${BRAND_TITLE}`;
}

function normalizeVoteToken(value) {
  if (typeof value !== "string") return null;
  const normalized = value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, "_");

  if (!normalized) return null;

  if (normalized === "1" || normalized === "si" || normalized === "a_favor" || normalized === "favor") {
    return "si";
  }
  if (normalized === "2" || normalized === "no" || normalized === "en_contra" || normalized === "contra") {
    return "no";
  }
  if (
    normalized === "3" ||
    normalized === "abstencion" ||
    normalized === "abstenerse" ||
    normalized === "se_abstuvo"
  ) {
    return "abstencion";
  }
  if (normalized === "4" || normalized === "no_vota" || normalized === "ausente") {
    return "no_vota";
  }

  return null;
}

function voteActionText(voteToken) {
  if (voteToken === "si") return "votó a favor";
  if (voteToken === "no") return "votó en contra";
  if (voteToken === "abstencion") return "se abstuvo";
  if (voteToken === "no_vota") return "no votó";
  return "participó";
}

function shortDiputadoName(name) {
  if (typeof name !== "string") return "";
  const trimmed = name.trim();
  if (!trimmed) return "";
  const [head] = trimmed.split(",");
  return head.trim() || trimmed;
}

function initials(value, max = 4) {
  const parts = String(value || "")
    .trim()
    .split(/[\s,/()-]+/)
    .filter(Boolean);
  if (!parts.length) return "";
  if (parts.length === 1) return parts[0].slice(0, max).toUpperCase();
  return parts
    .slice(0, max)
    .map((p) => p[0]?.toUpperCase() || "")
    .join("");
}

function normalizeGroupBrand(groupName) {
  const raw = String(groupName || "").trim();
  const lower = raw.toLowerCase();
  const upper = raw.toUpperCase();

  if (!raw) return { label: "Sin grupo", logo: "SG", color: "#64748b" };
  if (upper === "GP" || upper === "PP" || lower.includes("popular")) {
    return { label: "PP", logo: "PP", color: "#0056a0" };
  }
  if (
    upper === "GS" ||
    upper === "PSOE" ||
    lower.includes("socialista") ||
    upper === "PSC"
  ) {
    return { label: "PSOE", logo: "PSOE", color: "#ef1c27" };
  }
  if (upper === "GVOX" || upper === "VOX" || lower.includes("vox")) {
    return { label: "VOX", logo: "VOX", color: "#63be21" };
  }
  if (upper === "GSUMAR" || lower.includes("sumar")) {
    return { label: "Sumar", logo: "SUM", color: "#e51c55" };
  }
  if (upper === "GCS" || upper === "CS" || lower.includes("ciudadanos")) {
    return { label: "CS", logo: "CS", color: "#eb6109" };
  }
  if (upper.includes("BILDU") || lower.includes("bildu")) {
    return { label: "EH Bildu", logo: "BIL", color: "#b5cf18" };
  }
  if (upper === "GER" || upper === "GR" || upper === "ERC" || lower.includes("republic")) {
    return { label: "ERC", logo: "ERC", color: "#ffb232" };
  }
  if (upper.includes("JXCAT") || upper.includes("JUNTS") || lower.includes("junts")) {
    return { label: "Junts", logo: "JX", color: "#00c3b2" };
  }
  if (upper.includes("PNV") || lower.includes("vasco")) {
    return { label: "PNV", logo: "PNV", color: "#008000" };
  }
  if (upper.includes("MIXTO") || lower.includes("mixto")) {
    return { label: "Mixto", logo: "MIX", color: "#64748b" };
  }
  if (upper.includes("PODEMOS") || upper.includes("GIP") || lower.includes("podemos")) {
    return { label: "Podemos", logo: "UP", color: "#673ab7" };
  }

  return { label: raw, logo: initials(raw, 3) || "PG", color: "#64748b" };
}

function bytesToBase64(bytes) {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

async function imageUrlToDataUri(imageUrl) {
  if (!imageUrl) return null;
  const now = Date.now();
  const cached = imageDataUriCache.get(imageUrl);
  if (cached && cached.expiresAt > now) return cached.dataUri;

  try {
    const resp = await fetch(imageUrl, { method: "GET" });
    if (!resp.ok) return null;
    const contentType = String(resp.headers.get("content-type") || "").toLowerCase();
    if (!contentType.startsWith("image/")) return null;
    const bytes = new Uint8Array(await resp.arrayBuffer());
    if (!bytes.length || bytes.length > 1_500_000) return null;
    const dataUri = `data:${contentType};base64,${bytesToBase64(bytes)}`;
    imageDataUriCache.set(imageUrl, { dataUri, expiresAt: now + JSON_CACHE_TTL_MS });
    return dataUri;
  } catch {
    return null;
  }
}

function truncateText(value, maxLen = 180) {
  const text = String(value || "").trim().replace(/\s+/g, " ");
  if (text.length <= maxLen) return text;
  return `${text.slice(0, maxLen - 1).trimEnd()}…`;
}

function splitTitleLines(value, maxChars = 44, maxLines = 3) {
  const text = truncateText(value, 220);
  if (!text) return ["Votación parlamentaria"];
  const words = text.split(" ");
  const lines = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxChars) {
      current = candidate;
      continue;
    }
    if (current) lines.push(current);
    current = word;
    if (lines.length === maxLines - 1) break;
  }
  if (lines.length < maxLines && current) lines.push(current);
  if (lines.length > maxLines) lines.length = maxLines;
  if (lines.length === maxLines && words.join(" ").length > lines.join(" ").length) {
    lines[maxLines - 1] = truncateText(lines[maxLines - 1], maxChars);
  }
  return lines.length ? lines : ["Votación parlamentaria"];
}

function seatBreakdown(result) {
  const favor = Math.max(0, Number(result?.favor) || 0);
  const contra = Math.max(0, Number(result?.contra) || 0);
  const abstencion = Math.max(0, Number(result?.abstencion) || 0);
  const counted = favor + contra + abstencion;
  let total = Math.max(0, Number(result?.total) || 0);
  if (total < counted) total = counted;
  if (total <= 0) total = 350;
  const noVota = Math.max(0, total - counted);
  return { favor, contra, abstencion, noVota, total };
}

function buildSeatCoordinates(totalSeats, config) {
  const { cx, cy, outerR, innerR, rows, startDeg, endDeg } = config;
  if (!Number.isFinite(totalSeats) || totalSeats <= 0) return [];
  const rowCount = Math.max(1, Math.min(Math.max(1, totalSeats), Math.min(12, rows || 9)));
  const radii = [];
  for (let r = 0; r < rowCount; r++) {
    const t = rowCount === 1 ? 0 : r / (rowCount - 1);
    radii.push(outerR + (innerR - outerR) * t);
  }

  const radiusWeight = radii.reduce((sum, radius) => sum + radius, 0);
  const counts = radii.map((radius) => Math.max(1, Math.round((totalSeats * radius) / radiusWeight)));
  let diff = totalSeats - counts.reduce((sum, count) => sum + count, 0);

  // Keep distribution proportional while preserving at least one seat per row.
  while (diff !== 0) {
    for (let i = 0; i < counts.length && diff !== 0; i++) {
      const idx = i % counts.length;
      if (diff > 0) {
        counts[idx] += 1;
        diff -= 1;
      } else if (counts[idx] > 1) {
        counts[idx] -= 1;
        diff += 1;
      }
    }
  }

  const points = [];
  const start = Number(startDeg);
  const end = Number(endDeg);
  for (let row = 0; row < counts.length; row++) {
    const radius = radii[row];
    const seatCount = counts[row];
    for (let j = 0; j < seatCount; j++) {
      const ratio = seatCount === 1 ? 0.5 : j / (seatCount - 1);
      const angle = start + (end - start) * ratio;
      const rad = (angle * Math.PI) / 180;
      points.push({
        x: cx + radius * Math.cos(rad),
        y: cy + radius * Math.sin(rad),
      });
    }
  }
  return points;
}

function voteOgImageUrl(
  siteUrl,
  scopeId,
  voteId,
  dipName = "",
  voteToken = null,
  groupName = "",
  groupVoteToken = null
) {
  const path = `/og/votacion/${encodeURIComponent(scopeId)}/${encodeURIComponent(voteId)}`;
  const url = new URL(`${siteUrl}${path}`);
  if (dipName) url.searchParams.set("dip", dipName);
  if (voteToken) url.searchParams.set("vote", voteToken);
  if (groupName) url.searchParams.set("group", groupName);
  if (groupVoteToken) url.searchParams.set("groupVote", groupVoteToken);
  return url.toString();
}

function diputadoOgImageUrl(siteUrl, scopeId, diputadoName) {
  return `${siteUrl}/og/diputado/${encodeURIComponent(scopeId)}/${encodeURIComponent(diputadoName)}`;
}

function renderVoteOgImage({
  voteId,
  voteTitle,
  scopeId,
  date,
  category,
  result,
  dipName = "",
  voteToken = null,
  groupName = "",
  groupVoteToken = null,
}) {
  const titleLines = splitTitleLines(voteTitle, 45, 3);
  const totals = seatBreakdown(result);
  const coords = buildSeatCoordinates(totals.total, {
    cx: 330,
    cy: 305,
    outerR: 238,
    innerR: 96,
    rows: 9,
    startDeg: 210,
    endDeg: -30,
  });
  const seatRadius = totals.total > 300 ? 5.3 : 5.8;
  const seatColors = [];
  for (let i = 0; i < totals.favor; i++) seatColors.push(OG_COLORS.favor);
  for (let i = 0; i < totals.contra; i++) seatColors.push(OG_COLORS.contra);
  for (let i = 0; i < totals.abstencion; i++) seatColors.push(OG_COLORS.abst);
  for (let i = 0; i < totals.noVota; i++) seatColors.push(OG_COLORS.noVota);

  const circles = coords
    .map((point, index) => {
      const fill = seatColors[index] || OG_COLORS.noVota;
      return `<circle cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="${seatRadius}" fill="${fill}" />`;
    })
    .join("");

  const bars = [
    { label: "Sí", value: totals.favor, color: OG_COLORS.favor },
    { label: "No", value: totals.contra, color: OG_COLORS.contra },
    { label: "Abs.", value: totals.abstencion, color: OG_COLORS.abst },
  ]
    .map((row, i) => {
      const y = 488 + i * 28;
      const width = Math.round((row.value / Math.max(1, totals.total)) * 430);
      return `
        <text x="56" y="${y}" font-size="20" fill="${OG_COLORS.text}" font-weight="700">${row.label}</text>
        <rect x="95" y="${y - 14}" width="430" height="10" rx="5" fill="${OG_COLORS.border}" />
        <rect x="95" y="${y - 14}" width="${Math.max(0, width)}" height="10" rx="5" fill="${row.color}" />
        <text x="538" y="${y}" font-size="20" text-anchor="end" fill="${OG_COLORS.text}" font-weight="700">${row.value}</text>
      `;
    })
    .join("");

  const contextSnippetText = dipName
    ? `${shortDiputadoName(dipName)} ${voteActionText(voteToken)}`
    : groupName
      ? `${normalizeGroupBrand(groupName).label} ${voteActionText(groupVoteToken)}`
      : "";
  const contextSnippet = contextSnippetText
    ? `<text x="640" y="352" font-size="30" fill="${OG_COLORS.text}" font-weight="700">${escapeHtml(
        contextSnippetText
      )}</text>`
    : "";

  const titleSvg = titleLines
    .map(
      (line, index) =>
        `<text x="640" y="${114 + index * 48}" font-size="42" fill="${OG_COLORS.text}" font-weight="800">${escapeHtml(
          line
        )}</text>`
    )
    .join("");

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${OG_CANVAS.width}" height="${OG_CANVAS.height}" viewBox="0 0 ${OG_CANVAS.width} ${OG_CANVAS.height}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="${OG_COLORS.bgA}" />
      <stop offset="100%" stop-color="${OG_COLORS.bgB}" />
    </linearGradient>
  </defs>
  <rect width="${OG_CANVAS.width}" height="${OG_CANVAS.height}" fill="url(#bg)" />
  <rect x="32" y="32" width="560" height="566" rx="22" fill="${OG_COLORS.panel}" stroke="${OG_COLORS.border}" stroke-width="2" />
  ${circles}
  <text x="56" y="452" font-size="18" fill="${OG_COLORS.muted}" font-weight="700">VOTOS EMITIDOS</text>
  <text x="232" y="452" font-size="28" fill="${OG_COLORS.text}" font-weight="800">${totals.total}</text>
  ${bars}
  <text x="640" y="52" font-size="22" fill="${OG_COLORS.muted}" font-weight="700">LoQueVotan.es · ${escapeHtml(
    scopeId
  )}</text>
  ${titleSvg}
  <text x="640" y="286" font-size="24" fill="${OG_COLORS.muted}">${escapeHtml(date || "Sin fecha")} · ${escapeHtml(
    category || "Otros"
  )}</text>
  <text x="640" y="320" font-size="24" fill="${OG_COLORS.muted}">Resultado: ${escapeHtml(result?.result || "Sin resultado")}</text>
  ${contextSnippet}
  <text x="640" y="418" font-size="22" fill="${OG_COLORS.muted}">ID: ${escapeHtml(voteId)}</text>
  <text x="640" y="468" font-size="26" fill="${OG_COLORS.text}" font-weight="700">${totals.favor} sí · ${totals.contra} no · ${totals.abstencion} abst.</text>
</svg>`;
}

function renderDiputadoOgImage({
  diputadoName,
  scopeId,
  party,
  stats,
  photoDataUri = "",
}) {
  const nameLines = splitTitleLines(diputadoName, 26, 2);
  const votesTotal = Math.max(0, Number(stats?.total) || 0);
  const favor = Math.max(0, Number(stats?.favor) || 0);
  const contra = Math.max(0, Number(stats?.contra) || 0);
  const abst = Math.max(0, Number(stats?.abstencion) || 0);
  const noVota = Math.max(0, Number(stats?.no_vota) || 0);
  const loyaltyPct = Number.isFinite(stats?.loyalty) ? Math.round(stats.loyalty * 100) : null;
  const hasPhoto = Boolean(photoDataUri);
  const avatarFallback = initials(shortDiputadoName(diputadoName), 2) || "DV";

  const nameSvg = nameLines
    .map(
      (line, index) =>
        `<text x="620" y="${160 + index * 58}" font-size="50" fill="${OG_COLORS.text}" font-weight="800">${escapeHtml(
          line
        )}</text>`
    )
    .join("");

  const loyaltyBar = Math.max(0, Math.min(100, loyaltyPct || 0));

  const photoLayer = hasPhoto
    ? `<image href="${photoDataUri}" x="78" y="94" width="410" height="410" preserveAspectRatio="xMidYMid slice" clip-path="url(#avatarClip)" />`
    : `<circle cx="283" cy="299" r="162" fill="#1e293b" /><text x="283" y="322" text-anchor="middle" font-size="92" font-weight="800" fill="#94a3b8">${escapeHtml(
        avatarFallback
      )}</text>`;

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${OG_CANVAS.width}" height="${OG_CANVAS.height}" viewBox="0 0 ${OG_CANVAS.width} ${OG_CANVAS.height}">
  <defs>
    <linearGradient id="bgDip" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="${OG_COLORS.bgA}" />
      <stop offset="100%" stop-color="${OG_COLORS.bgB}" />
    </linearGradient>
    <clipPath id="avatarClip"><circle cx="283" cy="299" r="162" /></clipPath>
  </defs>
  <rect width="${OG_CANVAS.width}" height="${OG_CANVAS.height}" fill="url(#bgDip)" />
  <rect x="32" y="32" width="520" height="566" rx="28" fill="${OG_COLORS.panel}" stroke="${OG_COLORS.border}" stroke-width="2" />
  ${photoLayer}
  <circle cx="283" cy="299" r="164" fill="none" stroke="${OG_COLORS.text}" stroke-opacity="0.18" stroke-width="4" />
  <g transform="translate(418 146)">
    <circle cx="0" cy="0" r="64" fill="${party.color}" stroke="${OG_COLORS.text}" stroke-width="6" />
    <text x="0" y="10" text-anchor="middle" font-size="26" font-weight="800" fill="#ffffff">${escapeHtml(party.logo)}</text>
  </g>

  <text x="620" y="70" font-size="22" fill="${OG_COLORS.muted}" font-weight="700">LoQueVotan.es · ${escapeHtml(
    scopeId
  )}</text>
  ${nameSvg}
  <text x="620" y="300" font-size="40" fill="${party.color}" font-weight="800">${escapeHtml(party.label)}</text>

  <text x="620" y="356" font-size="24" fill="${OG_COLORS.muted}" font-weight="700">Votos registrados</text>
  <text x="910" y="356" font-size="34" fill="${OG_COLORS.text}" font-weight="800">${votesTotal}</text>
  <text x="620" y="394" font-size="24" fill="${OG_COLORS.muted}" font-weight="700">A favor ${favor} · En contra ${contra} · Abst. ${abst}</text>
  <text x="620" y="430" font-size="24" fill="${OG_COLORS.muted}" font-weight="700">No vota ${noVota}</text>

  <text x="620" y="486" font-size="24" fill="${OG_COLORS.muted}" font-weight="700">Disciplina de voto</text>
  <rect x="620" y="500" width="460" height="18" rx="9" fill="${OG_COLORS.border}" />
  <rect x="620" y="500" width="${Math.round((460 * loyaltyBar) / 100)}" height="18" rx="9" fill="${party.color}" />
  <text x="1092" y="516" text-anchor="end" font-size="24" fill="${OG_COLORS.text}" font-weight="800">${loyaltyPct ?? 0}%</text>
</svg>`;
}

function diputadoPhotoUrl(fotoEntry, siteUrl) {
  if (!fotoEntry) return null;

  if (typeof fotoEntry === "string") {
    return asAbsoluteUrl(fotoEntry, siteUrl);
  }

  if (typeof fotoEntry === "object") {
    const legs = Object.keys(fotoEntry);
    if (!legs.length) return null;
    const bestLeg = legs.reduce((a, b) =>
      (LEG_TO_NUM[a] || 0) >= (LEG_TO_NUM[b] || 0) ? a : b
    );
    const cod = fotoEntry[bestLeg];
    const num = LEG_TO_NUM[bestLeg];
    if (!cod || !num) return null;
    return `https://www.congreso.es/docu/imgweb/diputados/${cod}_${num}.jpg`;
  }

  return null;
}

function renderOgPage({
  title,
  description,
  canonicalUrl,
  imageUrl,
  imageAlt = "",
  redirectUrl,
  scopeId = "nacional",
  noindex = false,
}) {
  const escapedTitle = escapeHtml(title);
  const escapedDescription = escapeHtml(description);
  const escapedCanonical = escapeHtml(canonicalUrl);
  const escapedImage = escapeHtml(imageUrl);
  const escapedImageAlt = escapeHtml(imageAlt);
  const escapedRedirect = escapeHtml(redirectUrl);
  const escapedScope = escapeHtml(scopeId);
  const robots = noindex ? `<meta name="robots" content="noindex, nofollow">` : "";

  const html = `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapedTitle}</title>
  <meta name="description" content="${escapedDescription}">
  ${robots}
  <link rel="canonical" href="${escapedCanonical}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="${escapeHtml(SITE_NAME)}">
  <meta property="og:title" content="${escapedTitle}">
  <meta property="og:description" content="${escapedDescription}">
  <meta property="og:url" content="${escapedCanonical}">
  <meta property="og:image" content="${escapedImage}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="${escapedImageAlt}">
  <meta property="og:locale" content="es_ES">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${escapedTitle}">
  <meta name="twitter:description" content="${escapedDescription}">
  <meta name="twitter:image" content="${escapedImage}">
  <meta name="twitter:image:alt" content="${escapedImageAlt}">
  <script>
    try { localStorage.setItem("preferredScope", "${escapedScope}"); } catch (e) {}
    window.location.replace("${escapedRedirect}");
  </script>
</head>
<body>
  <p>Redirigiendo a la votación...</p>
  <p><a href="${escapedRedirect}">Abrir en ${escapeHtml(BRAND_TITLE)}</a></p>
</body>
</html>`;

  return new Response(html, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "public, max-age=600",
    },
  });
}

function splitPath(pathname) {
  return pathname.split("/").filter(Boolean);
}

function buildSiteUrl(env, requestUrl) {
  const envSiteUrl = typeof env.SITE_URL === "string" ? env.SITE_URL.trim() : "";
  if (envSiteUrl) return stripTrailingSlash(envSiteUrl);
  return stripTrailingSlash(`${requestUrl.protocol}//${requestUrl.host}`);
}

function buildImageUrl(env, siteUrl) {
  const custom = typeof env.OG_IMAGE_URL === "string" ? env.OG_IMAGE_URL.trim() : "";
  if (custom) return custom;
  return `${siteUrl}/og-image.png`;
}

async function handleVoteOgImage(request, env) {
  const requestUrl = new URL(request.url);
  const parts = splitPath(requestUrl.pathname);

  // /og/votacion/:scope/:id
  if (parts.length < 4) return null;

  const scopeId = normalizeScope(decodeSegment(parts[2]));
  const voteId = decodeSegment(parts.slice(3).join("/"));
  const dipParam = decodeSegment(requestUrl.searchParams.get("dip") || "").trim();
  const voteParam = normalizeVoteToken(requestUrl.searchParams.get("vote"));
  const groupParam = decodeSegment(requestUrl.searchParams.get("group") || "").trim();
  const groupVoteParam = normalizeVoteToken(requestUrl.searchParams.get("groupVote"));
  if (!voteId) return null;

  const scopes = await getAmbitos(env, requestUrl);
  if (!scopes.has(scopeId)) return null;

  const meta = await getScopeMeta(env, requestUrl, scopeId);
  const voteIndex = meta?.votIdById?.[voteId];

  if (!Number.isInteger(voteIndex)) {
    const svg = renderVoteOgImage({
      voteId,
      voteTitle: "Votación no encontrada",
      scopeId,
      date: "",
      category: "",
      result: { favor: 0, contra: 0, abstencion: 0, total: 0, result: "Sin datos" },
      dipName: dipParam,
      voteToken: voteParam,
      groupName: groupParam,
      groupVoteToken: groupVoteParam,
    });
    return new Response(svg, {
      status: 404,
      headers: {
        "content-type": "image/svg+xml; charset=utf-8",
        "cache-control": "public, max-age=120",
      },
    });
  }

  const vote = meta.votaciones[voteIndex];
  const result = meta.votResults?.[voteIndex] || {};
  const category = meta.categorias?.[vote?.categoria] || "Otros";
  const svg = renderVoteOgImage({
    voteId,
    voteTitle: vote?.titulo_ciudadano || voteId,
    scopeId,
    date: vote?.fecha || "",
    category,
    result,
    dipName: dipParam,
    voteToken: voteParam,
    groupName: groupParam,
    groupVoteToken: groupVoteParam,
  });

  return new Response(svg, {
    headers: {
      "content-type": "image/svg+xml; charset=utf-8",
      "cache-control": "public, max-age=600",
    },
  });
}

async function handleDiputadoOgImage(request, env) {
  const requestUrl = new URL(request.url);
  const parts = splitPath(requestUrl.pathname);

  // /og/diputado/:scope/:name
  if (parts.length < 4) return null;

  const scopeId = normalizeScope(decodeSegment(parts[2]));
  const diputadoName = decodeSegment(parts.slice(3).join("/"));
  if (!diputadoName) return null;

  const scopes = await getAmbitos(env, requestUrl);
  if (!scopes.has(scopeId)) return null;

  const meta = await getScopeMeta(env, requestUrl, scopeId);
  const dipIdx = (meta?.diputados || []).indexOf(diputadoName);

  if (dipIdx < 0) {
    const svg = renderDiputadoOgImage({
      diputadoName: "Diputado no encontrado",
      scopeId,
      party: { label: "Sin grupo", logo: "SG", color: "#64748b" },
      stats: {},
      photoDataUri: "",
    });
    return new Response(svg, {
      status: 404,
      headers: {
        "content-type": "image/svg+xml; charset=utf-8",
        "cache-control": "public, max-age=120",
      },
    });
  }

  const stats = meta?.dipStats?.[dipIdx] || {};
  const groupName =
    Number.isInteger(stats?.mainGrupo) && meta?.grupos?.[stats.mainGrupo]
      ? meta.grupos[stats.mainGrupo]
      : "Sin grupo";
  const party = normalizeGroupBrand(groupName);
  const siteUrl = buildSiteUrl(env, requestUrl);
  const dipPhoto = diputadoPhotoUrl(meta?.dipFotos?.[dipIdx], siteUrl);
  const photoDataUri = dipPhoto ? await imageUrlToDataUri(dipPhoto) : "";

  const svg = renderDiputadoOgImage({
    diputadoName,
    scopeId,
    party,
    stats,
    photoDataUri,
  });

  return new Response(svg, {
    headers: {
      "content-type": "image/svg+xml; charset=utf-8",
      "cache-control": "public, max-age=600",
    },
  });
}

async function handleVoteShare(request, env) {
  const requestUrl = new URL(request.url);
  const parts = splitPath(requestUrl.pathname);

  // /share/votacion/:scope/:id
  if (parts.length < 4) return null;

  const scopeId = normalizeScope(decodeSegment(parts[2]));
  const voteId = decodeSegment(parts.slice(3).join("/"));
  const dipParam = decodeSegment(requestUrl.searchParams.get("dip") || "").trim();
  const voteParam = normalizeVoteToken(requestUrl.searchParams.get("vote"));
  const groupParam = decodeSegment(requestUrl.searchParams.get("group") || "").trim();
  const groupVoteParam = normalizeVoteToken(requestUrl.searchParams.get("groupVote"));
  if (!voteId) return null;

  const scopes = await getAmbitos(env, requestUrl);
  if (!scopes.has(scopeId)) return null;

  const meta = await getScopeMeta(env, requestUrl, scopeId);
  const voteIndex = meta?.votIdById?.[voteId];

  const siteUrl = buildSiteUrl(env, requestUrl);
  const sharePath = `/share/votacion/${encodeURIComponent(scopeId)}/${encodeURIComponent(voteId)}`;
  const canonicalUrlObj = new URL(`${siteUrl}${sharePath}`);
  if (dipParam) canonicalUrlObj.searchParams.set("dip", dipParam);
  if (voteParam) canonicalUrlObj.searchParams.set("vote", voteParam);
  if (groupParam) canonicalUrlObj.searchParams.set("group", groupParam);
  if (groupVoteParam) canonicalUrlObj.searchParams.set("groupVote", groupVoteParam);
  const canonicalUrl = canonicalUrlObj.toString();
  const imageUrl = voteOgImageUrl(
    siteUrl,
    scopeId,
    voteId,
    dipParam,
    voteParam,
    groupParam,
    groupVoteParam
  );
  const redirectUrlObj = new URL(`${siteUrl}/votacion/${encodeURIComponent(voteId)}`);
  redirectUrlObj.searchParams.set("scope", scopeId);
  if (dipParam) redirectUrlObj.searchParams.set("dip", dipParam);
  if (voteParam) redirectUrlObj.searchParams.set("vote", voteParam);
  if (groupParam) redirectUrlObj.searchParams.set("group", groupParam);
  if (groupVoteParam) redirectUrlObj.searchParams.set("groupVote", groupVoteParam);
  const redirectUrl = redirectUrlObj.toString();

  if (!Number.isInteger(voteIndex)) {
    return renderOgPage({
      title: `Votación no encontrada | ${BRAND_TITLE}`,
      description: `No hemos encontrado esta votación en el ámbito ${scopeId}.`,
      canonicalUrl,
      imageUrl,
      redirectUrl,
      scopeId,
      noindex: true,
    });
  }

  const vote = meta.votaciones[voteIndex];
  const result = meta.votResults?.[voteIndex] || null;
  const voteTitle = vote?.titulo_ciudadano || voteId;
  const shortDipName = shortDiputadoName(dipParam);
  const groupDisplayName = groupParam ? normalizeGroupBrand(groupParam).label : "";
  const action = voteActionText(voteParam);
  const groupAction = voteActionText(groupVoteParam);
  const title = dipParam
    ? voteParam
      ? `${shortDipName} ${action} en ${voteTitle} | ${BRAND_TITLE}`
      : `${shortDipName} en ${voteTitle} | ${BRAND_TITLE}`
    : groupParam
      ? groupVoteParam
        ? `${groupDisplayName} ${groupAction} en ${voteTitle} | ${BRAND_TITLE}`
        : `${groupDisplayName} en ${voteTitle} | ${BRAND_TITLE}`
    : `${voteTitle} | ${BRAND_TITLE}`;
  const description = dipParam
    ? voteParam
      ? `${shortDipName} ${action} en esta votación. ${voteDescription(vote, result, meta.categorias || [])}`
      : `Consulta cómo votó ${dipParam} en este asunto. ${voteDescription(vote, result, meta.categorias || [])}`
    : groupParam
      ? groupVoteParam
        ? `${groupDisplayName} ${groupAction} en esta votación. ${voteDescription(vote, result, meta.categorias || [])}`
        : `Consulta qué votó ${groupDisplayName} en este asunto. ${voteDescription(vote, result, meta.categorias || [])}`
    : voteDescription(vote, result, meta.categorias || []);
  const imageAlt = dipParam
    ? voteParam
      ? `${shortDipName} ${action} en ${voteTitle}`
      : `Votación de ${voteTitle}`
    : groupParam
      ? groupVoteParam
        ? `${groupDisplayName} ${groupAction} en ${voteTitle}`
        : `Votación de ${voteTitle}`
    : `Resultado de votación: ${voteTitle}`;

  return renderOgPage({
    title,
    description,
    canonicalUrl,
    imageUrl,
    imageAlt,
    redirectUrl,
    scopeId,
  });
}

async function handleDiputadoShare(request, env) {
  const requestUrl = new URL(request.url);
  const parts = splitPath(requestUrl.pathname);

  // /share/diputado/:scope/:name
  if (parts.length < 4) return null;

  const scopeId = normalizeScope(decodeSegment(parts[2]));
  const diputadoName = decodeSegment(parts.slice(3).join("/"));
  if (!diputadoName) return null;

  const scopes = await getAmbitos(env, requestUrl);
  if (!scopes.has(scopeId)) return null;

  const meta = await getScopeMeta(env, requestUrl, scopeId);
  const dipIdx = (meta?.diputados || []).indexOf(diputadoName);

  const siteUrl = buildSiteUrl(env, requestUrl);
  const sharePath = `/share/diputado/${encodeURIComponent(scopeId)}/${encodeURIComponent(diputadoName)}`;
  const canonicalUrl = `${siteUrl}${sharePath}`;
  const defaultImageUrl = buildImageUrl(env, siteUrl);
  const redirectUrl = `${siteUrl}/diputado/${encodeURIComponent(diputadoName)}?scope=${encodeURIComponent(scopeId)}`;

  if (dipIdx < 0) {
    return renderOgPage({
      title: `Diputado no encontrado | ${BRAND_TITLE}`,
      description: `No hemos encontrado este perfil en el ámbito ${scopeId}.`,
      canonicalUrl,
      imageUrl: defaultImageUrl,
      imageAlt: "Imagen de portada de LoQueVotan.es",
      redirectUrl,
      scopeId,
      noindex: true,
    });
  }

  const stats = meta?.dipStats?.[dipIdx] || {};
  const groupName =
    Number.isInteger(stats?.mainGrupo) && meta?.grupos?.[stats.mainGrupo]
      ? meta.grupos[stats.mainGrupo]
      : "Sin grupo";
  const title = `${diputadoName} (${groupName}) | ${BRAND_TITLE}`;
  const description = diputadoDescription(diputadoName, groupName, stats);
  const imageUrl = diputadoOgImageUrl(siteUrl, scopeId, diputadoName);
  const imageAlt = `Perfil de ${diputadoName} (${normalizeGroupBrand(groupName).label})`;

  return renderOgPage({
    title,
    description,
    canonicalUrl,
    imageUrl,
    imageAlt,
    redirectUrl,
    scopeId,
  });
}

export default {
  async fetch(request, env) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return env.ASSETS.fetch(request);
    }

    const url = new URL(request.url);
    const pathname = url.pathname.replace(/\/+$/, "") || "/";

    try {
      if (pathname.startsWith("/og/votacion/")) {
        const imageResp = await handleVoteOgImage(request, env);
        if (imageResp) return imageResp;
      }

      if (pathname.startsWith("/og/diputado/")) {
        const imageResp = await handleDiputadoOgImage(request, env);
        if (imageResp) return imageResp;
      }

      if (pathname.startsWith("/share/votacion/")) {
        const voteResp = await handleVoteShare(request, env);
        if (voteResp) return voteResp;
      }

      if (pathname.startsWith("/share/diputado/")) {
        const dipResp = await handleDiputadoShare(request, env);
        if (dipResp) return dipResp;
      }
    } catch (err) {
      return new Response(`OG worker error: ${err?.message || err}`, {
        status: 500,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    return env.ASSETS.fetch(request);
  },
};

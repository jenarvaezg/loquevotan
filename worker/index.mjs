import jpeg from "jpeg-js";

const SITE_NAME = "Lo Que Votan";
const BRAND_TITLE = "LoQueVotan.es";
const JSON_CACHE_TTL_MS = 5 * 60 * 1000;
const API_CACHE_TTL_SECONDS = 120;
const API_MAX_PAGE_SIZE = 100;
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
const imageRgbaCache = new Map();
const PNG_TEXT_ENCODER = new TextEncoder();
const PNG_SIGNATURE = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]);
const CRC32_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[n] = c >>> 0;
  }
  return table;
})();
const PIXEL_FONT_5X7 = {
  A: ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
  B: ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
  C: ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
  D: ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
  E: ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
  F: ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
  G: ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
  H: ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
  I: ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
  J: ["00001", "00001", "00001", "00001", "10001", "10001", "01110"],
  K: ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
  L: ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
  M: ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
  N: ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
  O: ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
  P: ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
  Q: ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
  R: ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
  S: ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
  T: ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
  U: ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
  V: ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
  W: ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
  X: ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
  Y: ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
  Z: ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
  0: ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
  1: ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
  2: ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
  3: ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
  4: ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
  5: ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
  6: ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
  7: ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
  8: ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
  9: ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
  "?": ["01110", "10001", "00010", "00100", "00100", "00000", "00100"],
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function hexToRgba(hex, alpha = 255) {
  const fallback = [0, 0, 0, alpha];
  if (typeof hex !== "string") return fallback;
  let value = hex.trim().replace(/^#/, "");
  if (value.length === 3) {
    value = `${value[0]}${value[0]}${value[1]}${value[1]}${value[2]}${value[2]}`;
  }
  if (!/^[0-9a-fA-F]{6}$/.test(value)) return fallback;
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return [r, g, b, alpha];
}

function setPixelRgba(buffer, width, height, x, y, rgba) {
  if (x < 0 || y < 0 || x >= width || y >= height) return;
  const idx = (y * width + x) * 4;
  buffer[idx] = rgba[0];
  buffer[idx + 1] = rgba[1];
  buffer[idx + 2] = rgba[2];
  buffer[idx + 3] = rgba[3];
}

function drawRectRgba(buffer, width, height, x, y, rectWidth, rectHeight, rgba) {
  const x0 = clamp(Math.floor(x), 0, width);
  const y0 = clamp(Math.floor(y), 0, height);
  const x1 = clamp(Math.ceil(x + rectWidth), 0, width);
  const y1 = clamp(Math.ceil(y + rectHeight), 0, height);
  if (x1 <= x0 || y1 <= y0) return;

  for (let py = y0; py < y1; py++) {
    for (let px = x0; px < x1; px++) {
      const idx = (py * width + px) * 4;
      buffer[idx] = rgba[0];
      buffer[idx + 1] = rgba[1];
      buffer[idx + 2] = rgba[2];
      buffer[idx + 3] = rgba[3];
    }
  }
}

function drawFilledCircleRgba(buffer, width, height, cx, cy, radius, rgba) {
  const r2 = radius * radius;
  const y0 = clamp(Math.floor(cy - radius), 0, height - 1);
  const y1 = clamp(Math.ceil(cy + radius), 0, height - 1);

  for (let py = y0; py <= y1; py++) {
    const dy = py + 0.5 - cy;
    const dx2 = r2 - dy * dy;
    if (dx2 <= 0) continue;
    const dx = Math.sqrt(dx2);
    const x0 = clamp(Math.floor(cx - dx), 0, width - 1);
    const x1 = clamp(Math.ceil(cx + dx), 0, width - 1);
    for (let px = x0; px <= x1; px++) {
      setPixelRgba(buffer, width, height, px, py, rgba);
    }
  }
}

function drawPixelText(buffer, width, height, text, x, y, scale, rgba) {
  const safeText = String(text || "").toUpperCase();
  let cursorX = Math.round(x);
  const step = 6 * scale;

  for (const char of safeText) {
    if (char === " ") {
      cursorX += step;
      continue;
    }
    const glyph = PIXEL_FONT_5X7[char] || PIXEL_FONT_5X7["?"];
    for (let row = 0; row < glyph.length; row++) {
      const pattern = glyph[row];
      for (let col = 0; col < pattern.length; col++) {
        if (pattern[col] === "1") {
          drawRectRgba(
            buffer,
            width,
            height,
            cursorX + col * scale,
            y + row * scale,
            scale,
            scale,
            rgba
          );
        }
      }
    }
    cursorX += step;
  }
}

function drawCircularImageCoverRgba(
  destBuffer,
  destWidth,
  destHeight,
  cx,
  cy,
  radius,
  srcBuffer,
  srcWidth,
  srcHeight
) {
  if (!srcBuffer || !srcWidth || !srcHeight || radius <= 0) return;

  const diameter = radius * 2;
  const scale = Math.max(diameter / srcWidth, diameter / srcHeight);
  const srcCropW = diameter / scale;
  const srcCropH = diameter / scale;
  const srcOffsetX = (srcWidth - srcCropW) / 2;
  const srcOffsetY = (srcHeight - srcCropH) / 2;
  const r2 = radius * radius;

  const x0 = clamp(Math.floor(cx - radius), 0, destWidth - 1);
  const x1 = clamp(Math.ceil(cx + radius), 0, destWidth - 1);
  const y0 = clamp(Math.floor(cy - radius), 0, destHeight - 1);
  const y1 = clamp(Math.ceil(cy + radius), 0, destHeight - 1);

  for (let py = y0; py <= y1; py++) {
    const dy = py + 0.5 - cy;
    for (let px = x0; px <= x1; px++) {
      const dx = px + 0.5 - cx;
      if ((dx * dx) + (dy * dy) > r2) continue;

      const u = (px - (cx - radius)) / diameter;
      const v = (py - (cy - radius)) / diameter;
      const sx = clamp(Math.floor(srcOffsetX + u * srcCropW), 0, srcWidth - 1);
      const sy = clamp(Math.floor(srcOffsetY + v * srcCropH), 0, srcHeight - 1);

      const srcIdx = (sy * srcWidth + sx) * 4;
      const dstIdx = (py * destWidth + px) * 4;
      const alpha = srcBuffer[srcIdx + 3] / 255;
      if (alpha <= 0) continue;

      if (alpha >= 1) {
        destBuffer[dstIdx] = srcBuffer[srcIdx];
        destBuffer[dstIdx + 1] = srcBuffer[srcIdx + 1];
        destBuffer[dstIdx + 2] = srcBuffer[srcIdx + 2];
        destBuffer[dstIdx + 3] = 255;
      } else {
        const inv = 1 - alpha;
        destBuffer[dstIdx] = Math.round((srcBuffer[srcIdx] * alpha) + (destBuffer[dstIdx] * inv));
        destBuffer[dstIdx + 1] = Math.round((srcBuffer[srcIdx + 1] * alpha) + (destBuffer[dstIdx + 1] * inv));
        destBuffer[dstIdx + 2] = Math.round((srcBuffer[srcIdx + 2] * alpha) + (destBuffer[dstIdx + 2] * inv));
        destBuffer[dstIdx + 3] = 255;
      }
    }
  }
}

function fillVerticalGradient(buffer, width, height, topHex, bottomHex) {
  const top = hexToRgba(topHex);
  const bottom = hexToRgba(bottomHex);
  for (let y = 0; y < height; y++) {
    const t = height <= 1 ? 0 : y / (height - 1);
    const rgba = [
      Math.round(top[0] + (bottom[0] - top[0]) * t),
      Math.round(top[1] + (bottom[1] - top[1]) * t),
      Math.round(top[2] + (bottom[2] - top[2]) * t),
      255,
    ];
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4;
      buffer[idx] = rgba[0];
      buffer[idx + 1] = rgba[1];
      buffer[idx + 2] = rgba[2];
      buffer[idx + 3] = 255;
    }
  }
}

function crc32(bytes) {
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) {
    crc = CRC32_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function adler32(bytes) {
  let a = 1;
  let b = 0;
  for (let i = 0; i < bytes.length; i++) {
    a = (a + bytes[i]) % 65521;
    b = (b + a) % 65521;
  }
  return ((b << 16) | a) >>> 0;
}

function uint32ToBytes(value) {
  return new Uint8Array([
    (value >>> 24) & 0xff,
    (value >>> 16) & 0xff,
    (value >>> 8) & 0xff,
    value & 0xff,
  ]);
}

function concatBytes(chunks) {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    out.set(chunk, offset);
    offset += chunk.length;
  }
  return out;
}

function makePngChunk(type, data) {
  const typeBytes = PNG_TEXT_ENCODER.encode(type);
  const crcInput = new Uint8Array(typeBytes.length + data.length);
  crcInput.set(typeBytes, 0);
  crcInput.set(data, typeBytes.length);
  const crcBytes = uint32ToBytes(crc32(crcInput));

  return concatBytes([
    uint32ToBytes(data.length),
    typeBytes,
    data,
    crcBytes,
  ]);
}

function zlibStore(rawData) {
  const chunks = [new Uint8Array([0x78, 0x01])];
  let offset = 0;

  while (offset < rawData.length) {
    const len = Math.min(65535, rawData.length - offset);
    const isLast = offset + len >= rawData.length;
    const nlen = 0xffff - len;
    chunks.push(
      new Uint8Array([
        isLast ? 0x01 : 0x00,
        len & 0xff,
        (len >>> 8) & 0xff,
        nlen & 0xff,
        (nlen >>> 8) & 0xff,
      ]),
      rawData.subarray(offset, offset + len)
    );
    offset += len;
  }

  chunks.push(uint32ToBytes(adler32(rawData)));
  return concatBytes(chunks);
}

async function compressDeflate(rawData) {
  if (typeof CompressionStream !== "undefined") {
    try {
      const stream = new CompressionStream("deflate");
      const writer = stream.writable.getWriter();
      await writer.write(rawData);
      await writer.close();
      const compressed = await new Response(stream.readable).arrayBuffer();
      if (compressed.byteLength > 0) return new Uint8Array(compressed);
    } catch {
      // Fallback to uncompressed zlib blocks when CompressionStream is unavailable.
    }
  }
  return zlibStore(rawData);
}

async function encodeRgbaToPng(width, height, rgbaBuffer) {
  const rowSize = width * 4 + 1;
  const raw = new Uint8Array(rowSize * height);
  for (let y = 0; y < height; y++) {
    const rowStart = y * rowSize;
    raw[rowStart] = 0; // Filter method 0 (None)
    const srcStart = y * width * 4;
    raw.set(rgbaBuffer.subarray(srcStart, srcStart + width * 4), rowStart + 1);
  }

  const ihdr = new Uint8Array(13);
  ihdr.set(uint32ToBytes(width), 0);
  ihdr.set(uint32ToBytes(height), 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // color type RGBA
  ihdr[10] = 0; // compression
  ihdr[11] = 0; // filter
  ihdr[12] = 0; // interlace

  const idat = await compressDeflate(raw);
  return concatBytes([
    PNG_SIGNATURE,
    makePngChunk("IHDR", ihdr),
    makePngChunk("IDAT", idat),
    makePngChunk("IEND", new Uint8Array(0)),
  ]);
}

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

function normalizeTextKey(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function findDiputadoIndex(meta, dipName) {
  const diputados = Array.isArray(meta?.diputados) ? meta.diputados : [];
  if (!diputados.length || !dipName) return -1;

  const exact = diputados.indexOf(dipName);
  if (exact >= 0) return exact;

  const target = normalizeTextKey(dipName);
  if (!target) return -1;

  for (let i = 0; i < diputados.length; i++) {
    if (normalizeTextKey(diputados[i]) === target) return i;
  }
  return -1;
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

async function imageUrlToRgba(imageUrl) {
  if (!imageUrl) return null;
  const now = Date.now();
  const cached = imageRgbaCache.get(imageUrl);
  if (cached && cached.expiresAt > now) return cached.payload;

  try {
    const resp = await fetch(imageUrl, { method: "GET" });
    if (!resp.ok) return null;
    const contentType = String(resp.headers.get("content-type") || "").toLowerCase();
    if (!contentType.includes("jpeg") && !contentType.includes("jpg")) return null;

    const bytes = new Uint8Array(await resp.arrayBuffer());
    if (!bytes.length || bytes.length > 3_000_000) return null;

    const decoded = jpeg.decode(bytes, {
      useTArray: true,
      formatAsRGBA: true,
      tolerantDecoding: true,
      maxResolutionInMP: 8,
      maxMemoryUsageInMB: 64,
    });
    if (!decoded?.data || !decoded?.width || !decoded?.height) return null;
    if (decoded.width * decoded.height > 8_000_000) return null;

    const payload = {
      width: decoded.width,
      height: decoded.height,
      data: decoded.data instanceof Uint8Array ? decoded.data : new Uint8Array(decoded.data),
    };
    imageRgbaCache.set(imageUrl, { payload, expiresAt: now + JSON_CACHE_TTL_MS });
    return payload;
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
        angle,
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
  url.searchParams.set("format", "png");
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

async function renderVoteOgPng({
  result,
  voteToken = null,
  dipName = "",
  dipGroupName = "",
  dipAvatar = null,
  groupName = "",
  groupVoteToken = null,
}) {
  const width = OG_CANVAS.width;
  const height = OG_CANVAS.height;
  const rgba = new Uint8Array(width * height * 4);

  fillVerticalGradient(rgba, width, height, OG_COLORS.bgA, OG_COLORS.bgB);

  const panel = hexToRgba(OG_COLORS.panel);
  const border = hexToRgba(OG_COLORS.border);
  const muted = hexToRgba(OG_COLORS.muted);
  const favor = hexToRgba(OG_COLORS.favor);
  const contra = hexToRgba(OG_COLORS.contra);
  const abst = hexToRgba(OG_COLORS.abst);
  const noVota = hexToRgba(OG_COLORS.noVota);
  const seatStroke = hexToRgba("#0f172a");
  const white = hexToRgba("#ffffff");

  drawRectRgba(rgba, width, height, 30, 30, 564, 570, border);
  drawRectRgba(rgba, width, height, 34, 34, 556, 562, panel);

  drawRectRgba(rgba, width, height, 618, 72, 548, 486, border);
  drawRectRgba(rgba, width, height, 622, 76, 540, 478, panel);

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
  const orderedCoords = [...coords].sort((a, b) => {
    if (a.angle !== b.angle) return b.angle - a.angle;
    const ar = (a.x - 330) * (a.x - 330) + (a.y - 305) * (a.y - 305);
    const br = (b.x - 330) * (b.x - 330) + (b.y - 305) * (b.y - 305);
    return br - ar;
  });

  const seatColors = [];
  for (let i = 0; i < totals.favor; i++) seatColors.push(favor);
  for (let i = 0; i < totals.contra; i++) seatColors.push(contra);
  for (let i = 0; i < totals.abstencion; i++) seatColors.push(abst);
  for (let i = 0; i < totals.noVota; i++) seatColors.push(noVota);

  for (let i = 0; i < orderedCoords.length; i++) {
    const point = orderedCoords[i];
    const fill = seatColors[i] || noVota;
    drawFilledCircleRgba(rgba, width, height, point.x, point.y, seatRadius + 1.3, seatStroke);
    drawFilledCircleRgba(
      rgba,
      width,
      height,
      point.x,
      point.y,
      seatRadius,
      fill
    );
  }

  const barRows = [
    { value: totals.favor, color: favor },
    { value: totals.contra, color: contra },
    { value: totals.abstencion, color: abst },
  ];
  for (let i = 0; i < barRows.length; i++) {
    const y = 470 + i * 34;
    drawRectRgba(rgba, width, height, 94, y, 432, 12, border);
    const filled = Math.round((barRows[i].value / Math.max(1, totals.total)) * 432);
    drawRectRgba(rgba, width, height, 94, y, filled, 12, barRows[i].color);
  }

  const stackX = 700;
  const stackY = 180;
  const stackH = 300;
  const stackW = 160;
  drawRectRgba(rgba, width, height, stackX - 2, stackY - 2, stackW + 4, stackH + 4, border);
  const totalForStack = Math.max(1, totals.total);
  let cursorY = stackY + stackH;
  const stackRows = [
    { value: totals.favor, color: favor },
    { value: totals.contra, color: contra },
    { value: totals.abstencion, color: abst },
    { value: totals.noVota, color: noVota },
  ];
  for (let i = 0; i < stackRows.length; i++) {
    const h = Math.round((stackRows[i].value / totalForStack) * stackH);
    cursorY -= h;
    drawRectRgba(rgba, width, height, stackX, cursorY, stackW, h, stackRows[i].color);
  }

  const accentToken = voteToken || groupVoteToken;
  const accent =
    accentToken === "si"
      ? favor
      : accentToken === "no"
        ? contra
        : accentToken === "abstencion"
          ? abst
          : accentToken === "no_vota"
            ? noVota
            : muted;
  drawRectRgba(rgba, width, height, 620, 96, 542, 14, accent);

  const summaryBaseY = 186;
  const summaryRowH = 54;
  const summaryRows = [
    { value: totals.favor, color: favor },
    { value: totals.contra, color: contra },
    { value: totals.abstencion, color: abst },
    { value: totals.noVota, color: noVota },
  ];
  for (let i = 0; i < summaryRows.length; i++) {
    const y = summaryBaseY + i * summaryRowH;
    drawRectRgba(rgba, width, height, 900, y, 210, 10, border);
    const lineW = Math.round((summaryRows[i].value / totalForStack) * 210);
    drawRectRgba(rgba, width, height, 900, y, lineW, 10, summaryRows[i].color);
    const dotR = 8;
    drawFilledCircleRgba(rgba, width, height, 872, y + 5, dotR, summaryRows[i].color);
  }

  if (dipName) {
    const dipShort = shortDiputadoName(dipName);
    const dipInitials = initials(dipShort, 2) || "DV";
    const party = normalizeGroupBrand(dipGroupName || groupName);
    const partyColor = hexToRgba(party.color || "#64748b");
    const avatarX = 1052;
    const avatarY = 122;
    const avatarRadius = 58;

    drawFilledCircleRgba(rgba, width, height, avatarX, avatarY, avatarRadius + 4, white);
    drawFilledCircleRgba(rgba, width, height, avatarX, avatarY, avatarRadius, hexToRgba("#1f2937"));
    if (dipAvatar?.data && dipAvatar?.width && dipAvatar?.height) {
      drawCircularImageCoverRgba(
        rgba,
        width,
        height,
        avatarX,
        avatarY,
        avatarRadius,
        dipAvatar.data,
        dipAvatar.width,
        dipAvatar.height
      );
    } else {
      drawFilledCircleRgba(rgba, width, height, avatarX, avatarY + 6, avatarRadius - 10, hexToRgba("#111827"));
      const initScale = dipInitials.length > 1 ? 5 : 6;
      const initWidth = dipInitials.length * 6 * initScale - initScale;
      const initHeight = 7 * initScale;
      drawPixelText(
        rgba,
        width,
        height,
        dipInitials,
        avatarX - Math.floor(initWidth / 2),
        avatarY - Math.floor(initHeight / 2) + 4,
        initScale,
        white
      );
    }

    // Small party badge over the avatar.
    const partyBadgeX = avatarX + 42;
    const partyBadgeY = avatarY + 42;
    const partyLogo = String(party.logo || "PG")
      .toUpperCase()
      .slice(0, 3);
    const partyScale = partyLogo.length >= 3 ? 2 : 3;
    const partyWidth = partyLogo.length * 6 * partyScale - partyScale;
    const partyHeight = 7 * partyScale;
    drawFilledCircleRgba(rgba, width, height, partyBadgeX, partyBadgeY, 24, white);
    drawFilledCircleRgba(rgba, width, height, partyBadgeX, partyBadgeY, 21, partyColor);
    drawPixelText(
      rgba,
      width,
      height,
      partyLogo,
      partyBadgeX - Math.floor(partyWidth / 2),
      partyBadgeY - Math.floor(partyHeight / 2),
      partyScale,
      white
    );
  } else if (groupName) {
    const party = normalizeGroupBrand(groupName);
    const partyColor = hexToRgba(party.color || "#64748b");
    const badgeX = 1080;
    const badgeY = 118;
    drawFilledCircleRgba(rgba, width, height, badgeX, badgeY, 58, white);
    drawFilledCircleRgba(rgba, width, height, badgeX, badgeY, 52, partyColor);
    const logo = String(party.logo || initials(party.label || groupName, 3) || "PG")
      .toUpperCase()
      .slice(0, 4);
    const scale = logo.length >= 4 ? 3 : logo.length >= 3 ? 4 : 5;
    const textWidth = logo.length * 6 * scale - scale;
    const textHeight = 7 * scale;
    drawPixelText(
      rgba,
      width,
      height,
      logo,
      badgeX - Math.floor(textWidth / 2),
      badgeY - Math.floor(textHeight / 2),
      scale,
      white
    );
  }

  return encodeRgbaToPng(width, height, rgba);
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
  imageType = "",
  imageAlt = "",
  redirectUrl,
  scopeId = "nacional",
  noindex = false,
}) {
  const escapedTitle = escapeHtml(title);
  const escapedDescription = escapeHtml(description);
  const escapedCanonical = escapeHtml(canonicalUrl);
  const escapedImage = escapeHtml(imageUrl);
  const escapedImageType = escapeHtml(imageType);
  const escapedImageAlt = escapeHtml(imageAlt);
  const escapedRedirect = escapeHtml(redirectUrl);
  const escapedScope = escapeHtml(scopeId);
  const robots = noindex ? `<meta name="robots" content="noindex, nofollow">` : "";
  const imageTypeMeta = escapedImageType
    ? `<meta property="og:image:type" content="${escapedImageType}">`
    : "";

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
  ${imageTypeMeta}
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

function apiCorsHeaders(cacheControl = `public, max-age=${API_CACHE_TTL_SECONDS}`) {
  return {
    "content-type": "application/json; charset=utf-8",
    "cache-control": cacheControl,
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET, HEAD, OPTIONS",
    "access-control-allow-headers": "content-type",
    "access-control-max-age": "86400",
  };
}

function jsonResponse(payload, status = 200, cacheControl) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: apiCorsHeaders(cacheControl),
  });
}

function parsePositiveInt(value, fallback) {
  const n = Number.parseInt(String(value ?? ""), 10);
  if (!Number.isFinite(n) || n <= 0) return fallback;
  return n;
}

function normalizeSearchToken(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function asNumberOrNull(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function buildVoteRecord(meta, scopeId, index) {
  const vote = meta?.votaciones?.[index];
  if (!vote) return null;
  const result = meta?.votResults?.[index] || {};
  const categoriaIdx = Number.isInteger(vote.categoria) ? vote.categoria : null;
  const categoriaLabel =
    categoriaIdx !== null && Array.isArray(meta?.categorias)
      ? meta.categorias[categoriaIdx] || null
      : null;
  return {
    scope: scopeId,
    idx: index,
    id: String(vote.id || ""),
    legislatura: vote.legislatura || null,
    fecha: vote.fecha || null,
    titulo_ciudadano: vote.titulo_ciudadano || "",
    categoria_idx: categoriaIdx,
    categoria: categoriaLabel,
    etiquetas: Array.isArray(vote.etiquetas) ? vote.etiquetas : [],
    proponente: vote.proponente || "",
    sub_tipo: vote.subTipo || null,
    expediente: vote.exp || null,
    result: result.result || null,
    favor: asNumberOrNull(result.favor),
    contra: asNumberOrNull(result.contra),
    abstencion: asNumberOrNull(result.abstencion),
    total: asNumberOrNull(result.total),
  };
}

async function handleApiScopes(request, env) {
  const requestUrl = new URL(request.url);
  const raw = await fetchJsonAsset(env, requestUrl, "/data/ambitos.json");
  const scopes = Array.isArray(raw?.ambitos) ? raw.ambitos : [];
  return jsonResponse({
    items: scopes.map((scope) => ({
      id: String(scope.id || ""),
      nombre: scope.nombre || "",
      legislaturas: Array.isArray(scope.legislaturas) ? scope.legislaturas : [],
      wip: Boolean(scope.wip),
      wipLabel: scope.wipLabel || "",
    })),
  });
}

async function handleApiVotaciones(request, env) {
  const requestUrl = new URL(request.url);
  const scopeId = normalizeScope(requestUrl.searchParams.get("scope"));
  const scopes = await getAmbitos(env, requestUrl);
  if (!scopes.has(scopeId)) {
    return jsonResponse({ error: `Scope no válido: ${scopeId}` }, 400, "public, max-age=60");
  }

  const query = normalizeSearchToken(requestUrl.searchParams.get("q"));
  const leg = String(requestUrl.searchParams.get("leg") || "").trim().toUpperCase();
  const from = String(requestUrl.searchParams.get("from") || "").trim();
  const to = String(requestUrl.searchParams.get("to") || "").trim();
  const tag = normalizeSearchToken(requestUrl.searchParams.get("tag"));
  const page = parsePositiveInt(requestUrl.searchParams.get("page"), 1);
  const pageSize = Math.min(
    API_MAX_PAGE_SIZE,
    parsePositiveInt(requestUrl.searchParams.get("pageSize"), 20)
  );

  const meta = await getScopeMeta(env, requestUrl, scopeId);
  const fallbackIndices = (meta?.votaciones || []).map((_, idx) => idx);
  const orderedIndices = Array.isArray(meta?.sortedVotIdxByDate) ? meta.sortedVotIdxByDate : fallbackIndices;
  const matchedIndices = [];

  for (let i = 0; i < orderedIndices.length; i++) {
    const idx = orderedIndices[i];
    const vote = meta?.votaciones?.[idx];
    if (!vote) continue;

    if (leg && String(vote.legislatura || "").toUpperCase() !== leg) continue;
    if (from && String(vote.fecha || "") < from) continue;
    if (to && String(vote.fecha || "") > to) continue;

    if (tag) {
      const tags = Array.isArray(vote.etiquetas) ? vote.etiquetas : [];
      const hasTag = tags.some((t) => normalizeSearchToken(t) === tag);
      if (!hasTag) continue;
    }

    if (query) {
      const title = normalizeSearchToken(vote.titulo_ciudadano);
      const proposer = normalizeSearchToken(vote.proponente);
      const voteId = normalizeSearchToken(vote.id);
      if (!title.includes(query) && !proposer.includes(query) && !voteId.includes(query)) continue;
    }

    matchedIndices.push(idx);
  }

  const total = matchedIndices.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, totalPages);
  const start = (safePage - 1) * pageSize;
  const pagedIndices = matchedIndices.slice(start, start + pageSize);
  const items = pagedIndices
    .map((idx) => buildVoteRecord(meta, scopeId, idx))
    .filter(Boolean);

  return jsonResponse({
    scope: scopeId,
    page: safePage,
    pageSize,
    total,
    totalPages,
    filters: {
      q: query || null,
      leg: leg || null,
      from: from || null,
      to: to || null,
      tag: tag || null,
    },
    items,
  });
}

async function handleApiVotacionById(request, env) {
  const requestUrl = new URL(request.url);
  const parts = splitPath(requestUrl.pathname);
  if (parts.length < 4) return null;

  const scopeId = normalizeScope(decodeSegment(parts[2]));
  const voteId = decodeSegment(parts.slice(3).join("/"));
  if (!voteId) return null;

  const scopes = await getAmbitos(env, requestUrl);
  if (!scopes.has(scopeId)) {
    return jsonResponse({ error: `Scope no válido: ${scopeId}` }, 400, "public, max-age=60");
  }

  const meta = await getScopeMeta(env, requestUrl, scopeId);
  const voteIndex = meta?.votIdById?.[voteId];
  if (!Number.isInteger(voteIndex)) {
    return jsonResponse({ error: "Votación no encontrada", scope: scopeId, id: voteId }, 404, "public, max-age=60");
  }

  const vote = buildVoteRecord(meta, scopeId, voteIndex);
  return jsonResponse({ item: vote });
}

async function handleApiDiputadoByName(request, env) {
  const requestUrl = new URL(request.url);
  const parts = splitPath(requestUrl.pathname);
  if (parts.length < 4) return null;

  const scopeId = normalizeScope(decodeSegment(parts[2]));
  const diputadoName = decodeSegment(parts.slice(3).join("/"));
  if (!diputadoName) return null;

  const scopes = await getAmbitos(env, requestUrl);
  if (!scopes.has(scopeId)) {
    return jsonResponse({ error: `Scope no válido: ${scopeId}` }, 400, "public, max-age=60");
  }

  const meta = await getScopeMeta(env, requestUrl, scopeId);
  const dipIdx = findDiputadoIndex(meta, diputadoName);
  if (dipIdx < 0) {
    return jsonResponse(
      { error: "Diputado no encontrado", scope: scopeId, name: diputadoName },
      404,
      "public, max-age=60"
    );
  }

  const stats = meta?.dipStats?.[dipIdx] || {};
  const groupName =
    Number.isInteger(stats?.mainGrupo) && meta?.grupos?.[stats.mainGrupo]
      ? meta.grupos[stats.mainGrupo]
      : "Sin grupo";
  const party = normalizeGroupBrand(groupName);

  const item = {
    scope: scopeId,
    idx: dipIdx,
    nombre: meta?.diputados?.[dipIdx] || diputadoName,
    grupo: groupName,
    partido: party.label,
    logo: party.logo,
    color: party.color,
    stats: {
      total: asNumberOrNull(stats.total),
      favor: asNumberOrNull(stats.favor),
      contra: asNumberOrNull(stats.contra),
      abstencion: asNumberOrNull(stats.abstencion),
      no_vota: asNumberOrNull(stats.no_vota),
      loyalty: Number.isFinite(stats?.loyalty) ? Number(stats.loyalty) : null,
    },
    foto: meta?.dipFotos?.[dipIdx] || null,
    provincia: meta?.dipProvincias?.[dipIdx] || null,
  };

  return jsonResponse({ item });
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
  const formatParam = String(requestUrl.searchParams.get("format") || "svg").toLowerCase();
  const wantsPng = formatParam === "png";
  if (!voteId) return null;

  const scopes = await getAmbitos(env, requestUrl);
  if (!scopes.has(scopeId)) return null;

  const siteUrl = buildSiteUrl(env, requestUrl);
  const meta = await getScopeMeta(env, requestUrl, scopeId);
  const voteIndex = meta?.votIdById?.[voteId];
  let dipGroupName = "";
  let dipAvatar = null;
  if (dipParam) {
    const dipIdx = findDiputadoIndex(meta, dipParam);
    const mainGrupo = dipIdx >= 0 ? meta?.dipStats?.[dipIdx]?.mainGrupo : null;
    if (Number.isInteger(mainGrupo) && meta?.grupos?.[mainGrupo]) {
      dipGroupName = String(meta.grupos[mainGrupo]);
    }
    if (wantsPng && dipIdx >= 0) {
      const dipPhoto = diputadoPhotoUrl(meta?.dipFotos?.[dipIdx], siteUrl);
      dipAvatar = await imageUrlToRgba(dipPhoto);
    }
  }

  if (!Number.isInteger(voteIndex)) {
    if (wantsPng) {
      const png = await renderVoteOgPng({
        result: { favor: 0, contra: 0, abstencion: 0, total: 0, result: "Sin datos" },
        voteToken: voteParam,
        dipName: dipParam,
        dipGroupName,
        dipAvatar,
        groupName: groupParam,
        groupVoteToken: groupVoteParam,
      });
      return new Response(png, {
        status: 404,
        headers: {
          "content-type": "image/png",
          "cache-control": "public, max-age=120",
        },
      });
    }

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
  if (wantsPng) {
    const png = await renderVoteOgPng({
      result,
      voteToken: voteParam,
      dipName: dipParam,
      dipGroupName,
      dipAvatar,
      groupName: groupParam,
      groupVoteToken: groupVoteParam,
    });
    return new Response(png, {
      headers: {
        "content-type": "image/png",
        "cache-control": "public, max-age=600",
      },
    });
  }

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
      imageType: "image/png",
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
  const contextDescription = voteDescription(vote, result, meta.categorias || []);
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
      ? `Contexto completo de la votación: ${contextDescription}`
      : `Consulta cómo votó ${dipParam} en este asunto. ${contextDescription}`
    : groupParam
      ? groupVoteParam
        ? `Contexto completo de la votación: ${contextDescription}`
        : `Consulta qué votó ${groupDisplayName} en este asunto. ${contextDescription}`
    : contextDescription;
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
    imageType: "image/png",
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
    const url = new URL(request.url);
    const pathname = url.pathname.replace(/\/+$/, "") || "/";

    if (request.method === "OPTIONS" && pathname.startsWith("/api/")) {
      return new Response(null, { status: 204, headers: apiCorsHeaders("public, max-age=86400") });
    }

    if (request.method !== "GET" && request.method !== "HEAD") {
      return env.ASSETS.fetch(request);
    }

    try {
      if (pathname === "/api/health") {
        return jsonResponse({
          ok: true,
          service: "loquevotan-worker",
          timestamp: new Date().toISOString(),
          backend: env?.DB ? "d1+assets" : "assets",
        });
      }

      if (pathname === "/api/scopes") {
        return await handleApiScopes(request, env);
      }

      if (pathname === "/api/votaciones") {
        return await handleApiVotaciones(request, env);
      }

      if (pathname.startsWith("/api/votacion/")) {
        const resp = await handleApiVotacionById(request, env);
        if (resp) return resp;
      }

      if (pathname.startsWith("/api/diputado/")) {
        const resp = await handleApiDiputadoByName(request, env);
        if (resp) return resp;
      }

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

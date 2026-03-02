const SITE_NAME = "Lo Que Votan";
const BRAND_TITLE = "LoQueVotan.es";
const JSON_CACHE_TTL_MS = 5 * 60 * 1000;
const LEG_TO_NUM = { X: 10, XI: 11, XII: 12, XIII: 13, XIV: 14, XV: 15 };

const scopeMetaCache = new Map();
let ambitosCache = { expiresAt: 0, data: null };

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

async function handleVoteShare(request, env) {
  const requestUrl = new URL(request.url);
  const parts = splitPath(requestUrl.pathname);

  // /share/votacion/:scope/:id
  if (parts.length < 4) return null;

  const scopeId = normalizeScope(decodeSegment(parts[2]));
  const voteId = decodeSegment(parts.slice(3).join("/"));
  const dipParam = decodeSegment(requestUrl.searchParams.get("dip") || "").trim();
  const voteParam = normalizeVoteToken(requestUrl.searchParams.get("vote"));
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
  const canonicalUrl = canonicalUrlObj.toString();
  const imageUrl = buildImageUrl(env, siteUrl);
  const redirectUrlObj = new URL(`${siteUrl}/votacion/${encodeURIComponent(voteId)}`);
  redirectUrlObj.searchParams.set("scope", scopeId);
  if (dipParam) redirectUrlObj.searchParams.set("dip", dipParam);
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
  const action = voteActionText(voteParam);
  const title = dipParam
    ? voteParam
      ? `${shortDipName} ${action} en ${voteTitle} | ${BRAND_TITLE}`
      : `${shortDipName} en ${voteTitle} | ${BRAND_TITLE}`
    : `${voteTitle} | ${BRAND_TITLE}`;
  const description = dipParam
    ? voteParam
      ? `${shortDipName} ${action} en esta votación. ${voteDescription(vote, result, meta.categorias || [])}`
      : `Consulta cómo votó ${dipParam} en este asunto. ${voteDescription(vote, result, meta.categorias || [])}`
    : voteDescription(vote, result, meta.categorias || []);
  const imageAlt = dipParam
    ? voteParam
      ? `${shortDipName} ${action} en ${voteTitle}`
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
  const dipPhoto = diputadoPhotoUrl(meta?.dipFotos?.[dipIdx], siteUrl);
  const imageUrl = dipPhoto || defaultImageUrl;
  const imageAlt = dipPhoto
    ? `Foto de ${diputadoName}`
    : `Perfil de ${diputadoName} en LoQueVotan.es`;

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

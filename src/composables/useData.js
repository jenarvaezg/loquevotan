import { ref, shallowRef } from "vue";

const loading = ref(true);
const error = ref(null);
const loaded = ref(false);

const ambitos = ref([]);
const currentScopeId = ref(localStorage.getItem("preferredScope") || "nacional");

const diputados = shallowRef([]);
const grupos = shallowRef([]);
const categorias = shallowRef([]);
const votaciones = shallowRef([]);
const votos = shallowRef([]);
const manifest = ref(null);

const votosByVotacion = shallowRef({});
const votosByDiputado = shallowRef({});

const dipFotos = shallowRef([]);
const dipProvincias = shallowRef([]);

const votResults = shallowRef([]);
const dipStats = shallowRef([]);
const tagCounts = shallowRef({});
const topTags = shallowRef([]);
const sortedVotIdxByDate = shallowRef([]);
const groupAffinityByLeg = shallowRef({});
const votsByExp = shallowRef({});
const votacionDetail = shallowRef({});
const votIdById = shallowRef({});

const globalDiputados = shallowRef({});
const loadTelemetry = ref([]);

const votosLoaded = ref(new Set());

let _loadPromise = null;
const _legLoadPromises = {};
const FETCH_TIMEOUT_MS = 12000;
const MAX_TELEMETRY_EVENTS = 120;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function pushTelemetry(event) {
  const next = [...loadTelemetry.value, { ts: new Date().toISOString(), ...event }];
  loadTelemetry.value = next.length > MAX_TELEMETRY_EVENTS ? next.slice(-MAX_TELEMETRY_EVENTS) : next;
}

async function fetchJsonWithRetry(path, options = {}) {
  const {
    attempts = 3,
    timeoutMs = FETCH_TIMEOUT_MS,
    scope = currentScopeId.value,
    critical = true,
  } = options;

  const url = import.meta.env.BASE_URL + path;
  let lastErr = null;

  for (let attempt = 1; attempt <= attempts; attempt++) {
    const startedAt = Date.now();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const resp = await fetch(url, { signal: controller.signal });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const data = await resp.json();
      pushTelemetry({
        scope,
        path,
        attempt,
        ok: true,
        critical,
        status: resp.status,
        durationMs: Date.now() - startedAt,
      });
      return data;
    } catch (err) {
      lastErr = err;
      const msg = err?.name === "AbortError" ? "TIMEOUT" : String(err?.message || err);
      pushTelemetry({
        scope,
        path,
        attempt,
        ok: false,
        critical,
        error: msg,
        durationMs: Date.now() - startedAt,
      });
      if (attempt < attempts) {
        // Exponential backoff + slight jitter to smooth retries across scopes.
        const backoff = Math.round((450 * (2 ** (attempt - 1))) + (Math.random() * 180));
        await sleep(backoff);
      }
    } finally {
      clearTimeout(timeout);
    }
  }

  throw lastErr;
}

async function _doLoad() {
  loading.value = true;
  error.value = null;

  try {
    // Load ambitos config first
    try {
      const config = await fetchJsonWithRetry("data/ambitos.json", {
        attempts: 2,
        timeoutMs: 7000,
        scope: "global",
        critical: false,
      });
      ambitos.value = config.ambitos || [];
    } catch (err) {
      console.warn("Could not load ambitos config:", err);
    }

    // Load global diputados index
    if (Object.keys(globalDiputados.value).length === 0) {
      try {
        globalDiputados.value = await fetchJsonWithRetry("data/global_diputados.json", {
          attempts: 2,
          timeoutMs: 9000,
          scope: "global",
          critical: false,
        });
      } catch (err) {
        console.warn("Could not load global diputados index:", err);
      }
    }

    const scopePath = currentScopeId.value === "nacional" ? "" : `${currentScopeId.value}/`;
    const [raw, manifestData] = await Promise.all([
      fetchJsonWithRetry(`data/${scopePath}votaciones_meta.json`, {
        attempts: 4,
        timeoutMs: 15000,
        scope: currentScopeId.value,
        critical: true,
      }),
      fetchJsonWithRetry(`data/${scopePath}manifest_home.json`, {
        attempts: 3,
        timeoutMs: 10000,
        scope: currentScopeId.value,
        critical: false,
      }).catch(() => null)
    ]);

    manifest.value = manifestData;
    diputados.value = raw.diputados;
    grupos.value = raw.grupos;
    categorias.value = raw.categorias;
    votaciones.value = raw.votaciones;
    dipFotos.value = raw.dipFotos || [];
    dipProvincias.value = raw.dipProvincias || [];
    votResults.value = raw.votResults;
    dipStats.value = raw.dipStats;
    tagCounts.value = raw.tagCounts;
    topTags.value = raw.topTags;
    sortedVotIdxByDate.value = raw.sortedVotIdxByDate;
    groupAffinityByLeg.value = raw.groupAffinityByLeg;
    votsByExp.value = raw.votsByExp;
    votIdById.value = raw.votIdById || {};

    loaded.value = true;
  } catch (err) {
    console.error(`[useData] load failed for scope "${currentScopeId.value}"`, err);
    error.value =
      `Error cargando datos de ${currentScopeId.value}. Comprueba tu conexión e inténtalo de nuevo.`;
  } finally {
    loading.value = false;
  }
}

function retryLoad() {
  _loadPromise = null;
  loadData();
}

function setScope(scopeId) {
  if (currentScopeId.value === scopeId) return;
  currentScopeId.value = scopeId;
  localStorage.setItem("preferredScope", scopeId);
  
  // Reset state
  loaded.value = false;
  diputados.value = [];
  grupos.value = [];
  votaciones.value = [];
  votos.value = [];
  votosLoaded.value = new Set();
  _loadPromise = null;
  Object.keys(_legLoadPromises).forEach(k => delete _legLoadPromises[k]);
  
  return loadData();
}

async function loadVotosForLeg(legId) {
  if (!legId || votosLoaded.value.has(legId)) return;
  if (_legLoadPromises[legId]) return _legLoadPromises[legId];

  _legLoadPromises[legId] = (async () => {
    try {
      const scopePath = currentScopeId.value === "nacional" ? "" : `${currentScopeId.value}/`;
      const data = await fetchJsonWithRetry(`data/${scopePath}votos_${legId}.json`, {
        attempts: 3,
        timeoutMs: 18000,
        scope: `${currentScopeId.value}:${legId}`,
        critical: true,
      });
      const legVotos = data.votos;
      const legDetail = data.detail || {};

      const currentVotos = votos.value;
      const baseIdx = currentVotos.length;
      const merged = currentVotos.concat(legVotos);

      const _vbv = { ...votosByVotacion.value };
      const _vbd = { ...votosByDiputado.value };

      for (let i = 0; i < legVotos.length; i++) {
        const globalIdx = baseIdx + i;
        const votIdx = legVotos[i][0];
        const dipIdx = legVotos[i][1];
        if (!_vbv[votIdx]) _vbv[votIdx] = [];
        _vbv[votIdx].push(globalIdx);
        if (!_vbd[dipIdx]) _vbd[dipIdx] = [];
        _vbd[dipIdx].push(globalIdx);
      }

      votos.value = merged;
      votosByVotacion.value = _vbv;
      votosByDiputado.value = _vbd;

      // Merge detail fields into votacionDetail
      const detailKeys = Object.keys(legDetail);
      if (detailKeys.length) {
        const _detail = { ...votacionDetail.value };
        for (let i = 0; i < detailKeys.length; i++) {
          _detail[Number(detailKeys[i])] = legDetail[detailKeys[i]];
        }
        votacionDetail.value = _detail;
      }

      const newLoaded = new Set(votosLoaded.value);
      newLoaded.add(legId);
      votosLoaded.value = newLoaded;
    } catch (err) {
      console.error(`Error loading votos for ${legId}:`, err);
      delete _legLoadPromises[legId];
    }
  })();

  return _legLoadPromises[legId];
}

function loadData() {
  if (!_loadPromise) _loadPromise = _doLoad();
  return _loadPromise;
}

export function useData() {
  return {
    loading,
    error,
    loaded,
    loadData,
    ambitos,
    currentScopeId,
    setScope,
    diputados,
    grupos,
    categorias,
    votaciones,
    votos,
    manifest,
    votosByVotacion,
    votosByDiputado,
    votResults,
    dipStats,
    tagCounts,
    topTags,
    sortedVotIdxByDate,
    groupAffinityByLeg,
    dipFotos,
    dipProvincias,
    votsByExp,
    votacionDetail,
    votIdById,
    votosLoaded,
    globalDiputados,
    loadVotosForLeg,
    retryLoad,
    loadTelemetry,
  };
}

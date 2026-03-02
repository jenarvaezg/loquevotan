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
let _loadVersion = 0;
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

function isLatestLoad(loadVersion, scopeId) {
  return loadVersion === _loadVersion && scopeId === currentScopeId.value;
}

function resetScopeData() {
  loaded.value = false;
  error.value = null;
  manifest.value = null;
  diputados.value = [];
  grupos.value = [];
  categorias.value = [];
  votaciones.value = [];
  votos.value = [];
  votosByVotacion.value = {};
  votosByDiputado.value = {};
  votacionDetail.value = {};
  votIdById.value = {};
  votResults.value = [];
  dipStats.value = [];
  tagCounts.value = {};
  topTags.value = [];
  sortedVotIdxByDate.value = [];
  groupAffinityByLeg.value = {};
  votsByExp.value = {};
  dipFotos.value = [];
  dipProvincias.value = [];
  votosLoaded.value = new Set();
  Object.keys(_legLoadPromises).forEach((k) => delete _legLoadPromises[k]);
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

async function _doLoad(loadVersion, scopeId) {
  if (!isLatestLoad(loadVersion, scopeId)) return;
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
      if (isLatestLoad(loadVersion, scopeId)) {
        ambitos.value = config.ambitos || [];
      }
    } catch (err) {
      console.warn("Could not load ambitos config:", err);
    }

    // Load global diputados index
    if (Object.keys(globalDiputados.value).length === 0) {
      try {
        const globalIndex = await fetchJsonWithRetry("data/global_diputados.json", {
          attempts: 2,
          timeoutMs: 9000,
          scope: "global",
          critical: false,
        });
        if (isLatestLoad(loadVersion, scopeId)) {
          globalDiputados.value = globalIndex;
        }
      } catch (err) {
        console.warn("Could not load global diputados index:", err);
      }
    }

    const scopePath = scopeId === "nacional" ? "" : `${scopeId}/`;
    const [raw, manifestData] = await Promise.all([
      fetchJsonWithRetry(`data/${scopePath}votaciones_meta.json`, {
        attempts: 4,
        timeoutMs: 15000,
        scope: scopeId,
        critical: true,
      }),
      fetchJsonWithRetry(`data/${scopePath}manifest_home.json`, {
        attempts: 3,
        timeoutMs: 10000,
        scope: scopeId,
        critical: false,
      }).catch(() => null)
    ]);

    if (!isLatestLoad(loadVersion, scopeId)) return;

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
    if (!isLatestLoad(loadVersion, scopeId)) return;
    console.error(`[useData] load failed for scope "${scopeId}"`, err);
    error.value = `Error cargando datos de ${scopeId}. Comprueba tu conexión e inténtalo de nuevo.`;
  } finally {
    if (isLatestLoad(loadVersion, scopeId)) {
      loading.value = false;
    }
  }
}

function retryLoad() {
  _loadPromise = null;
  return loadData();
}

function setScope(scopeId) {
  const normalizedScopeId = String(scopeId || "nacional").trim().toLowerCase();
  if (currentScopeId.value === normalizedScopeId) return Promise.resolve();
  currentScopeId.value = normalizedScopeId;
  localStorage.setItem("preferredScope", normalizedScopeId);

  resetScopeData();
  _loadPromise = null;
  return loadData();
}

async function loadVotosForLeg(legId) {
  if (!legId || votosLoaded.value.has(legId)) return;
  const scopeId = currentScopeId.value;
  const promiseKey = `${scopeId}:${legId}`;
  if (_legLoadPromises[promiseKey]) return _legLoadPromises[promiseKey];

  _legLoadPromises[promiseKey] = (async () => {
    try {
      const scopePath = scopeId === "nacional" ? "" : `${scopeId}/`;
      const data = await fetchJsonWithRetry(`data/${scopePath}votos_${legId}.json`, {
        attempts: 3,
        timeoutMs: 18000,
        scope: `${scopeId}:${legId}`,
        critical: true,
      });
      if (currentScopeId.value !== scopeId) return;
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
      if (currentScopeId.value === scopeId) {
        console.error(`Error loading votos for ${legId}:`, err);
      }
    } finally {
      delete _legLoadPromises[promiseKey];
    }
  })();

  return _legLoadPromises[promiseKey];
}

function loadData() {
  if (!_loadPromise) {
    _loadVersion += 1;
    const loadVersion = _loadVersion;
    const scopeId = currentScopeId.value;
    _loadPromise = _doLoad(loadVersion, scopeId);
  }
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

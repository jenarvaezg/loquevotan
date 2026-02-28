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

const votosByVotacion = shallowRef({});
const votosByDiputado = shallowRef({});

const dipFotos = shallowRef([]);

const votResults = shallowRef([]);
const dipStats = shallowRef([]);
const tagCounts = shallowRef({});
const topTags = shallowRef([]);
const sortedVotIdxByDate = shallowRef([]);
const groupAffinityByLeg = shallowRef({});
const votsByExp = shallowRef({});
const votacionDetail = shallowRef({});
const votIdById = shallowRef({});

const votosLoaded = ref(new Set());

let _loadPromise = null;
const _legLoadPromises = {};

async function _doLoad(retryCount = 0) {
  loading.value = true;
  error.value = null;

  try {
    // Load ambitos config first
    const ambitosResp = await fetch(import.meta.env.BASE_URL + "data/ambitos.json");
    if (ambitosResp.ok) {
      const config = await ambitosResp.json();
      ambitos.value = config.ambitos || [];
    }

    const scopePath = currentScopeId.value === "nacional" ? "" : `${currentScopeId.value}/`;
    const url = import.meta.env.BASE_URL + `data/${scopePath}votaciones_meta.json`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const raw = await resp.json();

    diputados.value = raw.diputados;
    grupos.value = raw.grupos;
    categorias.value = raw.categorias;
    votaciones.value = raw.votaciones;
    dipFotos.value = raw.dipFotos || [];
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
    if (retryCount < 2) {
      await new Promise((r) => setTimeout(r, 1000 * (retryCount + 1)));
      return _doLoad(retryCount + 1);
    }
    error.value =
      "Error cargando datos. Comprueba tu conexión e inténtalo de nuevo.";
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
      const url = import.meta.env.BASE_URL + `data/${scopePath}votos_${legId}.json`;
      const resp = await fetch(url);
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const data = await resp.json();
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
    votosByVotacion,
    votosByDiputado,
    votResults,
    dipStats,
    tagCounts,
    topTags,
    sortedVotIdxByDate,
    groupAffinityByLeg,
    dipFotos,
    votsByExp,
    votacionDetail,
    votIdById,
    votosLoaded,
    loadVotosForLeg,
    retryLoad,
  };
}

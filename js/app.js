(() => {
  "use strict";

  const PAGE_SIZE = 50;
  const DATA_URL = "data/votaciones.json";

  // Normalized data from JSON
  let diputados = [];
  let grupos = [];
  let categorias = [];
  let votaciones = [];
  let votos = [];

  // Derived flat records for filtering/display
  let allData = [];
  let filtered = [];
  let currentPage = 1;
  let selectedTags = [];

  const els = {};

  // ── Bootstrap ──────────────────────────────────────────────

  async function init() {
    cacheElements();
    showLoading(true);

    try {
      const resp = await fetch(DATA_URL);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const raw = await resp.json();

      diputados = raw.diputados;
      grupos = raw.grupos;
      categorias = raw.categorias;
      votaciones = raw.votaciones;
      votos = raw.votos;

      allData = expandVotos();

      populateFilters();
      attachListeners();
      applyFilters();
    } catch (err) {
      showError(`Error cargando datos: ${err.message}`);
    } finally {
      showLoading(false);
    }
  }

  function expandVotos() {
    // Expand compact [votacion_idx, diputado_idx, grupo_idx, voto_code] into flat records
    const votoLabels = { 1: "A favor", 2: "En contra", 3: "Abstención" };
    const records = new Array(votos.length);

    for (let i = 0; i < votos.length; i++) {
      const v = votos[i];
      const vot = votaciones[v[0]];
      records[i] = {
        fecha: vot.fecha,
        titulo_ciudadano: vot.titulo_ciudadano,
        categoria_principal: categorias[vot.categoria],
        etiquetas: vot.etiquetas,
        diputado: diputados[v[1]],
        grupo: grupos[v[2]],
        voto: votoLabels[v[3]],
      };
    }

    return records;
  }

  function cacheElements() {
    [
      "search-diputado",
      "filter-categoria",
      "filter-grupo",
      "filter-voto",
      "filter-fecha-desde",
      "filter-fecha-hasta",
      "filter-etiqueta",
      "etiquetas-list",
      "tags-activos",
      "btn-reset",
      "results-count",
      "results-body",
      "pagination",
      "loading",
      "error",
    ].forEach((id) => {
      els[id] = document.getElementById(id);
    });
  }

  // ── Filters ────────────────────────────────────────────────

  function populateFilters() {
    const cats = categorias.slice().sort();
    fillSelect(els["filter-categoria"], cats, formatCategory);

    const grps = grupos.slice().sort();
    fillSelect(els["filter-grupo"], grps);

    // Populate datalist with all unique tags
    const allTags = unique(votaciones.flatMap((v) => v.etiquetas || [])).sort();
    const datalist = els["etiquetas-list"];
    allTags.forEach((tag) => {
      const opt = document.createElement("option");
      opt.value = formatTag(tag);
      datalist.appendChild(opt);
    });
  }

  function fillSelect(select, values, formatter) {
    values.forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = formatter ? formatter(v) : v;
      select.appendChild(opt);
    });
  }

  function formatCategory(cat) {
    return cat.replace(/_/g, " ");
  }

  function formatTag(tag) {
    return tag.replace(/_/g, " ");
  }

  function rawTag(formatted) {
    return formatted.replace(/ /g, "_");
  }

  function attachListeners() {
    els["search-diputado"].addEventListener("input", debounce(applyFilters, 250));
    els["filter-categoria"].addEventListener("change", applyFilters);
    els["filter-grupo"].addEventListener("change", applyFilters);
    els["filter-voto"].addEventListener("change", applyFilters);
    els["filter-fecha-desde"].addEventListener("change", applyFilters);
    els["filter-fecha-hasta"].addEventListener("change", applyFilters);
    els["btn-reset"].addEventListener("click", resetFilters);

    // Tag input: add tag on Enter or selection from datalist
    const tagInput = els["filter-etiqueta"];
    tagInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addTagFromInput();
      }
    });
    tagInput.addEventListener("change", () => {
      addTagFromInput();
    });
  }

  function addTagFromInput() {
    const input = els["filter-etiqueta"];
    const value = input.value.trim();
    if (!value) return;

    const tag = rawTag(value);
    if (!selectedTags.includes(tag)) {
      selectedTags = [...selectedTags, tag];
      renderActiveTags();
      applyFilters();
    }
    input.value = "";
  }

  function removeTag(tag) {
    selectedTags = selectedTags.filter((t) => t !== tag);
    renderActiveTags();
    applyFilters();
  }

  function renderActiveTags() {
    const container = els["tags-activos"];
    container.innerHTML = "";
    selectedTags.forEach((tag) => {
      const span = document.createElement("span");
      span.className = "tag-active";
      span.innerHTML =
        formatTag(tag) +
        ' <button type="button" class="tag-remove" aria-label="Quitar">\u00d7</button>';
      span.querySelector("button").addEventListener("click", () => removeTag(tag));
      container.appendChild(span);
    });
  }

  function resetFilters() {
    els["search-diputado"].value = "";
    els["filter-categoria"].value = "";
    els["filter-grupo"].value = "";
    els["filter-voto"].value = "";
    els["filter-fecha-desde"].value = "";
    els["filter-fecha-hasta"].value = "";
    els["filter-etiqueta"].value = "";
    selectedTags = [];
    renderActiveTags();
    applyFilters();
  }

  function applyFilters() {
    const search = els["search-diputado"].value.toLowerCase().trim();
    const cat = els["filter-categoria"].value;
    const grupo = els["filter-grupo"].value;
    const voto = els["filter-voto"].value;
    const desde = els["filter-fecha-desde"].value;
    const hasta = els["filter-fecha-hasta"].value;

    filtered = allData.filter((r) => {
      if (search && !r.diputado.toLowerCase().includes(search)) return false;
      if (cat && r.categoria_principal !== cat) return false;
      if (grupo && r.grupo !== grupo) return false;
      if (voto && r.voto !== voto) return false;
      if (desde && r.fecha < desde) return false;
      if (hasta && r.fecha > hasta) return false;
      if (selectedTags.length > 0) {
        const recordTags = r.etiquetas || [];
        if (!selectedTags.every((t) => recordTags.includes(t))) return false;
      }
      return true;
    });

    currentPage = 1;
    render();
  }

  // ── Rendering ──────────────────────────────────────────────

  function render() {
    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    const start = (currentPage - 1) * PAGE_SIZE;
    const page = filtered.slice(start, start + PAGE_SIZE);

    els["results-count"].textContent =
      `${total.toLocaleString("es-ES")} votos encontrados`;

    renderRows(page);
    renderPagination(totalPages);
  }

  function renderRows(rows) {
    const tbody = els["results-body"];
    tbody.innerHTML = "";

    if (rows.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 7;
      td.textContent = "No se encontraron resultados con los filtros actuales.";
      td.style.textAlign = "center";
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    const fragment = document.createDocumentFragment();

    rows.forEach((r) => {
      const tr = document.createElement("tr");

      const tdFecha = document.createElement("td");
      tdFecha.textContent = r.fecha;

      const tdDiputado = document.createElement("td");
      tdDiputado.textContent = r.diputado;

      const tdGrupo = document.createElement("td");
      const spanGrupo = document.createElement("span");
      spanGrupo.className = "badge";
      spanGrupo.textContent = r.grupo;
      tdGrupo.appendChild(spanGrupo);

      const tdAsunto = document.createElement("td");
      tdAsunto.textContent = r.titulo_ciudadano;
      tdAsunto.title = r.titulo_ciudadano;

      const tdCat = document.createElement("td");
      const spanCat = document.createElement("span");
      spanCat.className = "badge cat";
      spanCat.textContent = formatCategory(r.categoria_principal);
      tdCat.appendChild(spanCat);

      const tdTags = document.createElement("td");
      (r.etiquetas || []).forEach((tag) => {
        const span = document.createElement("span");
        span.className = "tag-pill";
        span.textContent = formatTag(tag);
        span.addEventListener("click", () => {
          if (!selectedTags.includes(tag)) {
            selectedTags = [...selectedTags, tag];
            renderActiveTags();
            applyFilters();
          }
        });
        tdTags.appendChild(span);
      });

      const tdVoto = document.createElement("td");
      const spanVoto = document.createElement("span");
      spanVoto.className = `voto voto-${votoClass(r.voto)}`;
      spanVoto.textContent = r.voto;
      tdVoto.appendChild(spanVoto);

      tr.appendChild(tdFecha);
      tr.appendChild(tdDiputado);
      tr.appendChild(tdGrupo);
      tr.appendChild(tdAsunto);
      tr.appendChild(tdCat);
      tr.appendChild(tdTags);
      tr.appendChild(tdVoto);

      fragment.appendChild(tr);
    });

    tbody.appendChild(fragment);
  }

  function votoClass(voto) {
    if (voto === "A favor") return "favor";
    if (voto === "En contra") return "contra";
    return "abstencion";
  }

  // ── Pagination ─────────────────────────────────────────────

  function renderPagination(totalPages) {
    const nav = els["pagination"];
    nav.innerHTML = "";

    if (totalPages <= 1) return;

    addPageBtn(nav, "\u2190 Anterior", currentPage > 1 ? currentPage - 1 : null);

    getPageRange(currentPage, totalPages).forEach((p) => {
      if (p === "...") {
        const span = document.createElement("span");
        span.textContent = "\u2026";
        span.className = "page-ellipsis";
        nav.appendChild(span);
      } else {
        addPageBtn(nav, String(p), p, p === currentPage);
      }
    });

    addPageBtn(nav, "Siguiente \u2192", currentPage < totalPages ? currentPage + 1 : null);
  }

  function addPageBtn(parent, label, page, active) {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.className = active ? "page-btn active" : "page-btn";
    btn.disabled = page === null;
    if (page !== null && !active) {
      btn.addEventListener("click", () => {
        currentPage = page;
        render();
        const table = els["results-body"].closest("table");
        if (table) {
          window.scrollTo({ top: table.offsetTop - 80, behavior: "smooth" });
        }
      });
    }
    parent.appendChild(btn);
  }

  function getPageRange(current, total) {
    if (total <= 7) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }
    const pages = [1];
    if (current > 3) pages.push("...");
    const lo = Math.max(2, current - 1);
    const hi = Math.min(total - 1, current + 1);
    for (let i = lo; i <= hi; i++) pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
    return pages;
  }

  // ── Helpers ────────────────────────────────────────────────

  function unique(arr) {
    return [...new Set(arr)];
  }

  function debounce(fn, ms) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }

  function showLoading(show) {
    els["loading"].style.display = show ? "block" : "none";
  }

  function showError(msg) {
    els["error"].textContent = msg;
    els["error"].style.display = "block";
  }

  // ── Start ──────────────────────────────────────────────────

  document.addEventListener("DOMContentLoaded", init);
})();

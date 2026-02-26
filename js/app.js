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

  // Precomputed indexes
  let votosByVotacion = {};  // votacion_idx -> [{diputado_idx, grupo_idx, voto_code}]
  let votosByDiputado = {};  // diputado_idx -> [{votacion_idx, grupo_idx, voto_code}]

  // List view state
  let allData = [];
  let filtered = [];
  let currentPage = 1;
  let selectedTags = [];

  // Detail view state
  let dipPage = 1;
  let dipFiltered = [];

  const votoLabels = { 1: "A favor", 2: "En contra", 3: "Abstencion" };

  // ── Bootstrap ──────────────────────────────────────────────

  async function init() {
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

      buildIndexes();
      allData = expandVotos();

      populateFilters();
      attachListeners();
      handleRoute();
    } catch (err) {
      showError(`Error cargando datos: ${err.message}`);
    } finally {
      showLoading(false);
    }
  }

  function buildIndexes() {
    votosByVotacion = {};
    votosByDiputado = {};
    for (let i = 0; i < votos.length; i++) {
      const v = votos[i];
      const entry = { votacion_idx: v[0], diputado_idx: v[1], grupo_idx: v[2], voto_code: v[3] };

      if (!votosByVotacion[v[0]]) votosByVotacion[v[0]] = [];
      votosByVotacion[v[0]].push(entry);

      if (!votosByDiputado[v[1]]) votosByDiputado[v[1]] = [];
      votosByDiputado[v[1]].push(entry);
    }
  }

  function expandVotos() {
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
        diputado_idx: v[1],
        grupo: grupos[v[2]],
        voto: votoLabels[v[3]],
        votacion_idx: v[0],
      };
    }
    return records;
  }

  // ── Routing ────────────────────────────────────────────────

  function handleRoute() {
    const hash = window.location.hash;

    document.getElementById("view-list").hidden = true;
    document.getElementById("view-votacion").hidden = true;
    document.getElementById("view-diputado").hidden = true;

    if (hash.startsWith("#votacion/")) {
      const idx = parseInt(hash.split("/")[1], 10);
      if (idx >= 0 && idx < votaciones.length) {
        renderVotacionDetail(idx);
        document.getElementById("view-votacion").hidden = false;
        window.scrollTo(0, 0);
        return;
      }
    }

    if (hash.startsWith("#diputado/")) {
      const name = decodeURIComponent(hash.substring("#diputado/".length));
      const idx = diputados.indexOf(name);
      if (idx >= 0) {
        renderDiputadoDetail(idx);
        document.getElementById("view-diputado").hidden = false;
        window.scrollTo(0, 0);
        return;
      }
    }

    // Default: list view
    document.getElementById("view-list").hidden = false;
    applyFilters();
  }

  // ── Filters (list view) ────────────────────────────────────

  function populateFilters() {
    const catSelect = document.getElementById("filter-categoria");
    categorias.slice().sort().forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = fmt(c);
      catSelect.appendChild(opt);
    });

    const grpSelect = document.getElementById("filter-grupo");
    grupos.slice().sort().forEach((g) => {
      const opt = document.createElement("option");
      opt.value = g;
      opt.textContent = g;
      grpSelect.appendChild(opt);
    });

    const datalist = document.getElementById("etiquetas-list");
    const allTags = [...new Set(votaciones.flatMap((v) => v.etiquetas || []))].sort();
    allTags.forEach((tag) => {
      const opt = document.createElement("option");
      opt.value = fmt(tag);
      datalist.appendChild(opt);
    });
  }

  function attachListeners() {
    window.addEventListener("hashchange", handleRoute);

    document.getElementById("search-diputado").addEventListener("input", debounce(applyFilters, 250));
    document.getElementById("filter-categoria").addEventListener("change", applyFilters);
    document.getElementById("filter-grupo").addEventListener("change", applyFilters);
    document.getElementById("filter-voto").addEventListener("change", applyFilters);
    document.getElementById("filter-fecha-desde").addEventListener("change", applyFilters);
    document.getElementById("filter-fecha-hasta").addEventListener("change", applyFilters);
    document.getElementById("btn-reset").addEventListener("click", resetFilters);

    const tagInput = document.getElementById("filter-etiqueta");
    tagInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); addTagFromInput(); }
    });
    tagInput.addEventListener("change", addTagFromInput);
  }

  function addTagFromInput() {
    const input = document.getElementById("filter-etiqueta");
    const value = input.value.trim();
    if (!value) return;
    const tag = value.replace(/ /g, "_");
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
    const container = document.getElementById("tags-activos");
    container.innerHTML = "";
    selectedTags.forEach((tag) => {
      const span = document.createElement("span");
      span.className = "tag-active";
      span.textContent = fmt(tag) + " ";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tag-remove";
      btn.textContent = "\u00d7";
      btn.addEventListener("click", () => removeTag(tag));
      span.appendChild(btn);
      container.appendChild(span);
    });
  }

  function resetFilters() {
    document.getElementById("search-diputado").value = "";
    document.getElementById("filter-categoria").value = "";
    document.getElementById("filter-grupo").value = "";
    document.getElementById("filter-voto").value = "";
    document.getElementById("filter-fecha-desde").value = "";
    document.getElementById("filter-fecha-hasta").value = "";
    document.getElementById("filter-etiqueta").value = "";
    selectedTags = [];
    renderActiveTags();
    applyFilters();
  }

  function applyFilters() {
    const search = document.getElementById("search-diputado").value.toLowerCase().trim();
    const cat = document.getElementById("filter-categoria").value;
    const grupo = document.getElementById("filter-grupo").value;
    const voto = document.getElementById("filter-voto").value;
    const desde = document.getElementById("filter-fecha-desde").value;
    const hasta = document.getElementById("filter-fecha-hasta").value;

    filtered = allData.filter((r) => {
      if (search && !r.diputado.toLowerCase().includes(search)) return false;
      if (cat && r.categoria_principal !== cat) return false;
      if (grupo && r.grupo !== grupo) return false;
      if (voto && r.voto !== voto) return false;
      if (desde && r.fecha < desde) return false;
      if (hasta && r.fecha > hasta) return false;
      if (selectedTags.length > 0) {
        const tags = r.etiquetas || [];
        if (!selectedTags.every((t) => tags.includes(t))) return false;
      }
      return true;
    });

    currentPage = 1;
    renderList();
  }

  // ── List view rendering ────────────────────────────────────

  function renderList() {
    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    const start = (currentPage - 1) * PAGE_SIZE;
    const page = filtered.slice(start, start + PAGE_SIZE);

    document.getElementById("results-count").textContent =
      `${total.toLocaleString("es-ES")} votos encontrados`;

    const tbody = document.getElementById("results-body");
    tbody.innerHTML = "";

    if (page.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center">No se encontraron resultados.</td></tr>';
      document.getElementById("pagination").innerHTML = "";
      return;
    }

    const frag = document.createDocumentFragment();
    page.forEach((r) => {
      const tr = document.createElement("tr");

      tr.appendChild(td(r.fecha));

      const dipTd = document.createElement("td");
      const dipLink = document.createElement("a");
      dipLink.href = `#diputado/${encodeURIComponent(r.diputado)}`;
      dipLink.textContent = r.diputado;
      dipTd.appendChild(dipLink);
      tr.appendChild(dipTd);

      tr.appendChild(td(r.grupo, "badge"));

      const asuntoTd = document.createElement("td");
      const asuntoLink = document.createElement("a");
      asuntoLink.href = `#votacion/${r.votacion_idx}`;
      asuntoLink.textContent = r.titulo_ciudadano;
      asuntoLink.title = r.titulo_ciudadano;
      asuntoTd.appendChild(asuntoLink);
      tr.appendChild(asuntoTd);

      tr.appendChild(td(fmt(r.categoria_principal), "badge cat"));
      tr.appendChild(tagsTd(r.etiquetas));
      tr.appendChild(voteTd(r.voto));

      frag.appendChild(tr);
    });
    tbody.appendChild(frag);

    renderPagination(document.getElementById("pagination"), totalPages, currentPage, (p) => {
      currentPage = p;
      renderList();
      window.scrollTo({ top: tbody.closest("table").offsetTop - 80, behavior: "smooth" });
    });
  }

  // ── Votacion detail ────────────────────────────────────────

  function renderVotacionDetail(idx) {
    const vot = votaciones[idx];
    const votVotos = votosByVotacion[idx] || [];

    document.getElementById("vot-titulo").textContent = vot.titulo_ciudadano;
    document.getElementById("vot-resumen").textContent = vot.resumen_sencillo || "";
    document.getElementById("vot-fecha").textContent = vot.fecha;
    document.getElementById("vot-categoria").textContent = fmt(categorias[vot.categoria]);

    const etContainer = document.getElementById("vot-etiquetas");
    etContainer.innerHTML = "";
    (vot.etiquetas || []).forEach((tag) => {
      const span = document.createElement("span");
      span.className = "tag-pill";
      span.textContent = fmt(tag);
      etContainer.appendChild(span);
    });

    // Count totals
    const totals = { 1: 0, 2: 0, 3: 0 };
    votVotos.forEach((v) => { totals[v.voto_code] = (totals[v.voto_code] || 0) + 1; });
    const total = votVotos.length;

    renderVoteBars(document.getElementById("vot-bars"), totals, total);

    document.getElementById("vot-totals").innerHTML =
      `<span class="voto voto-favor">${totals[1]} a favor</span> ` +
      `<span class="voto voto-contra">${totals[2]} en contra</span> ` +
      `<span class="voto voto-abstencion">${totals[3]} abstenciones</span> ` +
      `<span class="total-count">${total} votos totales</span>`;

    // Group breakdown
    const byGroup = {};
    votVotos.forEach((v) => {
      const g = grupos[v.grupo_idx];
      if (!byGroup[g]) byGroup[g] = { 1: 0, 2: 0, 3: 0, total: 0 };
      byGroup[g][v.voto_code]++;
      byGroup[g].total++;
    });

    const grpBody = document.getElementById("vot-grupos-body");
    grpBody.innerHTML = "";
    Object.keys(byGroup).sort().forEach((g) => {
      const d = byGroup[g];
      const tr = document.createElement("tr");
      tr.appendChild(td(g, "badge"));
      tr.appendChild(td(String(d[1])));
      tr.appendChild(td(String(d[2])));
      tr.appendChild(td(String(d[3])));
      tr.appendChild(td(String(d.total)));
      grpBody.appendChild(tr);
    });

    // Individual votes
    const searchInput = document.getElementById("vot-search-dip");
    searchInput.value = "";
    const renderIndividual = () => {
      const q = searchInput.value.toLowerCase().trim();
      const body = document.getElementById("vot-votos-body");
      body.innerHTML = "";
      const frag = document.createDocumentFragment();
      const sorted = [...votVotos].sort((a, b) => diputados[a.diputado_idx].localeCompare(diputados[b.diputado_idx]));
      sorted.forEach((v) => {
        const name = diputados[v.diputado_idx];
        if (q && !name.toLowerCase().includes(q)) return;
        const tr = document.createElement("tr");
        const nameTd = document.createElement("td");
        const nameLink = document.createElement("a");
        nameLink.href = `#diputado/${encodeURIComponent(name)}`;
        nameLink.textContent = name;
        nameTd.appendChild(nameLink);
        tr.appendChild(nameTd);
        tr.appendChild(td(grupos[v.grupo_idx], "badge"));
        tr.appendChild(voteTd(votoLabels[v.voto_code]));
        frag.appendChild(tr);
      });
      body.appendChild(frag);
    };
    searchInput.oninput = debounce(renderIndividual, 200);
    renderIndividual();
  }

  // ── Diputado detail ────────────────────────────────────────

  function renderDiputadoDetail(dipIdx) {
    const name = diputados[dipIdx];
    const dipVotos = votosByDiputado[dipIdx] || [];

    document.getElementById("dip-nombre").textContent = name;

    // Find most common grupo
    const grupoCount = {};
    dipVotos.forEach((v) => {
      const g = grupos[v.grupo_idx];
      grupoCount[g] = (grupoCount[g] || 0) + 1;
    });
    const mainGrupo = Object.keys(grupoCount).sort((a, b) => grupoCount[b] - grupoCount[a])[0] || "Sin grupo";
    document.getElementById("dip-grupo").textContent = `Grupo: ${mainGrupo}`;

    // Stats
    const totals = { 1: 0, 2: 0, 3: 0 };
    dipVotos.forEach((v) => { totals[v.voto_code]++; });
    const total = dipVotos.length;

    const statsEl = document.getElementById("dip-stats");
    statsEl.innerHTML =
      `<div class="stat-card"><strong>${total}</strong><small>Votaciones</small></div>` +
      `<div class="stat-card stat-favor"><strong>${totals[1]}</strong><small>A favor (${pct(totals[1], total)})</small></div>` +
      `<div class="stat-card stat-contra"><strong>${totals[2]}</strong><small>En contra (${pct(totals[2], total)})</small></div>` +
      `<div class="stat-card stat-abstencion"><strong>${totals[3]}</strong><small>Abstencion (${pct(totals[3], total)})</small></div>`;

    renderVoteBars(document.getElementById("dip-bars"), totals, total);

    // Top tags
    const tagCount = {};
    dipVotos.forEach((v) => {
      const vot = votaciones[v.votacion_idx];
      (vot.etiquetas || []).forEach((t) => { tagCount[t] = (tagCount[t] || 0) + 1; });
    });
    const topTags = Object.entries(tagCount).sort((a, b) => b[1] - a[1]).slice(0, 20);
    const tagsEl = document.getElementById("dip-top-tags");
    tagsEl.innerHTML = "";
    topTags.forEach(([tag, count]) => {
      const span = document.createElement("span");
      span.className = "tag-pill tag-with-count";
      span.textContent = `${fmt(tag)} (${count})`;
      tagsEl.appendChild(span);
    });

    // Vote history with filters
    const buildDipRecords = () => {
      return dipVotos.map((v) => {
        const vot = votaciones[v.votacion_idx];
        return {
          fecha: vot.fecha,
          titulo_ciudadano: vot.titulo_ciudadano,
          categoria_principal: categorias[vot.categoria],
          etiquetas: vot.etiquetas,
          voto: votoLabels[v.voto_code],
          votacion_idx: v.votacion_idx,
        };
      }).sort((a, b) => b.fecha.localeCompare(a.fecha));
    };

    const allDipRecords = buildDipRecords();
    dipPage = 1;

    const renderDipHistory = () => {
      const q = document.getElementById("dip-search-asunto").value.toLowerCase().trim();
      const votoFilter = document.getElementById("dip-filter-voto").value;

      dipFiltered = allDipRecords.filter((r) => {
        if (q && !r.titulo_ciudadano.toLowerCase().includes(q)) return false;
        if (votoFilter && r.voto !== votoFilter) return false;
        return true;
      });

      const totalPages = Math.max(1, Math.ceil(dipFiltered.length / PAGE_SIZE));
      if (dipPage > totalPages) dipPage = 1;
      const start = (dipPage - 1) * PAGE_SIZE;
      const page = dipFiltered.slice(start, start + PAGE_SIZE);

      const body = document.getElementById("dip-votos-body");
      body.innerHTML = "";
      const frag = document.createDocumentFragment();
      page.forEach((r) => {
        const tr = document.createElement("tr");
        tr.appendChild(td(r.fecha));
        const asuntoTd = document.createElement("td");
        const asuntoLink = document.createElement("a");
        asuntoLink.href = `#votacion/${r.votacion_idx}`;
        asuntoLink.textContent = r.titulo_ciudadano;
        asuntoTd.appendChild(asuntoLink);
        tr.appendChild(asuntoTd);
        tr.appendChild(td(fmt(r.categoria_principal), "badge cat"));
        tr.appendChild(tagsTd(r.etiquetas));
        tr.appendChild(voteTd(r.voto));
        frag.appendChild(tr);
      });
      body.appendChild(frag);

      renderPagination(document.getElementById("dip-pagination"), totalPages, dipPage, (p) => {
        dipPage = p;
        renderDipHistory();
      });
    };

    document.getElementById("dip-search-asunto").value = "";
    document.getElementById("dip-filter-voto").value = "";
    document.getElementById("dip-search-asunto").oninput = debounce(renderDipHistory, 250);
    document.getElementById("dip-filter-voto").onchange = renderDipHistory;
    renderDipHistory();
  }

  // ── Shared rendering helpers ───────────────────────────────

  function renderVoteBars(container, totals, total) {
    if (total === 0) { container.innerHTML = ""; return; }
    const pFavor = (totals[1] / total * 100).toFixed(1);
    const pContra = (totals[2] / total * 100).toFixed(1);
    const pAbst = (totals[3] / total * 100).toFixed(1);
    container.innerHTML =
      `<div class="bar-container">` +
      `<div class="bar bar-favor" style="width:${pFavor}%" title="A favor: ${pFavor}%"></div>` +
      `<div class="bar bar-contra" style="width:${pContra}%" title="En contra: ${pContra}%"></div>` +
      `<div class="bar bar-abstencion" style="width:${pAbst}%" title="Abstencion: ${pAbst}%"></div>` +
      `</div>`;
  }

  function renderPagination(nav, totalPages, current, onPage) {
    nav.innerHTML = "";
    if (totalPages <= 1) return;

    const addBtn = (label, page, active) => {
      const btn = document.createElement("button");
      btn.textContent = label;
      btn.className = active ? "page-btn active" : "page-btn";
      btn.disabled = page === null;
      if (page !== null && !active) {
        btn.addEventListener("click", () => onPage(page));
      }
      nav.appendChild(btn);
    };

    addBtn("\u2190", current > 1 ? current - 1 : null);
    getPageRange(current, totalPages).forEach((p) => {
      if (p === "...") {
        const span = document.createElement("span");
        span.textContent = "\u2026";
        span.className = "page-ellipsis";
        nav.appendChild(span);
      } else {
        addBtn(String(p), p, p === current);
      }
    });
    addBtn("\u2192", current < totalPages ? current + 1 : null);
  }

  function getPageRange(current, total) {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages = [1];
    if (current > 3) pages.push("...");
    for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
    return pages;
  }

  // ── DOM helpers ────────────────────────────────────────────

  function td(text, badgeClass) {
    const el = document.createElement("td");
    if (badgeClass) {
      const span = document.createElement("span");
      span.className = badgeClass;
      span.textContent = text;
      el.appendChild(span);
    } else {
      el.textContent = text;
    }
    return el;
  }

  function tagsTd(tags) {
    const el = document.createElement("td");
    (tags || []).forEach((tag) => {
      const span = document.createElement("span");
      span.className = "tag-pill";
      span.textContent = fmt(tag);
      span.addEventListener("click", () => {
        if (!selectedTags.includes(tag)) {
          selectedTags = [...selectedTags, tag];
          renderActiveTags();
          window.location.hash = "";
        }
      });
      el.appendChild(span);
    });
    return el;
  }

  function voteTd(voto) {
    const el = document.createElement("td");
    const span = document.createElement("span");
    span.className = `voto voto-${votoClass(voto)}`;
    span.textContent = voto;
    el.appendChild(span);
    return el;
  }

  function votoClass(voto) {
    if (voto === "A favor") return "favor";
    if (voto === "En contra") return "contra";
    return "abstencion";
  }

  function fmt(s) { return (s || "").replace(/_/g, " "); }
  function pct(n, t) { return t > 0 ? (n / t * 100).toFixed(1) + "%" : "0%"; }

  function debounce(fn, ms) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
  }

  function showLoading(show) {
    document.getElementById("loading").style.display = show ? "block" : "none";
  }

  function showError(msg) {
    const el = document.getElementById("error");
    el.textContent = msg;
    el.style.display = "block";
  }

  // ── Start ──────────────────────────────────────────────────

  document.addEventListener("DOMContentLoaded", init);
})();

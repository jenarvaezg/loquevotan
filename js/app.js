(() => {
  "use strict";

  const DATA_URL = "data/votaciones.json";
  const VOTES_PER_PAGE = 20;
  const DIPS_PER_PAGE = 30;

  const LEGISLATURAS = [
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

  function getLeg(fecha) {
    for (let i = LEGISLATURAS.length - 1; i >= 0; i--) {
      if (fecha >= LEGISLATURAS[i].desde && fecha <= LEGISLATURAS[i].hasta)
        return LEGISLATURAS[i].id;
    }
    return "";
  }

  // ── Raw data ──
  let diputados = [];
  let grupos = [];
  let categorias = [];
  let votaciones = [];
  let votos = [];

  // ── Indexes (store voto indices, not objects) ──
  let votosByVotacion = {}; // votacion_idx -> [voto_index, ...]
  let votosByDiputado = {}; // diputado_idx -> [voto_index, ...]

  // ── Precomputed ──
  let votResults = []; // [idx] = {favor, contra, abstencion, total, result, margin}
  let dipStats = []; // [idx] = {favor, contra, abstencion, total, mainGrupo, loyalty}
  let tagCounts = {}; // tag -> count
  let topTags = []; // [[tag, count], ...]
  let sortedVotIdxByDate = []; // votacion indices sorted by date desc
  let groupAffinity = {}; // "gaIdx,gbIdx" -> {same: N, total: N}

  // ── View state ──
  let votsPage = 1;
  let votsFiltered = [];
  let votsSelectedTags = [];
  let dipsPage = 1;
  let dipsFiltered = [];

  const VOTO_LABELS = { 1: "A favor", 2: "En contra", 3: "Abstencion" };

  // ═══════════════════════════════════════════════════════════
  // Bootstrap
  // ═══════════════════════════════════════════════════════════

  async function init() {
    initTheme();

    try {
      const resp = await fetch(DATA_URL);
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const raw = await resp.json();

      diputados = raw.diputados;
      grupos = raw.grupos;
      categorias = raw.categorias;
      votaciones = raw.votaciones;
      votos = raw.votos;

      buildIndexes();
      precompute();
      populateFilterOptions();
      attachListeners();
      handleRoute();
    } catch (err) {
      showError("Error cargando datos: " + err.message);
    } finally {
      $("loading").style.display = "none";
    }
  }

  // ═══════════════════════════════════════════════════════════
  // Indexes & Precomputation
  // ═══════════════════════════════════════════════════════════

  function buildIndexes() {
    votosByVotacion = {};
    votosByDiputado = {};
    for (let i = 0; i < votos.length; i++) {
      const votIdx = votos[i][0];
      const dipIdx = votos[i][1];
      if (!votosByVotacion[votIdx]) votosByVotacion[votIdx] = [];
      votosByVotacion[votIdx].push(i);
      if (!votosByDiputado[dipIdx]) votosByDiputado[dipIdx] = [];
      votosByDiputado[dipIdx].push(i);
    }
  }

  function precompute() {
    // 1. Votacion results + group majorities
    const groupMajority = {}; // votIdx -> grupoIdx -> majorityCode

    votResults = new Array(votaciones.length);
    for (let vi = 0; vi < votaciones.length; vi++) {
      const indices = votosByVotacion[vi] || [];
      const t = { 1: 0, 2: 0, 3: 0 };
      const byGroup = {};

      for (let j = 0; j < indices.length; j++) {
        const v = votos[indices[j]];
        const code = v[3];
        const grp = v[2];
        t[code]++;
        if (!byGroup[grp]) byGroup[grp] = { 1: 0, 2: 0, 3: 0 };
        byGroup[grp][code]++;
      }

      const total = indices.length;
      const favor = t[1];
      const contra = t[2];
      votResults[vi] = {
        favor: favor,
        contra: contra,
        abstencion: t[3],
        total: total,
        result:
          favor > contra ? "Aprobada" : contra > favor ? "Rechazada" : "Empate",
        margin: Math.abs(favor - contra),
      };

      // Group majority for loyalty
      groupMajority[vi] = {};
      for (const gIdx in byGroup) {
        const c = byGroup[gIdx];
        groupMajority[vi][gIdx] =
          c[1] >= c[2] && c[1] >= c[3] ? 1 : c[2] >= c[3] ? 2 : 3;
      }

      votaciones[vi].legislatura = getLeg(votaciones[vi].fecha);
    }

    // 2. Diputado stats + loyalty
    dipStats = new Array(diputados.length);
    for (let di = 0; di < diputados.length; di++) {
      const indices = votosByDiputado[di] || [];
      const t = { 1: 0, 2: 0, 3: 0 };
      const grupoCount = {};
      let loyal = 0;

      for (let j = 0; j < indices.length; j++) {
        const v = votos[indices[j]];
        const code = v[3];
        const grp = v[2];
        t[code]++;
        grupoCount[grp] = (grupoCount[grp] || 0) + 1;
        const maj = groupMajority[v[0]];
        if (maj && maj[grp] === code) loyal++;
      }

      const total = indices.length;
      const mainGrpKeys = Object.keys(grupoCount);
      let mainGrupo = -1;
      if (mainGrpKeys.length > 0) {
        mainGrupo = Number(
          mainGrpKeys.reduce((a, b) =>
            grupoCount[a] >= grupoCount[b] ? a : b,
          ),
        );
      }

      const legSet = {};
      for (let j = 0; j < indices.length; j++) {
        const leg = votaciones[votos[indices[j]][0]].legislatura;
        if (leg) legSet[leg] = true;
      }
      dipStats[di] = {
        favor: t[1],
        contra: t[2],
        abstencion: t[3],
        total: total,
        mainGrupo: mainGrupo,
        loyalty: total > 0 ? loyal / total : 0,
        legislaturas: LEGISLATURAS.map((l) => l.id).filter((id) => legSet[id]),
      };
    }

    // 3. Tag counts
    tagCounts = {};
    for (let i = 0; i < votaciones.length; i++) {
      const tags = votaciones[i].etiquetas;
      if (tags) {
        for (let j = 0; j < tags.length; j++) {
          tagCounts[tags[j]] = (tagCounts[tags[j]] || 0) + 1;
        }
      }
    }
    topTags = Object.entries(tagCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20);

    // 4. Sorted votacion indices by date desc
    sortedVotIdxByDate = Array.from({ length: votaciones.length }, (_, i) => i);
    sortedVotIdxByDate.sort((a, b) =>
      votaciones[b].fecha.localeCompare(votaciones[a].fecha),
    );

    // 5. Group affinity matrix
    groupAffinity = {};
    for (let vi = 0; vi < votaciones.length; vi++) {
      const gm = groupMajority[vi];
      const gKeys = Object.keys(gm).map(Number);
      for (let a = 0; a < gKeys.length; a++) {
        for (let b = a + 1; b < gKeys.length; b++) {
          const ga = gKeys[a],
            gb = gKeys[b];
          const key = ga < gb ? ga + "," + gb : gb + "," + ga;
          if (!groupAffinity[key]) groupAffinity[key] = { same: 0, total: 0 };
          groupAffinity[key].total++;
          if (gm[ga] === gm[gb]) groupAffinity[key].same++;
        }
      }
    }
  }

  // ═══════════════════════════════════════════════════════════
  // Routing
  // ═══════════════════════════════════════════════════════════

  function handleRoute() {
    const hash = location.hash;

    // Hide all views
    document
      .querySelectorAll(".view")
      .forEach((v) => v.classList.remove("active"));

    // Update nav
    document.querySelectorAll("[data-nav]").forEach((a) => {
      a.classList.toggle("active", hash === "#" + a.dataset.nav);
    });

    if (hash.startsWith("#votacion/")) {
      const idx = parseInt(hash.split("/")[1], 10);
      if (idx >= 0 && idx < votaciones.length) {
        renderVotacionDetail(idx);
        show("view-votacion");
        document.title = votaciones[idx].titulo_ciudadano + " | Lo Que Votan";
        scrollTop();
        return;
      }
    }

    if (hash.startsWith("#diputado/")) {
      const raw = hash.substring("#diputado/".length);
      const [dipPart, query] = raw.split("?");
      const name = decodeURIComponent(dipPart);
      const tagParam = query ? new URLSearchParams(query).get("tag") : null;
      const idx = diputados.indexOf(name);
      if (idx >= 0) {
        renderDiputadoDetail(idx);
        show("view-diputado");
        document.title = name + " | Lo Que Votan";
        scrollTop();
        if (tagParam) {
          renderAccountabilityCard(idx, tagParam);
        }
        return;
      }
    }

    if (hash === "#votaciones") {
      renderVotacionesList();
      show("view-votaciones");
      document.title = "Votaciones | Lo Que Votan";
      scrollTop();
      return;
    }

    if (hash === "#diputados") {
      renderDiputadosList();
      show("view-diputados");
      document.title = "Diputados | Lo Que Votan";
      scrollTop();
      return;
    }

    if (hash === "#grupos") {
      renderGrupos();
      show("view-grupos");
      document.title = "Comparador de partidos | Lo Que Votan";
      scrollTop();
      return;
    }

    // Default: homepage
    renderHome();
    show("view-home");
    document.title = "Lo Que Votan - Votaciones del Congreso de los Diputados";
  }

  function show(id) {
    $(id).classList.add("active");
  }
  function scrollTop() {
    window.scrollTo({ top: 0 });
  }

  // ═══════════════════════════════════════════════════════════
  // Homepage
  // ═══════════════════════════════════════════════════════════

  function renderHome() {
    // Stats
    const statsEl = $("home-stats");
    if (!statsEl.hasChildNodes()) {
      statsEl.innerHTML =
        statItem(diputados.length.toLocaleString("es-ES"), "diputados") +
        statItem(votaciones.length.toLocaleString("es-ES"), "votaciones") +
        statItem(votos.length.toLocaleString("es-ES"), "votos individuales");
    }

    // Grupos link card
    const statsEl2 = $("home-stats");
    if (statsEl2 && !statsEl2.querySelector(".grupos-link-card")) {
      const gruposCard =
        '<a href="#grupos" class="grupos-link-card btn btn--primary" style="margin-left:auto;display:inline-flex;align-items:center;gap:0.4rem;">&#128202; Compara partidos</a>';
      statsEl2.insertAdjacentHTML("beforeend", gruposCard);
    }

    // Topics
    const topicsEl = $("home-topics");
    if (!topicsEl.hasChildNodes()) {
      topicsEl.innerHTML = topTags
        .map(
          ([tag, count]) =>
            '<a class="topic-card" href="#votaciones" data-tag="' +
            esc(tag) +
            '"><span class="topic-card-label">' +
            esc(fmt(tag)) +
            '</span><span class="topic-card-count">' +
            count +
            "</span></a>",
        )
        .join("");

      topicsEl.addEventListener("click", (e) => {
        const card = e.target.closest(".topic-card");
        if (!card) return;
        e.preventDefault();
        const tag = card.dataset.tag;
        votsSelectedTags = [tag];
        location.hash = "#votaciones";
      });
    }

    // Rebels ranking
    const rebelsEl = $("home-rebels");
    if (rebelsEl && !rebelsEl.hasChildNodes()) {
      const rebels = Array.from({ length: diputados.length }, (_, i) => i)
        .filter((i) => dipStats[i].total > 50)
        .sort((a, b) => dipStats[a].loyalty - dipStats[b].loyalty)
        .slice(0, 10);
      rebelsEl.innerHTML = rebels
        .map((i) => {
          const ds = dipStats[i];
          const grp = ds.mainGrupo >= 0 ? grupos[ds.mainGrupo] : "Sin grupo";
          const loyaltyPct = Math.round(ds.loyalty * 100);
          return (
            '<a class="ranking-card card-link" href="#diputado/' +
            encodeURIComponent(diputados[i]) +
            '">' +
            avatarHTML(diputados[i]) +
            '<div class="ranking-info">' +
            '<span class="ranking-name">' +
            esc(diputados[i]) +
            "</span>" +
            '<span class="ranking-detail">' +
            esc(grp) +
            "</span>" +
            '<span class="ranking-stat">' +
            loyaltyPct +
            "% lealtad al grupo</span>" +
            "</div></a>"
          );
        })
        .join("");
    }

    // Tight votes
    const tightEl = $("home-tight");
    if (tightEl && !tightEl.hasChildNodes()) {
      const tight = sortedVotIdxByDate
        .filter((i) => votResults[i].total > 0)
        .sort((a, b) => votResults[a].margin - votResults[b].margin)
        .slice(0, 10);
      tightEl.innerHTML = tight.map((i) => voteCardHTML(i)).join("");
    }

    // Latest votaciones
    const latestEl = $("home-latest");
    if (!latestEl.hasChildNodes()) {
      const latest = sortedVotIdxByDate.slice(0, 10);
      latestEl.innerHTML = latest.map((i) => voteCardHTML(i)).join("");
    }
  }

  function statItem(number, label) {
    return (
      '<div class="stat-item"><span class="stat-number">' +
      number +
      '</span><span class="stat-label">' +
      label +
      "</span></div>"
    );
  }

  // ═══════════════════════════════════════════════════════════
  // Grupos — Affinity comparator
  // ═══════════════════════════════════════════════════════════

  function affinityColor(pct) {
    if (pct >= 0.8) return "#16a34a"; // dark green
    if (pct >= 0.6) return "#86efac"; // light green
    if (pct >= 0.4) return "#fde047"; // yellow
    if (pct >= 0.2) return "#fca5a5"; // light red
    return "#dc2626"; // red
  }

  function renderGrupos() {
    const leg = $("grupos-leg").value;

    // Collect valid group indices (appear in data)
    const grupoSet = new Set();
    for (let vi = 0; vi < votaciones.length; vi++) {
      if (leg && votaciones[vi].legislatura !== leg) continue;
      const indices = votosByVotacion[vi] || [];
      for (let j = 0; j < indices.length; j++) {
        grupoSet.add(votos[indices[j]][2]);
      }
    }

    // Recompute affinity filtered by legislatura
    const aff = {}; // "ga,gb" -> {same, total}
    for (let vi = 0; vi < votaciones.length; vi++) {
      if (leg && votaciones[vi].legislatura !== leg) continue;
      // compute group majority for this votacion
      const indices = votosByVotacion[vi] || [];
      const byGroup = {};
      for (let j = 0; j < indices.length; j++) {
        const v = votos[indices[j]];
        const grp = v[2],
          code = v[3];
        if (!byGroup[grp]) byGroup[grp] = { 1: 0, 2: 0, 3: 0 };
        byGroup[grp][code]++;
      }
      const gm = {};
      for (const gIdx in byGroup) {
        const c = byGroup[gIdx];
        gm[gIdx] = c[1] >= c[2] && c[1] >= c[3] ? 1 : c[2] >= c[3] ? 2 : 3;
      }
      const gKeys = Object.keys(gm).map(Number);
      for (let a = 0; a < gKeys.length; a++) {
        for (let b = a + 1; b < gKeys.length; b++) {
          const ga = gKeys[a],
            gb = gKeys[b];
          const key = ga < gb ? ga + "," + gb : gb + "," + ga;
          if (!aff[key]) aff[key] = { same: 0, total: 0 };
          aff[key].total++;
          if (gm[ga] === gm[gb]) aff[key].same++;
        }
      }
    }

    // Count total votaciones per group
    const groupTotals = {};
    for (const key in aff) {
      const parts = key.split(",");
      const ga = Number(parts[0]),
        gb = Number(parts[1]);
      groupTotals[ga] = (groupTotals[ga] || 0) + aff[key].total;
      groupTotals[gb] = (groupTotals[gb] || 0) + aff[key].total;
    }

    // Filter groups with >= 10 votaciones
    const validGroups = Array.from(grupoSet)
      .filter((g) => (groupTotals[g] || 0) >= 10)
      .sort((a, b) => a - b);

    if (validGroups.length === 0) {
      $("grupos-body").innerHTML =
        '<div class="empty-state"><div class="empty-state-icon">&#128202;</div>' +
        '<p class="empty-state-text">No hay datos suficientes para esta legislatura.</p></div>';
      return;
    }

    // Build header row
    let html =
      '<div class="affinity-table-wrap"><table class="affinity-table"><thead><tr><th></th>';
    for (let i = 0; i < validGroups.length; i++) {
      const gName = grupos[validGroups[i]] || "Grupo " + validGroups[i];
      html +=
        '<th class="affinity-th-col"><div class="affinity-th-label">' +
        esc(gName) +
        "</div></th>";
    }
    html += "</tr></thead><tbody>";

    // Build rows
    for (let r = 0; r < validGroups.length; r++) {
      const ga = validGroups[r];
      const gNameA = grupos[ga] || "Grupo " + ga;
      html += '<tr><td class="affinity-row-label">' + esc(gNameA) + "</td>";
      for (let c = 0; c < validGroups.length; c++) {
        const gb = validGroups[c];
        if (ga === gb) {
          html +=
            '<td class="affinity-cell affinity-cell--self" title="100%">100%</td>';
        } else {
          const key = ga < gb ? ga + "," + gb : gb + "," + ga;
          const d = aff[key];
          if (!d || d.total === 0) {
            html +=
              '<td class="affinity-cell" style="background:#e2e8f0" title="Sin datos">—</td>';
          } else {
            const pct = d.same / d.total;
            const pctStr = Math.round(pct * 100) + "%";
            const bg = affinityColor(pct);
            html +=
              '<td class="affinity-cell" style="background:' +
              bg +
              '" title="' +
              esc(pctStr) +
              " (" +
              d.same +
              "/" +
              d.total +
              " votaciones coinciden)" +
              '">' +
              pctStr +
              "</td>";
          }
        }
      }
      html += "</tr>";
    }
    html += "</tbody></table></div>";

    // Legend
    html +=
      '<div class="affinity-legend">' +
      '<span class="affinity-legend-item"><span class="affinity-legend-swatch" style="background:#16a34a"></span>&gt;80% coincidencia</span>' +
      '<span class="affinity-legend-item"><span class="affinity-legend-swatch" style="background:#86efac"></span>60-80%</span>' +
      '<span class="affinity-legend-item"><span class="affinity-legend-swatch" style="background:#fde047"></span>40-60%</span>' +
      '<span class="affinity-legend-item"><span class="affinity-legend-swatch" style="background:#fca5a5"></span>20-40%</span>' +
      '<span class="affinity-legend-item"><span class="affinity-legend-swatch" style="background:#dc2626"></span>&lt;20%</span>' +
      "</div>";

    $("grupos-body").innerHTML = html;
  }

  // ═══════════════════════════════════════════════════════════
  // Votaciones List
  // ═══════════════════════════════════════════════════════════

  function renderVotacionesList() {
    applyVotsFilters();
  }

  function applyVotsFilters() {
    const search = $("vots-f-search").value.toLowerCase().trim();
    const cat = $("vots-f-cat").value;
    const result = $("vots-f-result").value;
    const leg = $("vots-leg").value;
    const sortMode = $("vots-f-sort").value;

    let indices = sortedVotIdxByDate;

    votsFiltered = indices.filter((i) => {
      const vot = votaciones[i];
      if (search && !vot.titulo_ciudadano.toLowerCase().includes(search))
        return false;
      if (cat && categorias[vot.categoria] !== cat) return false;
      if (result && votResults[i].result !== result) return false;
      if (leg && vot.legislatura !== leg) return false;
      if (votsSelectedTags.length > 0) {
        const tags = vot.etiquetas || [];
        if (!votsSelectedTags.every((t) => tags.includes(t))) return false;
      }
      return true;
    });

    if (sortMode === "closest") {
      votsFiltered.sort((a, b) => votResults[a].margin - votResults[b].margin);
    }

    votsPage = 1;
    renderVotsPage();
    renderVotsActiveTags();
  }

  function renderVotsPage() {
    const total = votsFiltered.length;
    const totalPages = Math.max(1, Math.ceil(total / VOTES_PER_PAGE));
    if (votsPage > totalPages) votsPage = 1;
    const start = (votsPage - 1) * VOTES_PER_PAGE;
    const page = votsFiltered.slice(start, start + VOTES_PER_PAGE);

    $("vots-count").textContent = total.toLocaleString("es-ES") + " votaciones";

    const listEl = $("vots-list");
    if (page.length === 0) {
      listEl.innerHTML =
        '<div class="empty-state"><div class="empty-state-icon">&#128270;</div><p class="empty-state-text">No se encontraron votaciones</p></div>';
      $("vots-pagination").innerHTML = "";
      return;
    }

    listEl.innerHTML = page.map((i) => voteCardHTML(i)).join("");

    renderPagination($("vots-pagination"), totalPages, votsPage, (p) => {
      votsPage = p;
      renderVotsPage();
      $("vots-filters").scrollIntoView({ behavior: "smooth" });
    });
  }

  function renderVotsActiveTags() {
    const container = $("vots-active-tags");
    container.innerHTML = "";
    votsSelectedTags.forEach((tag) => {
      const span = document.createElement("span");
      span.className = "tag-active";
      span.textContent = fmt(tag) + " ";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tag-remove";
      btn.textContent = "\u00d7";
      btn.addEventListener("click", () => {
        votsSelectedTags = votsSelectedTags.filter((t) => t !== tag);
        applyVotsFilters();
      });
      span.appendChild(btn);
      container.appendChild(span);
    });
  }

  function addVotsTag() {
    const input = $("vots-f-tag");
    const value = input.value.trim();
    if (!value) return;
    const tag = value.replace(/ /g, "_");
    if (!votsSelectedTags.includes(tag)) {
      votsSelectedTags = [...votsSelectedTags, tag];
      applyVotsFilters();
    }
    input.value = "";
  }

  // ═══════════════════════════════════════════════════════════
  // Diputados List
  // ═══════════════════════════════════════════════════════════

  function renderDiputadosList() {
    applyDipsFilters();
  }

  function applyDipsFilters() {
    const search = $("dips-f-search").value.toLowerCase().trim();
    const grupo = $("dips-f-grupo").value;
    const sortMode = $("dips-f-sort").value;

    dipsFiltered = [];
    for (let i = 0; i < diputados.length; i++) {
      const ds = dipStats[i];
      if (ds.total === 0) continue;
      if (search && !diputados[i].toLowerCase().includes(search)) continue;
      if (grupo && (ds.mainGrupo < 0 || grupos[ds.mainGrupo] !== grupo))
        continue;
      dipsFiltered.push(i);
    }

    if (sortMode === "name") {
      dipsFiltered.sort((a, b) => diputados[a].localeCompare(diputados[b]));
    } else if (sortMode === "active") {
      dipsFiltered.sort((a, b) => dipStats[b].total - dipStats[a].total);
    } else if (sortMode === "loyalty-low") {
      dipsFiltered.sort((a, b) => dipStats[a].loyalty - dipStats[b].loyalty);
    }

    dipsPage = 1;
    renderDipsPage();
  }

  function renderDipsPage() {
    const total = dipsFiltered.length;
    const totalPages = Math.max(1, Math.ceil(total / DIPS_PER_PAGE));
    if (dipsPage > totalPages) dipsPage = 1;
    const start = (dipsPage - 1) * DIPS_PER_PAGE;
    const page = dipsFiltered.slice(start, start + DIPS_PER_PAGE);

    $("dips-count").textContent = total.toLocaleString("es-ES") + " diputados";

    const listEl = $("dips-list");
    if (page.length === 0) {
      listEl.innerHTML =
        '<div class="empty-state"><div class="empty-state-icon">&#128100;</div><p class="empty-state-text">No se encontraron diputados</p></div>';
      $("dips-pagination").innerHTML = "";
      return;
    }

    listEl.innerHTML = page.map((i) => dipCardHTML(i)).join("");

    renderPagination($("dips-pagination"), totalPages, dipsPage, (p) => {
      dipsPage = p;
      renderDipsPage();
      $("dips-filters").scrollIntoView({ behavior: "smooth" });
    });
  }

  // ═══════════════════════════════════════════════════════════
  // Votacion Detail
  // ═══════════════════════════════════════════════════════════

  function renderVotacionDetail(idx) {
    const vot = votaciones[idx];
    const r = votResults[idx];
    const voteIndices = votosByVotacion[idx] || [];

    // Header
    const resultClass =
      r.result === "Aprobada"
        ? "aprobada"
        : r.result === "Rechazada"
          ? "rechazada"
          : "empate";
    $("vot-header").innerHTML =
      "<h1>" +
      esc(vot.titulo_ciudadano) +
      "</h1>" +
      (vot.resumen
        ? '<p class="detail-summary">' + esc(vot.resumen) + "</p>"
        : "") +
      '<div class="detail-meta" style="margin-top:0.75rem">' +
      '<span class="result-badge result-badge--' +
      resultClass +
      ' result-badge--lg">' +
      esc(r.result) +
      "</span>" +
      '<span class="result-margin">' +
      resultMarginText(r) +
      "</span>" +
      '<span class="detail-meta-item">' +
      esc(vot.fecha) +
      "</span>" +
      (vot.legislatura
        ? '<span class="badge badge--leg">' + esc(vot.legislatura) + "</span>"
        : "") +
      (vot.proponente
        ? '<span class="badge badge--proponente">' +
          esc(vot.proponente) +
          "</span>"
        : "") +
      '<span class="badge badge--cat">' +
      esc(fmt(categorias[vot.categoria])) +
      "</span>" +
      tagsHTML(vot.etiquetas) +
      "</div>";

    // Body
    let html = "";

    // Vote bar + totals
    html += '<div class="detail-section">';
    html += "<h2>Resultado</h2>";
    html += voteBarHTML(r.favor, r.contra, r.abstencion, r.total, false);
    html += voteTotalsHTML(r);
    html += "</div>";

    // Group breakdown
    const byGroup = {};
    for (let j = 0; j < voteIndices.length; j++) {
      const v = votos[voteIndices[j]];
      const g = v[2];
      if (!byGroup[g]) byGroup[g] = { 1: 0, 2: 0, 3: 0, total: 0 };
      byGroup[g][v[3]]++;
      byGroup[g].total++;
    }

    html += '<div class="detail-section">';
    html += "<h2>Votos por grupo parlamentario</h2>";
    html +=
      '<div class="table-wrap"><table><thead><tr>' +
      "<th>Grupo</th><th>A favor</th><th>En contra</th><th>Abstenciones</th><th>Total</th>" +
      "</tr></thead><tbody>";

    Object.keys(byGroup)
      .map(Number)
      .sort((a, b) => grupos[a].localeCompare(grupos[b]))
      .forEach((gIdx) => {
        const d = byGroup[gIdx];
        html +=
          '<tr><td><span class="badge badge--grupo">' +
          esc(grupos[gIdx]) +
          "</span></td>" +
          "<td>" +
          d[1] +
          "</td><td>" +
          d[2] +
          "</td><td>" +
          d[3] +
          "</td><td>" +
          d.total +
          "</td></tr>";
      });

    html += "</tbody></table></div>";
    html += "</div>";

    // Individual votes
    html += '<div class="detail-section">';
    html += "<h2>Votos individuales</h2>";
    html +=
      '<input type="search" class="filter-input" id="vot-search-dip" placeholder="Buscar diputado/a..." style="max-width:350px;margin-bottom:0.75rem">';
    html +=
      '<div class="table-wrap"><table><thead><tr>' +
      "<th>Diputado/a</th><th>Grupo</th><th>Voto</th>" +
      '</tr></thead><tbody id="vot-indiv-body"></tbody></table></div>';
    html += "</div>";

    // Share
    html += shareBarHTML(vot.titulo_ciudadano, r.result);

    $("vot-body").innerHTML = html;

    // Render individual votes
    const sortedVotes = [...voteIndices].sort((a, b) =>
      diputados[votos[a][1]].localeCompare(diputados[votos[b][1]]),
    );

    const renderIndiv = () => {
      const q = $("vot-search-dip").value.toLowerCase().trim();
      const body = $("vot-indiv-body");
      let rows = "";
      for (let j = 0; j < sortedVotes.length; j++) {
        const v = votos[sortedVotes[j]];
        const name = diputados[v[1]];
        if (q && !name.toLowerCase().includes(q)) continue;
        rows +=
          '<tr><td><a href="#diputado/' +
          encodeURIComponent(name) +
          '">' +
          esc(name) +
          "</a></td>" +
          '<td><span class="badge badge--grupo">' +
          esc(grupos[v[2]]) +
          "</span></td>" +
          "<td>" +
          votoPillHTML(v[3]) +
          "</td></tr>";
      }
      body.innerHTML =
        rows ||
        '<tr><td colspan="3" class="text-center" style="padding:1.5rem;color:var(--color-muted)">Sin resultados</td></tr>';
    };

    $("vot-search-dip").oninput = debounce(renderIndiv, 200);
    renderIndiv();
  }

  // ═══════════════════════════════════════════════════════════
  // Diputado Detail
  // ═══════════════════════════════════════════════════════════

  function renderDiputadoDetail(dipIdx) {
    const name = diputados[dipIdx];
    const ds = dipStats[dipIdx];
    const grupoName = ds.mainGrupo >= 0 ? grupos[ds.mainGrupo] : "Sin grupo";

    // Header
    $("dip-header").innerHTML =
      "<h1>" +
      esc(name) +
      "</h1>" +
      '<div class="detail-meta" style="margin-top:0.5rem">' +
      '<span class="badge badge--grupo">' +
      esc(grupoName) +
      "</span>" +
      '<span class="detail-meta-item">' +
      ds.total +
      " votaciones</span>" +
      '<span class="detail-meta-item">Lealtad al grupo: ' +
      pct(ds.loyalty) +
      "</span>" +
      (ds.legislaturas && ds.legislaturas.length > 0
        ? ds.legislaturas
            .map((l) => '<span class="badge badge--leg">' + esc(l) + "</span>")
            .join(" ")
        : "") +
      "</div>";

    let html = "";

    // Stat cards
    html +=
      '<div class="stat-cards">' +
      '<div class="stat-card"><span class="stat-card-value">' +
      ds.total +
      '</span><span class="stat-card-label">Votaciones</span></div>' +
      '<div class="stat-card stat-card--favor"><span class="stat-card-value">' +
      ds.favor +
      '</span><span class="stat-card-label">A favor (' +
      pct(ds.favor / ds.total) +
      ")</span></div>" +
      '<div class="stat-card stat-card--contra"><span class="stat-card-value">' +
      ds.contra +
      '</span><span class="stat-card-label">En contra (' +
      pct(ds.contra / ds.total) +
      ")</span></div>" +
      '<div class="stat-card stat-card--abstencion"><span class="stat-card-value">' +
      ds.abstencion +
      '</span><span class="stat-card-label">Abstenciones (' +
      pct(ds.abstencion / ds.total) +
      ")</span></div>" +
      "</div>";

    // Vote bar
    html += voteBarHTML(ds.favor, ds.contra, ds.abstencion, ds.total, false);

    // Top tags
    const dipVoteIndices = votosByDiputado[dipIdx] || [];
    const dipTagCounts = {};
    for (let j = 0; j < dipVoteIndices.length; j++) {
      const vi = votos[dipVoteIndices[j]][0];
      const tags = votaciones[vi].etiquetas;
      if (tags) {
        for (let k = 0; k < tags.length; k++) {
          dipTagCounts[tags[k]] = (dipTagCounts[tags[k]] || 0) + 1;
        }
      }
    }
    const dipTopTags = Object.entries(dipTagCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20);

    // Category profile breakdown
    const catBreakdown = {};
    for (let j = 0; j < dipVoteIndices.length; j++) {
      const v = votos[dipVoteIndices[j]];
      const votIdx = v[0];
      const code = v[3];
      const cat = votaciones[votIdx].categoria;
      if (!catBreakdown[cat])
        catBreakdown[cat] = { 1: 0, 2: 0, 3: 0, total: 0 };
      catBreakdown[cat][code]++;
      catBreakdown[cat].total++;
    }
    const catEntries = Object.entries(catBreakdown)
      .sort((a, b) => b[1].total - a[1].total)
      .slice(0, 10);
    if (catEntries.length > 0) {
      html +=
        '<div class="detail-section"><h2>Perfil tem\u00e1tico</h2><div class="cat-profile">';
      catEntries.forEach(([catIdx, counts]) => {
        const catName = categorias[catIdx] || catIdx;
        const total = counts.total;
        const favorPct = Math.round((counts[1] / total) * 100);
        const contraPct = Math.round((counts[2] / total) * 100);
        const abstPct = 100 - favorPct - contraPct;
        html +=
          '<div class="cat-profile-row">' +
          '<span class="cat-profile-label" title="' +
          esc(fmt(catName)) +
          '">' +
          esc(fmt(catName)) +
          "</span>" +
          '<div class="cat-profile-bar">' +
          '<div class="cat-profile-seg" style="width:' +
          favorPct +
          '%;background:var(--color-favor)" title="' +
          favorPct +
          '% A favor"></div>' +
          '<div class="cat-profile-seg" style="width:' +
          contraPct +
          '%;background:var(--color-contra)" title="' +
          contraPct +
          '% En contra"></div>' +
          '<div class="cat-profile-seg" style="width:' +
          abstPct +
          '%;background:var(--color-abstencion)" title="' +
          abstPct +
          '% Abstenci\u00f3n"></div>' +
          "</div>" +
          '<span class="cat-profile-count">' +
          total +
          "</span>" +
          "</div>";
      });
      html += "</div></div>";
    }

    if (dipTopTags.length > 0) {
      html +=
        '<div class="detail-section"><h2>Temas mas votados</h2><div id="dip-tags">';
      dipTopTags.forEach(([tag, count]) => {
        html +=
          '<span class="chip chip--lg chip--clickable" data-tag="' +
          esc(tag) +
          '">' +
          esc(fmt(tag)) +
          " (" +
          count +
          ")</span> ";
      });
      html += "</div></div>";
    }

    // Vote history
    const legOptions = (ds.legislaturas || [])
      .map((l) => '<option value="' + esc(l) + '">' + esc(l) + "</option>")
      .join("");
    html += '<div class="detail-section"><h2>Historial de votos</h2>';
    html +=
      '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.75rem">' +
      '<input type="search" class="filter-input" id="dip-h-search" placeholder="Buscar asunto..." style="flex:1;min-width:200px">' +
      '<select class="filter-select" id="dip-h-voto" style="width:auto;min-width:130px">' +
      '<option value="">Todos los votos</option>' +
      '<option value="1">A favor</option><option value="2">En contra</option><option value="3">Abstencion</option>' +
      "</select>" +
      '<select class="filter-select" id="dip-h-leg" style="width:auto;min-width:130px">' +
      '<option value="">Todas las legislaturas</option>' +
      legOptions +
      "</select></div>";
    html +=
      '<div class="table-wrap"><table><thead><tr>' +
      "<th>Fecha</th><th>Legislatura</th><th>Asunto</th><th>Categoria</th><th>Resultado</th><th>Voto</th>" +
      '</tr></thead><tbody id="dip-h-body"></tbody></table></div>';
    html += '<nav class="pagination" id="dip-h-pagination"></nav>';
    html += "</div>";

    // Share
    html += shareBarHTML(name + " - " + grupoName, null);

    $("dip-body").innerHTML = html;

    // Build sorted records (by date desc)
    const dipRecords = dipVoteIndices
      .map((vi) => {
        const v = votos[vi];
        return { votIdx: v[0], code: v[3] };
      })
      .sort((a, b) =>
        votaciones[b.votIdx].fecha.localeCompare(votaciones[a.votIdx].fecha),
      );

    let dipHPage = 1;
    let dipActiveTag = "";

    const renderHistory = () => {
      const q = $("dip-h-search").value.toLowerCase().trim();
      const votoFilter = $("dip-h-voto").value;
      const legFilter = $("dip-h-leg").value;

      const filtered = dipRecords.filter((r) => {
        if (
          q &&
          !votaciones[r.votIdx].titulo_ciudadano.toLowerCase().includes(q)
        )
          return false;
        if (votoFilter && r.code !== Number(votoFilter)) return false;
        if (legFilter && votaciones[r.votIdx].legislatura !== legFilter)
          return false;
        if (
          dipActiveTag &&
          !(votaciones[r.votIdx].etiquetas || []).includes(dipActiveTag)
        )
          return false;
        return true;
      });

      const totalPages = Math.max(
        1,
        Math.ceil(filtered.length / VOTES_PER_PAGE),
      );
      if (dipHPage > totalPages) dipHPage = 1;
      const start = (dipHPage - 1) * VOTES_PER_PAGE;
      const page = filtered.slice(start, start + VOTES_PER_PAGE);

      const body = $("dip-h-body");
      let rows = "";
      for (let j = 0; j < page.length; j++) {
        const r = page[j];
        const vot = votaciones[r.votIdx];
        const vr = votResults[r.votIdx];
        const resultClass =
          vr.result === "Aprobada"
            ? "aprobada"
            : vr.result === "Rechazada"
              ? "rechazada"
              : "empate";
        rows +=
          "<tr><td>" +
          esc(vot.fecha) +
          "</td>" +
          "<td>" +
          (vot.legislatura
            ? '<span class="badge badge--leg">' +
              esc(vot.legislatura) +
              "</span>"
            : "") +
          "</td>" +
          '<td><a href="#votacion/' +
          r.votIdx +
          '">' +
          esc(vot.titulo_ciudadano) +
          "</a></td>" +
          '<td><span class="badge badge--cat">' +
          esc(fmt(categorias[vot.categoria])) +
          "</span></td>" +
          '<td><span class="result-badge result-badge--' +
          resultClass +
          '">' +
          esc(vr.result) +
          "</span></td>" +
          "<td>" +
          votoPillHTML(r.code) +
          "</td></tr>";
      }
      body.innerHTML =
        rows ||
        '<tr><td colspan="6" class="text-center" style="padding:1.5rem;color:var(--color-muted)">Sin resultados</td></tr>';

      renderPagination($("dip-h-pagination"), totalPages, dipHPage, (p) => {
        dipHPage = p;
        renderHistory();
      });
    };

    $("dip-h-search").oninput = debounce(() => {
      dipHPage = 1;
      renderHistory();
    }, 250);
    $("dip-h-voto").onchange = () => {
      dipHPage = 1;
      renderHistory();
    };
    $("dip-h-leg").onchange = () => {
      dipHPage = 1;
      renderHistory();
    };

    // Tag chips as quick-filters + accountability card
    const tagsContainer = $("dip-tags");
    if (tagsContainer) {
      tagsContainer.onclick = (e) => {
        const chip = e.target.closest("[data-tag]");
        if (!chip) return;
        const tag = chip.getAttribute("data-tag");
        if (dipActiveTag === tag) {
          dipActiveTag = "";
          chip.classList.remove("chip--active");
        } else {
          dipActiveTag = tag;
          tagsContainer
            .querySelectorAll(".chip--active")
            .forEach((c) => c.classList.remove("chip--active"));
          chip.classList.add("chip--active");
        }
        dipHPage = 1;
        renderHistory();
        renderAccountabilityCard(dipIdx, tag);
      };
    }

    renderHistory();
  }

  // ═══════════════════════════════════════════════════════════
  // Accountability Card
  // ═══════════════════════════════════════════════════════════

  function avatarHTML(name) {
    const parts = name.split(",");
    const apellido = (parts[0] || "").trim();
    const nombre = (parts[1] || "").trim();
    const initials = (nombre[0] || "") + (apellido[0] || "");
    const hue =
      Math.abs(name.split("").reduce((a, c) => a + c.charCodeAt(0), 0)) % 360;
    return (
      '<div class="avatar" style="background:hsl(' +
      hue +
      ',55%,45%)">' +
      esc(initials.toUpperCase()) +
      "</div>"
    );
  }

  function renderAccountabilityCard(dipIdx, tag) {
    const name = diputados[dipIdx];
    const ds = dipStats[dipIdx];
    const grupoName = ds.mainGrupo >= 0 ? grupos[ds.mainGrupo] : "Sin grupo";

    // Count votes for this tag
    const dipVoteIndices = votosByDiputado[dipIdx] || [];
    let favor = 0,
      contra = 0,
      abstencion = 0;
    for (let j = 0; j < dipVoteIndices.length; j++) {
      const v = votos[dipVoteIndices[j]];
      const votIdx = v[0];
      const code = v[3];
      const tags = votaciones[votIdx].etiquetas || [];
      if (!tags.includes(tag)) continue;
      if (code === 1) favor++;
      else if (code === 2) contra++;
      else if (code === 3) abstencion++;
    }
    const total = favor + contra + abstencion;

    const shareUrl =
      location.origin +
      location.pathname +
      "#diputado/" +
      encodeURIComponent(name) +
      "?tag=" +
      encodeURIComponent(tag);
    const topicLabel = fmt(tag);

    // Vote rows
    function voteRow(label, count, color) {
      const pctWidth = total > 0 ? Math.round((count / total) * 100) : 0;
      const veces = count === 1 ? "1 vez" : count + " veces";
      return (
        '<div class="acc-vote-row">' +
        '<span class="acc-vote-label">' +
        esc(label) +
        "</span>" +
        '<div class="acc-vote-bar"><div class="acc-vote-bar-fill" style="width:' +
        pctWidth +
        "%;background:" +
        color +
        '"></div></div>' +
        '<span class="acc-vote-count">' +
        esc(veces) +
        "</span>" +
        "</div>"
      );
    }

    const shareText =
      esc(name) +
      " (" +
      esc(grupoName) +
      ") ha votado " +
      favor +
      " veces A FAVOR de " +
      topicLabel +
      ". Compruebalo: " +
      shareUrl;
    const twitterUrl =
      "https://twitter.com/intent/tweet?text=" +
      encodeURIComponent(
        name +
          " (" +
          grupoName +
          ") ha votado " +
          favor +
          " veces A FAVOR de " +
          topicLabel +
          ". Compruebalo: " +
          shareUrl,
      );
    const waUrl =
      "whatsapp://send?text=" +
      encodeURIComponent(
        name +
          " (" +
          grupoName +
          ") ha votado " +
          favor +
          " veces A FAVOR de " +
          topicLabel +
          ". Compruebalo: " +
          shareUrl,
      );

    const html =
      '<div class="acc-overlay" id="acc-overlay">' +
      '<div class="acc-card">' +
      '<button class="acc-close" id="acc-close" aria-label="Cerrar">\u00d7</button>' +
      avatarHTML(name) +
      '<div class="acc-name">' +
      esc(name) +
      "</div>" +
      '<div class="acc-grupo">' +
      esc(grupoName) +
      "</div>" +
      '<div class="acc-topic">' +
      esc(topicLabel) +
      "</div>" +
      '<div class="acc-votes">' +
      voteRow("A FAVOR", favor, "var(--color-favor)") +
      voteRow("EN CONTRA", contra, "var(--color-contra)") +
      voteRow("ABSTENCI\u00d3N", abstencion, "var(--color-abstencion)") +
      "</div>" +
      '<div class="acc-url">loquevotan.es</div>' +
      '<div class="acc-share">' +
      '<button class="acc-share-btn acc-share-btn--primary" id="acc-copy">Copiar enlace</button>' +
      '<a class="acc-share-btn" href="' +
      twitterUrl +
      '" target="_blank" rel="noopener">X / Twitter</a>' +
      '<a class="acc-share-btn" href="' +
      waUrl +
      '" target="_blank" rel="noopener">WhatsApp</a>' +
      "</div>" +
      "</div>" +
      "</div>";

    const overlay = document.createElement("div");
    overlay.innerHTML = html;
    const overlayEl = overlay.firstChild;
    document.body.appendChild(overlayEl);

    function closeCard() {
      if (overlayEl.parentNode) overlayEl.parentNode.removeChild(overlayEl);
      document.removeEventListener("keydown", onKey);
    }

    function onKey(e) {
      if (e.key === "Escape") closeCard();
    }

    document.getElementById("acc-close").onclick = closeCard;
    overlayEl.addEventListener("click", (e) => {
      if (e.target === overlayEl) closeCard();
    });
    document.addEventListener("keydown", onKey);

    document.getElementById("acc-copy").onclick = function () {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(shareUrl).then(() => {
          this.textContent = "Copiado!";
          setTimeout(() => {
            this.textContent = "Copiar enlace";
          }, 2000);
        });
      } else {
        const ta = document.createElement("textarea");
        ta.value = shareUrl;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        this.textContent = "Copiado!";
        setTimeout(() => {
          this.textContent = "Copiar enlace";
        }, 2000);
      }
    };
  }

  // ═══════════════════════════════════════════════════════════
  // Card HTML Builders
  // ═══════════════════════════════════════════════════════════

  function voteCardHTML(idx) {
    const vot = votaciones[idx];
    const r = votResults[idx];
    const resultClass =
      r.result === "Aprobada"
        ? "aprobada"
        : r.result === "Rechazada"
          ? "rechazada"
          : "empate";

    return (
      '<a class="card vote-card card-link" href="#votacion/' +
      idx +
      '">' +
      '<div class="vote-card-header">' +
      '<span class="vote-card-title">' +
      esc(vot.titulo_ciudadano) +
      "</span>" +
      '<span class="result-badge result-badge--' +
      resultClass +
      '">' +
      esc(r.result) +
      "</span>" +
      "</div>" +
      '<div class="vote-card-meta">' +
      "<span>" +
      esc(vot.fecha) +
      "</span>" +
      '<span class="badge badge--cat">' +
      esc(fmt(categorias[vot.categoria])) +
      "</span>" +
      "</div>" +
      voteBarHTML(r.favor, r.contra, r.abstencion, r.total, true) +
      (vot.etiquetas && vot.etiquetas.length > 0
        ? '<div class="vote-card-tags">' +
          vot.etiquetas
            .slice(0, 4)
            .map((t) => '<span class="chip">' + esc(fmt(t)) + "</span>")
            .join("") +
          (vot.etiquetas.length > 4
            ? '<span class="chip">+' + (vot.etiquetas.length - 4) + "</span>"
            : "") +
          "</div>"
        : "") +
      "</a>"
    );
  }

  function dipCardHTML(idx) {
    const name = diputados[idx];
    const ds = dipStats[idx];
    const grupoName = ds.mainGrupo >= 0 ? grupos[ds.mainGrupo] : "Sin grupo";

    return (
      '<a class="card dip-card card-link" href="#diputado/' +
      encodeURIComponent(name) +
      '">' +
      '<div class="dip-card-name">' +
      esc(name) +
      "</div>" +
      '<span class="badge badge--grupo">' +
      esc(grupoName) +
      "</span>" +
      '<div class="dip-card-stats">' +
      "<span><strong>" +
      ds.total +
      "</strong> votos</span>" +
      "<span>Lealtad: <strong>" +
      pct(ds.loyalty) +
      "</strong></span>" +
      "</div>" +
      voteBarHTML(ds.favor, ds.contra, ds.abstencion, ds.total, true) +
      "</a>"
    );
  }

  // ═══════════════════════════════════════════════════════════
  // Shared Renderers
  // ═══════════════════════════════════════════════════════════

  function voteBarHTML(favor, contra, abstencion, total, small) {
    if (total === 0) return "";
    const pF = ((favor / total) * 100).toFixed(1);
    const pC = ((contra / total) * 100).toFixed(1);
    const pA = ((abstencion / total) * 100).toFixed(1);
    const cls = small ? "vote-bar vote-bar--sm" : "vote-bar";
    return (
      '<div class="' +
      cls +
      '">' +
      '<div class="vote-bar-seg vote-bar-seg--favor" style="width:' +
      pF +
      '%" title="A favor: ' +
      pF +
      '%">' +
      (small ? "" : favor) +
      "</div>" +
      '<div class="vote-bar-seg vote-bar-seg--contra" style="width:' +
      pC +
      '%" title="En contra: ' +
      pC +
      '%">' +
      (small ? "" : contra) +
      "</div>" +
      '<div class="vote-bar-seg vote-bar-seg--abstencion" style="width:' +
      pA +
      '%" title="Abstenciones: ' +
      pA +
      '%">' +
      (small ? "" : abstencion) +
      "</div>" +
      "</div>"
    );
  }

  function voteTotalsHTML(r) {
    return (
      '<div class="vote-totals">' +
      '<span class="vote-total-item vote-total-item--favor">' +
      r.favor +
      " a favor</span>" +
      '<span class="vote-total-item vote-total-item--contra">' +
      r.contra +
      " en contra</span>" +
      '<span class="vote-total-item vote-total-item--abstencion">' +
      r.abstencion +
      " abstenciones</span>" +
      '<span class="vote-total-item vote-total-item--total">' +
      r.total +
      " votos totales</span>" +
      "</div>"
    );
  }

  function votoPillHTML(code) {
    const label = VOTO_LABELS[code] || "?";
    const cls = code === 1 ? "favor" : code === 2 ? "contra" : "abstencion";
    return (
      '<span class="voto-pill voto-pill--' + cls + '">' + label + "</span>"
    );
  }

  function tagsHTML(tags) {
    if (!tags || tags.length === 0) return "";
    return tags
      .map((t) => '<span class="chip">' + esc(fmt(t)) + "</span>")
      .join(" ");
  }

  function resultMarginText(r) {
    if (r.result === "Empate") return "Empate";
    const verb = r.result === "Aprobada" ? "Aprobada" : "Rechazada";
    return verb + " por " + r.margin + " votos";
  }

  function shareBarHTML(title, result) {
    const url = location.href;
    const text = result
      ? title + " → " + result + ". Mira como voto cada diputado:"
      : title + " — Lo Que Votan:";
    return (
      '<div class="share-bar">' +
      '<button class="share-btn share-btn--copy" data-share-url="' +
      esc(url) +
      '" onclick="window._copyShare(this)">&#128279; Copiar enlace</button>' +
      '<a class="share-btn share-btn--twitter" href="https://twitter.com/intent/tweet?text=' +
      encodeURIComponent(text) +
      "&url=" +
      encodeURIComponent(url) +
      '" target="_blank" rel="noopener">&#120143; Compartir</a>' +
      '<a class="share-btn share-btn--whatsapp" href="https://api.whatsapp.com/send?text=' +
      encodeURIComponent(text + " " + url) +
      '" target="_blank" rel="noopener">&#128172; WhatsApp</a>' +
      "</div>"
    );
  }

  // Global share handler
  window._copyShare = function (btn) {
    const url = location.href;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(() => {
        btn.textContent = "Copiado!";
        setTimeout(() => {
          btn.innerHTML = "&#128279; Copiar enlace";
        }, 2000);
      });
    }
  };

  // ═══════════════════════════════════════════════════════════
  // Pagination
  // ═══════════════════════════════════════════════════════════

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
    for (
      let i = Math.max(2, current - 1);
      i <= Math.min(total - 1, current + 1);
      i++
    )
      pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
    return pages;
  }

  // ═══════════════════════════════════════════════════════════
  // Autocomplete (hero search)
  // ═══════════════════════════════════════════════════════════

  function initAutocomplete() {
    const input = $("hero-search");
    const dropdown = $("hero-dropdown");
    let highlightIdx = -1;

    const render = (query) => {
      if (query.length < 2) {
        dropdown.hidden = true;
        return;
      }

      const q = query.toLowerCase();
      const matches = [];
      for (let i = 0; i < diputados.length && matches.length < 8; i++) {
        if (dipStats[i].total === 0) continue;
        if (diputados[i].toLowerCase().includes(q)) {
          matches.push(i);
        }
      }

      if (matches.length === 0) {
        dropdown.hidden = true;
        return;
      }

      dropdown.innerHTML = matches
        .map(
          (i) =>
            '<a class="autocomplete-item" href="#diputado/' +
            encodeURIComponent(diputados[i]) +
            '"><span>' +
            esc(diputados[i]) +
            '</span><span class="ac-grupo">' +
            esc(
              dipStats[i].mainGrupo >= 0 ? grupos[dipStats[i].mainGrupo] : "",
            ) +
            "</span></a>",
        )
        .join("");

      highlightIdx = -1;
      dropdown.hidden = false;
    };

    input.addEventListener(
      "input",
      debounce(() => render(input.value.trim()), 150),
    );

    input.addEventListener("keydown", (e) => {
      if (dropdown.hidden) return;
      const items = dropdown.querySelectorAll(".autocomplete-item");
      if (e.key === "ArrowDown") {
        e.preventDefault();
        highlightIdx = Math.min(highlightIdx + 1, items.length - 1);
        updateHighlight(items);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        highlightIdx = Math.max(highlightIdx - 1, 0);
        updateHighlight(items);
      } else if (e.key === "Enter" && highlightIdx >= 0) {
        e.preventDefault();
        items[highlightIdx].click();
      } else if (e.key === "Escape") {
        dropdown.hidden = true;
      }
    });

    function updateHighlight(items) {
      items.forEach((el, i) =>
        el.classList.toggle("highlighted", i === highlightIdx),
      );
    }

    dropdown.addEventListener("click", () => {
      dropdown.hidden = true;
      input.value = "";
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".hero-search-wrap")) dropdown.hidden = true;
    });
  }

  // ═══════════════════════════════════════════════════════════
  // Dark Mode
  // ═══════════════════════════════════════════════════════════

  function initTheme() {
    const saved = localStorage.getItem("lqv-theme");
    if (saved) {
      document.documentElement.dataset.theme = saved;
    } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      document.documentElement.dataset.theme = "dark";
    }
    updateThemeIcon();
  }

  function toggleTheme() {
    const current = document.documentElement.dataset.theme;
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("lqv-theme", next);
    updateThemeIcon();
  }

  function updateThemeIcon() {
    const btn = $("theme-toggle");
    btn.textContent =
      document.documentElement.dataset.theme === "dark"
        ? "\u2600\uFE0F"
        : "\uD83C\uDF19";
  }

  // ═══════════════════════════════════════════════════════════
  // Filter Options Population
  // ═══════════════════════════════════════════════════════════

  function populateFilterOptions() {
    // Categories for votaciones filter
    const catSelect = $("vots-f-cat");
    categorias
      .slice()
      .sort()
      .forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c;
        opt.textContent = fmt(c);
        catSelect.appendChild(opt);
      });

    // Tags datalist
    const tagsList = $("vots-tags-list");
    const allTags = Object.keys(tagCounts).sort();
    allTags.forEach((tag) => {
      const opt = document.createElement("option");
      opt.value = fmt(tag);
      tagsList.appendChild(opt);
    });

    // Grupos for diputados filter
    const grpSelect = $("dips-f-grupo");
    grupos
      .slice()
      .sort()
      .forEach((g) => {
        const opt = document.createElement("option");
        opt.value = g;
        opt.textContent = g;
        grpSelect.appendChild(opt);
      });

    // Legislaturas for votaciones filter
    const legSelect = $("vots-leg");
    LEGISLATURAS.forEach((l) => {
      const opt = document.createElement("option");
      opt.value = l.id;
      opt.textContent = l.nombre;
      legSelect.appendChild(opt);
    });

    // Legislaturas for grupos filter
    const gruposLegSelect = $("grupos-leg");
    LEGISLATURAS.forEach((l) => {
      const opt = document.createElement("option");
      opt.value = l.id;
      opt.textContent = l.nombre;
      gruposLegSelect.appendChild(opt);
    });
    gruposLegSelect.value = "XV";

    // Default votaciones legislatura filter to current (XV)
    legSelect.value = "XV";
  }

  // ═══════════════════════════════════════════════════════════
  // Event Listeners
  // ═══════════════════════════════════════════════════════════

  function attachListeners() {
    window.addEventListener("hashchange", handleRoute);
    $("theme-toggle").addEventListener("click", toggleTheme);

    initAutocomplete();

    // Votaciones filters
    $("vots-f-search").addEventListener(
      "input",
      debounce(applyVotsFilters, 250),
    );
    $("vots-f-cat").addEventListener("change", applyVotsFilters);
    $("vots-f-result").addEventListener("change", applyVotsFilters);
    $("vots-leg").addEventListener("change", applyVotsFilters);
    $("vots-f-sort").addEventListener("change", applyVotsFilters);
    $("vots-f-tag").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addVotsTag();
      }
    });
    $("vots-f-tag").addEventListener("change", addVotsTag);
    $("vots-reset").addEventListener("click", () => {
      $("vots-f-search").value = "";
      $("vots-f-cat").value = "";
      $("vots-f-result").value = "";
      $("vots-leg").value = "";
      $("vots-f-sort").value = "recent";
      $("vots-f-tag").value = "";
      votsSelectedTags = [];
      applyVotsFilters();
    });

    // Diputados filters
    $("dips-f-search").addEventListener(
      "input",
      debounce(applyDipsFilters, 250),
    );
    $("dips-f-grupo").addEventListener("change", applyDipsFilters);
    $("dips-f-sort").addEventListener("change", applyDipsFilters);
    $("dips-reset").addEventListener("click", () => {
      $("dips-f-search").value = "";
      $("dips-f-grupo").value = "";
      $("dips-f-sort").value = "name";
      applyDipsFilters();
    });

    // Grupos affinity filter
    $("grupos-leg").addEventListener("change", renderGrupos);
  }

  // ═══════════════════════════════════════════════════════════
  // Helpers
  // ═══════════════════════════════════════════════════════════

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    if (!s) return "";
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmt(s) {
    return (s || "").replace(/_/g, " ");
  }

  function pct(n) {
    return (n * 100).toFixed(1) + "%";
  }

  function debounce(fn, ms) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }

  function showError(msg) {
    const el = $("error");
    el.textContent = msg;
    el.style.display = "block";
  }

  // ═══════════════════════════════════════════════════════════
  // Start
  // ═══════════════════════════════════════════════════════════

  document.addEventListener("DOMContentLoaded", init);
})();

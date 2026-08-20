const STATUS_LABELS = {
  live: "Aktif",
  stale: "Data terakhir",
  error: "Gangguan",
  restricted: "Akses terbatas",
  portal_only: "Portal publik",
  authentication_required: "Perlu token",
  institutional_access: "Akses institusi",
  license_required: "Perlu lisensi",
  imported: "Impor tervalidasi",
  manual_import: "Impor manual",
};

const ACCESS_LABELS = {
  public: "Publik",
  restricted: "Terbatas",
  licensed: "Berlisensi",
  institutional: "Institusional",
  internal: "Internal",
};

const CATEGORY = {
  critical: { label: "Merah · kematian terkonfirmasi", color: "#d93a2b", className: "tag-kritis" },
  high: { label: "Jingga · kejadian terkonfirmasi", color: "#e58a20", className: "tag-tinggi" },
  medium: { label: "Kuning · monitoring resmi", color: "#d6b019", className: "tag-sedang" },
  signal: { label: "Hijau · rumor/verifikasi", color: "#3f8654", className: "tag-sinyal" },
};

const REGION = {
  id: { scope: "Indonesia", center: [-2.5, 118], zoom: 5 },
  asean: { scope: "ASEAN", center: [8, 112], zoom: 4 },
  apac: { scope: "Asia-Pacific", center: [15, 100], zoom: 3 },
  global: { scope: "Global", center: [10, 20], zoom: 2 },
};

const state = {
  region: "id",
  period: "90",
  group: "all",
  disease: "all",
  source: "all",
  evidence: "all",
  selectedId: null,
};

let metadata = {};
let sources = [];
let records = [];
let map = null;
let markersLayer = null;
let leafletReady = false;

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "—")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch (_error) {
    return "";
  }
}

function numeric(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatNumber(value) {
  const number = numeric(value);
  return number === null ? "—" : number.toLocaleString("id-ID");
}

function formatDate(value, includeTime = false) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return escapeHtml(value);
  return new Intl.DateTimeFormat("id-ID", {
    timeZone: "Asia/Jakarta",
    day: "2-digit",
    month: "short",
    year: "numeric",
    ...(includeTime ? { hour: "2-digit", minute: "2-digit", timeZoneName: "short" } : {}),
  }).format(date);
}

function groupsOf(record) {
  if (Array.isArray(record.disease_groups) && record.disease_groups.length) return record.disease_groups;
  const disease = String(record.disease || "").toLowerCase();
  const tadTerms = [
    "foot-and-mouth", "fmd/pmk", "african swine fever", "lumpy skin", "classical swine",
    "peste des petits", "pleuropneumonia", "african horse", "sheep pox", "goat pox",
    "newcastle", "rinderpest", "avian influenza", "rift valley fever", "anthrax", "rabies", "brucellosis",
  ];
  const animalPriorityTerms = [
    ...tadTerms, "avian influenza", "rabies", "anthrax", "brucellosis",
    "septicaemia epizootica", "jembrana", "surra", "trypanosomiasis",
  ];
  const pureAnimalTerms = [
    "foot-and-mouth", "fmd/pmk", "african swine fever", "lumpy skin", "classical swine",
    "peste des petits", "pleuropneumonia", "african horse", "sheep pox", "goat pox",
    "newcastle", "rinderpest", "septicaemia epizootica", "jembrana", "surra", "trypanosomiasis",
  ];
  const groups = [];
  if (animalPriorityTerms.some((term) => disease.includes(term))) groups.push("Penyakit hewan prioritas");
  if (tadTerms.some((term) => disease.includes(term))) groups.push("TADs");
  if (!pureAnimalTerms.some((term) => disease.includes(term))) {
    groups.push("Zoonosis/EID");
  }
  return groups.length ? groups : ["Zoonosis/EID"];
}

function categoryOf(record) {
  if (record.evidence === "rumor") return "signal";
  const humanDeaths = numeric(record.human?.deaths) || 0;
  const animalDeaths = numeric(record.animal?.deaths) || 0;
  if (humanDeaths > 0 || animalDeaths > 0) return "critical";
  const confirmedImpact = [
    record.human?.confirmed,
    record.animal?.outbreaks,
    record.animal?.sick,
    record.animal?.culled,
  ].some((value) => (numeric(value) || 0) > 0);
  return confirmedImpact ? "high" : "medium";
}

function recordDate(record) {
  const value = record.published || record.reported || record.updated;
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date : null;
}

function withinPeriod(record) {
  if (state.period === "all") return true;
  const date = recordDate(record);
  if (!date) return false;
  const ageDays = (Date.now() - date.getTime()) / 86400000;
  return ageDays >= -1 && ageDays <= Number(state.period);
}

function filteredRecords() {
  const scope = REGION[state.region].scope;
  return records.filter((record) => {
    const inScope = Array.isArray(record.scopes) && record.scopes.includes(scope);
    const inGroup = state.group === "all" || groupsOf(record).includes(state.group);
    const isDisease = state.disease === "all" || record.disease === state.disease;
    const isSource = state.source === "all" || record.source_id === state.source;
    const isEvidence = state.evidence === "all" || record.evidence === state.evidence;
    return inScope && withinPeriod(record) && inGroup && isDisease && isSource && isEvidence;
  });
}

function sourceLink(record) {
  const url = safeUrl(record.source_url);
  const label = escapeHtml(record.source || "Sumber tidak dicantumkan");
  return url ? `<a class="source-link" href="${escapeHtml(url)}" target="_blank" rel="noopener">${label}</a>` : label;
}

function evidenceLabel(record) {
  return record.evidence === "rumor" ? "Rumor/verifikasi" : "Terkonfirmasi";
}

function initMap() {
  try {
    if (typeof window.L !== "undefined") {
      map = window.L.map("map", { scrollWheelZoom: false, attributionControl: true });
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(map);
      markersLayer = window.L.layerGroup().addTo(map);
      leafletReady = true;
    }
  } catch (_error) {
    leafletReady = false;
  }
  if (!leafletReady) {
    $("map").innerHTML = '<div class="empty-state">Peta tidak dapat dimuat. Data tabel dan indikator tetap tersedia.</div>';
  }
}

function renderMap(list) {
  if (!leafletReady) return;
  markersLayer.clearLayers();
  list
    .filter((record) => record.record_type === "event" && numeric(record.lat) !== null && numeric(record.lon) !== null)
    .forEach((record) => {
      const category = categoryOf(record);
      const marker = window.L.circleMarker([record.lat, record.lon], {
        radius: category === "critical" ? 10 : category === "high" ? 9 : 8,
        fillColor: CATEGORY[category].color,
        color: "#ffffff",
        weight: 2,
        fillOpacity: 0.92,
      }).addTo(markersLayer);
      marker.bindTooltip(
        `<strong>${escapeHtml(record.disease)}</strong><br>` +
        `${escapeHtml(record.title)}<br>` +
        `<strong>Lokasi:</strong> ${escapeHtml(record.location)}<br>` +
        `<strong>Status:</strong> ${escapeHtml(evidenceLabel(record))}<br>` +
        `<strong>Sumber:</strong> ${escapeHtml(record.source || "—")}`,
        { direction: "top", maxWidth: 420 },
      );
      marker.on("click", () => {
        state.selectedId = record.id;
        renderDetail(list);
      });
    });
  const region = REGION[state.region];
  map.setView(region.center, region.zoom);
}

function detailBlock(title, rows) {
  const content = rows.map(([key, value]) => `<div class="kv-row"><span class="k">${escapeHtml(key)}</span><span class="v">${value}</span></div>`).join("");
  return `<div class="detail-block"><h6>${escapeHtml(title)}</h6>${content}</div>`;
}

function renderDetail(list) {
  const record = list.find((item) => item.id === state.selectedId);
  if (!record) {
    $("detail-panel").innerHTML = '<div class="detail-empty">Pilih titik pada peta atau baris grafik untuk melihat rincian, status bukti, dan sumber.<br><br><span class="mono" style="font-size:11px;">Event ID: —</span></div>';
    return;
  }
  const category = CATEGORY[categoryOf(record)];
  const groupBadges = groupsOf(record).map((group) => `<span class="mini-badge">${escapeHtml(group)}</span>`).join(" ");
  const source = sourceLink(record);
  $("detail-panel").innerHTML = `
    <div class="detail-head">
      <span class="mono text-muted" style="font-size:11px;">Event ID: ${escapeHtml(record.id)}</span>
      <div style="font-family:var(--font-heading);font-weight:800;font-size:18px;margin-top:5px;">${escapeHtml(record.title || record.disease)}</div>
      <div class="text-muted" style="font-size:13px;margin:3px 0 8px;">${escapeHtml(record.disease)} · ${escapeHtml(record.location)}</div>
      <span class="tag ${category.className}">${escapeHtml(category.label)}</span>
      <div class="pub-badges">${groupBadges}</div>
    </div>
    ${detailBlock("Linimasa", [["Dilaporkan", escapeHtml(formatDate(record.reported || record.published, true))], ["Diperbarui", escapeHtml(formatDate(record.updated, true))]])}
    ${detailBlock("Dampak manusia", [["Suspek", escapeHtml(formatNumber(record.human?.suspected))], ["Terkonfirmasi", escapeHtml(formatNumber(record.human?.confirmed))], ["Meninggal", escapeHtml(formatNumber(record.human?.deaths))]])}
    ${detailBlock("Dampak hewan", [["Spesies", escapeHtml(record.animal?.species || "—")], ["Outbreak", escapeHtml(formatNumber(record.animal?.outbreaks))], ["Sakit", escapeHtml(formatNumber(record.animal?.sick))], ["Mati", escapeHtml(formatNumber(record.animal?.deaths))], ["Dimusnahkan", escapeHtml(formatNumber(record.animal?.culled))]])}
    ${detailBlock("Laboratorium", [["Hasil", escapeHtml(record.lab?.result || "—")], ["Metode", escapeHtml(record.lab?.method || "—")], ["Laboratorium", escapeHtml(record.lab?.name || "—")]])}
    ${detailBlock("Respons", [["Status", escapeHtml(record.response || "—")], ["Tindakan", escapeHtml(record.actions || "—")], ["PIC", escapeHtml(record.pic || "—")], ["Berikutnya", escapeHtml(record.next || "—")]])}
    ${detailBlock("Sumber dan verifikasi", [["Status bukti", escapeHtml(evidenceLabel(record))], ["Sumber", source], ["Verifikasi", escapeHtml(record.verification || "—")], ["Ringkasan", escapeHtml(record.summary || "—")], ["Ekonomi", escapeHtml(record.economic || "—")]])}
  `;
}

function sumKnown(list, getter) {
  const values = list.map(getter).filter((value) => numeric(value) !== null);
  return { known: values.length > 0, total: values.reduce((sum, value) => sum + value, 0) };
}

function renderStats(list) {
  const eventsOnly = list.filter((record) => record.record_type === "event");
  const confirmed = eventsOnly.filter((record) => record.evidence === "confirmed");
  const rumors = list.filter((record) => record.evidence === "rumor");
  const critical = confirmed.filter((record) => categoryOf(record) === "critical").length;
  const mappedRumors = rumors.filter((record) => record.record_type === "event" && numeric(record.lat) !== null).length;
  const humans = sumKnown(confirmed, (record) => record.human?.confirmed);
  const humanDeaths = sumKnown(confirmed, (record) => record.human?.deaths);
  const animalOutbreaks = sumKnown(confirmed, (record) => record.animal?.outbreaks);
  const animalDeaths = sumKnown(confirmed, (record) => record.animal?.deaths);

  $("stat-active").textContent = confirmed.length.toLocaleString("id-ID");
  $("stat-active-sub").textContent = `${critical.toLocaleString("id-ID")} berstatus merah/kritis`;
  $("stat-rumor").textContent = rumors.length.toLocaleString("id-ID");
  $("stat-rumor").nextElementSibling.textContent = `${mappedRumors.toLocaleString("id-ID")} sinyal dipetakan`;
  $("stat-human").textContent = humans.known ? humans.total.toLocaleString("id-ID") : "—";
  $("stat-human-sub").textContent = humanDeaths.known ? `${humanDeaths.total.toLocaleString("id-ID")} meninggal · kejadian resmi` : "Kematian manusia belum tersedia";
  $("stat-animal").textContent = animalOutbreaks.known ? animalOutbreaks.total.toLocaleString("id-ID") : "—";
  $("stat-animal").nextElementSibling.textContent = animalDeaths.known ? `${animalDeaths.total.toLocaleString("id-ID")} kematian hewan tercatat` : "Jumlah outbreak hewan dari kejadian resmi";
}

function chartMetric(record) {
  const candidates = [
    [record.human?.confirmed, "kasus manusia"],
    [record.animal?.outbreaks, "outbreak hewan"],
    [record.animal?.deaths, "kematian hewan"],
    [record.animal?.sick, "hewan sakit"],
  ];
  const match = candidates.find(([value]) => numeric(value) !== null);
  return match ? { value: match[0], label: match[1] } : { value: 1, label: "kejadian" };
}

function renderChart(list) {
  const eventRows = list.filter((record) => record.record_type === "event").map((record) => ({ record, metric: chartMetric(record) }));
  eventRows.sort((a, b) => b.metric.value - a.metric.value);
  if (!eventRows.length) {
    $("chart-wrap").innerHTML = '<div class="empty-state">Tidak ada kejadian yang sesuai dengan filter saat ini.</div>';
    return;
  }
  const max = Math.max(...eventRows.map((item) => item.metric.value), 1);
  const logMax = Math.log(max + 1);
  $("chart-wrap").innerHTML = eventRows.slice(0, 16).map(({ record, metric }) => {
    const width = Math.max((Math.log(metric.value + 1) / logMax) * 100, 4);
    const category = categoryOf(record);
    return `<div class="chart-row" data-record-id="${escapeHtml(record.id)}" role="button" tabindex="0">
      <div class="name">${escapeHtml(record.location)}<div class="text-muted" style="font-size:10.5px;font-weight:400;">${escapeHtml(record.disease)} · ${escapeHtml(evidenceLabel(record))}</div></div>
      <div class="chart-track"><div class="chart-fill" style="width:${width}%;background:${CATEGORY[category].color};"></div></div>
      <div class="num">${escapeHtml(formatNumber(metric.value))}<div class="text-muted" style="font-size:9px;font-family:var(--font-body);font-weight:400;">${escapeHtml(metric.label)}</div></div>
    </div>`;
  }).join("");
  $("chart-wrap").querySelectorAll("[data-record-id]").forEach((row) => {
    const select = () => {
      state.selectedId = row.dataset.recordId;
      renderDetail(list);
      $("detail-panel").scrollIntoView({ behavior: "smooth", block: "nearest" });
    };
    row.addEventListener("click", select);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") select();
    });
  });
}

function renderLatest(list) {
  const latest = [...list].sort((a, b) => (recordDate(b)?.getTime() || 0) - (recordDate(a)?.getTime() || 0)).slice(0, 12);
  if (!latest.length) {
    $("pub-list").innerHTML = '<div class="empty-state">Tidak ada laporan atau sinyal yang sesuai dengan filter.</div>';
    return;
  }
  $("pub-list").innerHTML = latest.map((record) => {
    const url = safeUrl(record.source_url);
    const title = escapeHtml(record.title || record.disease);
    const linkedTitle = url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener">${title}</a>` : title;
    const groupBadges = groupsOf(record).map((group) => `<span class="mini-badge">${escapeHtml(group)}</span>`).join("");
    return `<div class="pub-item">
      <span class="pub-date mono">${escapeHtml(formatDate(record.published))}</span>
      <span class="pub-title">${linkedTitle}<span class="pub-badges"><span class="mini-badge">${escapeHtml(record.record_type === "event" ? "Kejadian" : "Laporan")}</span><span class="mini-badge">${escapeHtml(evidenceLabel(record))}</span>${groupBadges}</span></span>
      <span class="pub-source">${escapeHtml(record.source || "—")}</span>
    </div>`;
  }).join("");
}

function renderRegistry() {
  const body = document.querySelector("#registry-table tbody");
  body.innerHTML = sources.map((source) => {
    const url = safeUrl(source.url);
    const name = escapeHtml(source.name);
    const linkedName = url ? `<a class="source-link" href="${escapeHtml(url)}" target="_blank" rel="noopener">${name}</a>` : name;
    const status = STATUS_LABELS[source.status] || source.status || "Belum diperiksa";
    const recordsCount = numeric(source.records) === null ? "" : ` · ${formatNumber(source.records)} rekaman`;
    return `<tr><td class="registry-name">${linkedName}</td><td>${escapeHtml(source.level || "—")}</td><td>${escapeHtml(ACCESS_LABELS[source.access_level] || source.access_level || "—")}</td><td><strong>${escapeHtml(status)}</strong>${escapeHtml(recordsCount)}<br><span class="text-muted">${escapeHtml(source.note || source.error || "—")}</span></td></tr>`;
  }).join("");
}

function renderMetadata() {
  const generated = formatDate(metadata.generated_at, true);
  $("data-status").textContent = `${formatNumber(metadata.records)} rekaman termuat`;
  $("data-status").classList.add("ready");
  $("data-updated").textContent = `Diperbarui ${generated} · setiap ${metadata.update_interval_hours || 48} jam`;
  const imported = metadata.imported_records || 0;
  const files = metadata.import_files_scanned || 0;
  const errors = metadata.import_validation_errors || 0;
  const warnings = metadata.import_validation_warnings || 0;
  $("import-status").innerHTML = `<strong>${formatNumber(imported)} rekaman aktif</strong> dari ${formatNumber(files)} file; ${formatNumber(errors)} error dan ${formatNumber(warnings)} peringatan validasi. TADs: ${formatNumber(metadata.tads_records || 0)} rekaman (${formatNumber(metadata.tads_confirmed || 0)} terkonfirmasi; ${formatNumber(metadata.tads_rumor || 0)} rumor).`;
}

function populateFilters() {
  const diseaseSelect = $("f-disease");
  const diseases = [...new Set(records.map((record) => record.disease).filter(Boolean))].sort((a, b) => a.localeCompare(b, "id"));
  diseaseSelect.innerHTML = '<option value="all">Semua penyakit</option>' + diseases.map((disease) => `<option value="${escapeHtml(disease)}">${escapeHtml(disease)}</option>`).join("");
  const sourceSelect = $("f-source");
  const activeSources = [...new Map(records.map((record) => [record.source_id, record.source || record.source_id])).entries()].filter(([id]) => id).sort((a, b) => a[1].localeCompare(b[1], "id"));
  sourceSelect.innerHTML = '<option value="all">Semua sumber aktif</option>' + activeSources.map(([id, name]) => `<option value="${escapeHtml(id)}">${escapeHtml(name)}</option>`).join("");
}

function render() {
  const list = filteredRecords();
  if (state.selectedId && !list.some((record) => record.id === state.selectedId)) state.selectedId = null;
  renderStats(list);
  renderMap(list);
  renderDetail(list);
  renderChart(list);
  renderLatest(list);
}

function bindFilters() {
  const bindings = [
    ["f-region", "region"],
    ["f-period", "period"],
    ["f-group", "group"],
    ["f-disease", "disease"],
    ["f-source", "source"],
  ];
  bindings.forEach(([id, key]) => $(id).addEventListener("change", (event) => {
    state[key] = event.target.value;
    state.selectedId = null;
    render();
  }));
  document.querySelectorAll(".evidence-chip").forEach((chip) => chip.addEventListener("click", () => {
    document.querySelectorAll(".evidence-chip").forEach((item) => item.classList.remove("on"));
    chip.classList.add("on");
    state.evidence = chip.dataset.ev;
    state.selectedId = null;
    render();
  }));
}

async function start() {
  try {
    // The dataset is regenerated every 48 hours. A timestamp query avoids a
    // stale module response from the GitHub Pages/CDN cache after deployment.
    const payload = await import(`../data/events.js?ts=${Date.now()}`);
    metadata = payload.metadata || {};
    sources = Array.isArray(payload.sources) ? payload.sources : [];
    records = Array.isArray(payload.events) ? payload.events : [];
    initMap();
    populateFilters();
    bindFilters();
    renderMetadata();
    renderRegistry();
    render();
    window.setTimeout(() => { if (leafletReady) map.invalidateSize(); }, 100);
  } catch (error) {
    $("data-status").textContent = "Data gagal dimuat";
    $("data-status").classList.add("error");
    $("data-updated").textContent = "Periksa data/events.js dan deployment";
    $("map").innerHTML = '<div class="empty-state">Dashboard tidak dapat membaca dataset terbaru.</div>';
    $("chart-wrap").innerHTML = '<div class="empty-state">Tidak ada data yang dapat ditampilkan.</div>';
    $("pub-list").innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

start();

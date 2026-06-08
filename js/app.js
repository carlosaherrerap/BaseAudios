// ── Configuración ──────────────────────────────────────────────
// Detecta si se abrió directo (file://) o si se está usando un servidor local (Live Server 127.0.0.1/localhost)
const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const isFile = window.location.protocol === 'file:';

const API_BASE = (isLocal || isFile) 
  ? "http://localhost:5000/api" 
  : `${window.location.origin}/api`;

const PAGE_SIZE = 10;

const COLUMNS = [
  { key: "ORDER", label: "Nº" },
  { key: "TELEFONO", label: "Teléfono", special: "telefono" },
  { key: "PESO", label: "Peso", special: "peso" },
  { key: "audio_path", label: "Audio", special: "audio_path" },
  { key: "gestion", label: "Gestión", special: "gestion" },
  { key: "SELECCIONAR", label: "Selección", special: "seleccionar" },
];

// ── State ──────────────────────────────────────────────────────
let state = { 
  query: "", 
  page: 1, 
  totalPages: 1, 
  debounceTimer: null,
  selectedAudios: JSON.parse(localStorage.getItem("selectedAudios") || "[]")
};

// ── DOM refs ───────────────────────────────────────────────────
const searchInput = document.getElementById("searchInput");
const clearBtn = document.getElementById("clearBtn");
const spinner = document.getElementById("spinner");
const resultsCount = document.getElementById("resultsCount");
const contentArea = document.getElementById("contentArea");
const pagination = document.getElementById("pagination");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const monthSelect = document.getElementById("monthSelect");
const sortSelect = document.getElementById("sortSelect");

// DOM Refs Bolsa de Audios
const bagBtn = document.getElementById("bagBtn");
const bagCount = document.getElementById("bagCount");
const bagModal = document.getElementById("bagModal");
const closeModalBtn = document.getElementById("closeModalBtn");
const selectedList = document.getElementById("selectedList");
const clearBagBtn = document.getElementById("clearBagBtn");
const downloadAllBtn = document.getElementById("downloadAllBtn");
const modalEmptyState = document.getElementById("modalEmptyState");
const modalListContainer = document.getElementById("modalListContainer");

// ── Health check ───────────────────────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
    const data = await res.json();
    if (data.status === "ok") {
      statusDot.className = "dot online";
      statusText.textContent = "API En Línea";
    } else throw new Error();
  } catch {
    statusDot.className = "dot offline";
    statusText.textContent = "API Desconectada";
  }
}

// ── Search ─────────────────────────────────────────────────────
async function search(query, page = 1) {
  state.query = query;
  state.page = page;
  const selectedMonth = monthSelect.value;
  const selectedSort = sortSelect ? sortSelect.value : "DEFAULT";

  if (query.length === 0) {
    renderEmpty("default");
    resultsCount.innerHTML = "";
    pagination.innerHTML = "";
    return;
  }
  if (query.length < 3) {
    renderEmpty("short");
    resultsCount.innerHTML = "";
    pagination.innerHTML = "";
    return;
  }

  spinner.classList.add("active");
  contentArea.style.opacity = "0.5";

  try {
    const url = `${API_BASE}/buscar?q=${encodeURIComponent(query)}&page=${page}&mes=${encodeURIComponent(selectedMonth)}&sort=${encodeURIComponent(selectedSort)}`;
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    state.totalPages = data.pages || 1;

    if (data.results.length === 0) {
      renderEmpty("noresults");
      resultsCount.innerHTML = "";
      pagination.innerHTML = "";
    } else {
      renderTable(data.results, query);
      renderResultsCount(data.total, page, data.results.length);
      renderPagination(page, data.pages);
    }
  } catch (err) {
    renderEmpty("error");
    resultsCount.innerHTML = "";
    pagination.innerHTML = "";
    console.error(err);
  } finally {
    spinner.classList.remove("active");
    contentArea.style.opacity = "1";
  }
}

// ── Render: Table ──────────────────────────────────────────────
function renderTable(rows, query) {
  const thead = `<thead><tr>${COLUMNS.map(c =>
    `<th class="${c.special === "telefono" ? "col-telefono" : ""}">${c.label}</th>`
  ).join("")
    }</tr></thead>`;

  const tbody = `<tbody>${rows.map((row, index) => {
    return `<tr class="fade-in" style="animation-delay: ${index * 0.01}s">${COLUMNS.map(c => {

      if (c.key === "ORDER") {
        const orderNum = (state.page - 1) * PAGE_SIZE + index + 1;
        return `<td class="cell-order">${orderNum}</td>`;
      }

      let val = row[c.key] ?? "";

      if (c.special === "telefono") {
        const highlighted = String(val).replace(
          new RegExp(`^(${escapeRegex(query)})`, "i"),
          "<mark>$1</mark>"
        );
        return `<td class="cell-telefono">${highlighted || '—'}</td>`;
      }

      if (c.special === "peso") {
        let text = String(val).trim();
        if (text && text !== "NaN" && text !== "null") {
          if (!text.toLowerCase().includes("kb")) {
            text += " kb";
          }
        } else {
          text = "—";
        }
        return `<td class="cell-peso">${escapeHtml(text)}</td>`;
      }

      if (c.special === "audio_path") {
        const rutaStr = String(row["RUTA"] || "").trim();
        const nombreStr = String(row["NOMBRE_COMPLETO"] || "").trim();
        let audioPlayerHtml = "";

        if (rutaStr && nombreStr && rutaStr !== "null" && nombreStr !== "null") {
          let fullPath = rutaStr;
          if (!fullPath.endsWith(nombreStr)) {
            if (!fullPath.endsWith("\\") && !fullPath.endsWith("/")) {
              fullPath += "\\";
            }
            fullPath += nombreStr;
          }
          if (!fullPath.toLowerCase().endsWith(".mp3")) {
            fullPath += ".mp3";
          }
          const urlPath = `${API_BASE}/audio?path=${encodeURIComponent(fullPath)}`;
          audioPlayerHtml = `
            <div class="audio-player-wrapper">
              <audio controls class="audio-player" src="${urlPath}" preload="none" title="${escapeHtml(fullPath)}">
                Tu navegador no soporta el elemento de audio.
              </audio>
            </div>
          `;
        }

        return `
          <td class="cell-audio-combined">
            <div class="audio-path-text">${escapeHtml(String(val || '—'))}</div>
            ${audioPlayerHtml}
          </td>
        `;
      }

      if (c.special === "gestion") {
        const status = String(val).toLowerCase();
        return `<td class="cell-gestion">
          <span class="traffic-light-circle ${status}" title="Estado: ${status}"></span>
        </td>`;
      }

      if (c.special === "seleccionar") {
        const path = row["audio_path"] || "";
        const isSelected = state.selectedAudios.includes(path);
        const btnClass = isSelected ? "btn-select selected" : "btn-select";
        return `
          <td class="cell-action">
            <button class="${btnClass}" data-path="${escapeHtml(path)}">
              SELECCIONAR
            </button>
          </td>
        `;
      }

      return `<td>${escapeHtml(String(val))}</td>`;
    }).join("")}</tr>`;
  }).join("")}</tbody>`;

  contentArea.innerHTML = `
    <div class="table-container fade-in">
      <div class="table-scroll">
        <table aria-label="Resultados de búsqueda">${thead}${tbody}</table>
      </div>
    </div>`;
}

// ── Render: Empty states ───────────────────────────────────────
const STATES = {
  default: { icon: "bi-search", title: "Encuentra tus audios", desc: "Escribe el número de teléfono en la barra superior para explorar la base de datos." },
  short: { icon: "bi-keyboard", title: "Sigue escribiendo...", desc: "Ingresa al menos 3 dígitos para obtener coincidencias precisas." },
  noresults: { icon: "bi-inbox", title: "No hay coincidencias", desc: "No hemos encontrado ningún registro de audio asociado a ese número." },
  error: { icon: "bi-plug-fill", title: "Error de conexión", desc: "No se pudo establecer conexión con el servidor de la API." },
};

// ── Bolsa de Audios (Lógica) ───────────────────────────────────
function updateBagCount() {
  if (bagCount) {
    bagCount.textContent = state.selectedAudios.length;
  }
}

function toggleSelectAudio(path, buttonEl) {
  const idx = state.selectedAudios.indexOf(path);
  if (idx > -1) {
    state.selectedAudios.splice(idx, 1);
    if (buttonEl) {
      buttonEl.classList.remove("selected");
    }
  } else {
    state.selectedAudios.push(path);
    if (buttonEl) {
      buttonEl.classList.add("selected");
    }
  }
  updateBagCount();
  localStorage.setItem("selectedAudios", JSON.stringify(state.selectedAudios));

  // Actualizar botones visibles correspondientes a esta misma ruta
  document.querySelectorAll(`.btn-select[data-path]`).forEach(btn => {
    if (btn.dataset.path === path) {
      if (state.selectedAudios.includes(path)) {
        btn.classList.add("selected");
      } else {
        btn.classList.remove("selected");
      }
    }
  });

  if (bagModal && bagModal.open) {
    renderSelectedList();
  }
}

function renderSelectedList() {
  if (!selectedList) return;
  selectedList.innerHTML = "";

  if (state.selectedAudios.length === 0) {
    modalEmptyState.style.display = "flex";
    modalListContainer.style.display = "none";
    return;
  }

  modalEmptyState.style.display = "none";
  modalListContainer.style.display = "block";

  state.selectedAudios.forEach(path => {
    const li = document.createElement("li");
    li.className = "selected-item fade-in";

    const span = document.createElement("span");
    span.className = "item-path";
    span.textContent = path;
    span.title = path;

    const removeBtn = document.createElement("button");
    removeBtn.className = "remove-item-btn";
    removeBtn.title = "Eliminar de la bolsa";
    removeBtn.innerHTML = '<i class="bi bi-trash"></i>';
    removeBtn.addEventListener("click", () => {
      toggleSelectAudio(path);
    });

    li.appendChild(span);
    li.appendChild(removeBtn);
    selectedList.appendChild(li);
  });
}

async function downloadAllSelected() {
  if (state.selectedAudios.length === 0) return;
  
  const originalHtml = downloadAllBtn.innerHTML;
  downloadAllBtn.disabled = true;
  downloadAllBtn.textContent = "COMPRIMIENDO Y DESCARGANDO...";

  try {
    const response = await fetch(`${API_BASE}/download_zip`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true"
      },
      body: JSON.stringify({ paths: state.selectedAudios })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = "audios_seleccionados.zip";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(blobUrl);
  } catch (err) {
    console.error("Error downloading ZIP:", err);
    alert("Hubo un error al generar o descargar el archivo ZIP.");
  } finally {
    downloadAllBtn.disabled = false;
    downloadAllBtn.innerHTML = originalHtml;
  }
}

function renderEmpty(type) {
  const s = STATES[type];
  contentArea.innerHTML = `
    <div class="state-box fade-in">
      <div class="state-icon"><i class="bi ${s.icon}"></i></div>
      <div class="state-title">${s.title}</div>
      <div class="state-desc">${s.desc}</div>
    </div>`;
}

// ── Render: Results count ──────────────────────────────────────
function renderResultsCount(total, page, count) {
  const from = (page - 1) * PAGE_SIZE + 1;
  const to = from + count - 1;
  resultsCount.innerHTML =
    `Visualizando <strong>${from} – ${to}</strong> de <strong>${total.toLocaleString("es-ES")}</strong> audios encontrados`;
}

// ── Render: Pagination ─────────────────────────────────────────
function renderPagination(current, total) {
  if (total <= 1) { pagination.innerHTML = ""; return; }

  const pages = [];
  const range = 2;

  pages.push(1);
  for (let i = Math.max(2, current - range); i <= Math.min(total - 1, current + range); i++) {
    pages.push(i);
  }
  if (total > 1) pages.push(total);

  const unique = [...new Set(pages)].sort((a, b) => a - b);

  let html = `<button class="page-btn" id="prevPage" ${current === 1 ? "disabled" : ""}><i class="bi bi-chevron-left"></i></button>`;
  let prev = 0;
  for (const p of unique) {
    if (p - prev > 1) html += `<span class="page-btn" style="cursor:default;opacity:.2;border:none;background:transparent;">...</span>`;
    html += `<button class="page-btn ${p === current ? "active" : ""}" data-page="${p}">${p}</button>`;
    prev = p;
  }
  html += `<button class="page-btn" id="nextPage" ${current === total ? "disabled" : ""}><i class="bi bi-chevron-right"></i></button>`;

  pagination.innerHTML = html;

  pagination.querySelectorAll("[data-page]").forEach(btn => {
    btn.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      search(state.query, +btn.dataset.page);
    });
  });
  pagination.querySelector("#prevPage")?.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    search(state.query, current - 1);
  });
  pagination.querySelector("#nextPage")?.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    search(state.query, current + 1);
  });
}

// ── Helpers ────────────────────────────────────────────────────
function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// ── Event Listeners ────────────────────────────────────────────
searchInput.addEventListener("input", () => {
  const q = searchInput.value.trim();
  clearBtn.classList.toggle("visible", q.length > 0);
  clearTimeout(state.debounceTimer);
  state.debounceTimer = setTimeout(() => search(q), 350);
});

clearBtn.addEventListener("click", () => {
  searchInput.value = "";
  clearBtn.classList.remove("visible");
  search("");
  searchInput.focus();
});

monthSelect.addEventListener("change", () => {
  if (state.query.length >= 3) {
    search(state.query, 1);
  }
});

if (sortSelect) {
  sortSelect.addEventListener("change", () => {
    if (state.query.length >= 3) {
      search(state.query, 1);
    }
  });
}

// Event Delegation para Selección de Botón
contentArea.addEventListener("click", (e) => {
  if (e.target && e.target.classList.contains("btn-select")) {
    const path = e.target.dataset.path;
    toggleSelectAudio(path, e.target);
  }
});

// Event Listeners Bolsa de Audios (Modal)
if (bagBtn && bagModal) {
  bagBtn.addEventListener("click", () => {
    renderSelectedList();
    bagModal.showModal();
  });
}

if (closeModalBtn && bagModal) {
  closeModalBtn.addEventListener("click", () => {
    bagModal.close();
  });
}

// Cerrar modal al hacer clic en el fondo de la pantalla (Light Dismiss)
if (bagModal) {
  bagModal.addEventListener("click", (e) => {
    const rect = bagModal.getBoundingClientRect();
    const isInDialog = (rect.top <= e.clientY && e.clientY <= rect.top + rect.height &&
      rect.left <= e.clientX && e.clientX <= rect.left + rect.width);
    if (!isInDialog) {
      bagModal.close();
    }
  });
}

if (clearBagBtn) {
  clearBagBtn.addEventListener("click", () => {
    state.selectedAudios = [];
    localStorage.setItem("selectedAudios", JSON.stringify(state.selectedAudios));
    updateBagCount();
    
    // Restaurar estilos en los botones visibles
    document.querySelectorAll(".btn-select").forEach(btn => {
      btn.classList.remove("selected");
    });
    
    renderSelectedList();
  });
}

if (downloadAllBtn) {
  downloadAllBtn.addEventListener("click", () => {
    downloadAllSelected();
  });
}

// ── Init ───────────────────────────────────────────────────────
checkHealth();
renderEmpty("default");
updateBagCount();

// Static gallery: reads ../studio/library/index.json and renders cards.
// Designed to be hosted at the repo root via GitHub Pages without a server.

const STATE = { assets: [], filtered: [] };

const LIBRARY_INDEX_URL = "library/index.json";
const SVG_PATH_PREFIX = "library/";  // SVGs live at library/svg/<slug>.svg

async function load() {
  try {
    const res = await fetch(LIBRARY_INDEX_URL, { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const items = await res.json();
    STATE.assets = items;
    STATE.filtered = items;
    populateFilters(items);
    render();
  } catch (e) {
    document.getElementById("gallery").innerHTML =
      `<div style="color:#7d8590;padding:30px;grid-column:1/-1">No library yet at <code>${LIBRARY_INDEX_URL}</code>. Run <code>studio generate ...</code> locally or open <a href="generator.html">the playground</a>.</div>`;
  }
}

function populateFilters(items) {
  const types = new Set(), palettes = new Set();
  items.forEach(a => { types.add(a.type); palettes.add(a.palette); });
  const typeSel = document.getElementById("type");
  const palSel = document.getElementById("palette");
  [...types].sort().forEach(t => {
    const o = document.createElement("option");
    o.value = t; o.textContent = t; typeSel.appendChild(o);
  });
  [...palettes].sort().forEach(p => {
    const o = document.createElement("option");
    o.value = p; o.textContent = p; palSel.appendChild(o);
  });
  typeSel.addEventListener("change", filterAndRender);
  palSel.addEventListener("change", filterAndRender);
  document.getElementById("q").addEventListener("input", filterAndRender);
}

function filterAndRender() {
  const q = document.getElementById("q").value.trim().toLowerCase();
  const t = document.getElementById("type").value;
  const p = document.getElementById("palette").value;
  STATE.filtered = STATE.assets.filter(a => {
    if (t && a.type !== t) return false;
    if (p && a.palette !== p) return false;
    if (q) {
      const blob = [a.slug, a.title, a.description, a.prompt, ...(a.tags || [])].join(" ").toLowerCase();
      if (!blob.includes(q)) return false;
    }
    return true;
  });
  render();
}

async function render() {
  const gallery = document.getElementById("gallery");
  gallery.innerHTML = "";
  document.getElementById("count").textContent = `${STATE.filtered.length} of ${STATE.assets.length}`;
  for (const a of STATE.filtered) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="preview" data-svg="${a.svg_path}"></div>
      <div class="meta">
        <p class="title">${escapeHtml(a.title)}</p>
        <div class="tags">${(a.tags || []).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join("")}</div>
      </div>
    `;
    card.addEventListener("click", () => showDetail(a));
    gallery.appendChild(card);
    // Lazy-load the SVG file inline so we can recolor it via CSS variables later.
    fetch(SVG_PATH_PREFIX + a.svg_path).then(r => r.text()).then(svgText => {
      card.querySelector(".preview").innerHTML = svgText;
    }).catch(() => {});
  }
}

async function showDetail(a) {
  const dlg = document.getElementById("detail");
  const body = document.getElementById("detail-body");
  let svgText = "";
  try {
    svgText = await fetch(SVG_PATH_PREFIX + a.svg_path).then(r => r.text());
  } catch (e) { svgText = `<!-- failed to load ${a.svg_path} -->`; }
  body.innerHTML = `
    <h2>${escapeHtml(a.title)} <small style="color:#7d8590;font-weight:400">— ${escapeHtml(a.slug)}</small></h2>
    <div class="body">
      <div class="preview">${svgText}</div>
      <div>
        <p><strong>type:</strong> ${escapeHtml(a.type)}</p>
        <p><strong>palette:</strong> ${escapeHtml(a.palette)}</p>
        <p><strong>model:</strong> ${escapeHtml(a.model || "")}</p>
        <p><strong>created:</strong> ${escapeHtml(a.created_at || "")}</p>
        <p><strong>tags:</strong> ${(a.tags || []).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join(" ")}</p>
        <p><strong>prompt:</strong> <em>${escapeHtml(a.prompt || "")}</em></p>
        <div class="row">
          <a class="copy" href="${SVG_PATH_PREFIX + a.svg_path}" download>Download SVG</a>
          <button class="copy" onclick="copySvg('${a.svg_path}')">Copy SVG</button>
        </div>
        <pre>${escapeHtml(JSON.stringify(a, null, 2))}</pre>
      </div>
    </div>
  `;
  dlg.showModal();
}

async function copySvg(path) {
  const txt = await fetch(SVG_PATH_PREFIX + path).then(r => r.text());
  await navigator.clipboard.writeText(txt);
}
window.copySvg = copySvg;

function escapeHtml(s) {
  return String(s || "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
}

load();

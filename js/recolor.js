// In-browser deterministic recolor — mirrors studio/style/recolor.py.

import { LAYER_TO_STOP, ALL_STOPS, nearestColor, paletteColors } from "./palettes.js";

const HEX_RE = /#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b/;

function normalizeHex(v) {
  if (!v) return null;
  const m = HEX_RE.exec(v.trim());
  if (!m) return null;
  let h = m[1];
  if (h.length === 3) h = h.split("").map(c => c + c).join("");
  return "#" + h.toLowerCase();
}

function sourceStopFor(elColor, sourcePalette) {
  const lookup = {};
  for (const k of ALL_STOPS) lookup[sourcePalette[k].toLowerCase()] = k;
  if (lookup[elColor]) return lookup[elColor];
  const nearest = nearestColor(elColor, paletteColors(sourcePalette));
  return lookup[nearest.toLowerCase()] || "mid";
}

// Parse an SVG string with DOMParser so we get a real DOM tree to mutate.
function parseSvg(svgText) {
  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  const err = doc.querySelector("parsererror");
  if (err) throw new Error("SVG parse error: " + err.textContent);
  return doc;
}

export function recolor(svgText, sourcePalette, targetPalette) {
  const doc = parseSvg(svgText);
  let fills = 0, strokes = 0;
  const walk = (el) => {
    if (el.nodeType !== 1) return;
    const layerAttr = el.getAttribute("data-layer");
    for (const attr of ["fill", "stroke"]) {
      const v = el.getAttribute(attr);
      if (!v) continue;
      const hex = normalizeHex(v);
      if (!hex) continue;
      let stop = null;
      if (layerAttr !== null) {
        const li = parseInt(layerAttr, 10);
        if (!Number.isNaN(li)) stop = LAYER_TO_STOP[li] || "mid";
      }
      if (!stop) stop = sourceStopFor(hex, sourcePalette);
      const newColor = targetPalette[stop];
      if (newColor && newColor.toLowerCase() !== hex) {
        el.setAttribute(attr, newColor);
        if (attr === "fill") fills += 1; else strokes += 1;
      }
    }
    for (const child of el.children) walk(child);
  };
  walk(doc.documentElement);
  return { svg: new XMLSerializer().serializeToString(doc.documentElement), fills, strokes };
}

// Apply a fully custom color map. `colorMap` is { "data-role-or-#hex": "#newhex" }.
// If the key starts with `role:` it matches data-role; if it starts with `layer:`
// it matches data-layer; if it's a hex it remaps every node with that fill.
export function applyOverrides(svgText, colorMap) {
  const doc = parseSvg(svgText);
  let changed = 0;
  const walk = (el) => {
    if (el.nodeType !== 1) return;
    const role = el.getAttribute("data-role");
    const layer = el.getAttribute("data-layer");
    for (const attr of ["fill", "stroke"]) {
      const v = el.getAttribute(attr);
      if (!v) continue;
      const hex = normalizeHex(v);
      let newColor = null;
      if (role && colorMap[`role:${role}`]) newColor = colorMap[`role:${role}`];
      if (!newColor && layer !== null && colorMap[`layer:${layer}`]) newColor = colorMap[`layer:${layer}`];
      if (!newColor && hex && colorMap[hex]) newColor = colorMap[hex];
      if (newColor && newColor !== hex) {
        el.setAttribute(attr, newColor);
        changed += 1;
      }
    }
    for (const child of el.children) walk(child);
  };
  walk(doc.documentElement);
  return { svg: new XMLSerializer().serializeToString(doc.documentElement), changed };
}

export function listRoles(svgText) {
  const doc = parseSvg(svgText);
  const out = [];
  const seen = new Set();
  doc.documentElement.querySelectorAll("[data-role]").forEach(el => {
    const r = el.getAttribute("data-role");
    if (!seen.has(r)) { seen.add(r); out.push(r); }
  });
  return out;
}

export function listLayers(svgText) {
  const doc = parseSvg(svgText);
  const set = new Set();
  doc.documentElement.querySelectorAll("[data-layer]").forEach(el => set.add(el.getAttribute("data-layer")));
  return Array.from(set).sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
}

export function toggleLayerVisibility(svgText, hiddenLayers) {
  const doc = parseSvg(svgText);
  const hidden = new Set(hiddenLayers.map(String));
  doc.documentElement.querySelectorAll("[data-layer]").forEach(el => {
    if (hidden.has(el.getAttribute("data-layer"))) {
      el.setAttribute("opacity", "0");
    } else {
      el.removeAttribute("opacity");
    }
  });
  return new XMLSerializer().serializeToString(doc.documentElement);
}

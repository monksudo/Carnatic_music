// In-browser SVG sanitizer — minimal mirror of studio/style/sanitizer.py.
// Strips gradient/filter/mask defs, remaps url(#x) refs to nearest palette
// swatch, snaps off-palette solid colors to the palette. Returns
// { svg, report } where report has the same shape as the Python one.

import { nearestColor, paletteColors } from "./palettes.js";

const HEX_RE = /#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b/;
const URL_REF_RE = /url\(\s*#([^)\s]+)\s*\)/;
const STYLE_BAD = /\b(gradient|filter|mask)\b/i;

const FORBIDDEN = ["linearGradient", "radialGradient", "filter", "mask", "image", "foreignObject", "pattern"];

function normalizeHex(v) {
  if (!v) return null;
  const t = v.trim();
  if (["none", "currentcolor", "transparent", "inherit"].includes(t.toLowerCase())) return null;
  const m = HEX_RE.exec(t);
  if (!m) return null;
  let h = m[1];
  if (h.length === 3) h = h.split("").map(c => c + c).join("");
  return "#" + h.toLowerCase();
}

function gradientMidColor(gradEl) {
  const stops = Array.from(gradEl.children).filter(c => c.localName === "stop");
  const colors = [];
  for (const s of stops) {
    let c = s.getAttribute("stop-color");
    if (!c) {
      const style = s.getAttribute("style") || "";
      const m = /stop-color\s*:\s*([^;]+)/.exec(style);
      if (m) c = m[1].trim();
    }
    if (c) {
      const hex = HEX_RE.exec(c);
      if (hex) colors.push("#" + hex[1]);
    }
  }
  if (!colors.length) return null;
  return colors[Math.floor(colors.length / 2)];
}

export function sanitize(svgText, palette) {
  const report = {
    gradients_removed: 0, filters_removed: 0, masks_removed: 0,
    refs_remapped: 0, colors_snapped: 0, nodes_removed: 0,
    forbidden_tags_removed: [], fallback_color: palette.mid,
  };
  const palColors = paletteColors(palette);
  const fallback = palette.mid;

  const start = svgText.indexOf("<svg");
  const end = svgText.lastIndexOf("</svg>");
  if (start === -1 || end === -1) throw new Error("No <svg>...</svg> found in input.");
  svgText = svgText.slice(start, end + "</svg>".length);

  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  const err = doc.querySelector("parsererror");
  if (err) throw new Error("SVG parse error: " + err.textContent);
  const root = doc.documentElement;
  if (root.localName !== "svg") throw new Error("Root element is not <svg>.");

  // 1. Build url(#id) → palette-snapped color map.
  const refToColor = {};
  for (const g of root.querySelectorAll("linearGradient, radialGradient")) {
    const id = g.getAttribute("id");
    const mid = gradientMidColor(g);
    if (id && mid) refToColor[id] = nearestColor(mid, palColors);
    report.gradients_removed += 1;
  }

  // 2. Strip forbidden tags.
  for (const tag of FORBIDDEN) {
    for (const el of root.querySelectorAll(tag)) {
      report.forbidden_tags_removed.push(tag);
      if (tag === "filter") report.filters_removed += 1;
      else if (tag === "mask") report.masks_removed += 1;
      el.parentNode && el.parentNode.removeChild(el);
      report.nodes_removed += 1;
    }
  }

  // 3. Walk every element; remap refs, snap colors, drop external href / dangling
  //    filter/mask/clip-path attributes.
  const walk = (el) => {
    if (el.nodeType !== 1) return;
    for (const attr of ["href", "xlink:href"]) {
      const v = el.getAttribute(attr);
      if (v && !v.startsWith("#")) {
        el.removeAttribute(attr);
        report.nodes_removed += 1;
      }
    }
    for (const attr of ["filter", "mask", "clip-path"]) {
      if (el.getAttribute(attr)) {
        el.removeAttribute(attr);
        report.nodes_removed += 1;
      }
    }
    for (const attr of ["fill", "stroke"]) {
      const v = el.getAttribute(attr);
      if (!v) continue;
      const ref = URL_REF_RE.exec(v);
      if (ref) {
        const rid = ref[1];
        el.setAttribute(attr, refToColor[rid] || fallback);
        report.refs_remapped += 1;
        continue;
      }
      const hex = normalizeHex(v);
      if (!hex) continue;
      const snapped = nearestColor(hex, palColors);
      if (snapped !== hex) {
        el.setAttribute(attr, snapped);
        report.colors_snapped += 1;
      }
    }
    let style = el.getAttribute("style");
    if (style && STYLE_BAD.test(style)) {
      el.removeAttribute("style");
      report.nodes_removed += 1;
    }
    for (const child of el.children) walk(child);
  };
  walk(root);

  return { svg: new XMLSerializer().serializeToString(root), report };
}

export function validate(svgText, { minLayers = 3, requireRole = true } = {}) {
  const errors = [];
  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  if (doc.querySelector("parsererror")) { errors.push({ code: "PARSE", message: "SVG is not well-formed" }); return errors; }
  const root = doc.documentElement;
  if (root.localName !== "svg") { errors.push({ code: "ROOT", message: "Root is not <svg>" }); return errors; }
  if (!root.getAttribute("viewBox")) errors.push({ code: "VIEWBOX", message: "Missing viewBox" });
  for (const tag of ["linearGradient", "radialGradient", "filter", "mask", "image", "foreignObject", "pattern"]) {
    if (root.querySelector(tag)) errors.push({ code: "FORBIDDEN_TAG", message: `<${tag}> still present` });
  }
  if (requireRole && root.querySelectorAll("[data-role]").length === 0)
    errors.push({ code: "NO_ROLES", message: "No data-role anywhere" });
  const layers = new Set();
  root.querySelectorAll("[data-layer]").forEach(el => layers.add(el.getAttribute("data-layer")));
  if (layers.size < minLayers)
    errors.push({ code: "FEW_LAYERS", message: `Only ${layers.size} layers, need ≥${minLayers}` });
  return errors;
}

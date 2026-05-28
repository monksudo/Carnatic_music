// Palettes mirroring studio/style/palettes.py — keep the order of the keys
// identical so JS and Python agree on what "highlight/light/mid/base/shadow"
// mean.

export const PALETTES = {
  dusk: {
    name: "Dusk", description: "Cool indigo/teal sky.",
    highlight: "#e8f0ff", light: "#a8c0ee", mid: "#5d7bc7",
    base: "#2c3a6b", shadow: "#161d3a",
    accent_a: "#f5a623", accent_b: "#22d3ee",
    background: "#0e1117", ink: "#0b0f1a",
  },
  forest: {
    name: "Forest", description: "Sage/pine layered greens.",
    highlight: "#ecfccb", light: "#a3e635", mid: "#4d7c0f",
    base: "#1f3a1f", shadow: "#0c1f0c",
    accent_a: "#fbbf24", accent_b: "#22d3ee",
    background: "#f6faf2", ink: "#0a1408",
  },
  terracotta: {
    name: "Terracotta", description: "Warm earth-tone clay.",
    highlight: "#fff1e6", light: "#fbb88a", mid: "#d97757",
    base: "#7c3a1f", shadow: "#3a1b0c",
    accent_a: "#0ea5e9", accent_b: "#facc15",
    background: "#fdf6ef", ink: "#2a1409",
  },
  cobalt: {
    name: "Cobalt", description: "Electric blue with neon accents.",
    highlight: "#dbeafe", light: "#60a5fa", mid: "#2563eb",
    base: "#1e1b4b", shadow: "#0b0a24",
    accent_a: "#f472b6", accent_b: "#34d399",
    background: "#0a0e1f", ink: "#04060d",
  },
  mono: {
    name: "Monochrome", description: "Neutral grayscale layers.",
    highlight: "#ffffff", light: "#d4d4d8", mid: "#71717a",
    base: "#27272a", shadow: "#0a0a0a",
    accent_a: "#ef4444", accent_b: "#22d3ee",
    background: "#fafafa", ink: "#000000",
  },
  candy: {
    name: "Candy", description: "Pastel pinks & mints.",
    highlight: "#fff0f6", light: "#fbcfe8", mid: "#ec4899",
    base: "#831843", shadow: "#3f0a23",
    accent_a: "#a7f3d0", accent_b: "#fde68a",
    background: "#fff7fb", ink: "#1a0a13",
  },
  slate: {
    name: "Slate", description: "Cool blue-gray architecture palette.",
    highlight: "#f1f5f9", light: "#cbd5e1", mid: "#64748b",
    base: "#1e293b", shadow: "#0b1220",
    accent_a: "#f59e0b", accent_b: "#10b981",
    background: "#f8fafc", ink: "#020617",
  },
};

export const RAMP_STOPS = ["shadow", "base", "mid", "light", "highlight"];
export const ALL_STOPS = [...RAMP_STOPS, "accent_a", "accent_b", "background", "ink"];

// Same data-layer → stop mapping as studio/style/recolor.py.
export const LAYER_TO_STOP = { 0: "shadow", 1: "base", 2: "mid", 3: "light", 4: "highlight", 5: "highlight", 6: "highlight" };

export function palette(id) {
  const p = PALETTES[id];
  if (!p) throw new Error(`unknown palette ${id}`);
  return p;
}

export function paletteColors(p) {
  return ALL_STOPS.map(k => p[k]);
}

// --- nearest color via OKLab ΔE — matches studio/style/palettes.py ---

function hexToRgb(h) {
  h = (h || "").trim().replace(/^#/, "");
  if (h.length === 3) h = h.split("").map(c => c + c).join("");
  if (h.length !== 6) return null;
  return [parseInt(h.slice(0, 2), 16) / 255, parseInt(h.slice(2, 4), 16) / 255, parseInt(h.slice(4, 6), 16) / 255];
}
function srgbToLinear(c) { return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
function rgbToOklab([r, g, b]) {
  r = srgbToLinear(r); g = srgbToLinear(g); b = srgbToLinear(b);
  const l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b;
  const m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b;
  const s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b;
  const l_ = Math.cbrt(l), m_ = Math.cbrt(m), s_ = Math.cbrt(s);
  return [
    0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
    1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
    0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
  ];
}
export function nearestColor(target, candidates) {
  const t = rgbToOklab(hexToRgb(target));
  let best = candidates[0], bestD = Infinity;
  for (const c of candidates) {
    const co = rgbToOklab(hexToRgb(c));
    const d = (t[0] - co[0]) ** 2 + (t[1] - co[1]) ** 2 + (t[2] - co[2]) ** 2;
    if (d < bestD) { best = c; bestD = d; }
  }
  return best;
}

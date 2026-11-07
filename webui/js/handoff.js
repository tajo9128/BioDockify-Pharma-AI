/**
 * BioDockify inter-module handoff system.
 * Additive-only: no core files touched. Loaded via <script> include in
 * participating components, or lazily on first use.
 *
 * Usage:  window.sendToModule("admet-predict", { smiles: "CCO" })
 *         sendHandoffBar("CCO", ["admet", "dock", "retro"])  → returns HTML string
 */

// Store-name map: window id → Alpine store name
const _STORE = {
  "molecular-toolkit": "molecularToolkit",
  "admet-predict": "admetPredict",
  "qsar3d": "qsar3d",
  "reaction-lab": "reactionLab",
  "retrosynthesis": "retroSyn",
  "generative-chemistry": "genChem",
  "bioactivity": "bioactivity",
  "pharmacophore": "pharmacophore",
  "netpharm-pro": "netpro",
};

// Which store-fields each target accepts from a handoff
const _FIELDS = {
  "molecular-toolkit": (p) => ({ dockingLigand: p.smiles }),
  "admet-predict": (p) => ({ smiles: p.smiles }),
  "qsar3d": (p) => ({ smilesInput: p.smiles }),
  "reaction-lab": (p) => ({ reactantsText: p.reactants || p.smiles }),
  "retrosynthesis": (p) => ({ targetSmiles: p.smiles, activeTab: "plan" }),
  "generative-chemistry": (p) => ({ seedSmiles: p.smiles, activeTab: "design" }),
  "bioactivity": (p) => ({ predictSmiles: p.smiles, activeTab: "predict" }),
  "pharmacophore": (p) => ({ smiles: p.smiles, activeTab: "features" }),
  "netpharm-pro": (p) => ({}),
};

/** Send a payload to another module: sets its store fields + opens its window. */
window.sendToModule = function (targetId, payload) {
  try {
    const ws = window.Alpine?.store("desktopWorkspace");
    if (ws) ws.openWindow(targetId);
    const storeName = _STORE[targetId];
    if (storeName) {
      let tries = 0;
      const apply = () => {
        const store = window.Alpine?.store(storeName);
        if (store) {
          const fields = (_FIELDS[targetId] || ((p) => ({})))(payload || {});
          Object.entries(fields).forEach(([k, v]) => {
            if (v !== undefined && v !== null && k in store) store[k] = v;
          });
        } else if (tries++ < 20) {
          setTimeout(apply, 300); // wait for component to load + register store
        }
      };
      apply();
    }
    return true;
  } catch (e) {
    console.warn("handoff failed:", e);
    return false;
  }
};

// ── HTML action-bar builder (inline styles — no CSS injection needed) ────────
const _ACTIONS = {
  admet:   { label: "→ ADMET",    target: "admet-predict",      icon: "medication" },
  dock:    { label: "→ Dock",     target: "molecular-toolkit",  icon: "precision_manufacturing" },
  qsar:    { label: "→ QSAR",     target: "qsar3d",             icon: "model_training" },
  retro:   { label: "→ Retro",    target: "retrosynthesis",     icon: "alt_route" },
  react:   { label: "→ React",    target: "reaction-lab",       icon: "science" },
  genchem: { label: "→ Design",   target: "generative-chemistry", icon: "auto_awesome" },
  bioact:  { label: "→ BioAct",   target: "bioactivity",        icon: "insights" },
  pharma:  { label: "→ Phar'more", target: "pharmacophore",     icon: "ads_click" },
};

/**
 * Build a compact handoff bar HTML for a SMILES payload.
 * sendHandoffBar("CCO") → all default targets
 * sendHandoffBar("CCO", ["admet", "dock"]) → only those two
 */
window.sendHandoffBar = function (smiles, actions, extraPayload = {}) {
  if (!smiles) return "";
  const keys = (actions && actions.length) ? actions : ["admet", "dock", "retro", "react"];
  const btns = keys.filter((k) => _ACTIONS[k]).map((k) => {
    const a = _ACTIONS[k];
    return `<button onclick="sendToModule('${a.target}', { smiles: '${smiles.replace(/'/g, "\\'")}', ...${JSON.stringify(extraPayload)} })"
      style="display:inline-flex;align-items:center;gap:3px;padding:4px 10px;margin:2px 3px 2px 0;background:color-mix(in srgb, var(--color-primary) 8%, var(--color-panel));border:1px solid color-mix(in srgb, var(--color-primary) 25%, var(--color-border));border-radius:6px;color:var(--color-primary);cursor:pointer;font-size:0.6rem;font-weight:600;white-space:nowrap"
      onmouseover="this.style.background='color-mix(in srgb, var(--color-primary) 15%, var(--color-panel))'"
      onmouseout="this.style.background='color-mix(in srgb, var(--color-primary) 8%, var(--color-panel))'">
      <span class="material-symbols-outlined" style="font-size:13px">${a.icon}</span>${a.label}</button>`;
  }).join("");
  return `<div style="display:flex;align-items:center;gap:2px;flex-wrap:wrap;padding-top:6px;border-top:1px dotted var(--color-border);margin-top:6px">${btns}</div>`;
};

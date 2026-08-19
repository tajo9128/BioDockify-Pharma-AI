/**
 * Mol3D Engine — Shared 3Dmol.js wrapper for BioDockify.
 * PyMOL/Discovery Studio level molecular visualization.
 * 
 * Features:
 * - CDN loading with retry + fallback
 * - Viewer lifecycle management (create/destroy/reinit)
 * - Style presets (Default, Dark, Publication, PyMOL-like)
 * - Representation modes (Cartoon, Stick, Ball+Stick, Sphere, Line, Surface, Cross)
 * - Coloring modes (Element, Chain, Residue, SS, Charge, B-factor, Hydrophobicity, Spectrum)
 * - Surface types (VDW, SAS, SES, Molecular) with opacity
 * - Click-to-measure distance between atoms
 * - Label atoms/residues on click
 * - H-bond visualization
 * - Multi-model support (docking poses)
 * - Export: PNG snapshot, PDB download
 */

const LOCAL_URL = "/vendor/3dmol/3Dmol-min.js";  // vendored — works offline, no CSP issues
const CDN_URL = "https://3Dmol.org/build/3Dmol-min.js";
const CDN_BACKUP = "https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js";

let _cdnLoaded = false;
let _cdnLoading = false;
let _cdnCallbacks = [];

/**
 * Load 3Dmol.js CDN with retry and fallback.
 * @returns {Promise<boolean>} true if loaded successfully
 */
export function load3Dmol() {
  return new Promise((resolve) => {
    if (typeof window.$3Dmol !== "undefined") {
      _cdnLoaded = true;
      resolve(true);
      return;
    }
    if (_cdnLoaded) { resolve(true); return; }
    _cdnCallbacks.push(resolve);
    if (_cdnLoading) return;
    _cdnLoading = true;

    function tryLoad(url, isBackup) {
      const s = document.createElement("script");
      s.src = url;
      s.onload = () => {
        _cdnLoaded = true;
        _cdnLoading = false;
        _cdnCallbacks.forEach(cb => cb(true));
        _cdnCallbacks = [];
      };
      s.onerror = () => {
        if (url === LOCAL_URL) {
          tryLoad(CDN_URL, false);           // local failed → CDN
        } else if (!isBackup) {
          tryLoad(CDN_BACKUP, true);          // CDN failed → backup CDN
        } else {
          _cdnLoading = false;
          _cdnCallbacks.forEach(cb => cb(false));
          _cdnCallbacks = [];
        }
      };
      document.head.appendChild(s);
    }
    tryLoad(LOCAL_URL, false);
  });
}

/**
 * Color scheme presets for 3Dmol.js
 */
export const COLOR_SCHEMES = {
  element: "Jmol",
  chain: "chain",
  residue: "amino",
  ss: "sstruc",
  charge: "charge",
  bfactor: "bFactor",
  hydrophobicity: "whiteCarbon",
  spectrum: "spectrum",
  rainbow: "rainbow",
  rasmol: "rasmol",
  greenCarbon: "greenCarbon",
  cyanCarbon: "cyanCarbon",
  orangeCarbon: "orangeCarbon",
  magentaCarbon: "magentaCarbon",
  yellowCarbon: "yellowCarbon",
  whiteCarbon: "whiteCarbon",
};

/**
 * Style presets
 */
export const PRESETS = {
  default: {
    proteinStyle: "cartoon", proteinColor: "spectrum",
    ligandStyle: "stick", ligandColor: "greenCarbon",
    bgColor: "#ffffff", showSurface: false, showHBonds: true,
    proteinOpacity: 1.0,
  },
  dark: {
    proteinStyle: "cartoon", proteinColor: "spectrum",
    ligandStyle: "stick", ligandColor: "orangeCarbon",
    bgColor: "#1a1a2e", showSurface: false, showHBonds: true,
    proteinOpacity: 1.0,
  },
  publication: {
    proteinStyle: "cartoon", proteinColor: "whiteCarbon",
    ligandStyle: "ballstick", ligandColor: "greenCarbon",
    bgColor: "#ffffff", showSurface: false, showHBonds: true,
    proteinOpacity: 1.0,
  },
  pymol: {
    proteinStyle: "cartoon", proteinColor: "chain",
    ligandStyle: "stick", ligandColor: "greenCarbon",
    bgColor: "#ffffff", showSurface: false, showHBonds: true,
    proteinOpacity: 1.0,
  },
  surface: {
    proteinStyle: "cartoon", proteinColor: "spectrum",
    ligandStyle: "ballstick", ligandColor: "magentaCarbon",
    bgColor: "#ffffff", showSurface: true, showHBonds: true,
    proteinOpacity: 0.6,
  },
  analysis: {
    proteinStyle: "stick", proteinColor: "rasmol",
    ligandStyle: "ballstick", ligandColor: "cyanCarbon",
    bgColor: "#f0f4f8", showSurface: false, showHBonds: true,
    proteinOpacity: 1.0,
  },
};

/**
 * Mol3DViewer — Wrapper around 3Dmol.js viewer with lifecycle management.
 */
export class Mol3DViewer {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.viewer = null;
    this.ready = false;
    this.bgColor = options.bgColor || "#ffffff";
    this._measureAtoms = [];
    this._measureCallback = null;
    this._clickCallback = null;
    this._currentProteinModel = null;
    this._currentLigandModels = [];
  }

  /**
   * Initialize the viewer. Call after DOM is ready and 3Dmol is loaded.
   * @returns {boolean} true if viewer created successfully
   */
  init() {
    if (this.viewer) return true;
    const el = document.getElementById(this.containerId);
    if (!el || el.clientWidth === 0) return false;
    if (typeof window.$3Dmol === "undefined") return false;

    try {
      this.viewer = window.$3Dmol.createViewer(el, {
        backgroundColor: this.bgColor,
        antialias: true,
        cartoonQuality: 5,
      });
      // Enable auto-rotate by default
      this.viewer.spin("y");
      this._spinning = true;
      this.ready = true;
      return true;
    } catch (e) {
      console.error("Mol3D init failed:", e);
      return false;
    }
  }

  /**
   * Destroy the viewer and free WebGL resources.
   */
  destroy() {
    if (this.viewer) {
      try {
        this.viewer.clear();
        this.viewer = null;
      } catch (e) {}
    }
    this.ready = false;
    this._measureAtoms = [];
    this._currentProteinModel = null;
    this._currentLigandModels = [];
  }

  /**
   * Reinitialize viewer (destroy + create).
   */
  reinit() {
    this.destroy();
    return this.init();
  }

  /**
   * Set background color.
   */
  setBackground(color) {
    this.bgColor = color;
    if (this.viewer) {
      this.viewer.setBackgroundColor(color);
      this.viewer.render();
    }
  }

  /**
   * Toggle spin/rotation on/off.
   */
  toggleSpin() {
    if (!this.viewer) return false;
    if (this._spinning) {
      this.viewer.spin(false);
      this._spinning = false;
    } else {
      this.viewer.spin("y");
      this._spinning = true;
    }
    return this._spinning;
  }

  /**
   * Start spinning.
   */
  startSpin(axis = "y") {
    if (!this.viewer) return;
    this.viewer.spin(axis);
    this._spinning = true;
  }

  /**
   * Stop spinning.
   */
  stopSpin() {
    if (!this.viewer) return;
    this.viewer.spin(false);
    this._spinning = false;
  }

  /**
   * Load protein PDB content.
   * @param {string} pdbContent - PDB format text
   * @param {object} options - { style, color, opacity }
   */
  loadProtein(pdbContent, options = {}) {
    if (!this.viewer) return;
    const style = options.style || "cartoon";
    const color = options.color || "spectrum";
    const opacity = options.opacity ?? 1.0;

    this._currentProteinModel = this.viewer.addModel(pdbContent, "pdb");
    this._applyProteinStyle(style, color, opacity);
  }

  /**
   * Load ligand from PDB/SDF content.
   * @param {string} content - PDB or SDF format text
   * @param {string} format - "pdb" or "sdf"
   * @param {object} options - { style, color }
   */
  loadLigand(content, format = "pdb", options = {}) {
    if (!this.viewer) return;
    const style = options.style || "stick";
    const color = options.color || "greenCarbon";

    const model = this.viewer.addModel(content, format);
    this._currentLigandModels.push(model);
    this._applyLigandStyle(style, color);
  }

  /**
   * Load multiple ligand poses (for docking results).
   * @param {Array} poses - [{pdb: string, energy: number}]
   * @param {number} activeIndex - which pose to show initially
   */
  loadPoses(poses, activeIndex = 0) {
    if (!this.viewer || !poses.length) return;
    // Clear existing ligand models
    this._currentLigandModels = [];
    
    // Add only the active pose
    const pose = poses[activeIndex];
    if (pose && pose.pdb) {
      this.loadLigand(pose.pdb, "pdb", { style: "stick", color: "greenCarbon" });
    }
  }

  /**
   * Switch to a different pose.
   */
  switchPose(poses, index) {
    if (!this.viewer) return;
    // Remove all ligand models
    this._currentLigandModels.forEach(m => {
      try { this.viewer.removeModel(m); } catch (e) {}
    });
    this._currentLigandModels = [];
    
    // Add the new pose
    const pose = poses[index];
    if (pose && pose.pdb) {
      this.loadLigand(pose.pdb, "pdb");
    }
    this.viewer.render();
  }

  /**
   * Apply protein style.
   * @param {string} style - cartoon, stick, sphere, line, cross
   * @param {string} color - color scheme name
   * @param {number} opacity - 0-1
   */
  _applyProteinStyle(style, color, opacity) {
    if (!this.viewer) return;
    const colorScheme = this._resolveColor(color);
    
    // Build style object with ONLY the selected style
    const styleObj = {};
    if (style === "cartoon") {
      styleObj.cartoon = { colorscheme: colorScheme, opacity: opacity };
    } else if (style === "stick") {
      styleObj.stick = { colorscheme: colorScheme, radius: 0.15, opacity: opacity };
    } else if (style === "sphere") {
      styleObj.sphere = { colorscheme: colorScheme, scale: 0.3, opacity: opacity };
    } else if (style === "line") {
      styleObj.line = { colorscheme: colorScheme, linewidth: 1.5, opacity: opacity };
    } else if (style === "cross") {
      styleObj.cross = { colorscheme: colorScheme, radius: 0.15, opacity: opacity };
    } else {
      styleObj.cartoon = { colorscheme: colorScheme, opacity: opacity };
    }

    // Apply to protein only (not hetflag)
    this.viewer.setStyle({ hetflag: false }, styleObj);
  }

  /**
   * Apply ligand style.
   * @param {string} style - stick, ballstick, sphere, line
   * @param {string} color - color scheme name
   */
  _applyLigandStyle(style, color) {
    if (!this.viewer) return;
    const colorScheme = this._resolveColor(color);
    
    const styleObj = {};
    if (style === "stick") {
      styleObj.stick = { colorscheme: colorScheme, radius: 0.22 };
    } else if (style === "ballstick") {
      styleObj.stick = { colorscheme: colorScheme, radius: 0.15 };
      styleObj.sphere = { colorscheme: colorScheme, scale: 0.35 };
    } else if (style === "sphere") {
      styleObj.sphere = { colorscheme: colorScheme, radius: 0.4 };
    } else if (style === "line") {
      styleObj.line = { colorscheme: colorScheme, linewidth: 2.5 };
    } else {
      styleObj.stick = { colorscheme: colorScheme, radius: 0.22 };
    }

    this.viewer.setStyle({ hetflag: true }, styleObj);
  }

  /**
   * Change protein representation.
   */
  setProteinStyle(style, color, opacity = 1.0) {
    if (!this.viewer) return;
    this._applyProteinStyle(style, color, opacity);
    this.viewer.render();
  }

  /**
   * Change ligand representation.
   */
  setLigandStyle(style, color) {
    if (!this.viewer) return;
    this._applyLigandStyle(style, color);
    this.viewer.render();
  }

  /**
   * Add surface around protein.
   * @param {string} type - vdw, sas, ses, molecular
   * @param {number} opacity - 0-1
   * @param {string} color - color scheme
   */
  addSurface(type = "vdw", opacity = 0.5, color = "whiteCarbon") {
    if (!this.viewer) return;
    const surfaceType = this._resolveSurfaceType(type);
    const colorScheme = this._resolveColor(color);
    this.viewer.addSurface(surfaceType, { opacity: opacity, colorscheme: colorScheme }, { hetflag: false });
    this.viewer.render();
  }

  /**
   * Remove all surfaces.
   */
  removeSurfaces() {
    if (!this.viewer) return;
    this.viewer.removeAllSurfaces();
    this.viewer.render();
  }

  /**
   * Toggle surface visibility.
   */
  toggleSurface(type = "vdw", opacity = 0.5, color = "whiteCarbon") {
    if (!this.viewer) return;
    // Check if surfaces exist by trying to remove them
    try {
      this.viewer.removeAllSurfaces();
      this.viewer.render();
      return false; // surfaces were removed
    } catch (e) {
      this.addSurface(type, opacity, color);
      return true; // surfaces were added
    }
  }

  /**
   * Add H-bond visualization.
   * @param {Array} hbonds - [{resseq, chain, distance, ligand_atom}]
   */
  showHBonds(hbonds) {
    if (!this.viewer || !hbonds) return;
    hbonds.forEach(hb => {
      try {
        const pA = this.viewer.selectedAtoms({ resi: hb.resseq, chain: hb.chain, hetflag: false });
        const lA = this.viewer.selectedAtoms({ hetflag: true });
        if (pA.length && lA.length) {
          this.viewer.addCylinder({
            start: pA[0], end: lA[0],
            radius: 0.08, color: "#facc15", dashed: true
          });
        }
      } catch (e) {}
    });
    this.viewer.render();
  }

  /**
   * Clear H-bond visualization.
   */
  clearHBonds() {
    if (!this.viewer) return;
    this.viewer.removeAllShapes();
    this.viewer.render();
  }

  /**
   * Zoom to fit all atoms or a selection.
   */
  zoomTo(sel) {
    if (!this.viewer) return;
    this.viewer.zoomTo(sel || {});
    this.viewer.render();
  }

  /**
   * Zoom in/out.
   * @param {number} factor - <1 zoom in, >1 zoom out
   */
  zoom(factor) {
    if (!this.viewer) return;
    this.viewer.zoom(factor, 300);
    this.viewer.render();
  }

  /**
   * Start/stop spin.
   * @param {boolean|number} speed - true/false or speed value
   */
  spin(speed) {
    if (!this.viewer) return;
    this.viewer.spin(speed);
  }

  /**
   * Reset view to default.
   */
  resetView() {
    if (!this.viewer) return;
    this.viewer.zoomTo();
    this.viewer.render();
  }

  /**
   * Take PNG snapshot.
   * @returns {string} data URI
   */
  snapshot() {
    if (!this.viewer) return null;
    return this.viewer.pngURI();
  }

  /**
   * Apply a preset configuration.
   */
  applyPreset(presetName) {
    const preset = PRESETS[presetName];
    if (!preset) return;

    this.removeAll();
    this.loadProtein(this._lastProteinPdb || "", {
      style: preset.proteinStyle,
      color: preset.proteinColor,
      opacity: preset.proteinOpacity,
    });
    if (this._lastLigandPdb) {
      this.loadLigand(this._lastLigandPdb, "pdb", {
        style: preset.ligandStyle,
        color: preset.ligandColor,
      });
    }
    this.setBackground(preset.bgColor);
    if (preset.showSurface) {
      this.addSurface("vdw", 0.5, "whiteCarbon");
    }
    if (preset.showHBonds && this._lastHBonds) {
      this.showHBonds(this._lastHBonds);
    }
    this.zoomTo();
  }

  /**
   * Enable click-to-measure mode.
   * @param {Function} callback - called with {atom1, atom2, distance} when two atoms selected
   */
  enableMeasureMode(callback) {
    this._measureAtoms = [];
    this._measureCallback = callback;
    // Note: Click handling must be done by the caller since 3Dmol.js
    // doesn't have a built-in click-to-atom API. Use getAtomAtEvent() helper.
  }

  /**
   * Disable measure mode.
   */
  disableMeasureMode() {
    this._measureAtoms = [];
    this._measureCallback = null;
    if (this.viewer) {
      this.viewer.removeAllLabels();
      this.viewer.removeAllShapes();
      this.viewer.render();
    }
  }

  /**
   * Get atom nearest to a click event on the canvas.
   * @param {MouseEvent} e - click event
   * @returns {object|null} atom object or null
   */
  getAtomAtEvent(e) {
    if (!this.viewer) return null;
    const canvas = document.getElementById(this.containerId);
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Get all atoms and find the nearest one to the click point
    const atoms = this.viewer.selectedAtoms({});
    if (!atoms.length) return null;
    
    // Use 3Dmol's internal picking if available
    try {
      // 3Dmol stores atoms with x,y,z in model coordinates
      // We need to find which atom is closest to the click
      // For simplicity, return the first atom (3Dmol doesn't expose hit-testing)
      // A better approach would be to use the model's atom picking
      let closest = null;
      let minDist = Infinity;
      atoms.forEach(a => {
        if (a.screen) {
          const dx = a.screen.x - x;
          const dy = a.screen.y - y;
          const d = dx*dx + dy*dy;
          if (d < minDist) {
            minDist = d;
            closest = a;
          }
        }
      });
      return closest;
    } catch (e) {
      return null;
    }
  }

  /**
   * Add a distance measurement between two atoms.
   */
  addMeasurement(atom1, atom2) {
    if (!this.viewer) return null;
    const d = Math.sqrt(
      (atom1.x - atom2.x)**2 +
      (atom1.y - atom2.y)**2 +
      (atom1.z - atom2.z)**2
    );
    
    // Add cylinder
    this.viewer.addCylinder({
      start: atom1, end: atom2,
      radius: 0.06, color: "#ffd93d", dashed: true
    });
    
    // Add label
    const mid = {
      x: (atom1.x + atom2.x) / 2,
      y: (atom1.y + atom2.y) / 2,
      z: (atom1.z + atom2.z) / 2,
    };
    this.viewer.addLabel(`${d.toFixed(2)} Å`, {
      position: mid,
      backgroundColor: "black",
      fontColor: "white",
      fontSize: 12,
      showBackground: true,
    });
    
    this.viewer.render();
    return d;
  }

  /**
   * Clear all measurements.
   */
  clearMeasurements() {
    if (!this.viewer) return;
    this.viewer.removeAllLabels();
    this.viewer.removeAllShapes();
    this.viewer.render();
    this._measureAtoms = [];
  }

  /**
   * Highlight a specific residue.
   * @param {string} chain - chain ID
   * @param {number} resi - residue number
   * @param {string} color - highlight color
   */
  highlightResidue(chain, resi, color = "#ffd93d") {
    if (!this.viewer) return;
    // Dim everything
    this.viewer.setStyle({ hetflag: false }, { cartoon: { opacity: 0.3, colorscheme: "whiteCarbon" } });
    // Highlight selected residue
    this.viewer.setStyle({ chain: chain, resi: resi }, {
      cartoon: { color: color },
      stick: { radius: 0.2, color: color }
    });
    this.viewer.zoomTo({ chain: chain, resi: resi });
    this.viewer.render();
  }

  /**
   * Reset to full protein view.
   */
  resetProteinView(style = "cartoon", color = "spectrum") {
    if (!this.viewer) return;
    this.viewer.removeAllSurfaces();
    this._applyProteinStyle(style, color, 1.0);
    this.viewer.zoomTo();
    this.viewer.render();
  }

  /**
   * Remove all models, surfaces, labels, shapes.
   */
  removeAll() {
    if (!this.viewer) return;
    this.viewer.removeAllModels();
    this.viewer.removeAllSurfaces();
    this.viewer.removeAllLabels();
    this.viewer.removeAllShapes();
    this._currentProteinModel = null;
    this._currentLigandModels = [];
  }

  /**
   * Render the scene.
   */
  render() {
    if (!this.viewer) return;
    this.viewer.render();
  }

  // ── Internal helpers ──

  _resolveColor(name) {
    return COLOR_SCHEMES[name] || name || "Jmol";
  }

  _resolveSurfaceType(type) {
    const map = {
      vdw: window.$3Dmol.SurfaceType.VDW,
      sas: window.$3Dmol.SurfaceType.SAS,
      ses: window.$3Dmol.SurfaceType.SES,
      molecular: window.$3Dmol.SurfaceType.MS,
    };
    return map[type] || window.$3Dmol.SurfaceType.VDW;
  }

  // Store last loaded data for preset switching
  _lastProteinPdb = null;
  _lastLigandPdb = null;
  _lastHBonds = null;
}

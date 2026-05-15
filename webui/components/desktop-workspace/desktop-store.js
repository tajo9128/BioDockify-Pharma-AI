import { createStore } from "/js/AlpineStore.js";

const STORAGE_KEY = "a0.desktopWorkspace";

function generateId() {
  return "win-" + Date.now() + "-" + Math.random().toString(36).substr(2, 9);
}

const defaultModules = [
  { id: "desktop", title: "Kali Desktop", icon: "desktop_windows", component: "/components/desktop/desktop-panel.html", order: 1, defaultWidth: 900, defaultHeight: 600 },
  { id: "research-dashboard", title: "Research Command Center", icon: "science", component: "/components/research-dashboard/research-dashboard.html", order: 2, defaultWidth: 800, defaultHeight: 600 },
  { id: "molecular-toolkit", title: "Molecular Toolkit", icon: "biotech", component: "/components/molecular-toolkit/molecular-toolkit.html", order: 3, defaultWidth: 700, defaultHeight: 550 },
  { id: "system-health", title: "System Health", icon: "monitoring", component: "/components/system-health/system-health.html", order: 15, defaultWidth: 500, defaultHeight: 500 },
  { id: "research", title: "All Tools", icon: "apps", component: "/components/research/research-tools.html", order: 3, defaultWidth: 700, defaultHeight: 500 },
  { id: "statistics", title: "Statistics", icon: "analytics", component: "/components/statistics/statistics-modal.html", order: 4, defaultWidth: 750, defaultHeight: 550 },
  { id: "drug-properties", title: "Drug Properties", icon: "medication", component: "/components/drug-properties/drug-properties-panel.html", order: 5, defaultWidth: 650, defaultHeight: 450 },
  { id: "literature", title: "Literature", icon: "menu_book", component: "/components/literature/literature-modal.html", order: 6, defaultWidth: 700, defaultHeight: 500 },
  { id: "patent-analyzer", title: "Patent Analyzer", icon: "gavel", component: "/components/patent-analyzer/patent-panel.html", order: 7, defaultWidth: 750, defaultHeight: 500 },
  { id: "knowledge", title: "Knowledge Base", icon: "psychology", component: "/components/knowledge/knowledge-modal.html", order: 8, defaultWidth: 700, defaultHeight: 500 },
  { id: "thesis", title: "Academic Writer", icon: "description", component: "/components/thesis/thesis-modal.html", order: 9, defaultWidth: 700, defaultHeight: 500 },
  { id: "slides", title: "Slides", icon: "slideshow", component: "/components/slides/slides-modal.html", order: 10, defaultWidth: 700, defaultHeight: 500 },
  { id: "wetlab", title: "Wet Lab", icon: "biotech", component: "/components/wetlab/wetlab-modal.html", order: 11, defaultWidth: 700, defaultHeight: 500 },
  { id: "lecture-builder", title: "Lecture Builder", icon: "school", component: "/components/lecture-builder/lecture-panel.html", order: 12, defaultWidth: 700, defaultHeight: 500 },
  { id: "backup", title: "Backup", icon: "backup", component: "/components/backup-recovery/recovery-panel.html", order: 13, defaultWidth: 650, defaultHeight: 450 },
];

const model = {
  desktopLayout: 'chat',
  windows: [],
  activeWindowId: null,
  nextZIndex: 100,
  startMenuOpen: false,
  taskbarPinned: ["desktop", "research-dashboard", "research", "statistics", "knowledge"],
  _searchQuery: "",
  _initialized: false,

  get isChatMode() { return this.desktopLayout === 'chat'; },
  get isSplitMode() { return this.desktopLayout === 'split'; },
  get isDesktopMode() { return this.desktopLayout === 'desktop'; },

  cycleLayout() {
    const modes = ['chat', 'split', 'desktop'];
    const idx = modes.indexOf(this.desktopLayout);
    this.desktopLayout = modes[(idx + 1) % modes.length];
    this.persist();
  },

  setChatMode() {
    this.desktopLayout = 'chat';
    this.persist();
  },

  getDesktopAreaBounds() {
    const el = document.querySelector('.desktop-area');
    if (!el) return { w: window.innerWidth - 100, h: window.innerHeight - 148 };
    const r = el.getBoundingClientRect();
    return { w: r.width - 100, h: r.height - 148 };
  },

  init() {
    if (this._initialized) return;
    this._initialized = true;
    this.restore();
  },

  toggleDesktopMode() {
    this.cycleLayout();
  },

  openWindow(moduleId) {
    const module = defaultModules.find(m => m.id === moduleId);
    if (!module) return;

    if (this.desktopLayout === 'chat') {
      this.desktopLayout = 'split';
      this.persist();
    }

    const existing = this.windows.find(w => w.moduleId === moduleId && !w.closed);
    if (existing) {
      this.focusWindow(existing.id);
      if (existing.minimized) {
        existing.minimized = false;
      }
      return;
    }

    const bounds = this.getDesktopAreaBounds();
    const availW = Math.max(300, bounds.w);
    const availH = Math.max(200, bounds.h);
    const w = Math.min(module.defaultWidth, availW);
    const h = Math.min(module.defaultHeight, availH);
    const x = Math.max(20, Math.floor((availW - w) / 2) + Math.random() * 40 - 20);
    const y = Math.max(20, Math.floor((availH - h) / 2) + Math.random() * 40 - 20);

    const win = {
      id: generateId(),
      moduleId: module.id,
      title: module.title,
      icon: module.icon,
      component: module.component,
      x, y,
      width: w,
      height: h,
      minWidth: 300,
      minHeight: 200,
      zIndex: this.nextZIndex++,
      minimized: false,
      maximized: false,
      closed: false,
      prevBounds: null,
    };

    this.windows.push(win);
    this.activeWindowId = win.id;
    this.startMenuOpen = false;
  },

  closeWindow(windowId) {
    const win = this.windows.find(w => w.id === windowId);
    if (win) {
      win.closed = true;
      if (this.activeWindowId === windowId) {
        const openWindows = this.windows.filter(w => !w.closed && !w.minimized);
        this.activeWindowId = openWindows.length > 0 ? openWindows[openWindows.length - 1].id : null;
      }
    }
  },

  minimizeWindow(windowId) {
    const win = this.windows.find(w => w.id === windowId);
    if (win) {
      win.minimized = true;
      if (this.activeWindowId === windowId) {
        const openWindows = this.windows.filter(w => !w.closed && !w.minimized);
        this.activeWindowId = openWindows.length > 0 ? openWindows[openWindows.length - 1].id : null;
      }
    }
  },

  maximizeWindow(windowId) {
    const win = this.windows.find(w => w.id === windowId);
    if (!win) return;

    if (win.maximized) {
      if (win.prevBounds) {
        win.x = win.prevBounds.x;
        win.y = win.prevBounds.y;
        win.width = win.prevBounds.width;
        win.height = win.prevBounds.height;
      }
      win.maximized = false;
    } else {
      win.prevBounds = { x: win.x, y: win.y, width: win.width, height: win.height };
      const bounds = this.getDesktopAreaBounds();
      win.x = 0;
      win.y = 0;
      win.width = Math.max(400, bounds.w + 100);
      win.height = Math.max(300, bounds.h + 100);
      win.maximized = true;
    }
  },

  focusWindow(windowId) {
    const win = this.windows.find(w => w.id === windowId);
    if (win) {
      win.zIndex = this.nextZIndex++;
      this.activeWindowId = windowId;
    }
  },

  moveWindow(windowId, x, y) {
    const win = this.windows.find(w => w.id === windowId);
    if (win && !win.maximized) {
      win.x = Math.round(x);
      win.y = Math.round(y);
    }
  },

  resizeWindow(windowId, width, height) {
    const win = this.windows.find(w => w.id === windowId);
    if (win && !win.maximized) {
      win.width = Math.max(win.minWidth, Math.round(width));
      win.height = Math.max(win.minHeight, Math.round(height));
    }
  },

  get visibleWindows() {
    return this.windows.filter(w => !w.closed && !w.minimized).sort((a, b) => a.zIndex - b.zIndex);
  },

  get taskbarWindows() {
    return this.windows.filter(w => !w.closed).sort((a, b) => a.zIndex - b.zIndex);
  },

  get activeWindow() {
    return this.windows.find(w => w.id === this.activeWindowId) || null;
  },

  get sortedModules() {
    return [...defaultModules].sort((a, b) => a.order - b.order);
  },

  isWindowPinned(moduleId) {
    return this.taskbarPinned.includes(moduleId);
  },

  togglePin(moduleId) {
    const idx = this.taskbarPinned.indexOf(moduleId);
    if (idx >= 0) {
      this.taskbarPinned.splice(idx, 1);
    } else {
      this.taskbarPinned.push(moduleId);
    }
    this.persist();
  },

  persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        desktopLayout: this.desktopLayout,
        taskbarPinned: this.taskbarPinned,
        splitRatio: this.splitRatio,
      }));
    } catch (e) {
      console.warn("Could not persist desktop workspace state", e);
    }
  },

  restore() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      if (saved.desktopLayout) this.desktopLayout = saved.desktopLayout;
      if (saved.taskbarPinned) this.taskbarPinned = saved.taskbarPinned;
      if (saved.splitRatio) this.splitRatio = saved.splitRatio;
    } catch (e) {
      console.warn("Could not restore desktop workspace state", e);
    }
    this._applySplitRatio();
  },

  splitRatio: 35,

  _applySplitRatio() {
    const container = document.querySelector('.container.split-mode');
    if (!container) return;
    const panel = document.getElementById('right-panel');
    const wrapper = document.getElementById('desktop-wrapper');
    if (panel) panel.style.flexBasis = this.splitRatio + '%';
    if (wrapper) wrapper.style.flexBasis = (100 - this.splitRatio) + '%';
  },

  resizeSplit(event) {
    const container = document.querySelector('.container.split-mode');
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const sidebarW = 250;
    const dividerW = 6;
    const availW = rect.width - sidebarW - dividerW;
    const x = event.clientX - rect.left - sidebarW;
    const pct = Math.max(20, Math.min(80, (x / availW) * 100));
    this.splitRatio = Math.round(pct);
    this._applySplitRatio();
  },

  startDrag(event, windowId) {
    const win = this.windows.find(w => w.id === windowId);
    if (!win || win.maximized) return;
    event.preventDefault();
    this.focusWindow(windowId);

    const startX = event.clientX;
    const startY = event.clientY;
    const origX = win.x;
    const origY = win.y;

    const onMove = (e) => {
      win.x = origX + (e.clientX - startX);
      win.y = Math.max(0, origY + (e.clientY - startY));
    };

    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    document.body.style.cursor = "move";
    document.body.style.userSelect = "none";
  },

  startResize(event, windowId) {
    const win = this.windows.find(w => w.id === windowId);
    if (!win || win.maximized) return;
    event.preventDefault();
    event.stopPropagation();

    const startX = event.clientX;
    const startY = event.clientY;
    const origW = win.width;
    const origH = win.height;

    const onMove = (e) => {
      win.width = Math.max(win.minWidth, origW + (e.clientX - startX));
      win.height = Math.max(win.minHeight, origH + (e.clientY - startY));
    };

    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    document.body.style.cursor = "nwse-resize";
    document.body.style.userSelect = "none";
  },
};

export const store = createStore("desktopWorkspace", model);

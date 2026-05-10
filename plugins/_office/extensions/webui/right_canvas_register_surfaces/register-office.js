import { store as officeStore } from "/plugins/_office/webui/office-store.js";

void officeStore;

function waitForElement(selector, timeoutMs = 10000) {
  const found = document.querySelector(selector);
  if (found) return Promise.resolve(found);
  return new Promise((resolve) => {
    const timeout = globalThis.setTimeout(() => {
      observer.disconnect();
      resolve(document.querySelector(selector));
    }, timeoutMs);
    const observer = new MutationObserver(() => {
      const element = document.querySelector(selector);
      if (!element) return;
      globalThis.clearTimeout(timeout);
      observer.disconnect();
      resolve(element);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });
}

export default async function registerOfficeSurface(canvas) {
  canvas.registerSurface({
    id: "office",
    title: "Desktop",
    icon: "desktop_windows",
    order: 20,
    modalPath: "/plugins/_office/webui/main.html",
    async beginDockHandoff() {
      const office = globalThis.Alpine?.store?.("office");
      office?.beforeDesktopHostHandoff?.();
    },
    async finishDockHandoff(payload = {}) {
      const office = globalThis.Alpine?.store?.("office");
      if (payload.opened !== false) office?.afterDesktopHostShown?.({ source: "dock" });
    },
    async cancelDockHandoff() {
      const office = globalThis.Alpine?.store?.("office");
      office?.cancelDesktopHostHandoff?.();
    },
    async open(payload = {}) {
      const panel = await waitForElement('[data-surface-id="office"] .office-panel');
      if (!panel) throw new Error("Office canvas panel did not mount.");
      const office = globalThis.Alpine?.store?.("office");
      await office?.onMount?.(panel, { mode: "canvas" });
      await office?.onOpen?.(payload);
      office?.afterDesktopHostShown?.({ source: payload?.source || "canvas" });
    },
    async close(payload = {}) {
      const office = globalThis.Alpine?.store?.("office");
      office?.beforeHostHidden?.({ unloadDesktop: payload?.reason === "mobile" });
    },
  });
}

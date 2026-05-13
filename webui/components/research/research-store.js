import { createStore } from "/js/AlpineStore.js";

function openResearchTool(surfaceId) {
  const canvas = globalThis.Alpine?.store("rightCanvas");
  if (canvas && typeof canvas.open === "function") {
    canvas.open(surfaceId);
  }
}

export const store = createStore("researchTools", {});

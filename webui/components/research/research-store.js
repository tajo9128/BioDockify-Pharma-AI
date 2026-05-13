import { createStore } from "/js/AlpineStore.js";

function openResearchTool(surfaceId) {
  const canvas = globalThis.Alpine?.store("rightCanvas");
  if (canvas && typeof canvas.open === "function") {
    canvas.open(surfaceId);
  } else {
    console.warn("rightCanvas store not available");
  }
}

export const store = createStore("researchTools", {
  init() {
    console.log("BioDockify Research Tools initialized");
  },

  async openStatistics() {
    openResearchTool("statistics");
  },

  async openLiterature() {
    openResearchTool("literature");
  },

  async openThesis() {
    openResearchTool("thesis");
  },

  async openSlides() {
    openResearchTool("slides");
  },

  async openWetLab() {
    openResearchTool("wetlab");
  },

  async openKnowledge() {
    openResearchTool("knowledge");
  }
});
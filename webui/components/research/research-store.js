import { createStore } from "/js/AlpineStore.js";

export const store = createStore("researchTools", {
  init() {
    console.log("BioDockify Research Tools initialized");
  },

  async openStatistics() {
    openModal("components/statistics/statistics-modal.html");
  },

  async openLiterature() {
    openModal("components/literature/literature-modal.html");
  },

  async openThesis() {
    openModal("components/thesis/thesis-modal.html");
  },

  async openSlides() {
    openModal("components/slides/slides-modal.html");
  },

  async openWetLab() {
    openModal("components/wetlab/wetlab-modal.html");
  },

  async openKnowledge() {
    openModal("components/knowledge/knowledge-modal.html");
  }
});
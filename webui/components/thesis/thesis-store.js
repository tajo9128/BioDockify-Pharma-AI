import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("thesisModal", {
  chapters: [],
  activeChapter: null,
  loading: false,
  error: "",
  topic: "",
  selectedBranch: "general",
  selectedDegree: "phd",

  async loadChapters() {
    this.loading = true;
    try {
      const result = await callJsonApi("thesis/chapters", {});
      this.chapters = result.chapters || [];
    } catch (e) {
      this.chapters = [
        {id: "introduction", title: "Introduction", section_count: 4},
        {id: "literature_review", title: "Literature Review", section_count: 3},
        {id: "methods", title: "Methods", section_count: 5},
        {id: "results", title: "Results", section_count: 4},
        {id: "discussion", title: "Discussion", section_count: 4},
        {id: "conclusion", title: "Conclusion", section_count: 2},
      ];
    }
    this.loading = false;
  },

  selectChapter(chapter) {
    this.activeChapter = chapter;
  },

  async generateChapter(chapterId) {
    if (!this.topic.trim()) {
      this.error = "Please enter a research topic first";
      return;
    }
    this.loading = true;
    this.error = "";
    try {
      const result = await callJsonApi("thesis/generate", {
        chapter_id: chapterId,
        topic: this.topic,
        branch: this.selectedBranch,
        degree: this.selectedDegree
      });
      return result;
    } catch (e) {
      this.error = e.message;
    }
    this.loading = false;
  },

  async exportLatex() {
    alert("LaTeX export: Use the agent chat to request publication export with your thesis content");
  }
});
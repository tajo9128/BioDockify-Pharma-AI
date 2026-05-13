import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("thesisModal", {
  step: 1,
  docType: "",
  topic: "",
  detail: "",
  sections: "",
  references: "",
  includeCode: false,
  outputFormat: "markdown",
  status: "idle",
  result: "",

  selectType(type) {
    this.docType = type;
    this.step = 2;
  },

  back() {
    if (this.step > 1) this.step--;
  },

  reset() {
    this.step = 1;
    this.docType = "";
    this.topic = "";
    this.detail = "";
    this.sections = "";
    this.references = "";
    this.includeCode = false;
    this.outputFormat = "markdown";
    this.status = "idle";
    this.result = "";
  },

  get typeLabel() {
    const labels = { review: "Literature Review", research: "Research Paper", thesis: "Thesis Chapter" };
    return labels[this.docType] || "";
  },

  get typeDesc() {
    const descs = {
      review: "A structured review of existing literature on your topic",
      research: "A complete research paper with methodology and results",
      thesis: "A chapter for your PhD thesis with academic formatting"
    };
    return descs[this.docType] || "";
  },

  get typeIcon() {
    const icons = { review: "menu_book", research: "science", thesis: "description" };
    return icons[this.docType] || "edit_note";
  },

  async generate() {
    if (!this.topic.trim()) return;
    this.status = "generating";
    this.result = "";
    try {
      const result = await callJsonApi("thesis/generate-agent", {
        type: this.docType,
        topic: this.topic,
        detail: this.detail,
        sections: this.sections,
        references: this.references,
        include_code: this.includeCode,
        output_format: this.outputFormat
      });
      this.result = result.content || result.text || JSON.stringify(result, null, 2);
      this.status = "complete";
      this.step = 3;
    } catch (e) {
      this.result = "Error: " + e.message;
      this.status = "error";
    }
  }
});

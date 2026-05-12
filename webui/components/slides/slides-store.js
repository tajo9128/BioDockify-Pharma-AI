import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("slidesModal", {
  slides: [],
  currentSlide: 0,
  title: "Presentation",
  theme: "academic",
  loading: false,
  error: "",

  async generateFromPrompt() {
    if (!this.title.trim()) {
      this.error = "Please enter a presentation topic";
      return;
    }
    this.loading = true;
    this.error = "";
    try {
      const result = await callJsonApi("slides/generate/from-prompt", {
        prompt: this.title,
        style: this.theme,
        num_slides: 10
      });
      if (result.slides) {
        this.slides = result.slides;
      }
    } catch (e) {
      this.error = e.message;
    }
    this.loading = false;
  },

  async generateFromKB() {
    if (!this.title.trim()) {
      this.error = "Please enter a research topic";
      return;
    }
    this.loading = true;
    this.error = "";
    try {
      const result = await callJsonApi("slides/generate/from-kb", {
        topic: this.title,
        style: this.theme,
        num_slides: 10
      });
      if (result.slides) {
        this.slides = result.slides;
      }
    } catch (e) {
      this.error = e.message;
    }
    this.loading = false;
  },

  addSlide() {
    this.slides.push({ title: "New Slide", content: "", type: "content" });
    this.currentSlide = this.slides.length - 1;
  },

  removeSlide(index) {
    this.slides.splice(index, 1);
    if (this.currentSlide >= this.slides.length) {
      this.currentSlide = Math.max(0, this.slides.length - 1);
    }
  },

  async generate() {
    if (this.slides.length === 0) {
      this.error = "No slides to generate. Add slides first or use KB/prompt generation.";
      return;
    }
    alert("PowerPoint generation: Use the agent chat to request export with your slide content");
  }
});
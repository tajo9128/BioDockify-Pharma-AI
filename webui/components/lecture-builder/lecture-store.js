import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

export const store = createStore("lectureBuilder", {
  topic: "",
  duration: "60",
  level: "undergraduate",
  loading: false,
  result: null,
  error: "",
  activeTab: "lecture",

  async generate() {
    if (!this.topic.trim()) return;
    this.loading = true;
    this.error = "";
    try {
      const resp = await callJsonApi("lecture_generate", {
        topic: this.topic,
        duration: this.duration,
        level: this.level
      });
      if (resp.error) { this.error = resp.error; return; }
      this.result = resp;
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  clear() {
    this.topic = "";
    this.result = null;
    this.error = "";
  }
});

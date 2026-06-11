import { callJsonApi } from "/js/api.js";

Alpine.data("statisticsModal", () => ({
  step: 1,
  fileName: "",
  columns: [],
  rowCount: 0,
  summary: null,          // AI analysis: column classification + recommendations
  testType: "",
  loading: false,
  errorMessage: "",
  result: null,            // Final results with explanations

  // === Step 1: Upload ===
  openFilePicker() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv,.xlsx,.xls,.json";
    input.style.display = "none";
    input.onchange = (e) => {
      const file = e.target.files?.[0];
      input.remove();
      if (file) this.processUpload(file);
    };
    document.body.appendChild(input);
    input.click();
  },

  handleDrop(e) {
    const file = e.dataTransfer?.files?.[0];
    if (file) this.processUpload(file);
  },

  async processUpload(file) {
    this.loading = true;
    this.errorMessage = "";
    this.fileName = file.name;
    this.summary = null;
    this.result = null;
    try {
      const { content } = await this.readContent(file);
      // Step 2+3: AI analyzes file — classifies columns, recommends tests
      const r = await callJsonApi("statistics_auto", {
        action: "analyze",
        content: content,
        filename: file.name,
      });
      if (r.status === "ok") {
        this.summary = r;
        this.columns = r.data_summary?.column_names || [];
        this.rowCount = r.data_summary?.total_rows || 0;
        this.step = 2;
        this.testType = r.recommended_test || "";
      } else {
        this.errorMessage = r.error || "Upload failed";
      }
    } catch (e) {
      this.errorMessage = "Upload error: " + (e.message || "API unavailable");
    }
    this.loading = false;
  },

  readContent(file) {
    const ext = (file.name || "").split(".").pop().toLowerCase();
    if (ext === "xlsx" || ext === "xls") {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const bytes = new Uint8Array(reader.result);
          let b = "";
          for (let i = 0; i < bytes.length; i += 8192)
            b += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i + 8192, bytes.length)));
          resolve({ content: btoa(b), isBinary: true });
        };
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsArrayBuffer(file);
      });
    }
    return file.text().then(t => ({ content: t, isBinary: false }));
  },

  // === Step 2 → Run Selected Test ===
  async runSelectedTest() {
    if (!this.testType) { this.errorMessage = "Select a test type"; return; }
    this.loading = true;
    this.errorMessage = "";
    this.result = null;
    try {
      // Step 3-6: AI decides sub-type, performs test, returns results + explanations
      const r = await callJsonApi("statistics_analyze", {
        action: "auto_decide",
        test_type: this.testType,
        columns: this.columns,
        summary: this.summary?.data_summary || {},
      });
      if (r.status === "ok") {
        this.result = r;
        this.step = 3;
      } else {
        this.errorMessage = r.error || "Analysis failed";
      }
    } catch (e) {
      this.errorMessage = "Analysis error: " + (e.message || "API unavailable");
    }
    this.loading = false;
  },

  // === Navigation ===
  resetData() {
    this.step = 1;
    this.fileName = "";
    this.columns = [];
    this.rowCount = 0;
    this.summary = null;
    this.testType = "";
    this.result = null;
    this.errorMessage = "";
  },

  goBack() {
    this.step = 2;
    this.result = null;
  },

  // === Save ===
  saveToKB() {
    if (typeof $store !== "undefined" && $store.knowledgeModal?.addNoteBookEntry && this.result) {
      $store.knowledgeModal.addNoteBookEntry(
        `${this.testType} — ${this.fileName}`,
        JSON.stringify(this.result, null, 2),
        "Statistical Analysis",
        ["statistics", this.testType]
      );
    }
  },

  downloadJSON() {
    if (!this.result) return;
    const blob = new Blob([JSON.stringify(this.result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "statistics-result.json";
    a.click();
    URL.revokeObjectURL(url);
  },
}));

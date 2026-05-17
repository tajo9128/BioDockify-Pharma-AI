import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

const LS = "biodockify.faculty";

export const store = createStore("facultyTools", {
  activeTab: "syllabus",
  loading: false,
  error: "",
  message: "",

  // Multi-subject support (max 3)
  subjects: [
    { id: 1, name: "Subject 1", syllabusText: "", syllabusFileName: "", syllabusFileSize: 0, syllabusResult: null, lectureTopic: "", lectureResult: null, assignTopic: "", assignResult: null },
    { id: 2, name: "Subject 2", syllabusText: "", syllabusFileName: "", syllabusFileSize: 0, syllabusResult: null, lectureTopic: "", lectureResult: null, assignTopic: "", assignResult: null },
    { id: 3, name: "Subject 3", syllabusText: "", syllabusFileName: "", syllabusFileSize: 0, syllabusResult: null, lectureTopic: "", lectureResult: null, assignTopic: "", assignResult: null },
  ],
  activeSubject: 1,
  _restored: false,

  // Shared
  lectureDuration: "60",
  lectureLevel: "undergraduate",
  assignType: "essay",
  assignLevel: "undergraduate",
  assignWords: "2000",
  plagText: "",
  plagResult: null,

  // Flat properties (synced from active subject)
  syllabusText: "",
  syllabusFileName: "",
  syllabusFileSize: 0,
  syllabusResult: null,
  lectureTopic: "",
  lectureResult: null,
  assignTopic: "",
  assignResult: null,

  switchSubject(id) {
    this.activeSubject = id;
    this._syncFromSub();
    this.persist();
  },

  _syncFromSub() {
    const s = this.subjects[this.activeSubject - 1];
    this.syllabusText = s.syllabusText || "";
    this.syllabusFileName = s.syllabusFileName || "";
    this.syllabusFileSize = s.syllabusFileSize || 0;
    this.syllabusResult = s.syllabusResult;
    this.lectureTopic = s.lectureTopic || "";
    this.lectureResult = s.lectureResult;
    this.assignTopic = s.assignTopic || "";
    this.assignResult = s.assignResult;
  },

  _syncToSub() {
    const s = this.subjects[this.activeSubject - 1];
    s.syllabusText = this.syllabusText;
    s.syllabusFileName = this.syllabusFileName;
    s.syllabusFileSize = this.syllabusFileSize;
    s.lectureTopic = this.lectureTopic;
    s.assignTopic = this.assignTopic;
  },

  handleFileUpload(event) {
    const f = event.target.files[0];
    if (!f) return;
    const ext = f.name.split('.').pop().toLowerCase();
    const sizeKB = (f.size / 1024).toFixed(1);

    this.syllabusFileName = f.name;
    this.syllabusFileSize = sizeKB;
    this.error = "";

    if (ext === 'txt' || ext === 'md') {
      const r = new FileReader();
      r.onload = () => {
        this.syllabusText = r.result;
        this.message = `Uploaded: ${f.name} (${sizeKB} KB) — text content loaded`;
      };
      r.onerror = () => { this.error = "Failed to read file"; };
      r.readAsText(f);
    } else if (ext === 'pdf' || ext === 'docx') {
      this.syllabusText = `[File: ${f.name} (${sizeKB} KB)] — binary content sent to agent for processing`;
      this.message = `Uploaded: ${f.name} (${sizeKB} KB) — click "Parse Syllabus" to extract with AI`;
    } else {
      this.syllabusText = f.name;
      this.message = `Uploaded: ${f.name} (${sizeKB} KB)`;
    }
    this._syncToSub();
    this.persist();
  },

  renameSubject(id) {
    const name = prompt("Subject name:", this.subjects[id-1].name);
    if (name) { this.subjects[id-1].name = name; this.persist(); }
  },

  persist() {
    try { localStorage.setItem(LS, JSON.stringify({ subjects: this.subjects, activeSubject: this.activeSubject })); } catch {}
  },
  restore() {
    if (this._restored) return; this._restored = true;
    try {
      const s = JSON.parse(localStorage.getItem(LS) || "{}");
      if (s.subjects) this.subjects = s.subjects;
      if (s.activeSubject) this.activeSubject = s.activeSubject;
    } catch {}
    this._syncFromSub();
  },

  clearUpload() {
    this.syllabusText = "";
    this.syllabusFileName = "";
    this.syllabusFileSize = 0;
    this.syllabusResult = null;
    this.message = "";
    this._syncToSub();
    this.persist();
  },

  async syllabusParse() {
    this._syncToSub();
    if (!this.syllabusText.trim()) return;
    this.loading = true; this.error = ""; this.message = ""; this.syllabusResult = null;
    try {
      this.syllabusResult = await callJsonApi("faculty_tools", { action: "syllabus", text: this.syllabusText });
      if (!this.syllabusResult || this.syllabusResult.error) {
        this.error = this.syllabusResult?.error || "Failed to parse syllabus. Try again or paste text manually.";
        return;
      }
      this.subjects[this.activeSubject - 1].syllabusResult = this.syllabusResult;
      this.message = `Parsed: ${this.syllabusResult.course_name || 'Course'} — ${this.syllabusResult.topic_count || 0} topics`;
    } catch (e) { this.error = "API not available. Paste syllabus text and the agent will parse it."; }
    this.loading = false;
  },

  async genLecture() {
    this._syncToSub();
    if (!this.lectureTopic.trim()) return;
    this.loading = true; this.error = ""; this.lectureResult = null;
    try {
      this.lectureResult = await callJsonApi("faculty_tools", { action: "lecture", topic: this.lectureTopic, duration: this.lectureDuration, level: this.lectureLevel });
      if (this.lectureResult) {
        this.subjects[this.activeSubject - 1].lectureResult = this.lectureResult;
      }
    } catch (e) {
      this.sendToAgent(`Generate a detailed ${this.lectureDuration}-minute lecture on: "${this.lectureTopic}" at ${this.lectureLevel} level. Include: 1) Learning objectives, 2) Lecture structure with timings, 3) Key concepts, 4) Examples, 5) Homework/assignments.`);
    }
    this.loading = false;
  },

  async genAssignment() {
    this._syncToSub();
    if (!this.assignTopic.trim()) return;
    this.loading = true; this.error = ""; this.assignResult = null;
    try {
      this.assignResult = await callJsonApi("faculty_tools", { action: "assignment", topic: this.assignTopic, type: this.assignType, level: this.assignLevel, word_count: this.assignWords });
      if (this.assignResult) {
        this.subjects[this.activeSubject - 1].assignResult = this.assignResult;
      }
    } catch (e) {
      this.sendToAgent(`Create a ${this.assignWords}-word ${this.assignType} assignment on: "${this.assignTopic}" at ${this.assignLevel} level. Include: 1) Assignment prompt, 2) Instructions, 3) Grading rubric (100 marks), 4) Submission guidelines.`);
    }
    this.loading = false;
  },

  async checkPlagiarism() {
    if (!this.plagText.trim()) return;
    this.loading = true; this.error = ""; this.plagResult = null;
    try {
      this.plagResult = await callJsonApi("faculty_tools", { action: "plagiarism", text: this.plagText });
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  sendToAgent(prompt) {
    const input = document.getElementById("chat-input");
    if (input) {
      input.value = prompt;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
      this.message = "Sent to agent. Check the chat panel.";
    } else {
      this.error = "Chat input not found. Open a new chat first.";
    }
  },

  litReview() {
    const name = this.syllabusResult?.course_name || this.subjects[this.activeSubject-1].name;
    this.sendToAgent(`Conduct a comprehensive literature review for: ${name}. Search PubMed, Semantic Scholar, arXiv for recent papers (last 5 years). Structure: 1) Introduction, 2) Current State of Knowledge, 3) Key Findings, 4) Research Gaps, 5) Future Directions. Include 10+ citations.`);
  },

  prepareNotes() {
    const name = this.syllabusResult?.course_name || this.subjects[this.activeSubject-1].name;
    const topics = (this.syllabusResult?.topics || []).join(', ');
    this.sendToAgent(`Prepare structured study notes for: ${name}. Topics: ${topics}. For each topic provide: 1) Key concepts (bullet points), 2) Important definitions, 3) Diagrams to draw, 4) Memory aids/mnemonics, 5) Practice questions. Format as student-ready notes.`);
  },

  makeSlides() {
    const name = this.syllabusResult?.course_name || this.subjects[this.activeSubject-1].name;
    const topics = (this.syllabusResult?.topics || []).slice(0, 10).join(', ');
    this.sendToAgent(`Create a ${Math.min(this.syllabusResult?.topic_count || 10, 15)}-slide presentation for: ${name}. Topics to cover: ${topics}. For each slide: Slide number, Title, 3-4 bullet points, Speaker notes. Style: Academic. Include introduction and summary slides.`);
  },
});

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
    { id: 1, name: "Subject 1", syllabusText: "", syllabusResult: null, lectureTopic: "", lectureResult: null, assignTopic: "", assignResult: null },
    { id: 2, name: "Subject 2", syllabusText: "", syllabusResult: null, lectureTopic: "", lectureResult: null, assignTopic: "", assignResult: null },
    { id: 3, name: "Subject 3", syllabusText: "", syllabusResult: null, lectureTopic: "", lectureResult: null, assignTopic: "", assignResult: null },
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
    this.syllabusResult = s.syllabusResult;
    this.lectureTopic = s.lectureTopic || "";
    this.lectureResult = s.lectureResult;
    this.assignTopic = s.assignTopic || "";
    this.assignResult = s.assignResult;
  },

  _syncToSub() {
    const s = this.subjects[this.activeSubject - 1];
    s.syllabusText = this.syllabusText;
    s.lectureTopic = this.lectureTopic;
    s.assignTopic = this.assignTopic;
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

  async syllabusParse() {
    this._syncToSub();
    if (!this.syllabusText.trim()) return;
    this.loading = true; this.error = ""; this.syllabusResult = null;
    try {
      this.syllabusResult = await callJsonApi("faculty_tools", { action: "syllabus", text: this.syllabusText });
      this.subjects[this.activeSubject - 1].syllabusResult = this.syllabusResult;
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async genLecture() {
    this._syncToSub();
    if (!this.lectureTopic.trim()) return;
    this.loading = true; this.error = ""; this.lectureResult = null;
    try {
      this.lectureResult = await callJsonApi("faculty_tools", { action: "lecture", topic: this.lectureTopic, duration: this.lectureDuration, level: this.lectureLevel });
      this.subjects[this.activeSubject - 1].lectureResult = this.lectureResult;
    } catch (e) { this.error = e.message; }
    this.loading = false;
  },

  async genAssignment() {
    this._syncToSub();
    if (!this.assignTopic.trim()) return;
    this.loading = true; this.error = ""; this.assignResult = null;
    try {
      this.assignResult = await callJsonApi("faculty_tools", { action: "assignment", topic: this.assignTopic, type: this.assignType, level: this.assignLevel, word_count: this.assignWords });
      this.subjects[this.activeSubject - 1].assignResult = this.assignResult;
    } catch (e) { this.error = e.message; }
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
    const input = document.querySelector("#chat-bar-input textarea, .chat-bar-input textarea");
    if (input) { input.value = prompt; input.dispatchEvent(new Event("input", { bubbles: true })); input.focus(); }
  },
});

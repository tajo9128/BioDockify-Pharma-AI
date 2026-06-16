# Chapter 2: Navigating the Interface

## 2.1 Layout Modes

BioDockify has three layout modes, toggled via the bottom-right buttons:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Chat** | Full-width chat interface | Conversations, research queries |
| **Split** | Chat left + module right | Side-by-side work |
| **Desktop** | Full desktop workspace with windows | Multi-module workflows |

### Chat Mode
Default mode. The welcome screen shows quick-start cards and recent activity. Type in the chat input to interact with the AI agent.

### Split Mode
Chat occupies the left panel, the active module occupies the right panel. Drag the divider to resize.

### Desktop Mode
Full windowed environment. Open multiple modules as draggable, resizable windows. Each window has minimize/maximize/close controls.

---

## 2.2 The Toolbar

The left sidebar contains 16 module icons:

| Icon | Module | Description |
|------|--------|-------------|
| 🚀 | Research CMD | Research pipeline + Literature + Wet Lab |
| 🔬 | Molecular Toolkit | ADMET + Docking + Analysis |
| 📊 | Statistics | 20 analysis types + 8 charts |
| 📖 | Academic Writer | Paper + Thesis + Grant + Regulatory + Citations |
| 🎓 | Faculty CMD | Syllabus + Lectures + Assignments + Slides |
| ✅ | Journal Finder | 36,145 journals + verify + deep research |
| ⚖️ | QSAR | ML models + batch predict + read-across |
| 🎯 | Pharmacophore | 13 pharmacophore actions |
| ✏️ | Molecule Editor | Draw + 3D + Properties + Filters + Optimize |
| 💾 | Backup | System backup & recovery |
| ❤️ | System Health | Dependency monitoring |
| 🧪 | Benchmark | System validation |

Click any icon to open that module. In Split/Desktop mode, it opens as a window.

---

## 2.3 The All Tools Grid

Click **All Tools** (grid icon) to see all 16 modules as cards with subtask labels:

```
Research CMD          Molecular Toolkit       Molecule Editor
Auto-research +       ADMET + Docking +       Draw + 3D + Props +
Literature + Wet Lab  Analysis                Filters + Optimize
```

Each card shows what's inside the parent module. Click to open.

---

## 2.4 Module Windows (Desktop Mode)

In Desktop mode, modules open as draggable windows:

- **Title bar**: Module name + icon + minimize/maximize/close buttons
- **Content**: Module-specific UI with tabs
- **Resize handle**: Drag bottom-right corner
- **Taskbar**: Bottom bar shows all open windows

### Window Management

| Action | How |
|--------|-----|
| Open module | Click icon in sidebar or All Tools grid |
| Minimize | Click minimize button (−) |
| Maximize | Click maximize button (□) |
| Close | Click close button (×) |
| Bring to front | Click anywhere on the window |
| Resize | Drag bottom-right corner |

---

## 2.5 Tab Navigation Within Modules

Most modules have internal tabs. Examples:

**Molecule Editor** (4 tabs):
```
[3D View] [Properties] [Filters] [Optimize]
```

**Molecular Toolkit** (4 tabs):
```
[ADMET] [Similarity] [Chem Space] [Docking] [Analysis]
```

**Academic Writer** (8 tabs):
```
[Lit Review] [Paper] [Thesis] [Grant] [Regulatory] [Citations] [Lecture] [Slides]
```

Click tabs to switch views. Each tab has its own inputs, actions, and results.

---

## 2.6 Chat Interface

The chat panel (left side in Chat/Split mode) is the primary interaction with the AI agent:

### Input Area
- **Text input**: Type questions or commands
- **Attachment button**: Upload files (PDF, images, data)
- **Voice button**: Speech-to-text input
- **Send button**: Submit message

### Message History
- Scroll through conversation history
- Messages are saved per session
- Click on code blocks to copy

### Agent Commands
The AI agent can:
- Run any module via chat commands
- Analyze uploaded data
- Answer research questions
- Generate code, papers, analyses
- Execute terminal commands (with permission)

---

## 2.7 Session Persistence

BioDockify saves session data automatically:

| Data | Storage | Persists Across Restarts? |
|------|---------|--------------------------|
| Chat history | Browser localStorage | ✅ Yes |
| Module state | Browser localStorage | ✅ Yes |
| QSAR models | Docker volume | ✅ Yes |
| Docking jobs | Docker volume | ✅ Yes |
| Knowledge base | Docker volume | ✅ Yes |
| Settings | Docker volume | ✅ Yes |

### Clearing Session Data
- **Chat**: Click "New Chat" in sidebar
- **Module state**: Refresh browser (F5)
- **All data**: Settings → Reset

---

## 2.8 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line in input |
| `Ctrl+K` | Quick search |
| `Ctrl+Shift+M` | Toggle sidebar |
| `Escape` | Close modal/popup |
| `F5` | Refresh module state |

---

## 2.9 Quick Access Patterns

### From Chat to Module
Type a command and the agent opens the relevant module:
- "Dock aspirin against COX-2" → Opens Molecular Toolkit
- "Run QSAR on this dataset" → Opens QSAR Modeler
- "Find a journal for my paper" → Opens Journal Finder

### From Module to Chat
Click the "Ask agent" button in any module to send context to chat.

### Cross-Module Workflows
1. **Molecule Editor → Docking**: Draw molecule → "Send to Docking" button
2. **Journal Finder → Academic Writer**: Find journal → use in paper writing
3. **QSAR → Molecule Editor**: Predict activity → load molecule in editor
4. **Docking Analysis → QSAR**: Analyze poses → train QSAR on binding data

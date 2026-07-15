## PPT Master Tool

**Purpose:** Generate real, editable PowerPoint presentations with native shapes, charts, animations, and speaker notes. Based on github.com/hugohe3/ppt-master.

**When to use:**
- User asks to "make PPT", "create slides", "generate presentation", "make PowerPoint"
- User wants lecture slides, conference presentation, or research presentation
- User has research results, literature, or data that needs to be presented
- User says "convert my research to slides"

**Actions:**
- `status` — Check PPT Master engine availability and capabilities
- `generate` — Generate a PPTX presentation
- `list_templates` — List available design templates
- `list_workflows` — List available generation workflows

**For full SVG pipeline (recommended for high-quality output):**
Load the `ppt-master` skill at `skills/ppt-master/` and follow its pipeline:
1. **Strategist** — Analyze topic, plan slide structure, select palette/rendering
2. **Executor** — Generate SVG slides page by page with native shapes
3. **Quality Check** — Verify consistency, layout, readability
4. **Post-processing** — Add animations, speaker notes, audio narration
5. **Export** — Convert SVG → PPTX (editable, not images)

**For quick generation via API:**
```
Tool: ppt_master
Action: generate
slides: [
  {type: "title", title: "Drug Discovery Pipeline", subtitle: "AI-Driven Approach"},
  {type: "content", title: "Introduction", bullets: ["Point 1", "Point 2"]},
  {type: "chart", title: "Results", table: [["Drug","Score"],["Aspirin","8.5"]]},
  {type: "two_column", title: "Comparison", left: {title: "Method A", bullets: [...]}, right: {title: "Method B", bullets: [...]}},
]
theme: academic
```

**Capabilities:**
- ✅ Native editable PPTX (click and edit in PowerPoint)
- ✅ SVG-based slide generation (vector graphics)
- ✅ Editable charts & tables (change data in PowerPoint)
- ✅ Animations & transitions
- ✅ Speaker notes with audio narration (TTS)
- ✅ Custom .pptx template support
- ✅ Multiple color palettes & rendering styles
- ✅ AI image generation & search integration
- ✅ Source document parsing (PDF/DOCX/URL/Markdown → slides)
- ✅ Multi-role AI collaboration pipeline

**Slide Types:**
- `title` — Title slide with centered title + subtitle
- `section` — Section divider with colored accent bar
- `content` — Standard content with title + bullets
- `chart` — Content with editable data table
- `two_column` — Two-column comparison layout

**Themes:** academic, clinical, corporate, minimal, dark

# Changelog

All notable changes to BioDockify Pharma AI.

## [v5.7.1] - 2026-05-15
### Added
- System Health dashboard: Internet, ChromaDB, RDKit, Disk, Memory monitoring
- Feature fallback status panel (TTS, Drug Properties, Literature)
- GDrive cloud backup UI in Backup module
- `system_health` API wiring connection_doctor + system_doctor + guardian
### Fixed
- LICENSE merge conflict markers removed

## [v5.7.0] - 2026-05-15
### Fixed
- 6 critical frontend bugs: Alpine.js `{{ }}` syntax, duplicate `clear()`, taskbar double-minimize, setInterval leak, stray `</template>`
- Null-safety guards added to 10 modules ($store?. references)
- CSS: 106-line duplicate tooltip block removed, 4 missing CSS variables defined
- Backend: logging added to drug_properties, literature_search (3 backends), kokoro_tts
- Kokoro TTS model cached as singleton (was created per-request)
- Literature arXiv fixed to HTTPS, timeouts improved
### Security
- Dockerfile: EXPOSE 50001, HEALTHCHECK every 30s

## [v5.6.4] - 2026-05-15
### Added
- Agent Zero constitution with 7 governing principles
- Proactive module monitoring (15 modules, 30-minute intervals)
- Self-healing protocol: detect → diagnose → repair → verify → log
- Aggressive research protocol with 8-item exhaustion checklist
- 15-module registry + 4 sub-agent registry in identity.md

## [v5.6.3] - 2026-05-15
### Added
- Molecular Toolkit module: ADMET prediction, Tanimoto similarity, chemical space PCA
- Wired 3 previously unwired APIs: admet_predict, molecular_similarity, chemical_space
### Audit
- Full codebase audit: 29 files changed from v4.7.7, zero Agent Zero core touched

## [v5.6.2] - 2026-05-15
### Added
- Cross-module integration: Research Dashboard → Academic Writer, Notebook → Academic Writer
- Export Research Report from Research Dashboard (pipeline + milestones + wet lab)
- Save to Notebook from Statistics results

## [v5.6.1] - 2026-05-15
### Added
- Research Notebook upgrade: tag system, favorites, knowledge graph (canvas force-directed)
- Save to Notebook button in Literature search results
- Rich entry cards with source attribution, date, entry tags

## [v5.6.0] - 2026-05-15
### Added
- Research Command Center: 4-tab dashboard (Projects, Pipeline, Milestones, Wet Lab)
- Wired to 23 existing backend API endpoints (zero new backend)
- Auto-start comprehensive research from PhD title input
- Gantt-style milestone progress tracking

## [v5.5.5] - 2026-05-15
### Added
- Session persistence (localStorage) for Statistics, Drug Properties, Literature, Academic Writer
### Fixed
- Desktop-store module ordering (duplicate order numbers resolved)

## [v5.5.4] - 2026-05-15
### Added
- 5-tab Academic Writer: Literature Review, Research Paper, Thesis, Lecture, Slides
- Kokoro TTS integration with 3-tier fallback (Kokoro → Edge-TTS → Browser)

## [v5.5.3] - 2026-05-15
### Added
- Slides Generator with style/ slide count options
- Lecture Builder with duration/level selection
- Wet Lab Manager with 3-tab interface
- Literature module with PubMed/Semantic Scholar/arXiv search

## [v5.5.2] - 2026-05-15
### Added
- Drug Properties module with SMILES input, property table, Lipinski Rule-of-5
- Literature multi-database search API (PubMed, Semantic Scholar, arXiv)

## [v5.5.1] - 2026-05-15
### Added
- Statistics module rebuild: replaced prompt() dialogs with proper dropdowns
- Download CSV/JSON buttons, data preview, agent-help buttons
- Test-type dropdown selector with parameter forms per analysis type

## [v5.5.0] - 2026-05-15
### Added
- 3-mode layout: Chat, Split-pane (chat + desktop), Full Desktop
- Resizable split divider between chat and desktop
- Right-side icon rail with 13 module launchers
- Right-canvas restored as overlay in chat panel
### Fixed
- #desktop-wrapper moved inside .container (CSS selectors now match)
- Duplicate CSS blocks removed from desktop-workspace.css

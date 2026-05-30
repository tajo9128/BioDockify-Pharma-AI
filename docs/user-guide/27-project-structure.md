# Chapter 27: Project Structure & File Organization

## 27.1 Root Directory Structure

```
BioDockify-Pharma-AI/
├── api/                    # API endpoint handlers
├── webui/                  # Frontend components
├── modules/                # Backend modules
├── helpers/                # Shared utilities
├── tools/                  # Agent tools
├── knowledge/              # Agent knowledge base
├── prompts/                # System prompts
├── skills/                 # Skill definitions
├── data/                   # Persistent data (Docker volume)
├── tmp/                    # Temporary files (Docker volume)
├── docs/                   # Documentation
├── docker-compose.yml      # Docker configuration
├── Dockerfile              # Base Docker image
├── Dockerfile.release      # Release Docker image
├── requirements.txt        # Python dependencies
└── README.md               # Project overview
```

## 27.2 API Directory

```
api/
├── health.py               # System health check
├── drug_properties.py      # Drug property calculation
├── drug_analysis.py        # PAINS/Brenk/NIH filters
├── structure_3d.py         # 3D conformer generation
├── structure_export.py     # PNG/SVG/MOL/SDF export
├── admet_swiss.py          # SwissADME engine
├── admet_plot.py           # BOILED-Egg + Radar plots
├── qsar.py                 # QSAR modeler
├── pharmacophore.py        # Pharmacophore modeling
├── journal_finder.py       # Journal verification
├── docking_prepare.py      # PDBQT preparation
├── docking_run.py          # Vina + GNINA docking
├── docking_analysis.py     # Post-docking analysis
├── docking_download.py     # File downloads
└── docking_gnina.py        # GNINA CNN scoring
```

## 27.3 Frontend Components

```
webui/components/
├── molecular-toolkit/      # ADMET + Docking
├── molecule-editor/        # Draw + 3D + Properties
├── qsar/                   # QSAR Modeler
├── pharmacophore/          # Pharmacophore
├── journal-finder/         # Journal Finder
├── thesis/                 # Academic Writer
├── faculty-dashboard/      # Faculty CMD
├── research-dashboard/     # Research CMD
├── statistics/             # Statistics
├── knowledge/              # Knowledge Base
├── system-health/          # System Health
├── benchmark/              # Benchmark
└── sidebar/                # UI sidebar
```

## 27.4 Data Directory (Persistent)

```
data/
├── qsar_models/            # Trained QSAR models (.pkl + .json)
├── journal_data/           # Journal database
└── integrity/              # Hijacked journal DB
```

## 27.5 Temporary Directory

```
tmp/
├── docking_jobs/           # Docking results (PDBQT, SDF, logs)
│   └── <job_id>/
│       ├── protein.pdb
│       ├── protein.pdbqt
│       ├── ligand.pdbqt
│       ├── docked_output.pdbqt
│       ├── docked_poses.sdf
│       └── vina_log.txt
└── qsar_cache/             # Temporary QSAR data
```

## 27.6 Docker Volumes

| Volume | Path | Contents |
|--------|------|----------|
| `biodockify_usr` | `/a0/usr` | User data, plugins, uploads |
| `biodockify_data` | `/a0/data` | Models, databases |
| `biodockify_tmp` | `/a0/tmp` | Docking jobs, temp files |

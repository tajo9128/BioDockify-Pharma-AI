# Docker Build Checklist — MANDATORY Before Every Release

## Pre-Build Checks (Local)

### 1. Verify ALL Python dependencies are in Dockerfile
```bash
# Extract all imports from api/*.py and check they're installed
grep -rh "^from\|^import" api/*.py | grep -v "from \." | grep -v "from helpers" | sort -u
```

Every third-party import must be in one of:
- `/opt/venv-a0` (framework venv) — packages listed in Dockerfile RUN line
- `/opt/venv` (execution venv) — packages listed in Dockerfile RUN line
- System packages via `apt-get install`

### 2. Dependency Verification Matrix

| Package | Framework venv (`/opt/venv-a0`) | Execution venv (`/opt/venv`) | Why |
|---------|:---:|:---:|-----|
| flask | ✅ (base image) | ✅ MUST INSTALL | API handlers import Flask |
| litellm | ✅ (base image) | ✅ (base image) | LLM calls |
| rdkit | ✅ | ✅ (via system pkg) | Molecular modeling |
| scipy | ✅ | ✅ | Statistics |
| scikit-learn | ✅ | ✅ | QSAR, ML |
| pandas | ✅ | ✅ | Data analysis |
| matplotlib | ✅ | ✅ | Plots |
| numpy | ✅ | ✅ | Math |
| openmm | ✅ | ✅ | MD simulation |
| mdtraj | ✅ | ✅ | MD analysis |
| pdbfixer | ✅ | ✅ | MD preparation |
| mdanalysis | ✅ | ✅ | MD advanced analysis |
| xgboost | ✅ MUST INSTALL | ✅ MUST INSTALL | QSAR models |
| lightgbm | ✅ MUST INSTALL | ✅ MUST INSTALL | QSAR models |
| catboost | ✅ MUST INSTALL | ✅ MUST INSTALL | QSAR models |
| plotly | ✅ | ✅ MUST INSTALL | Interactive plots |
| seaborn | ✅ | ✅ | Statistics plots |
| statsmodels | ✅ | ✅ | Statistics |
| lifelines | ✅ | — | Survival analysis |
| reportlab | ✅ | — | PDF generation |
| chromadb | ✅ | — | Vector DB |
| faiss-cpu | ✅ | — | Vector search |
| sentence-transformers | ✅ | — | Embeddings |
| fastapi | ✅ | — | API framework |
| meeko | ✅ | — | Docking prep |
| biopython | ✅ | — | Bioinformatics |
| arxiv | ✅ | — | Literature search |
| semanticscholar | ✅ | — | Literature search |
| tabulate | ✅ | — | Tables |
| pingouin | ✅ | — | Statistics |
| supervisor | — | — | System Python (/usr/bin/python3) |

### 3. Build Verification Script

After building the image, ALWAYS run:
```bash
docker build -f Dockerfile.release -t tajo9128/biodockify-pharma-ai:latest .
# Then verify:
docker run --rm tajo9128/biodockify-pharma-ai:latest /exe/verify_packages.sh
```

### 4. UI Panel Verification

| Panel | Registration File | HTML File | Verified? |
|-------|------------------|-----------|-----------|
| Molecular Toolkit | register-molecular-toolkit.js | molecular-toolkit.html | ☐ |
| ADMET Prediction | register-admet-predict.js | admet-predict-panel.html | ☐ |
| Docking Analysis | register-docking-analysis.js | docking-analysis.html | ☐ |
| Pharmacophore | register-pharmacophore.js | (via API) | ☐ |
| QSAR 3D | register-qsar3d.js | qsar3d.html | ☐ |
| Knowledge Base | register-knowledge.js | knowledge-modal.html | ☐ |
| Backup & Recovery | register-backup-recovery.js | recovery-panel.html | ☐ |
| Statistics | register-statistics.js | statistics.html | ☐ |
| Clinical | register-clinical.js | clinical.html | ☐ |

### 5. API Endpoint Smoke Test

```python
# Run this inside the container to verify all critical APIs import
import sys; sys.path.insert(0, "/a0")
from api.literature_search import LiteratureSearch  # ← was breaking
from api.admet_predict import AdmetPredict
from api.pharmacophore import PharmacophoreHandler
from api.qsar3d import QSAR3DHandler
from api.md_lite import MDLite
from api.docking_run import DockingRun
from api.clinical import ClinicalHandler
print("ALL CRITICAL APIs IMPORT OK")
```

## Post-Build Checks (Container)

### 6. Verify container starts cleanly
- [ ] No `FATAL` in supervisord logs (except the_listener if supervisor missing)
- [ ] `Uvicorn running on http://0.0.0.0:80`
- [ ] `BioDockify AI is running`
- [ ] Health check returns `{"status": "ok"}`

### 7. Verify image size
- Expected: 15-19 GB (base image ~13 GB + packages ~2-4 GB + models ~1 GB)
- If < 14 GB → packages are missing!
- If > 20 GB → unnecessary files included

### 8. Version verification
- [ ] `version_info.txt` matches release tag
- [ ] Sidebar shows correct version
- [ ] Welcome screen shows correct version
- [ ] Health API returns correct version
- [ ] Agent role prompt has correct version

## LESSONS LEARNED

### v7.9.5 Mistake (2026-07-29)
- **Issue**: Flask not in execution venv → research agent crashed
- **Root cause**: Assumed base image had Flask in both venvs — it didn't
- **Fix**: Added flask to `/opt/venv` pip install in Dockerfile
- **Prevention**: Always run `verify_packages.sh` after build

### v7.9.5 Mistake 2 (2026-07-29)
- **Issue**: xgboost, lightgbm, catboost not installed → QSAR showed 16 not 19+ models
- **Root cause**: Added to code but forgot to add to Dockerfile
- **Fix**: Added all three to both venvs
- **Prevention**: Cross-check every `import` in code against Dockerfile packages

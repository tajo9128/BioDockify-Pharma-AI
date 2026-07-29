#!/bin/bash
# Package Verification Script — run after every Docker build
# Usage: docker run --rm tajo9128/biodockify-pharma-ai:latest /exe/verify_packages.sh

echo "================================================"
echo "BioDockify Package Verification"
echo "================================================"
echo ""

FAILURES=0

# ── Framework venv (/opt/venv-a0) ──
echo "=== Framework venv (/opt/venv-a0) ==="
FRAMEWORK_PKGS=(
    flask rdkit scipy scikit-learn pandas matplotlib numpy
    openmm mdtraj pdbfixer MDAnalysis
    xgboost lightgbm catboost
    plotly seaborn statsmodels lifelines reportlab
    chromadb faiss sentence_transformers
    fastapi meeko Bio arxiv semanticscholar tabulate pingouin
)
for pkg in "${FRAMEWORK_PKGS[@]}"; do
    if /opt/venv-a0/bin/python -c "import $pkg" 2>/dev/null; then
        echo "  ✓ $pkg"
    else
        echo "  ✗ $pkg — MISSING!"
        FAILURES=$((FAILURES + 1))
    fi
done

echo ""

# ── Execution venv (/opt/venv) ──
echo "=== Execution venv (/opt/venv) ==="
EXEC_PKGS=(
    flask scipy scikit-learn pandas matplotlib numpy
    openmm mdtraj pdbfixer MDAnalysis
    xgboost lightgbm catboost
    plotly seaborn statsmodels
)
for pkg in "${EXEC_PKGS[@]}"; do
    if /opt/venv/bin/python -c "import $pkg" 2>/dev/null; then
        echo "  ✓ $pkg"
    else
        echo "  ✗ $pkg — MISSING!"
        FAILURES=$((FAILURES + 1))
    fi
done

echo ""

# ── System packages ──
echo "=== System packages ==="
if /usr/bin/python3 -c "from supervisor.childutils import listener" 2>/dev/null; then
    echo "  ✓ supervisor (system Python)"
else
    echo "  ✗ supervisor — MISSING from system Python!"
    FAILURES=$((FAILURES + 1))
fi

if which vina >/dev/null 2>&1; then
    echo "  ✓ autodock-vina"
else
    echo "  ✗ autodock-vina — MISSING!"
    FAILURES=$((FAILURES + 1))
fi

if which obabel >/dev/null 2>&1; then
    echo "  ✓ openbabel"
else
    echo "  ✗ openbabel — MISSING!"
    FAILURES=$((FAILURES + 1))
fi

echo ""

# ── API Import Test ──
echo "=== API Import Test (framework venv) ==="
cd /a0
API_MODULES=(
    "api.literature_search:LiteratureSearch"
    "api.admet_predict:AdmetPredict"
    "api.pharmacophore:PharmacophoreHandler"
    "api.qsar3d:QSAR3DHandler"
    "api.md_lite:MDLite"
    "api.docking_run:DockingRun"
    "api.clinical:ClinicalHandler"
    "api.homo_lumo:HomoLumoHandler"
    "api.rdkit_descriptors:RdkitDescriptorsHandler"
    "api.mol_plots:MolPlotsHandler"
)
for mod_cls in "${API_MODULES[@]}"; do
    mod="${mod_cls%%:*}"
    cls="${mod_cls##*:}"
    if /opt/venv-a0/bin/python -c "import sys; sys.path.insert(0,'/a0'); from $mod import $cls" 2>/dev/null; then
        echo "  ✓ $mod ($cls)"
    else
        echo "  ✗ $mod ($cls) — IMPORT FAILED!"
        FAILURES=$((FAILURES + 1))
    fi
done

echo ""

# ── Summary ──
echo "================================================"
if [ $FAILURES -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED — image is ready for release"
else
    echo "❌ $FAILURES CHECK(S) FAILED — fix before releasing!"
    echo "   Run this script: docker run --rm tajo9128/biodockify-pharma-ai:latest /exe/verify_packages.sh"
fi
echo "================================================"
exit $FAILURES

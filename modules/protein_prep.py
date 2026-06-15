"""Protein Preparation — fix PDB structures using pdbfixer (OpenMM ecosystem)."""
import os, sys, logging, tempfile, subprocess

log = logging.getLogger("protein_prep")

HAS_PDBFIXER = False
try:
    import pdbfixer
    from openmm.app import PDBFixer, PDBFile
    HAS_PDBFIXER = True
except ImportError:
    pass


def _ensure_pdbfixer():
    global HAS_PDBFIXER
    if HAS_PDBFIXER:
        return True
    log.info("pdbfixer not found — attempting auto-install")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "pdbfixer>=1.9"],
            timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        import pdbfixer
        from openmm.app import PDBFixer, PDBFile
        HAS_PDBFIXER = True
        log.info("pdbfixer auto-installed successfully")
        return True
    except Exception as e:
        log.error(f"pdbfixer auto-install failed: {e}")
        return False


def prepare_protein(pdb_input, output_path=None, ph=7.4):
    if not _ensure_pdbfixer():
        return {"status": "error", "error": "pdbfixer not installed and auto-install failed. Run: pip install pdbfixer"}

    from openmm.app import PDBFixer, PDBFile

    tmpdir = tempfile.mkdtemp(prefix="protein_prep_")
    tmp_input = os.path.join(tmpdir, "input.pdb")
    output = output_path or os.path.join(tmpdir, "prepared.pdb")
    try:
        if os.path.exists(str(pdb_input)):
            tmp_input = pdb_input
        else:
            with open(tmp_input, "w") as f:
                f.write(str(pdb_input))

        fixer = PDBFixer(filename=tmp_input)
        fixer.removeHeterogens(keepWater=False)
        fixer.findNonstandardResidues()
        fixer.replaceNonstandardResidues()
        fixer.findMissingResidues()
        fixer.missingResidues = {}
        fixer.findMissingAtoms()
        fixer.addMissingAtoms()
        fixer.addMissingHydrogens(ph)

        with open(output, "w") as f:
            PDBFile.writeFile(fixer.topology, fixer.positions, f)

        with open(output) as f:
            output_content = f.read()

        return {"status": "ok", "output_path": output, "ph": ph, "output_pdb": output_content}
    except Exception as e:
        log.exception("PDBFixer failed")
        return {"status": "error", "error": str(e)}
    finally:
        if os.path.exists(tmp_input) and tmp_input != pdb_input:
            try: os.remove(tmp_input)
            except: pass

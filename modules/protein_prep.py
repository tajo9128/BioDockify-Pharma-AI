"""Protein Preparation — fix PDB structures using pdbfixer (OpenMM ecosystem)."""
import os, logging, tempfile, uuid

log = logging.getLogger("protein_prep")

try:
    import pdbfixer
    from openmm.app import PDBFixer, PDBFile
    HAS_PDBFIXER = True
except ImportError:
    HAS_PDBFIXER = False


def prepare_protein(pdb_input, output_path=None, ph=7.4):
    """
    Prepare protein structure using pdbfixer.
    pdb_input: file path (str) OR raw PDB content (str)
    Returns validated structure with hydrogens, missing atoms filled.
    """
    if not HAS_PDBFIXER:
        return {"status": "error", "error": "pdbfixer not installed. Run: pip install pdbfixer"}

    tmpdir = tempfile.mkdtemp(prefix="protein_prep_")
    tmp_input = os.path.join(tmpdir, "input.pdb")
    try:
        # Accept both file paths and raw PDB content strings
        if os.path.exists(str(pdb_input)):
            tmp_input = pdb_input
        else:
            with open(tmp_input, "w") as f:
                f.write(str(pdb_input))

        fixer = PDBFixer(filename=tmp_input)

        # Remove water molecules
        fixer.removeHeterogens(keepWater=False)

        # Replace non-standard residues (e.g. MSE → MET, HIP → HIS)
        fixer.findNonstandardResidues()
        fixer.replaceNonstandardResidues()

        # Clear missing residue flags (pdbfixer fills gaps)
        fixer.findMissingResidues()
        fixer.missingResidues = {}

        # Add missing heavy atoms and hydrogens
        fixer.findMissingAtoms()
        fixer.addMissingAtoms()
        fixer.addMissingHydrogens(ph)

        output = output_path or os.path.join(tmpdir, "prepared.pdb")
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
            os.remove(tmp_input)
        if os.path.exists(output) and output != tmp_input:
            pass  # keep output for caller

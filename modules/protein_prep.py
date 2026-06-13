"""Protein Preparation — fix PDB structures using pdbfixer (OpenMM ecosystem)."""
import os, logging

log = logging.getLogger("protein_prep")

try:
    import pdbfixer
    from openmm.app import PDBFixer, PDBFile
    HAS_PDBFIXER = True
except ImportError:
    HAS_PDBFIXER = False


def prepare_protein(pdb_path, output_path=None, add_hydrogens=True, ph=7.4,
                    replace_nonstandard=True, add_missing_residues=True,
                    remove_water=True):
    if not HAS_PDBFIXER:
        return {"status": "error", "error": "pdbfixer not installed. Run: pip install pdbfixer"}
    if not os.path.exists(pdb_path):
        return {"status": "error", "error": f"PDB file not found: {pdb_path}"}

    try:
        fixer = PDBFixer(filename=pdb_path)

        if remove_water:
            fixer.removeHeterogens(keepWater=False)

        if replace_nonstandard:
            fixer.findNonstandardResidues()
            fixer.replaceNonstandardResidues()

        if add_missing_residues:
            fixer.findMissingResidues()
            fixer.missingResidues = {}

        if add_hydrogens:
            fixer.findMissingAtoms()
            fixer.addMissingAtoms()
            fixer.addMissingHydrogens(ph)

        output = output_path or pdb_path.replace(".pdb", "_prepared.pdb")
        with open(output, "w") as f:
            PDBFile.writeFile(fixer.topology, fixer.positions, f)

        return {"status": "ok", "output_path": output, "ph": ph}
    except Exception as e:
        log.exception("PDBFixer failed")
        return {"status": "error", "error": str(e)}

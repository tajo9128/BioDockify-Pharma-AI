"""
BioDockify MD Lite — Protein & Ligand Preparation

Production-grade preparation pipeline for OpenMM molecular dynamics.
Based on official OpenMM/PDBFixer best practices.

The canonical order of operations (from PDBFixer docs + OpenMM User Guide):
  1. findMissingResidues()        — identify chain breaks from SEQRES
  2. findNonstandardResidues()    — find modified residues (SEP, TPO, MSE…)
  3. replaceNonstandardResidues() — convert to standard parent (SEP→SER…)
  4. removeHeterogens()           — strip ligands/waters/ions (keep protein)
  5. findMissingAtoms()           — find missing heavy atoms
  6. addMissingAtoms()            — rebuild heavy atoms
  7. addMissingHydrogens(pH=7.0)  — add H atoms, assign protonation states

CRITICAL: createSystem() must receive the topology from the SAME object
that had hydrogens added. Passing pdb.topology (original, no H) is the
root cause of "No template found for residue X — missing N H atoms".
"""

import os
import logging
from typing import Optional, Tuple

log = logging.getLogger("md_lite.preparation")


def prepare_protein(pdb_path: str, output_path: str = None, pH: float = 7.0) -> dict:
    """Full protein preparation pipeline using PDBFixer.

    Args:
        pdb_path: Path to input PDB file (raw, from RCSB or docking).
        output_path: Where to write the prepared PDB. If None, derived from input.
        pH: pH for hydrogen addition (default 7.0, physiological).

    Returns:
        {"status": "ok", "atoms": N, "residues": N, "output": path}
        or {"status": "error", "error": "message"}
    """
    try:
        from pdbfixer import PDBFixer
        from openmm.app import PDBFile
    except ImportError as e:
        return {"status": "error",
                "error": f"PDBFixer/OpenMM not installed: {e}. "
                         "Install with: pip install pdbfixer openmm"}

    if output_path is None:
        base, ext = os.path.splitext(pdb_path)
        output_path = f"{base}_prepared.pdb"

    try:
        log.info(f"Preparing protein: {pdb_path}")

        # ── Step 1: Load with PDBFixer ──
        fixer = PDBFixer(filename=pdb_path)
        log.info(f"Loaded: {len(list(fixer.topology.residues()))} residues")

        # ── Step 2: Find and handle missing residues (chain breaks) ──
        fixer.findMissingResidues()
        missing_residues = list(fixer.missingResidues.keys())
        # Drop terminal gaps — modelling disordered tails is unreliable
        chains = list(fixer.topology.chains())
        if missing_residues and chains:
            terminal_keys = []
            for key in list(fixer.missingResidues.keys()):
                chain_idx, res_idx = key
                chain = chains[chain_idx] if chain_idx < len(chains) else None
                if chain and res_idx == 0:
                    terminal_keys.append(key)
                elif chain:
                    chain_residues = list(chain.residues())
                    if res_idx + len(fixer.missingResidues[key]) >= len(chain_residues):
                        terminal_keys.append(key)
            for key in terminal_keys:
                del fixer.missingResidues[key]
        log.info(f"Missing residues: {len(fixer.missingResidues)} (after terminal gap removal)")

        # ── Step 3: Find and replace non-standard residues ──
        fixer.findNonstandardResidues()
        fixer.replaceNonstandardResidues()
        log.info("Non-standard residues replaced")

        # ── Step 4: Remove heterogens (keep water for now — engine handles solvent) ──
        fixer.removeHeterogens(keepWater=True)
        log.info("Heterogens removed (water kept)")

        # ── Step 5: Find and add missing heavy atoms ──
        fixer.findMissingAtoms()
        missing_heavy = len(fixer.missingAtoms)
        missing_terminals = len(fixer.missingTerminals)
        log.info(f"Missing heavy atoms: {missing_heavy}, terminals: {missing_terminals}")

        fixer.addMissingAtoms()
        log.info("Missing atoms added")

        # ── Step 6: Add hydrogens at the specified pH ──
        fixer.addMissingHydrogens(pH=pH)
        log.info(f"Hydrogens added at pH {pH}")

        # ── Step 7: Write the prepared PDB ──
        with open(output_path, 'w') as f:
            PDBFile.writeFile(fixer.topology, fixer.positions, f)
        log.info(f"Prepared protein written: {output_path}")

        n_atoms = sum(1 for _ in fixer.topology.atoms())
        n_residues = sum(1 for _ in fixer.topology.residues())

        return {
            "status": "ok",
            "output": output_path,
            "atoms": n_atoms,
            "residues": n_residues,
            "missing_residues_found": len(missing_residues),
            "missing_atoms_found": missing_heavy,
            "pH": pH,
        }

    except Exception as e:
        log.error(f"Protein preparation failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


def prepare_ligand(ligand_path: str, output_path: str = None,
                   resname: str = "LIG") -> dict:
    """Prepare a small-molecule ligand for OpenMM MD.

    Handles SDF/MOL/MOL2 → RDKit Mol, PDBQT (Vina) → Meeko → RDKit Mol,
    PDB → RDKit Mol. Adds explicit H, generates 3D if missing.

    Args:
        ligand_path: Path to ligand file (.sdf, .mol2, .pdb, .pdbqt).
        output_path: Where to write prepared ligand PDB. If None, derived.
        resname: 3-letter residue name for the ligand (default "LIG").

    Returns:
        {"status": "ok", "output": path, "atoms": N, "smiles": "..."}
        or {"status": "error", "error": "message"}
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        return {"status": "error", "error": "RDKit not installed"}

    if output_path is None:
        base, ext = os.path.splitext(ligand_path)
        output_path = f"{base}_prepared.pdb"

    try:
        ext = os.path.splitext(ligand_path)[1].lower()
        mol = None

        # ── Read ligand from various formats ──
        if ext == '.pdbqt':
            try:
                from meeko import PDBQTMolecule, RDKitMolCreate
                pdbqt_mol = PDBQTMolecule.from_file(ligand_path)
                mols = RDKitMolCreate.from_pdbqt_mol(pdbqt_mol)
                mol = mols[0] if mols else None
                log.info("Ligand loaded from PDBQT via Meeko")
            except ImportError:
                mol = Chem.MolFromPDBFile(ligand_path, removeHs=False, sanitize=False)
                log.warning("Meeko not available — PDBQT read as PDB")
        elif ext in ('.sdf', '.mol'):
            suppl = Chem.SDMolSupplier(ligand_path, removeHs=False)
            mol = next(suppl, None) if suppl else None
            log.info("Ligand loaded from SDF")
        elif ext == '.mol2':
            mol = Chem.MolFromMol2File(ligand_path, removeHs=False, sanitize=False)
            log.info("Ligand loaded from MOL2")
        elif ext in ('.pdb', '.ent'):
            mol = Chem.MolFromPDBFile(ligand_path, removeHs=False, sanitize=False)
            log.info("Ligand loaded from PDB")
        elif ext in ('.smi', '.smiles'):
            with open(ligand_path) as f:
                smiles = f.readline().strip()
            mol = Chem.MolFromSmiles(smiles)
            log.info("Ligand loaded from SMILES")
        else:
            return {"status": "error", "error": f"Unsupported ligand format: {ext}"}

        if mol is None:
            return {"status": "error", "error": f"RDKit could not parse ligand: {ligand_path}"}

        # ── Sanitize ──
        try:
            Chem.SanitizeMol(mol)
        except Exception:
            log.warning("Sanitization failed — continuing")

        # ── Add explicit hydrogens ──
        mol = Chem.AddHs(mol)

        # ── Generate 3D if missing ──
        conf = mol.GetConformer() if mol.GetNumConformers() > 0 else None
        if conf is None or not conf.Is3D():
            AllChem.EmbedMolecule(mol, AllChem.ETKDG())
            AllChem.MMFFOptimizeMolecule(mol)
            log.info("Generated 3D coordinates for ligand")

        # ── Set residue name ──
        for atom in mol.GetAtoms():
            info = Chem.AtomPDBResidueInfo(resname, chainId=' ', residueNumber=1)
            atom.SetPDBResidueInfo(info)

        # ── Write as PDB ──
        Chem.MolToPDBFile(mol, output_path)
        log.info(f"Prepared ligand written: {output_path}")

        smiles = Chem.MolToSmiles(Chem.RemoveHs(mol))
        n_atoms = mol.GetNumAtoms()

        return {
            "status": "ok",
            "output": output_path,
            "atoms": n_atoms,
            "smiles": smiles,
            "resname": resname,
        }

    except Exception as e:
        log.error(f"Ligand preparation failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


def prepare_complex(protein_pdb: str, ligand_path: str,
                    output_path: str = None, pH: float = 7.0) -> dict:
    """Prepare a protein-ligand complex: prep protein + prep ligand + merge.

    Args:
        protein_pdb: Path to protein PDB.
        ligand_path: Path to ligand (.sdf, .mol2, .pdb, .pdbqt).
        output_path: Where to write the merged complex PDB.
        pH: pH for protein hydrogen addition.

    Returns:
        {"status": "ok", "output": path, ...}
    """
    if output_path is None:
        base = os.path.splitext(protein_pdb)[0]
        output_path = f"{base}_complex.pdb"

    protein_result = prepare_protein(protein_pdb, pH=pH)
    if protein_result["status"] != "ok":
        return protein_result

    ligand_result = prepare_ligand(ligand_path)
    if ligand_result["status"] != "ok":
        return ligand_result

    try:
        with open(output_path, 'w') as f:
            with open(protein_result["output"], 'r') as pf:
                for line in pf:
                    if not line.strip().startswith('END'):
                        f.write(line)
            with open(ligand_result["output"], 'r') as lf:
                for line in lf:
                    if not line.strip().startswith('END') and not line.strip().startswith('CRYST1'):
                        f.write(line)
            f.write("END\n")

        log.info(f"Complex written: {output_path}")
        return {
            "status": "ok",
            "output": output_path,
            "protein_atoms": protein_result.get("atoms"),
            "ligand_atoms": ligand_result.get("atoms"),
            "ligand_smiles": ligand_result.get("smiles"),
        }

    except Exception as e:
        return {"status": "error", "error": f"Complex merge failed: {e}"}

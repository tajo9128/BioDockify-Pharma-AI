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


def _load_pdbqt_ligand(pdbqt_path: str):
    """Parse a PDBQT file (AutoDock Vina output) into an RDKit Mol.

    PDBQT is PDB format with partial charges in columns 71-76 and an
    AutoDock atom type in columns 77-79. Standard PDB parsers choke on these
    extra columns. This function:
      1. Tries Meeko (best, preserves bond orders)
      2. Falls back to stripping PDBQT→PDB and reading with RDKit
      3. Picks MODEL 1 (best docking pose) from multi-model files

    Returns an RDKit Mol with 3D coordinates, or None on failure.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        return None

    # Strategy 1: Meeko (if installed)
    try:
        from meeko import PDBQTMolecule, RDKitMolCreate
        pdbqt_mol = PDBQTMolecule.from_file(pdbqt_path)
        mols = RDKitMolCreate.from_pdbqt_mol(pdbqt_mol)
        if mols and mols[0] is not None:
            log.info("Ligand loaded from PDBQT via Meeko")
            return mols[0]
    except ImportError:
        pass
    except Exception as e:
        log.debug(f"Meeko PDBQT parsing failed: {e}")

    # Strategy 2: Convert PDBQT→PDB by stripping extra columns, then RDKit
    pdb_lines = []
    in_model_1 = True
    model_count = 0
    with open(pdbqt_path, 'r', encoding='utf-8', errors='replace') as f:
        for raw_line in f:
            line = raw_line.rstrip()
            if line.startswith("MODEL"):
                model_count += 1
                if model_count > 1:
                    in_model_1 = False
                continue
            if line.startswith("ENDMDL"):
                if model_count >= 1:
                    break
                continue
            if not in_model_1:
                continue
            if line.startswith(("ATOM", "HETATM")):
                # PDBQT lines are 79+ chars; standard PDB is 80 with element at 76-78
                # Strip the partial charge (col 71-76) and AD type (col 77-79)
                # Keep only first 66 chars (through temp factor), then add element
                if len(line) >= 77:
                    # Extract element from AD atom type (last 1-2 chars of col 77-79)
                    ad_type = line[77:79].strip()
                    element = ad_type[0] if ad_type else line[12:14].strip()[0]
                    # Build standard PDB line: first 66 chars + padding + element
                    pdb_line = line[:66].ljust(76) + f" {element:>2}" + "\n"
                elif len(line) >= 54:
                    # Short PDBQT line — extract element from atom name
                    atom_name = line[12:16].strip()
                    element = ''.join(c for c in atom_name if c.isalpha())[:1]
                    pdb_line = line[:66].ljust(76) + f" {element:>2}" + "\n"
                else:
                    continue
                pdb_lines.append(pdb_line)
            elif line.startswith(("TER", "END")):
                pdb_lines.append(line + "\n")

    if not pdb_lines:
        log.warning("PDBQT file contains no ATOM/HETATM records")
        return None

    pdb_lines.append("END\n")
    pdb_block = "".join(pdb_lines)

    # Try RDKit PDB parser
    mol = Chem.MolFromPDBBlock(pdb_block, removeHs=False, sanitize=False)
    if mol is None:
        # Last resort: try with proximity bonding
        mol = Chem.MolFromPDBBlock(pdb_block, removeHs=False, sanitize=False,
                                    proximityBonding=True)
    if mol is None:
        log.warning("RDKit could not parse converted PDBQT→PDB block")
        return None

    # Sanitize carefully — docking outputs may have weird valences
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        # Try partial sanitization (skip valence check)
        try:
            Chem.SanitizeMol(mol, sanitizeOps=Chem.SanitizeFlags.SANITIZE_ALL ^
                             Chem.SanitizeFlags.SANITIZE_PROPERTIES)
        except Exception:
            pass

    # Assign bond orders from SMILES if possible (PDBQT loses bond order info)
    try:
        from rdkit.Chem import rdDetermineBonds
        rdDetermineBonds.DetermineBonds(mol)
        log.info("Bond orders determined from 3D coordinates")
    except (ImportError, Exception):
        pass

    log.info(f"Ligand loaded from PDBQT (converted to PDB): {mol.GetNumAtoms()} atoms")
    return mol


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
            mol = _load_pdbqt_ligand(ligand_path)
            if mol is None:
                return {"status": "error",
                        "error": f"Could not parse PDBQT ligand: {ligand_path}. "
                                 "Ensure it contains valid ATOM/HETATM lines from docking output."}
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
            try:
                Chem.SanitizeMol(mol, sanitizeOps=Chem.SanitizeFlags.SANITIZE_ALL ^
                                 Chem.SanitizeFlags.SANITIZE_PROPERTIES)
            except Exception:
                log.warning("Sanitization failed — continuing with raw mol")

        # ── Add explicit hydrogens ──
        mol = Chem.AddHs(mol, addCoords=True)

        # ── Generate 3D if missing (preserve docking pose if already 3D) ──
        has_3d = False
        if mol.GetNumConformers() > 0:
            conf = mol.GetConformer()
            has_3d = conf.Is3D()
        if not has_3d:
            result = AllChem.EmbedMolecule(mol, AllChem.ETKDG())
            if result == -1:
                AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
            AllChem.MMFFOptimizeMolecule(mol)
            log.info("Generated 3D coordinates for ligand")
        else:
            log.info("Preserving docking pose 3D coordinates")

        # ── Set residue name for PDB output ──
        for atom in mol.GetAtoms():
            atom_name = f" {atom.GetSymbol()}{atom.GetIdx()+1:<2}"[:4]
            info = Chem.AtomPDBResidueInfo()
            info.SetName(atom_name)
            info.SetResidueName(resname)
            info.SetResidueNumber(1)
            info.SetChainId("L")
            info.SetIsHeteroAtom(True)
            atom.SetMonomerInfo(info)

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
            "total_atoms": (protein_result.get("atoms") or 0) + (ligand_result.get("atoms") or 0),
            "ligand_smiles": ligand_result.get("smiles"),
            "message": "Protein-ligand complex prepared for MD",
        }

    except Exception as e:
        return {"status": "error", "error": f"Complex merge failed: {e}"}

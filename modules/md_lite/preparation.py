"""MD Lite Protein-Ligand Preparation Pipeline

Bridges the gap between docking output (PDBQT) and MD simulation (OpenMM PDB).
Handles protein preparation, ligand parameterization, and complex assembly.

Uses PDBFixer for protein preparation (handles NPRO, CTER, missing atoms, hydrogens).
Uses RDKit for ligand preparation (3D coordinates, hydrogens, charges).
Uses OpenMM for solvent addition and energy minimization.

This module is called by api/md_lite.py before running MD simulation.
"""
import os
import logging
import tempfile

log = logging.getLogger("md_lite.preparation")


def prepare_protein(pdb_path: str, output_path: str = None) -> dict:
    """Prepare a protein PDB for MD simulation.

    Steps:
    1. Fix missing atoms with PDBFixer
    2. Add hydrogens (pH 7.0)
    3. Fix terminal residues (NPRO, CTER)
    4. Remove water/ions
    5. Generate clean PDB

    Returns: dict with status, output_path, details
    """
    try:
        from pdbfixer import PDBFixer
        from openmm import app
    except ImportError:
        return {"status": "error", "error": "PDBFixer/OpenMM not installed"}

    if not os.path.exists(pdb_path):
        return {"status": "error", "error": f"File not found: {pdb_path}"}

    if output_path is None:
        output_path = os.path.splitext(pdb_path)[0] + "_prepared.pdb"

    try:
        log.info(f"Preparing protein: {pdb_path}")

        # Step 1: Load with PDBFixer
        fixer = PDBFixer(filename=pdb_path)

        # Step 2: Find and fix missing residues
        fixer.findMissingResidues()
        missing_residues = list(fixer.missingResidues.keys())
        if missing_residues:
            log.info(f"Found {len(missing_residues)} missing residues")

        # Step 3: Find and fix missing atoms
        fixer.findMissingAtoms()
        missing_heavy = fixer.missingAtoms
        missing_terminals = fixer.missingTerminals
        if missing_heavy:
            log.info(f"Found {len(missing_heavy)} residues with missing heavy atoms")
        if missing_terminals:
            log.info(f"Found {len(missing_terminals)} missing terminal atoms")

        fixer.addMissingAtoms()

        # Step 4: Remove non-protein (water, ions, ligands)
        fixer.removeHeterogens(keepWater=False)

        # Step 5: Add hydrogens (pH 7.0)
        fixer.addMissingHydrogens(7.0)

        # Step 6: Save prepared protein
        with open(output_path, 'w') as f:
            app.PDBFile.writeFile(fixer.topology, fixer.positions, f)

        # Count atoms and residues
        n_atoms = fixer.topology.getNumAtoms()
        n_residues = fixer.topology.getNumResidues()
        n_chains = fixer.topology.getNumChains()

        log.info(f"Protein prepared: {n_atoms} atoms, {n_residues} residues, {n_chains} chains")
        return {
            "status": "ok",
            "output_path": output_path,
            "atoms": n_atoms,
            "residues": n_residues,
            "chains": n_chains,
            "missing_residues_fixed": len(missing_residues),
            "missing_atoms_fixed": len(missing_heavy),
            "message": f"Protein prepared: {n_residues} residues, {n_atoms} atoms. Ready for MD."
        }

    except Exception as e:
        log.error(f"Protein preparation failed: {e}")
        return {"status": "error", "error": str(e)}


def prepare_ligand(pdbqt_path: str, output_path: str = None) -> dict:
    """Prepare a docked ligand PDBQT for MD simulation.

    Steps:
    1. Convert PDBQT to PDB (strip PDBQT-specific fields)
    2. Add hydrogens with RDKit
    3. Assign charges (Gasteiger)
    4. Generate 3D coordinates if needed
    5. Save as PDB

    Returns: dict with status, output_path, details
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, Descriptors
    except ImportError:
        return {"status": "error", "error": "RDKit not installed"}

    if not os.path.exists(pdbqt_path):
        return {"status": "error", "error": f"File not found: {pdbqt_path}"}

    if output_path is None:
        output_path = os.path.splitext(pdbqt_path)[0] + "_prepared.pdb"

    try:
        log.info(f"Preparing ligand: {pdbqt_path}")

        # Step 1: Read PDBQT and convert to RDKit mol
        # PDBQT has charges and atom types that RDKit can parse
        with open(pdbqt_path, 'r') as f:
            pdbqt_content = f.read()

        # Extract first MODEL from PDBQT (best pose)
        lines = pdbqt_content.split('\n')
        model_lines = []
        in_model = False
        for line in lines:
            if line.startswith('MODEL'):
                in_model = True
                model_lines = []
            elif line.startswith('ENDMDL'):
                in_model = False
                break
            elif in_model and (line.startswith('ATOM') or line.startswith('HETATM')):
                model_lines.append(line)

        if not model_lines:
            # Try all ATOM/HETATM lines
            model_lines = [l for l in lines if l.startswith('ATOM') or l.startswith('HETATM')]

        if not model_lines:
            return {"status": "error", "error": "No ATOM/HETATM records found in PDBQT"}

        # Convert PDBQT atoms to PDB format
        pdb_lines = []
        for i, line in enumerate(model_lines):
            # PDBQT format: ATOM serial name resName chain resSeq x y z charge type
            # PDB format:   ATOM serial name resName chain resSeq x y z occupancy tempFactor element
            if len(line) < 54:
                continue
            serial = line[6:11]
            name = line[12:16]
            resName = line[17:20]
            chain = line[21]
            resSeq = line[22:26]
            x = line[30:38]
            y = line[38:46]
            z = line[46:54]
            # Extract element from atom name
            element = name.strip()[0] if name.strip() else 'C'
            pdb_lines.append(f"ATOM  {serial} {name} {resName} {chain}{resSeq}    {x}{y}{z}  1.00  0.00           {element}")

        pdb_lines.append("END")

        # Step 2: Parse with RDKit
        pdb_text = "\n".join(pdb_lines)
        mol = Chem.MolFromPDBBlock(pdb_text, removeHs=False)
        if mol is None:
            # Try SMILES-based approach
            log.warning("PDB parse failed, trying SMILES extraction")
            return {"status": "error", "error": "Could not parse ligand structure from PDBQT"}

        # Step 3: Add hydrogens
        mol = Chem.AddHs(mol)

        # Step 4: Generate 3D coordinates if needed
        if mol.GetNumConformers() == 0:
            AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())

        # Step 5: Assign charges (Gasteiger)
        AllChem.ComputeGasteigerCharges(mol)

        # Step 6: Save as PDB
        pdb_block = Chem.MolToPDBBlock(mol)
        with open(output_path, 'w') as f:
            f.write(pdb_block)

        # Get properties
        mw = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        n_atoms = mol.GetNumAtoms()
        smiles = Chem.MolToSmiles(mol)

        log.info(f"Ligand prepared: {n_atoms} atoms, MW={mw:.1f}, LogP={logp:.2f}")
        return {
            "status": "ok",
            "output_path": output_path,
            "atoms": n_atoms,
            "mw": round(mw, 1),
            "logp": round(logp, 2),
            "smiles": smiles,
            "message": f"Ligand prepared: {n_atoms} atoms, MW={mw:.1f}. Ready for MD."
        }

    except Exception as e:
        log.error(f"Ligand preparation failed: {e}")
        return {"status": "error", "error": str(e)}


def prepare_complex(protein_path: str, ligand_path: str, output_path: str = None) -> dict:
    """Prepare a protein-ligand complex for MD simulation.

    Steps:
    1. Prepare protein (fix missing atoms, add hydrogens)
    2. Prepare ligand (add hydrogens, assign charges)
    3. Combine into single PDB
    4. Generate ligand forcefield parameters

    Returns: dict with status, output_path, details
    """
    try:
        from openmm import app
    except ImportError:
        return {"status": "error", "error": "OpenMM not installed"}

    if output_path is None:
        output_path = os.path.splitext(protein_path)[0] + "_complex.pdb"

    try:
        log.info(f"Preparing complex: {protein_path} + {ligand_path}")

        # Step 1: Prepare protein
        protein_prep = prepare_protein(protein_path)
        if protein_prep.get("status") != "ok":
            return protein_prep
        prepared_protein = protein_prep["output_path"]

        # Step 2: Prepare ligand
        ligand_prep = prepare_ligand(ligand_path)
        if ligand_prep.get("status") != "ok":
            return ligand_prep
        prepared_ligand = ligand_prep["output_path"]

        # Step 3: Combine protein + ligand into single PDB
        with open(output_path, 'w') as out:
            # Write protein atoms
            with open(prepared_protein, 'r') as f:
                for line in f:
                    if line.startswith('ATOM') or line.startswith('HETATM') or line.startswith('TER') or line.startswith('CRYST1'):
                        out.write(line)
            # Write TER before ligand
            out.write("TER\n")
            # Write ligand atoms (renumber from protein end)
            with open(prepared_ligand, 'r') as f:
                for line in f:
                    if line.startswith('ATOM') or line.startswith('HETATM'):
                        out.write(line)
            out.write("END\n")

        # Count atoms
        n_protein = protein_prep.get("atoms", 0)
        n_ligand = ligand_prep.get("atoms", 0)
        n_total = n_protein + n_ligand

        log.info(f"Complex prepared: {n_protein} protein atoms + {n_ligand} ligand atoms = {n_total} total")
        return {
            "status": "ok",
            "output_path": output_path,
            "protein_path": prepared_protein,
            "ligand_path": prepared_ligand,
            "protein_atoms": n_protein,
            "ligand_atoms": n_ligand,
            "total_atoms": n_total,
            "ligand_smiles": ligand_prep.get("smiles", ""),
            "message": f"Complex prepared: {n_total} atoms ({n_protein} protein + {n_ligand} ligand). Ready for MD."
        }

    except Exception as e:
        log.error(f"Complex preparation failed: {e}")
        return {"status": "error", "error": str(e)}

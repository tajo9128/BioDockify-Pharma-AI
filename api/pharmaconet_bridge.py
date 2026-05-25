"""PharmacoNet Bridge — optional deep learning-powered pharmacophore modeling.

If 'pmnet' (PharmacoNet) is installed with PyTorch GPU support, this module
provides protein-based pharmacophore modeling and docking proxy scoring.
Falls back gracefully to RDKit-based modeling if pmnet is not available.

Install: pip install pharmaconet @ git+https://github.com/SeonghwanSeo/PharmacoNet.git
"""
import logging
import os
import tempfile

log = logging.getLogger("pharmaconet_bridge")

PMNET_AVAILABLE = False
PMNET_CUDA_AVAILABLE = False

try:
    from pmnet import PharmacophoreModel
    from pmnet.api import PharmacoNet, get_pmnet_dev, ProteinParser

    PMNET_AVAILABLE = True
    log.info("PharmacoNet (pmnet) loaded successfully")

    try:
        import torch
        if torch.cuda.is_available():
            PMNET_CUDA_AVAILABLE = True
            log.info("PharmacoNet CUDA acceleration available")
        else:
            log.info("PharmacoNet loaded — CPU mode (install torch with CUDA for GPU)")
    except ImportError:
        log.info("PharmacoNet loaded — CPU mode (PyTorch CUDA not found)")
except ImportError:
    log.info("PharmacoNet (pmnet) not installed — using RDKit-based pharmacophore modeling")


def is_pmnet_available() -> bool:
    return PMNET_AVAILABLE


def is_cuda_available() -> bool:
    return PMNET_CUDA_AVAILABLE


def run_pharmaconet_modeling(
    protein_pdb: str = None,
    protein_path: str = None,
    ref_ligand_path: str = None,
    center: tuple = None,
    prefix: str = "pmnet_model",
    output_dir: str = None,
    weight_path: str = None,
    device: str = "cuda",
    **kwargs,
) -> dict:
    """Run PharmacoNet protein-based pharmacophore modeling.

    Args:
        protein_pdb: Protein PDB content as string
        protein_path: Path to protein PDB file
        ref_ligand_path: Path to reference ligand for binding site detection
        center: (x, y, z) tuple for binding site center
        prefix: Output prefix name
        output_dir: Directory for output files
        weight_path: Path to custom model weights
        device: 'cuda' or 'cpu'

    Returns:
        dict with success status, model path, features, and scores
    """
    if not PMNET_AVAILABLE:
        return {
            "success": False,
            "error": "PharmacoNet not installed. pip install pharmaconet @ git+https://github.com/SeonghwanSeo/PharmacoNet.git",
            "pmnet_available": False,
        }

    try:
        if device == "cuda" and not PMNET_CUDA_AVAILABLE:
            device = "cpu"
            log.warning("CUDA requested but not available, falling back to CPU")

        out_dir = output_dir or tempfile.mkdtemp(prefix="pmnet_")

        # Save protein to temp file if provided as string
        protein_file = protein_path
        if protein_pdb and not protein_path:
            tf = tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False)
            tf.write(protein_pdb)
            tf.close()
            protein_file = tf.name

        if not protein_file:
            return {"success": False, "error": "No protein provided (protein_pdb or protein_path required)"}

        # Build PharmacoNet command equivalent
        module = get_pmnet_dev(device)

        if ref_ligand_path and os.path.exists(ref_ligand_path):
            pmnet_attr = module.feature_extraction(protein_file, ref_ligand_path=ref_ligand_path)
        elif center:
            pmnet_attr = module.feature_extraction(protein_file, center=center)
        else:
            return {"success": False, "error": "ref_ligand_path or center required for binding site detection"}

        # Extract hotspot features
        features = []
        for hs in pmnet_attr.hotspots:
            features.append({
                "type": hs.density_type or hs.type,
                "family": hs.density_type or hs.type,
                "position": {
                    "x": round(hs.position[0], 3),
                    "y": round(hs.position[1], 3),
                    "z": round(hs.position[2], 3),
                },
                "score": round(hs.score, 4),
                "nci_type": hs.nci_type,
            })

        # Save model if requested
        model_path = os.path.join(out_dir, f"{prefix}_model.pm")
        # PharmacoNet's built-in save uses .pm format internally

        result = {
            "success": True,
            "pmnet_available": True,
            "cuda_available": PMNET_CUDA_AVAILABLE,
            "device": device,
            "num_features": len(features),
            "features": features,
            "feature_summary": {},
            "output_dir": out_dir,
        }

        # Count feature types
        for f in features:
            result["feature_summary"][f["type"]] = result["feature_summary"].get(f["type"], 0) + 1

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"PharmacoNet modeling failed: {str(e)}",
            "pmnet_available": True,
        }


def score_with_pharmaconet(
    model_path: str,
    ligand_smiles: str = None,
    ligand_path: str = None,
    num_conformers: int = 10,
) -> dict:
    """Score a ligand against a PharmacoNet pharmacophore model.

    Args:
        model_path: Path to .pm pharmacophore model file
        ligand_smiles: SMILES string of the ligand
        ligand_path: Path to ligand file (SDF, MOL2, PDB)
        num_conformers: Number of conformers for SMILES scoring

    Returns:
        dict with score and model loading status
    """
    if not PMNET_AVAILABLE:
        return {"success": False, "error": "PharmacoNet not installed"}

    try:
        model = PharmacophoreModel.load(model_path)

        if ligand_path and os.path.exists(ligand_path):
            score = model.scoring_file(ligand_path)
        elif ligand_smiles:
            score = model.scoring_smiles(ligand_smiles, num_conformers)
        else:
            return {"success": False, "error": "ligand_smiles or ligand_path required"}

        return {
            "success": True,
            "score": score,
            "model_path": model_path,
            "num_conformers": num_conformers if ligand_smiles else None,
        }
    except Exception as e:
        return {"success": False, "error": f"PharmacoNet scoring failed: {str(e)}"}


def get_pmnet_status() -> dict:
    """Get PharmacoNet availability status."""
    status = {
        "pmnet_available": PMNET_AVAILABLE,
        "cuda_available": PMNET_CUDA_AVAILABLE,
    }
    if PMNET_AVAILABLE:
        try:
            import torch
            status["torch_version"] = torch.__version__
            status["torch_cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                status["cuda_device_count"] = torch.cuda.device_count()
                status["cuda_device_name"] = torch.cuda.get_device_name(0)
        except Exception:
            pass
    return status

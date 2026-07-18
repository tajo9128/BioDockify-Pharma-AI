"""3D-QSAR API — Molecular Interaction Fields + PLS regression.
Based on Open3DQSAR + Py-CoMFA merged engine."""
from helpers.api import ApiHandler, Request
import os, json, uuid, logging, numpy as np
from datetime import datetime

log = logging.getLogger("qsar3d_api")
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "qsar3d_models")
os.makedirs(MODELS_DIR, exist_ok=True)


class QSAR3DHandler(ApiHandler):
    """3D-QSAR API handler — build, predict, list, delete models."""
    
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "build": return self._build(input)
        if action == "predict": return self._predict(input)
        if action == "models": return self._models(input)
        if action == "delete": return self._delete(input)
        if action == "info": return self._info()
        return {
            "actions": ["build", "predict", "models", "delete", "info"],
            "hint": "POST with action=build to create a 3D-QSAR model, action=predict to predict activity"
        }
    
    def _info(self):
        """Get 3D-QSAR engine information."""
        return {
            "status": "ok",
            "engine": "BioDockify QSAR Engine v2.0",
            "based_on": ["Open3DQSAR (Tosco & Balle)", "Py-CoMFA (Ragno, Sapienza)", "OPERA (Mansouri, US EPA)"],
            "modes": {
                "3d": "3D-QSAR with Molecular Interaction Fields (steric + electrostatic)",
                "2d": "2D-QSAR with molecular descriptors (50+ RDKit descriptors, OPERA-style)",
            },
            "features": [
                "3D-QSAR: Molecular Interaction Fields (steric + electrostatic)",
                "2D-QSAR: 50+ molecular descriptors (replaces PaDEL-Java)",
                "Structure standardization (OPERA-style curation)",
                "Salt removal, charge neutralization, tautomer canonicalization",
                "PLS regression with optimal component search",
                "Leave-One-Out cross-validation",
                "Leave-5-Out cross-validation (100 iterations)",
                "Y-scrambling for chance correlation check",
                "Applicability domain with confidence scoring (OPERA-style)",
                "Jaccard/Tanimoto structural similarity",
                "MCS-based molecular alignment",
                "Descriptor importance ranking",
                "3D contour plot data export",
                "Activity prediction for new molecules",
            ],
        }
    
    def _build(self, input: dict):
        """Build a 3D-QSAR model from SMILES + activity data."""
        smiles = input.get("smiles", [])
        activity = input.get("activity", [])
        test_fraction = input.get("test_fraction", 0.2)
        grid_spacing = input.get("grid_spacing", 2.0)
        grid_margin = input.get("grid_margin", 5.0)
        field_types = input.get("field_types", ["steric", "electrostatic"])
        reference_smiles = input.get("reference_smiles", None)
        name = input.get("name", "3D-QSAR Model")
        mode = input.get("mode", "3d")
        
        if not smiles or not activity:
            return {"error": "smiles and activity lists are required"}
        if len(smiles) < 10:
            return {"error": "Need at least 10 molecules for 3D-QSAR"}
        if len(smiles) != len(activity):
            return {"error": "SMILES and activity lists must have equal length"}
        
        try:
            from modules.qsar3d.builder import QSAR3DBuilder
            
            builder = QSAR3DBuilder(
                grid_spacing=grid_spacing,
                grid_margin=grid_margin,
                field_types=field_types,
                mode=mode,
            )
            
            if mode == '2d':
                stats = builder.build_2d_from_smiles(
                    smiles, activity,
                    test_fraction=test_fraction,
                )
            else:
                stats = builder.build_from_smiles(
                    smiles, activity,
                    test_fraction=test_fraction,
                    reference_smiles=reference_smiles,
                )
            
            # Save model to file
            model_id = stats.get('model_id', str(uuid.uuid4())[:8])
            model_path = os.path.join(MODELS_DIR, f"{model_id}.pkl")
            builder.save_model(model_path)
            
            # Save metadata
            metadata = {
                "model_id": model_id,
                "name": name,
                "mode": mode,
                "field_types": field_types,
                "r2": stats.get('r2'),
                "q2": stats.get('q2'),
                "r2_pred": stats.get('r2_pred'),
                "n_components": stats.get('n_components'),
                "n_molecules": stats.get('n_molecules'),
                "model_path": model_path,
                "created_at": datetime.now().isoformat(),
                "grid_info": stats.get('grid_info', {}),
                "l5o": stats.get('l5o', {}),
                "y_scrambling": stats.get('y_scrambling', {}),
            }
            
            metadata_path = os.path.join(MODELS_DIR, f"{model_id}_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return_result = {
                "status": "ok",
                "model_id": model_id,
                "name": name,
                "mode": mode,
                "r2": stats.get('r2'),
                "q2": stats.get('q2'),
                "r2_pred": stats.get('r2_pred'),
                "n_components": stats.get('n_components'),
                "n_molecules": stats.get('n_molecules'),
                "message": f"3D-QSAR model built successfully. r²={stats.get('r2')}, q²={stats.get('q2')}"
            }
            # ── AUTO-STORE ──
            try:
                from modules.knowledge.auto_store import auto_store
                auto_store("qsar3d", f"QSAR Model: {name} ({mode})", return_result,
                           source="3D-QSAR Engine", tags=["qsar", mode, name[:20]])
            except Exception:
                pass
            return return_result
        
        except Exception as e:
            log.error(f"[QSAR3D] Build failed: {e}", exc_info=True)
            return {"error": f"Model build failed: {str(e)[:200]}"}
    
    def _predict(self, input: dict):
        """Predict activity for new molecules using a trained model."""
        model_id = input.get("model_id", "")
        smiles = input.get("smiles", [])
        
        if not model_id:
            return {"error": "model_id is required"}
        if not smiles:
            return {"error": "smiles list is required"}
        
        try:
            model_path = os.path.join(MODELS_DIR, f"{model_id}.pkl")
            if not os.path.exists(model_path):
                return {"error": "Model not found"}
            
            from modules.qsar3d.builder import QSAR3DBuilder
            builder = QSAR3DBuilder.load_model(model_path)
            result = builder.predict(smiles)
            
            return {
                "status": "ok",
                "model_id": model_id,
                "predictions": result.get("predictions", []),
                "confidence": result.get("confidence", []),
                "applicability_domain": result.get("applicability_domain", []),
            }
        
        except Exception as e:
            log.error(f"[QSAR3D] Predict failed: {e}", exc_info=True)
            return {"error": f"Prediction failed: {str(e)[:200]}"}
    
    def _models(self, input: dict):
        """List available 3D-QSAR models."""
        try:
            models = []
            for f in os.listdir(MODELS_DIR):
                if f.endswith("_metadata.json"):
                    metadata_path = os.path.join(MODELS_DIR, f)
                    with open(metadata_path, 'r') as file:
                        metadata = json.load(file)
                        models.append({
                            "model_id": metadata.get("model_id"),
                            "name": metadata.get("name"),
                            "mode": metadata.get("mode"),
                            "r2": metadata.get("r2"),
                            "q2": metadata.get("q2"),
                            "n_molecules": metadata.get("n_molecules"),
                            "created_at": metadata.get("created_at"),
                        })
            
            return {
                "status": "ok",
                "models": models,
                "count": len(models),
            }
        
        except Exception as e:
            log.error(f"[QSAR3D] List models failed: {e}", exc_info=True)
            return {"error": f"Failed to list models: {str(e)[:200]}"}
    
    def _delete(self, input: dict):
        """Delete a 3D-QSAR model."""
        model_id = input.get("model_id", "")
        
        if not model_id:
            return {"error": "model_id is required"}
        
        try:
            model_path = os.path.join(MODELS_DIR, f"{model_id}.pkl")
            metadata_path = os.path.join(MODELS_DIR, f"{model_id}_metadata.json")
            
            if os.path.exists(model_path):
                os.remove(model_path)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            return {
                "status": "ok",
                "message": f"Model {model_id} deleted",
            }
        
        except Exception as e:
            log.error(f"[QSAR3D] Delete failed: {e}", exc_info=True)
            return {"error": f"Failed to delete model: {str(e)[:200]}"}

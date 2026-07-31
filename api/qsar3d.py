"""3D-QSAR API — Molecular Interaction Fields + PLS regression.
Based on Open3DQSAR + Py-CoMFA merged engine."""
from helpers.api import ApiHandler, Request
from helpers import files
import asyncio, os, json, uuid, logging, numpy as np
from datetime import datetime

log = logging.getLogger("qsar3d_api")
MODELS_DIR = files.get_abs_path("data/qsar3d_models")
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
        if action == "ml_compare": return self._ml_compare(input)
        if action == "fingerprint": return self._fingerprint(input)
        if action == "descriptors": return self._descriptors(input)
        return {
            "actions": ["build", "predict", "models", "delete", "info",
                        "ml_compare", "fingerprint", "descriptors"],
            "hint": "POST with action=ml_compare to train & compare 10+ ML models, action=fingerprint for Morgan FPs"
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
    
    async def _build(self, input: dict):
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

        def _do_build():
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

        return await asyncio.to_thread(_do_build)

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

    async def _ml_compare(self, input: dict):
        """Train & compare 20+ ML models on molecular fingerprints or descriptors.

        Full Omixium QSAR pipeline with EDA, model comparison, actual vs predicted,
        feature importance, and fingerprint bit interpretation.

        Input: smiles (list), activity (list), feature_type (fingerprint|descriptors),
               target_names (optional list), test_fraction (float),
               test_smiles (optional list for prediction validation)
        Returns: model comparison table, plots, best model, feature importance.
        """
        smiles = input.get("smiles", [])
        activity = input.get("activity", [])
        feature_type = input.get("feature_type", "fingerprint")
        target_names = input.get("target_names", None)
        test_fraction = input.get("test_fraction", 0.2)
        test_smiles = input.get("test_smiles", None)

        if not smiles or not activity:
            return {"error": "smiles and activity lists required"}
        if len(smiles) != len(activity):
            return {"error": "smiles and activity must have equal length"}
        if len(smiles) < 20:
            return {"error": "Need at least 20 molecules for multi-model comparison"}

        def _do_ml_compare():
          try:
            from modules.qsar3d.ml_models import (
                generate_morgan_fingerprints, calculate_descriptors,
                train_and_compare, get_feature_importance,
                generate_eda_plots, generate_actual_vs_predicted_plots,
                generate_model_comparison_chart, interpret_fingerprint_bits,
            )
            import numpy as np

            # Generate features
            if feature_type == "descriptors":
                X, feature_names, valid_idx = calculate_descriptors(smiles)
            else:
                X, valid_idx = generate_morgan_fingerprints(smiles)
                feature_names = [f"Bit_{i}" for i in range(X.shape[1])]

            # Align activity to valid molecules
            y = np.array([float(activity[i]) for i in valid_idx])

            if len(X) < 20:
                return {"error": f"Only {len(X)} valid molecules. Need at least 20."}

            # EDA plots
            eda_plots = generate_eda_plots(
                [smiles[i] for i in valid_idx], y, target_names
            )

            # Train & compare
            result = train_and_compare(X, y, target_names=target_names,
                                       test_fraction=test_fraction)

            # Feature importance for best model
            best_model_name = None
            best_r2 = -999
            for t_name in result.get("target_names", []):
                info = result["best_per_target"].get(t_name, {})
                if info.get("r2", -999) > best_r2:
                    best_r2 = info["r2"]
                    best_model_name = info.get("model")

            importance = []
            if best_model_name and best_model_name in result.get("trained_models", {}):
                importance = get_feature_importance(
                    result["trained_models"][best_model_name],
                    best_model_name, feature_names, top_n=15
                )

            # Actual vs Predicted plots
            avp_plots = generate_actual_vs_predicted_plots(
                result.get("predictions", {}), result.get("target_names", []), top_n_models=5
            )

            # Model comparison chart
            comp_chart = generate_model_comparison_chart(result.get("results", []))

            # Fingerprint bit interpretation
            fp_interpretation = []
            if feature_type == "fingerprint" and best_model_name:
                sample_smiles = smiles[valid_idx[0]] if valid_idx else smiles[0]
                fp_interpretation = interpret_fingerprint_bits(
                    result["trained_models"].get(best_model_name),
                    best_model_name, feature_names, sample_smiles, top_n=10
                )

            # Build comparison table
            comparison = []
            for r in result.get("results", []):
                if r.get("r2") is not None:
                    comparison.append(r)
            comparison.sort(key=lambda r: r["r2"], reverse=True)

            response = {
                "status": "ok",
                "feature_type": feature_type,
                "n_molecules": len(X),
                "n_features": X.shape[1],
                "n_models_tested": result.get("n_models_tested", 0),
                "comparison": comparison,
                "best_per_target": result.get("best_per_target", {}),
                "feature_importance": importance,
                "fingerprint_interpretation": fp_interpretation,
                "eda_plots": eda_plots,
                "actual_vs_predicted_plots": avp_plots,
                "model_comparison_chart": comp_chart,
                "message": f"Compared {result.get('n_models_tested', 0)} models on {len(X)} molecules "
                           f"({X.shape[1]} features). Best: {best_model_name} (R²={best_r2})",
            }

            # Auto-store
            try:
                from modules.knowledge.auto_store import auto_store
                auto_store("qsar3d", f"QSAR ML Comparison: {feature_type}", response,
                           source="QSAR Multi-Model", tags=["qsar", "ml", feature_type])
            except Exception:
                pass

            return response

          except Exception as e:
            log.error(f"[QSAR] ML compare failed: {e}", exc_info=True)
            return {"error": f"ML comparison failed: {str(e)[:200]}"}

        return await asyncio.to_thread(_do_ml_compare)

    def _fingerprint(self, input: dict):
        """Generate Morgan fingerprints for molecules.

        Input: smiles (list), fp_size (int, default 2048), radius (int, default 2)
        Returns: fingerprint matrix, bit statistics, active bit positions.
        """
        smiles = input.get("smiles", [])
        fp_size = input.get("fp_size", 2048)
        radius = input.get("radius", 2)

        if not smiles:
            return {"error": "smiles list required"}

        try:
            from modules.qsar3d.ml_models import generate_morgan_fingerprints
            X, valid_idx = generate_morgan_fingerprints(smiles, fp_size=fp_size, radius=radius)

            # Statistics
            bits_per_mol = X.sum(axis=1)
            bit_frequency = X.sum(axis=0)

            return {
                "status": "ok",
                "n_molecules": len(valid_idx),
                "fp_size": fp_size,
                "radius": radius,
                "avg_bits_per_molecule": round(float(bits_per_mol.mean()), 1),
                "total_active_bits": int((bit_frequency > 0).sum()),
                "bit_density": round(float((bit_frequency > 0).mean()), 4),
                "valid_indices": valid_idx,
            }
        except Exception as e:
            return {"error": str(e)}

    def _descriptors(self, input: dict):
        """Calculate 50+ RDKit molecular descriptors.

        Input: smiles (list)
        Returns: descriptor matrix, descriptor names, statistics.
        """
        smiles = input.get("smiles", [])

        if not smiles:
            return {"error": "smiles list required"}

        try:
            from modules.qsar3d.ml_models import calculate_descriptors
            import numpy as np

            X, names, valid_idx = calculate_descriptors(smiles)

            # Statistics per descriptor
            stats = []
            for i, name in enumerate(names):
                col = X[:, i]
                stats.append({
                    "descriptor": name,
                    "mean": round(float(col.mean()), 4),
                    "std": round(float(col.std()), 4),
                    "min": round(float(col.min()), 4),
                    "max": round(float(col.max()), 4),
                })

            return {
                "status": "ok",
                "n_molecules": len(valid_idx),
                "n_descriptors": len(names),
                "descriptor_names": names,
                "statistics": stats,
                "valid_indices": valid_idx,
            }
        except Exception as e:
            return {"error": str(e)}

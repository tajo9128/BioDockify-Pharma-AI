"""Self-Healing Engine — PIVOT/REFINE auto-recovery for docking, QSAR, statistics, literature."""
from helpers.api import ApiHandler, Request, Response
from helpers import files
import os, logging, glob

log = logging.getLogger("self_heal")
JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


def _heal_docking(job_id: str, error_type: str) -> dict:
    """Auto-recover failed docking jobs."""
    job_dir = os.path.join(JOBS_DIR, job_id)
    if not os.path.isdir(job_dir):
        return {"action": "pivot", "reason": f"Job directory {job_id} not found", "steps": []}

    if error_type == "no_poses" or "parse_pdbqt" in error_type:
        # REFINE: expand grid, increase exhaustiveness, re-prepare
        return {
            "action": "refine",
            "reason": "No binding poses or bad PDBQT — expanding grid and re-preparing",
            "steps": [
                {"step": 1, "action": "expand_grid", "detail": "Increase grid size by 10A each dimension, increase exhaustiveness to 12"},
                {"step": 2, "action": "reprepare_receptor", "detail": "Re-run obabel -xr on protein.pdb"},
                {"step": 3, "action": "reprepare_ligand", "detail": "Re-prepare ligand with meeko or RDKit fallback"},
                {"step": 4, "action": "rerun_vina", "detail": "Re-run Vina with expanded grid"},
            ],
        }
    if error_type == "high_energy" or "best_energy > -5":
        # PIVOT: switch to GNINA CNN scoring
        return {
            "action": "refine",
            "reason": "Vina energies too weak — switching to GNINA CNN scoring",
            "steps": [
                {"step": 1, "action": "run_gnina", "detail": "Run GNINA with cnn_scoring=rescore on same PDBQT"},
                {"step": 2, "action": "compare_scores", "detail": "Compare Vina vs GNINA scores"},
            ],
        }
    if "gnina_failed" in error_type:
        return {
            "action": "pivot",
            "reason": "GNINA unavailable or failed — proceeding with Vina results only",
            "steps": [{"step": 1, "action": "use_vina_only", "detail": "Accept Vina results, note GNINA unavailable"}],
        }
    if "timeout" in error_type:
        return {
            "action": "refine",
            "reason": "Docking timed out — reducing grid size and exhaustiveness",
            "steps": [
                {"step": 1, "action": "reduce_grid", "detail": "Reduce grid to 15x15x15, exhaustiveness to 4"},
                {"step": 2, "action": "rerun_vina", "detail": "Re-run with reduced parameters"},
            ],
        }
    return {"action": "pivot", "reason": f"Unhandled docking error: {error_type}", "steps": []}


def _heal_qsar(job_id: str, error_type: str) -> dict:
    """Auto-recover failed QSAR training/prediction."""
    model_order = ["RandomForest", "GradientBoosting", "SVR", "PLS", "Ridge", "Lasso"]

    if "low_r2" in error_type or "cv_r2 < 0.3" in error_type:
        return {
            "action": "refine",
            "reason": "Low CV R² — switching models and trying different descriptors",
            "steps": [
                {"step": 1, "action": "switch_model", "detail": f"Try next model in order: {model_order}"},
                {"step": 2, "action": "add_descriptors", "detail": "Include all descriptor groups (physicochemical + topological + electronic + fragment)"},
                {"step": 3, "action": "retrain", "detail": "Re-train with expanded feature set"},
            ],
        }
    if "no_valid" in error_type or "invalid_smiles" in error_type:
        return {
            "action": "pivot",
            "reason": "Invalid SMILES in dataset — need clean input",
            "steps": [{"step": 1, "action": "clean_dataset", "detail": "Remove failed SMILES, re-import"}],
        }
    return {"action": "pivot", "reason": f"Unhandled QSAR error: {error_type}", "steps": []}


def _heal_stats(error_type: str) -> dict:
    """Auto-recover failed statistical tests."""
    if "normality_failed" in error_type or "not_normal" in error_type:
        return {
            "action": "refine",
            "reason": "Normality assumption violated — switching to non-parametric equivalent",
            "steps": [
                {"step": 1, "action": "t_test_to_mann_whitney", "detail": "Switch independent t-test → Mann-Whitney U"},
                {"step": 2, "action": "anova_to_kruskal_wallis", "detail": "Switch ANOVA → Kruskal-Wallis"},
            ],
        }
    if "variance" in error_type or "heteroscedastic" in error_type:
        return {
            "action": "refine",
            "reason": "Variance homogeneity violated — switching to Welch correction",
            "steps": [{"step": 1, "action": "use_welch_ttest", "detail": "Use Welch's t-test (unequal variance)"}],
        }
    if "power_low" in error_type:
        return {
            "action": "pivot",
            "reason": "Statistical power too low — need larger sample size",
            "steps": [{"step": 1, "action": "report_limitation", "detail": "Report result with power limitation caveat"}],
        }
    return {"action": "pivot", "reason": f"Unhandled stats error: {error_type}", "steps": []}


def _heal_literature(error_type: str) -> dict:
    """Auto-recover literature search failures."""
    if "no_results" in error_type or "zero_papers" in error_type:
        return {
            "action": "refine",
            "reason": "No papers found — expanding search terms and databases",
            "steps": [
                {"step": 1, "action": "expand_query", "detail": "Add synonyms, broader terms, MeSH terms"},
                {"step": 2, "action": "add_database", "detail": "Add Semantic Scholar and Google Scholar"},
                {"step": 3, "action": "retry_search", "detail": "Re-run search with expanded scope"},
            ],
        }
    return {"action": "pivot", "reason": f"Unhandled literature error: {error_type}", "steps": []}


class SelfHealHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "analyze")

        if action == "analyze":
            domain = input.get("domain", "docking")
            error_type = input.get("error_type", "unknown")
            job_id = input.get("job_id", "")

            if domain == "docking":
                result = _heal_docking(job_id, error_type)
            elif domain == "qsar":
                result = _heal_qsar(job_id, error_type)
            elif domain == "stats" or domain == "statistics":
                result = _heal_stats(error_type)
            elif domain == "literature":
                result = _heal_literature(error_type)
            else:
                result = {"action": "pivot", "reason": f"Unknown domain: {domain}", "steps": []}

            result["domain"] = domain
            result["error_type"] = error_type
            result["job_id"] = job_id
            return {"success": True, **result}

        if action == "domains":
            return {
                "domains": {
                    "docking": ["no_poses", "parse_pdbqt", "high_energy", "gnina_failed", "timeout"],
                    "qsar": ["low_r2", "no_valid", "invalid_smiles"],
                    "statistics": ["normality_failed", "variance", "power_low"],
                    "literature": ["no_results", "zero_papers"],
                },
                "actions": ["refine", "pivot"],
                "max_retries": 3,
            }

        return {"error": f"Unknown action: {action}"}

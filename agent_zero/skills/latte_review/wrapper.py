"""
LatteReview Integration Wrapper
"""
import os
import sys
import asyncio
import pandas as pd
import traceback
from typing import Optional, List, Dict, Any
from loguru import logger
from pathlib import Path
import threading

LATTE_AVAILABLE = False

# --- Dynamic Import for External Submodule ---
# We point to the cloned repo in _external/LatteReview
LATTE_DIR = Path(os.path.abspath(__file__)).parent.parent.parent.parent / "_external" / "LatteReview"
if str(LATTE_DIR) not in sys.path:
    sys.path.insert(0, str(LATTE_DIR))

try:
    from lattereview.providers import LiteLLMProvider
    from lattereview.agents import TitleAbstractReviewer, ScoringReviewer, AbstractionReviewer
    from lattereview.workflows import ReviewWorkflow
    LATTE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LatteReview not available: {e}")


class LatteReviewSkill:
    """
    Skill wrapper for LatteReview framework.
    """
    def __init__(self):
        if not LATTE_AVAILABLE:
             logger.error("LatteReview dependencies missing. Skill cannot be fully initialized.")
             self.available = False
             return
        self.available = True
            
        # Default Model Setup for LM Studio
        self.lm_studio_base = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        self.default_model = os.getenv("LATTE_MODEL", "openai/local-model")
        
    def _get_provider(self, model: Optional[str] = None):
        """Helper to get a configured LiteLLMProvider."""
        target_model = model or self.default_model
        # Use LiteLLMProvider which is model-agnostic
        return LiteLLMProvider(
            model=target_model,
            api_base=self.lm_studio_base,
            api_key="lm-studio" # Dummy key for local
        )

    def screen_papers(self, 
                     input_path: str, 
                     inclusion_criteria: str,
                     exclusion_criteria: str,
                     output_path: Optional[str] = None) -> str:
        """
        Perform Title/Abstract Screening on a CSV file.
        """
        data = pd.read_csv(input_path)
        reviewer = TitleAbstractReviewer(
            provider=self._get_provider(),
            name="Screener",
            backstory="A precise systematic reviewer.",
            inclusion_criteria=inclusion_criteria,
            exclusion_criteria=exclusion_criteria
        )
        
        workflow = ReviewWorkflow(
            workflow_schema=[{
                "round": 'Screening',
                "reviewers": [reviewer],
                "text_inputs": ["title", "abstract"]
            }]
        )
        
        return self._run_workflow(workflow, data, input_path, output_path, "screened")

    def score_papers(self,
                    input_path: str,
                    scoring_task: str,
                    scoring_set: List[int],
                    scoring_rules: str,
                    output_path: Optional[str] = None) -> str:
        """
        Assign numerical scores to papers based on custom rules.
        """
        data = pd.read_csv(input_path)
        reviewer = ScoringReviewer(
            provider=self._get_provider(),
            name="Scorer",
            backstory="An expert evaluator.",
            scoring_task=scoring_task,
            scoring_set=scoring_set,
            scoring_rules=scoring_rules
        )
        
        workflow = ReviewWorkflow(
            workflow_schema=[{
                "round": 'Scoring',
                "reviewers": [reviewer],
                "text_inputs": ["title", "abstract"]
            }]
        )
        
        return self._run_workflow(workflow, data, input_path, output_path, "scored")

    def abstract_papers(self,
                       input_path: str,
                       abstraction_keys: Dict[str, Any],
                       key_descriptions: Dict[str, str],
                       output_path: Optional[str] = None) -> str:
        """
        Extract specific data points (keys) from papers.
        """
        data = pd.read_csv(input_path)
        reviewer = AbstractionReviewer(
            provider=self._get_provider(),
            name="Abstractor",
            backstory="A detail-oriented data extractor.",
            abstraction_keys=abstraction_keys,
            key_descriptions=key_descriptions,
            reasoning=None # Abstraction reviewer doesn't use reasoning by default in Latte
        )
        
        workflow = ReviewWorkflow(
            workflow_schema=[{
                "round": 'Abstraction',
                "reviewers": [reviewer],
                "text_inputs": ["title", "abstract"]
            }]
        )
        
        return self._run_workflow(workflow, data, input_path, output_path, "abstracted")

    def _run_workflow(self, workflow, data, input_path, output_path, prefix) -> str:
        """Helper to run workflow and save results."""
        logger.info(f"Running LatteReview {prefix} on {len(data)} papers...")
        try:
            results = asyncio.run(workflow(data))
        except RuntimeError:
            try:
                import nest_asyncio
                nest_asyncio.apply()
                results = asyncio.run(workflow(data))
            except ImportError:
                logger.error("nest_asyncio not installed. Cannot run nested async logic.")
                raise
        except Exception as e:
            logger.error(f"LatteReview workflow failed: {e}")
            raise
            
        if not output_path:
            output_path = str(Path(input_path).parent / f"{prefix}_{Path(input_path).name}")
            
        results.to_csv(output_path, index=False)
        logger.info(f"Complete. Saved to {output_path}")
        return output_path

# Singleton
_latte_instance = None
_latte_lock = threading.Lock()

def get_latte_review() -> LatteReviewSkill:
    global _latte_instance
    with _latte_lock:
        if not _latte_instance:
            _latte_instance = LatteReviewSkill()
    return _latte_instance


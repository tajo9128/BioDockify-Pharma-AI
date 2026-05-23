"""Cross-Run Evolution Engine — pharma knowledge retention across research runs."""
from helpers.api import ApiHandler, Request, Response
import os, json, logging, time
from datetime import datetime, timedelta

log = logging.getLogger("evolution")
EVOLUTION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "evolution")
os.makedirs(EVOLUTION_DIR, exist_ok=True)

CATEGORIES = ["target", "compound", "method", "literature", "failure", "quality"]


def _decay_weight(lesson_age_days: int, max_days: int = 30) -> float:
    """Ebbinghaus-style time decay for lesson relevance."""
    if lesson_age_days <= 0:
        return 1.0
    if lesson_age_days >= max_days:
        return 0.05
    return max(0.05, 1.0 - (lesson_age_days / max_days) ** 0.7)


def _store_lesson(category: str, context: dict, lesson: str, importance: float = 0.5):
    """Store a lesson for future runs."""
    path = os.path.join(EVOLUTION_DIR, f"{category}.json")
    try:
        if os.path.exists(path):
            with open(path) as f:
                lessons = json.load(f)
        else:
            lessons = []

        lessons.append({
            "ts": datetime.now().isoformat(),
            "context": context,
            "lesson": lesson,
            "importance": importance,
        })
        # Keep last 100 per category
        lessons = lessons[-100:]
        with open(path, "w") as f:
            json.dump(lessons, f, indent=2)
    except Exception as e:
        log.warning(f"Failed to store lesson: {e}")


def _query_lessons(category: str, query_context: str, top_k: int = 5) -> list:
    """Retrieve relevant lessons by recency + importance."""
    path = os.path.join(EVOLUTION_DIR, f"{category}.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            lessons = json.load(f)
    except Exception:
        return []

    now = datetime.now()
    scored = []
    for l in lessons:
        try:
            ts = datetime.fromisoformat(l["ts"])
            age = (now - ts).total_seconds() / 86400
            weight = _decay_weight(age)
            # Bonus for context match
            ctx = l.get("context", {})
            ctx_str = json.dumps(ctx).lower()
            bonus = 0.2 if query_context.lower() in ctx_str else 0
            scored.append({**l, "age_days": round(age, 1), "weight": round(weight + bonus, 3)})
        except Exception:
            scored.append({**l, "age_days": 0, "weight": 0.5})

    scored.sort(key=lambda x: (x["weight"], x.get("importance", 0.5)), reverse=True)
    return scored[:top_k]


class EvolutionHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "store")

        if action == "store":
            category = input.get("category", "target")
            if category not in CATEGORIES:
                return {"error": f"Invalid category. Valid: {CATEGORIES}"}
            context = input.get("context", {})
            lesson = input.get("lesson", "")
            importance = float(input.get("importance", 0.5))
            if not lesson:
                return {"error": "lesson required"}

            _store_lesson(category, context, lesson, importance)
            return {"success": True, "stored": True, "category": category, "count": len(_query_lessons(category, "", 100))}

        if action == "query":
            category = input.get("category", "target")
            context = input.get("context", "")
            top_k = int(input.get("top_k", 5))
            if category not in CATEGORIES:
                return {"error": f"Invalid category. Valid: {CATEGORIES}"}
            results = _query_lessons(category, context, top_k)
            return {"success": True, "results": results, "count": len(results), "decay_model": "Ebbinghaus (30-day)"}

        if action == "deduce":
            """Auto-extract lessons from a completed pipeline run."""
            pipeline = input.get("pipeline", input.get("data", {}))
            if not pipeline:
                return {"error": "pipeline data required"}
            lessons = []
            stages = pipeline.get("stages", {})
            topic = pipeline.get("topic", "unknown")

            # Check for docking failures → store fix
            for sid, sdata in stages.items():
                result = sdata.get("result", {}) or {}
                if sdata.get("status") == "completed" and isinstance(result, dict):
                    # Docking lessons
                    if "best_energy" in result or "poses" in result:
                        energy = result.get("best_energy", 0)
                        if float(energy) < -8:
                            _store_lesson("target", {"pipeline_topic": topic, "stage": sid}, f"Strong binding achieved: {energy} kcal/mol", 0.8)
                    # QSAR lessons
                    if "cv_r2" in result or "r_squared" in result:
                        r2 = result.get("cv_r2", result.get("r_squared", 0))
                        if float(r2) > 0.7:
                            _store_lesson("method", {"pipeline_topic": topic, "stage": sid}, f"QSAR model with R²={r2} — good predictive power", 0.7)

            lessons = _query_lessons("target", topic, 10) + _query_lessons("method", topic, 10)
            return {"success": True, "lessons_extracted": len([l for l in lessons if l.get("weight", 0) > 0.3])}

        if action == "stats":
            stats = {}
            for cat in CATEGORIES:
                lessons = _query_lessons(cat, "", 1000)
                stats[cat] = {"total": len(lessons), "active": sum(1 for l in lessons if l.get("weight", 0) > 0.3)}
            return {"success": True, "stats": stats, "categories": CATEGORIES}

        if action == "categories":
            return {
                "target": "Per-protein docking parameters and binding preferences",
                "compound": "QSAR model performance per compound class",
                "method": "Which statistical test / model worked best per data type",
                "literature": "Search terms and databases that yielded best results",
                "failure": "Common failure patterns and their fixes",
                "quality": "Quality gate pass rates and common rejection reasons",
            }

        return {"error": f"Unknown action: {action}"}

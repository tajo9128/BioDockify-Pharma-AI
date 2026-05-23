"""Pharma Research Pipeline — 25-stage autonomous drug discovery engine."""
from helpers.api import ApiHandler, Request, Response
import os, json, uuid, logging, time
from datetime import datetime

log = logging.getLogger("pipeline")

PIPELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "pipelines")
os.makedirs(PIPELINE_DIR, exist_ok=True)

STAGES = {
    1:  {"name": "TOPIC_INIT",        "phase": "Scoping",      "desc": "Decompose research topic"},
    2:  {"name": "SCOPE_DEFINE",      "phase": "Scoping",      "desc": "Define target, endpoint, method"},
    3:  {"name": "SEARCH_STRATEGY",   "phase": "Literature",   "desc": "Build search queries"},
    4:  {"name": "LITERATURE_COLLECT","phase": "Literature",   "desc": "Search PubMed + Semantic Scholar + arXiv"},
    5:  {"name": "LITERATURE_SCREEN", "phase": "Literature",   "desc": "Screen papers — GATE 1"},
    6:  {"name": "KNOWLEDGE_EXTRACT", "phase": "Literature",   "desc": "Extract key findings"},
    7:  {"name": "MOLECULE_ANALYZE",  "phase": "Molecular",    "desc": "Drug properties, ADMET, filters"},
    8:  {"name": "PHARMACOPHORE",     "phase": "Molecular",    "desc": "Pharmacophoric feature detection"},
    9:  {"name": "QSAR_TRAIN",        "phase": "QSAR",         "desc": "Train QSAR models"},
    10: {"name": "QSAR_SCREEN",       "phase": "QSAR",         "desc": "Screen compound library"},
    11: {"name": "DOCKING_PREPARE",   "phase": "Docking",      "desc": "Prepare receptor + ligands"},
    12: {"name": "DOCKING_RUN",       "phase": "Docking",      "desc": "Vina → GNINA CNN docking"},
    13: {"name": "DOCKING_ANALYZE",   "phase": "Docking",      "desc": "Deep analysis: 3D, clusters"},
    14: {"name": "STAT_ANALYZE",      "phase": "Statistics",   "desc": "Statistical analysis"},
    15: {"name": "STAT_TEST",         "phase": "Statistics",   "desc": "Appropriate test selection"},
    16: {"name": "CLUSTER_RMSD",      "phase": "Analysis",     "desc": "RMSD clustering of poses"},
    17: {"name": "RESULT_ANALYSIS",    "phase": "Analysis",     "desc": "Multi-perspective analysis"},
    18: {"name": "RESEARCH_DECISION",  "phase": "Decision",     "desc": "PROCEED / REFINE / PIVOT"},
    19: {"name": "PAPER_OUTLINE",      "phase": "Writing",      "desc": "Generate paper outline"},
    20: {"name": "PAPER_DRAFT",        "phase": "Writing",      "desc": "Section-by-section drafting"},
    21: {"name": "PEER_REVIEW",        "phase": "Writing",      "desc": "Multi-agent peer review"},
    22: {"name": "PAPER_REVISION",     "phase": "Writing",      "desc": "Revise based on review"},
    23: {"name": "QUALITY_GATE",       "phase": "Finalization", "desc": "5-dimension quality gate"},
    24: {"name": "CITATION_VERIFY",    "phase": "Finalization", "desc": "5-layer citation verification"},
    25: {"name": "EXPORT_PUBLISH",     "phase": "Finalization", "desc": "Export LaTeX + DOCX + slides"},
}

GATE_STAGES = {5, 11, 23}  # Literature, Docking Prep, Quality


def _init_pipeline(topic: str, config: dict = None) -> dict:
    pid = str(uuid.uuid4())[:12]
    ts = datetime.now().isoformat()
    stages_state = {}
    for sid in sorted(STAGES):
        stages_state[str(sid)] = {"status": "pending", "started": None, "completed": None, "result": None, "retries": 0}
    pipeline = {
        "pipeline_id": pid,
        "topic": topic,
        "config": config or {},
        "status": "initialized",
        "current_stage": 1,
        "stages": stages_state,
        "created_at": ts,
        "updated_at": ts,
        "history": [f"{ts}: Pipeline initialized for topic: {topic}"],
        "gates": {},
    }
    _save(pid, pipeline)
    return pipeline


def _save(pid, data):
    path = os.path.join(PIPELINE_DIR, f"{pid}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _load(pid):
    path = os.path.join(PIPELINE_DIR, f"{pid}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _advance_stage(pipeline, result=None):
    sid = pipeline["current_stage"]
    skey = str(sid)
    pipeline["stages"][skey]["status"] = "completed"
    pipeline["stages"][skey]["completed"] = datetime.now().isoformat()
    pipeline["stages"][skey]["result"] = result
    pipeline["history"].append(f"Stage {sid} ({STAGES[sid]['name']}): completed")

    # Check if gate needed
    if sid in GATE_STAGES:
        pipeline["gates"][skey] = {"status": "pending_approval", "approved": False}

    if sid < 25:
        pipeline["current_stage"] = sid + 1
        nkey = str(sid + 1)
        pipeline["stages"][nkey]["status"] = "in_progress"
        pipeline["stages"][nkey]["started"] = datetime.now().isoformat()
        pipeline["status"] = "running"
        pipeline["history"].append(f"Stage {sid+1} ({STAGES[sid+1]['name']}): started")
    else:
        pipeline["status"] = "completed"
        pipeline["history"].append("Pipeline completed")

    pipeline["updated_at"] = datetime.now().isoformat()
    _save(pipeline["pipeline_id"], pipeline)
    return pipeline


def _retry_stage(pipeline, error):
    sid = pipeline["current_stage"]
    skey = str(sid)
    pipeline["stages"][skey]["retries"] += 1
    pipeline["stages"][skey]["status"] = "retrying"
    pipeline["history"].append(f"Stage {sid} ({STAGES[sid]['name']}): retry #{pipeline['stages'][skey]['retries']} — {error}")
    pipeline["updated_at"] = datetime.now().isoformat()
    _save(pipeline["pipeline_id"], pipeline)
    return pipeline


class PipelineHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "start")

        if action == "start":
            topic = input.get("topic", "")
            if not topic:
                return {"error": "topic required"}
            pl = _init_pipeline(topic, input.get("config"))
            return {"success": True, "pipeline": pl, "total_stages": len(STAGES)}

        if action == "status":
            pid = input.get("pipeline_id", "")
            pl = _load(pid)
            if not pl:
                return {"error": f"Pipeline {pid} not found"}
            return {"success": True, "pipeline": pl}

        if action == "advance":
            pid = input.get("pipeline_id", "")
            pl = _load(pid)
            if not pl:
                return {"error": f"Pipeline {pid} not found"}
            pl = _advance_stage(pl, input.get("result"))
            return {"success": True, "pipeline": pl}

        if action == "retry":
            pid = input.get("pipeline_id", "")
            pl = _load(pid)
            if not pl:
                return {"error": f"Pipeline {pid} not found"}
            pl = _retry_stage(pl, input.get("error", "unknown"))
            return {"success": True, "pipeline": pl}

        if action == "abort":
            pid = input.get("pipeline_id", "")
            pl = _load(pid)
            if not pl:
                return {"error": f"Pipeline {pid} not found"}
            pl["status"] = "aborted"
            pl["history"].append(f"Pipeline aborted at stage {pl['current_stage']}")
            pl["updated_at"] = datetime.now().isoformat()
            _save(pid, pl)
            return {"success": True, "pipeline": pl}

        if action == "history":
            files = sorted(os.listdir(PIPELINE_DIR), reverse=True)
            return {"pipelines": [json.load(open(os.path.join(PIPELINE_DIR, f))) for f in files[:20] if f.endswith(".json")]}

        if action == "stages":
            return {"stages": {str(k): v for k, v in STAGES.items()}, "total": len(STAGES), "gate_stages": list(GATE_STAGES)}

        return {"error": f"Unknown action: {action}"}

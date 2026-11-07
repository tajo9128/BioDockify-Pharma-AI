"""GMP & Quality Audit Suite — additive module (QA/Regulatory department).

Offline knowledge base + trackers:
  · Audit checklists — WHO TRS 986 / EU GMP Part I / US 21 CFR 211 / PIC/S
  · Deviation & CAPA tracker (JSON store, status workflow, due alerts)
  · Environmental monitoring & water-system limits (Grades A–D, PW/WFI)
  · Self-inspection planner (areas rotation + interval tracking)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

CHECKLISTS: Dict[str, List[Dict[str, str]]] = {
    "EU GMP Part I (Basic requirements)": [
        {"ref": "Ch.1", "item": "Pharmaceutical Quality System documented & effective (ICH Q10)"},
        {"ref": "Ch.3", "item": "Premises: flow layout, grade separation, cleaning validated"},
        {"ref": "Ch.4", "item": "Documentation: batch records contemporaneous, ALCOA+ data integrity"},
        {"ref": "Ch.5", "item": "Production: dedicated/validated equipment, line clearance"},
        {"ref": "Ch.5.24–26", "item": "Cross-contamination control: dedicated facilities for penicillins/HPAPIs reviewed"},
        {"ref": "Ch.6", "item": "QC: incoming testing, OOS procedure with full investigation"},
        {"ref": "Ch.6.16+", "item": "Out-of-spec & out-of-trend handled; retention samples kept"},
        {"ref": "Annex 1", "item": "Sterile: grade A/B/C/D classification, media fills, APQ (contamination control strategy)"},
        {"ref": "Annex 11", "item": "Computerised systems validated, audit trail on, access control"},
        {"ref": "Annex 15", "item": "Qualification & validation: URS→DQ→IQ→OQ→PQ, requalification schedule"},
        {"ref": "Annex 16", "item": "QP batch certification: deviations evaluated before release"},
        {"ref": "Annex 19", "item": "Reference & retention samples stored & labeled correctly"},
        {"ref": "Annex 21", "item": "Importation/manipulation of medicinal products licensed"},
    ],
    "WHO TRS 986 GMP (main principles)": [
        {"ref": "2.1", "item": "QA system covers all stages: dev, procurement, production, QC, release, distribution"},
        {"ref": "4", "item": "Sanitation & hygiene: written programme, personnel practices, pest control"},
        {"ref": "5", "item": "Qualification & validation: equipment, processes, cleaning, analytical methods"},
        {"ref": "7", "item": "Materials management: approved suppliers, quarantine, FIFO/FEFO"},
        {"ref": "9", "item": "Self-inspection programme with recorded follow-up CAPA"},
        {"ref": "10", "item": "Complaints & product recalls: mock recall performed, timeframes defined"},
        {"ref": "12", "item": "Contract manufacturing: technical/quality agreements in place"},
        {"ref": "14", "item": "Personnel: key personnel designated, training records current"},
    ],
    "US 21 CFR 211 (Pharmaceutical GMP)": [
        {"ref": "211.22", "item": "QC unit responsibilities & authority documented"},
        {"ref": "211.25", "item": "Personnel qualified by training/education; records maintained"},
        {"ref": "211.42", "item": "Design & construction: adequate space, flow, environmental control"},
        {"ref": "211.63", "item": "Equipment suitably located, designed for intended use"},
        {"ref": "211.67", "item": "Equipment cleaning & maintenance: schedules + logs"},
        {"ref": "211.84", "item": "Component testing: at least one specific identity test"},
        {"ref": "211.100", "item": "Written procedures deviated only with documented authorization"},
        {"ref": "211.160", "item": "Laboratory controls: calibration schedule, standards traceability"},
        {"ref": "211.165", "item": "Release testing: each batch tested before distribution"},
        {"ref": "211.166", "item": "Stability program: ongoing, expiry justified"},
        {"ref": "211.167", "item": "Sterility & pyrogen testing for sterile products"},
        {"ref": "211.192", "item": "Batch record review: complete investigation of unexplained discrepancies"},
    ],
    "PIC/S PE 009 (harmonised)": [
        {"ref": "I.4", "item": "Documentation system: SOPs reviewed at defined intervals"},
        {"ref": "I.5", "item": "Production: in-process controls at defined frequency"},
        {"ref": "II.5", "item": "Starting material & packaging: suppliers qualified, audits done"},
        {"ref": "II.6", "item": "QC & stability: methods validated (ICH Q2), stability per ICH Q1"},
        {"ref": "II.7", "item": "OOS investigation: lab + production phases, trending"},
        {"ref": "II.9", "item": "Self-inspection: risk-based frequency, independent inspectors"},
    ],
}

EM_LIMITS = [
    {"zone": "Grade A (at rest)", "cfu_m3_air": "<1", "cfu_settle_90mm": "<1", "cfu_contact_55mm": "<1", "glove_5f": "<1"},
    {"zone": "Grade A (in operation)", "cfu_m3_air": "<1", "cfu_settle_90mm": "<1", "cfu_contact_55mm": "<1", "glove_5f": "<1"},
    {"zone": "Grade B (at rest)", "cfu_m3_air": 10, "cfu_settle_90mm": 5, "cfu_contact_55mm": 5, "glove_5f": 5},
    {"zone": "Grade C (at rest)", "cfu_m3_air": 100, "cfu_settle_90mm": 50, "cfu_contact_55mm": 25, "glove_5f": "-"},
    {"zone": "Grade C (in operation)", "cfu_m3_air": 1000, "cfu_settle_90mm": 100, "cfu_contact_55mm": 50, "glove_5f": "-"},
    {"zone": "Grade D (at rest)", "cfu_m3_air": 200, "cfu_settle_90mm": 100, "cfu_contact_55mm": 50, "glove_5f": "-"},
    {"zone": "Grade D (in operation)", "cfu_m3_air": "—", "cfu_settle_90mm": "—", "cfu_contact_55mm": "—", "glove_5f": "-"},
]

WATER_LIMITS = [
    {"system": "Purified Water (PW)", "conductivity_us_cm": "≤1.3 @ 25°C (Ph.Eur.)", "toc_ppb": "≤500", "bioburden_cfu_ml": "≤100", "notes": "RO/EDI typical; seasonal water-quality validation"},
    {"system": "Water for Injection (WFI)", "conductivity_us_cm": "≤1.3 @ 25°C", "toc_ppb": "≤500", "bioburden_cfu_ml": "≤10 (action)", "notes": "Distillation or RO per EU (since 2017); endotoxin ≤0.25 EU/mL"},
    {"system": "Highly Purified Water (legacy)", "conductivity_us_cm": "≤1.1", "toc_ppb": "≤500", "bioburden_cfu_ml": "≤10", "notes": "Phased out in EU; align with PW/WFI"},
]

# ── Deviation / CAPA tracker (JSON store) ─────────────────────────────────────

_STORE_DIR = os.environ.get("GMP_STORE", "/a0/tmp/gmp_audit" if os.name != "nt" else "tmp/gmp_audit")


def _load() -> Dict[str, List[Dict[str, Any]]]:
    os.makedirs(_STORE_DIR, exist_ok=True)
    p = os.path.join(_STORE_DIR, "records.json")
    if os.path.exists(p):
        try:
            return json.loads(open(p, encoding="utf-8").read())
        except Exception:
            pass
    return {"deviations": [], "capas": []}


def _save(store: Dict) -> None:
    os.makedirs(_STORE_DIR, exist_ok=True)
    with open(os.path.join(_STORE_DIR, "records.json"), "w", encoding="utf-8") as f:
        json.dump(store, f, indent=1, ensure_ascii=False)


def add_record(kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    store = _load()
    key = "deviations" if kind == "deviation" else "capas"
    rid = f"{kind[0].upper()}-{datetime.now().strftime('%y%m%d')}-{len(store[key]) + 1:03d}"
    rec = {"id": rid, "kind": kind, "title": str(payload.get("title", ""))[:120],
           "area": str(payload.get("area", ""))[:60],
           "severity": str(payload.get("severity", "minor")).lower(),
           "status": "open", "created": datetime.now().isoformat(timespec="seconds"),
           "due": (datetime.now() + timedelta(days=int(payload.get("due_days", 30) or 30))).isoformat(timespec="seconds"),
           "description": str(payload.get("description", ""))[:2000],
           "actions": []}
    store[key].append(rec)
    _save(store)
    return {"success": True, "record": rec}


def update_record(rid: str, status: str = None, action: str = None) -> Dict[str, Any]:
    store = _load()
    for key in ("deviations", "capas"):
        for rec in store[key]:
            if rec["id"] == rid:
                if status:
                    rec["status"] = status
                if action:
                    rec["actions"].append({"at": datetime.now().isoformat(timespec="seconds"), "text": str(action)[:300]})
                _save(store)
                return {"success": True, "record": rec}
    return {"error": f"record {rid} not found"}


def dashboard() -> Dict[str, Any]:
    store = _load()
    now = datetime.now()
    def _meta(r):
        overdue = r["status"] != "closed" and r["due"] and r["due"] < now.isoformat()
        return {"id": r["id"], "title": r["title"], "severity": r["severity"], "status": r["status"],
                "due": r["due"][:10], "overdue": bool(overdue)}
    devs = [_meta(r) for r in store["deviations"]]
    caps = [_meta(r) for r in store["capas"]]
    return {"deviations": {"total": len(devs), "open": sum(1 for d in devs if d["status"] != "closed"),
                           "overdue": sum(1 for d in devs if d["overdue"]), "records": devs},
            "capas": {"total": len(caps), "open": sum(1 for c in caps if c["status"] != "closed"),
                      "overdue": sum(1 for c in caps if c["overdue"]), "records": caps},
            "note": "Teaching tracker — production QMS must be validated (21 CFR 11 / Annex 11 compliant)."}


# ── Self-inspection planner ────────────────────────────────────────────────────

AREAS = ["Production (solid)", "Production (sterile)", "QC laboratory", "Warehouse & distribution",
         "Engineering & maintenance", "QA systems & documentation", "IT / computerised systems",
         "Personnel & training", "Sanitation & hygiene", "Complaints & recalls", "Contract givers/acceptors"]


def self_inspection_plan(last_audit: Dict[str, str] = None, interval_months: int = 12) -> Dict[str, Any]:
    """Rotation plan with next-due dates from last-done map {area: 'YYYY-MM-DD'}."""
    last = last_audit or {}
    rows = []
    today = datetime.now()
    for area in AREAS:
        done = last.get(area)
        if done:
            try:
                d = datetime.strptime(str(done)[:10], "%Y-%m-%d")
                due = d + timedelta(days=interval_months * 30)
                rows.append({"area": area, "last_done": str(done)[:10], "next_due": due.strftime("%Y-%m-%d"),
                             "status": "OVERDUE" if due < today else ("due <60d" if (due - today).days < 60 else "scheduled")})
            except ValueError:
                rows.append({"area": area, "last_done": str(done), "next_due": "—", "status": "invalid date"})
        else:
            rows.append({"area": area, "last_done": "never", "next_due": "—", "status": "never audited"})
    return {"interval_months": interval_months, "areas": rows,
            "note": "Risk-based frequency per WHO Ch.9 / EU Ch.1.4(xii); high-risk areas may need 6-monthly."}

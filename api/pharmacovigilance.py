"""Pharmacovigilance Studio API — signal detection, DDI screening, ICSR reporting.

Surfaces the existing safety_signal engine (PRR/ROR/chi-square disproportionality,
modules/clinical/safety_signal.py) and the curated DDI database
(modules/clinical/drug_interactions.py, 50+ pairs) with a researcher-friendly UI.
Research/academic use — hypothesis-generating only.
"""
from helpers.api import ApiHandler, Request, Response
import json
import logging
import re

log = logging.getLogger("pharmacovigilance")


class PharmacovigilanceHandler(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")

        if action == "analyze_pair":
            return self._analyze_pair(input)
        elif action == "analyze_series":
            return self._analyze_series(input)
        elif action == "ddi_check":
            return self._ddi_check(input)
        elif action == "ddi_list":
            return self._ddi_list()
        elif action == "icsr_draft":
            return self._icsr_draft(input)

        return {"actions": ["analyze_pair", "analyze_series", "ddi_check", "ddi_list", "icsr_draft"],
                "hint": "Pharmacovigilance Studio: disproportionality (PRR/ROR/chi2), "
                        "drug-interaction screening, and ICSR-style ADR report drafting."}

    # ── Disproportionality: one 2x2 table ────────────────────────────────────

    @staticmethod
    def _analyze_pair(input: dict) -> dict:
        from modules.clinical.safety_signal import analyze_contingency, SafetySignalInputError
        try:
            return {"success": True, **analyze_contingency(
                input.get("a"), input.get("b"), input.get("c"), input.get("d"),
                label=input.get("label") or "Drug–event pair",
                min_cases=int(input.get("min_cases", 3)),
                prr_threshold=float(input.get("prr_threshold", 2.0)),
                chi_square_threshold=float(input.get("chi_square_threshold", 4.0)),
            )}
        except (SafetySignalInputError, TypeError, ValueError) as e:
            return {"error": str(e)[:200]}

    # ── Disproportionality: many pairs (JSON array or CSV) ──────────────────

    @staticmethod
    def _analyze_series(input: dict) -> dict:
        from modules.clinical.safety_signal import analyze_event_series, SafetySignalInputError
        events = input.get("events")
        if events is None:
            csv_text = str(input.get("csv", "")).strip()
            if not csv_text:
                return {"error": "Provide events (JSON array) or csv text"}
            events = PharmacovigilanceHandler._parse_series_csv(csv_text)
            if isinstance(events, dict):
                return events
        try:
            return {"success": True, **analyze_event_series(events)}
        except (SafetySignalInputError, TypeError, ValueError) as e:
            return {"error": str(e)[:200]}

    @staticmethod
    def _parse_series_csv(text: str):
        rows, errors = [], []
        lines = [l for l in text.splitlines() if l.strip()]
        if not lines:
            return {"error": "empty csv"}
        # header optional: label,a,b,c,d
        start = 0
        first = [c.strip().lower() for c in lines[0].split(",")]
        if first[0] in ("label", "event", "pair") or first[0] == "":
            start = 1
        for i, line in enumerate(lines[start:], start=start + 1):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                errors.append({"index": str(i), "error": "need label,a,b,c,d"})
                continue
            try:
                rows.append({"label": parts[0] or f"pair {i}",
                             "a": int(float(parts[1])), "b": int(float(parts[2])),
                             "c": int(float(parts[3])), "d": int(float(parts[4]))})
            except ValueError:
                errors.append({"index": str(i), "error": "non-numeric cell"})
        if not rows:
            return {"error": "no valid rows" + (f" — {errors[:3]}" if errors else "")}
        out = rows
        if errors:
            log.info("series csv: %d rows, %d bad", len(rows), len(errors))
        return out

    # ── DDI screening over a medication list ─────────────────────────────────

    _SEV_ORDER = {"Contraindicated": 0, "Major": 1, "Moderate": 2, "Minor": 3}

    @staticmethod
    def _norm_drug(name: str) -> str:
        n = re.sub(r"[^a-z]", "", str(name or "").lower())
        aliases = {"paracetamol": "acetaminophen", "ibruprofen": "ibuprofen",
                   "witamin": "vitamin", "ndx": "nsaid", "asa": "aspirin"}
        return aliases.get(n, n)

    @staticmethod
    def _ddi_check(input: dict) -> dict:
        from modules.clinical.drug_interactions import DRUG_INTERACTIONS
        raw = input.get("drugs")
        if isinstance(raw, str):
            raw = re.split(r"[,;\n]+", raw)
        drugs = [str(d).strip() for d in (raw or []) if str(d).strip()]
        if not drugs:
            return {"error": "Provide one or more drug names"}
        if len(drugs) > 40:
            return {"error": "Maximum 40 drugs per screen"}
        norm = {d: PharmacovigilanceHandler._norm_drug(d) for d in drugs}
        hits = []
        for (d1, d2), info in DRUG_INTERACTIONS.items():
            for user1, n1 in norm.items():
                for user2, n2 in norm.items():
                    if user1 == user2:
                        continue
                    if (n1 == d1 and n2 == d2):
                        hits.append({"drug_1": user1, "drug_2": user2, **info})
        # also: single-drug interactions with classes present (nsaid, ssri…)
        hits.sort(key=lambda h: PharmacovigilanceHandler._SEV_ORDER.get(h.get("severity", "Minor"), 9))
        # de-duplicate reversed duplicates
        seen, clean = set(), []
        for h in hits:
            key = tuple(sorted((h["drug_1"].lower(), h["drug_2"].lower())))
            if key in seen:
                continue
            seen.add(key)
            clean.append(h)
        counts = {}
        for h in clean:
            counts[h["severity"]] = counts.get(h["severity"], 0) + 1
        return {"success": True, "drugs_screened": len(drugs),
                "interactions": clean, "counts": counts,
                "clean": not clean,
                "notice": "Screening aid only — verify against Lexicomp/Stockley's before clinical decisions."}

    @staticmethod
    def _ddi_list() -> dict:
        from modules.clinical.drug_interactions import DRUG_INTERACTIONS
        rows = [{"drug_1": d1, "drug_2": d2, **info} for (d1, d2), info in DRUG_INTERACTIONS.items()]
        rows.sort(key=lambda r: PharmacovigilanceHandler._SEV_ORDER.get(r.get("severity", "Minor"), 9))
        return {"success": True, "total": len(rows), "interactions": rows}

    # ── ICSR-style ADR report draft ──────────────────────────────────────────

    @staticmethod
    def _icsr_draft(input: dict) -> dict:
        def g(k, d=""):
            return str(input.get(k, d) or d).strip()[:300]
        fields = [
            ("1. Patient information", [
                ("Initials / ID", g("patient_id", "—")),
                ("Age / Sex", f'{g("age", "—")} / {g("sex", "—")}'),
                ("Weight (kg)", g("weight", "—")),
                ("Relevant history", g("history", "—")),
            ]),
            ("2. Suspected medicinal product", [
                ("Drug name (brand/generic)", g("drug", "—")),
                ("Dose / Route / Frequency", f'{g("dose", "—")} / {g("route", "—")} / {g("frequency", "—")}'),
                ("Start & stop dates", f'{g("start_date", "—")} → {g("stop_date", "—")}'),
                ("Indication", g("indication", "—")),
            ]),
            ("3. Suspected adverse reaction", [
                ("Reaction (MedDRA-style term)", g("reaction", "—")),
                ("Onset date", g("onset_date", "—")),
                ("Serious? (criterion)", f'{g("serious", "—")} {g("serious_criteria", "")}'.strip()),
                ("Outcome", g("outcome", "—")),
            ]),
            ("4. Causality assessment", [
                ("Naranjo score (if known)", g("naranjo", "—")),
                ("Dechallenge / Rechallenge", f'{g("dechallenge", "—")} / {g("rechallenge", "—")}'),
                ("Alternative explanations", g("alternatives", "—")),
            ]),
            ("5. Reporter", [
                ("Name / role", f'{g("reporter", "—")} ({g("reporter_role", "pharmacist")})'),
                ("Date of report", g("report_date", "—")),
            ]),
        ]
        narrative = "; ".join(f"{k}: {v}" for _, rows in fields for k, v in rows if v != "—")
        return {"success": True, "sections": [{"section": s, "fields": rows} for s, rows in fields],
                "summary_line": narrative[:800] or "no data provided",
                "notice": "Draft structure for teaching/research — not a regulatory submission. "
                          "Real ICSRs go through PvPI (India) / FDA MedWatch / EudraVigilance."}

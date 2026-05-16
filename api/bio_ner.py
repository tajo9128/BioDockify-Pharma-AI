"""Bio-NER API - Biomedical Named Entity Recognition for entity extraction from text."""
from helpers.api import ApiHandler, Request
import logging

logger = logging.getLogger("bio_ner")


class BioNERApi(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        text = (input.get("text", "") or "").strip()
        if not text:
            return {"error": "Text required for NER extraction"}

        entities = {"drugs": [], "diseases": [], "genes": []}

        try:
            from modules.bio_ner.ner_engine import BioNER, RegexMatcher

            matcher = RegexMatcher()
            entities = matcher.extract(text)

            # Deduplicate and sort
            for cat in entities:
                entities[cat] = sorted(set(entities[cat]))

        except ImportError:
            # Fallback regex patterns
            import re
            patterns = {
                "drugs": [r"\b\w+(mab|ib|vir|stat|cin|micin|cycline|pril|sartan|lol|dipine|zolam)\b"],
                "diseases": [r"\b[\w\s]+(syndrome|disease|cancer|tumor|itis|osis|emia|pathy)\b"],
                "genes": [r"\b[A-Z]{2,}[0-9]+\b"],
            }
            for cat, pats in patterns.items():
                for p in pats:
                    for m in re.finditer(p, text, re.IGNORECASE if cat == "diseases" else 0):
                        w = m.group(0).strip()
                        if len(w) > 3 and w not in entities[cat]:
                            entities[cat].append(w)

        total = sum(len(v) for v in entities.values())
        return {
            "entities": entities,
            "counts": {k: len(v) for k, v in entities.items()},
            "total": total,
            "text_length": len(text),
        }

"""Writing Tools API — Flask handler for LaTeX export, gap analysis, lit matrix, PRISMA, faculty review, citation verification, journal suggestions."""
from helpers.api import ApiHandler, Request
import asyncio, logging, urllib.request

log = logging.getLogger("writing_tools")


async def _async_urlopen(req, timeout=10):
    """Non-blocking urlopen with proper resource cleanup."""
    def _fetch():
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    return await asyncio.to_thread(_fetch)


class WritingTools(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False  # Writing tools are public (used by Academic Writer UI)

    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "export-latex":       return self._export_latex(input)
        if action == "export-docx":        return self._export_docx(input)
        if action == "gap-analysis":       return self._gap_analysis(input)
        if action == "literature-matrix":  return self._lit_matrix(input)
        if action == "prisma-flowchart":   return self._prisma_flowchart(input)
        if action == "faculty-review":     return self._faculty_review(input)
        if action == "verify-citations":   return self._verify_citations(input)
        if action == "suggest-journals":   return self._suggest_journals(input)
        if action == "kb_sources":         return self._kb_sources(input)
        if action == "kb_categories":      return self._kb_categories(input)
        if action == "pharma_citation_verify":  return await self._pharma_citation_verify(input)
        if action == "pharma_reporting_check":  return self._pharma_reporting_check(input)
        if action == "pharma_scorecard":        return self._pharma_scorecard(input)
        # ── Advanced Research Skills (v7.7.1+) ──
        if action == "equator_checklist":        return self._equator_checklist(input)
        if action == "ai_disclosure":            return self._ai_disclosure(input)
        if action == "prisma_pipeline":          return self._prisma_pipeline(input)
        if action == "peer_review":              return self._peer_review(input)
        if action == "integrity_audit":          return self._integrity_audit(input)
        if action == "citation_network":         return self._citation_network(input)
        # ── Advanced Writing Skills (v7.8.0+) ──
        if action == "de_aigc":                  return self._de_aigc(input)
        if action == "section_analysis":         return self._section_analysis(input)
        if action == "citation_gaps":            return self._citation_gaps(input)
        if action == "terminology_check":        return self._terminology_check(input)
        if action == "scientific_rigor":         return self._scientific_rigor(input)
        if action == "quality_control":          return self._quality_control(input)
        if action == "executive_summary":        return self._executive_summary(input)
        return {"actions": ["export-latex","export-docx","gap-analysis","literature-matrix","prisma-flowchart","faculty-review","verify-citations","suggest-journals","kb_sources","kb_categories","pharma_citation_verify","pharma_reporting_check","pharma_scorecard","equator_checklist","ai_disclosure","prisma_pipeline","peer_review","integrity_audit","citation_network","de_aigc","section_analysis","citation_gaps","terminology_check","scientific_rigor","quality_control","executive_summary"]}

    def _kb_categories(self, input: dict) -> dict:
        """List all KB categories with entry counts — for the writer's category dropdown."""
        try:
            from modules.knowledge.auto_store import _load_index
            idx = _load_index()
            cats = {}
            for e in idx.get("entries", []):
                c = e.get("category", "misc")
                cats[c] = cats.get(c, 0) + 1
            # Sort by count desc
            sorted_cats = sorted(cats.items(), key=lambda x: -x[1])
            return {
                "status": "ok",
                "categories": [{"key": c, "count": n} for c, n in sorted_cats],
                "total_entries": len(idx.get("entries", [])),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _kb_sources(self, input: dict) -> dict:
        """Load KB entries by category, formatted as a source bundle for the Academic Writer.

        Keeps categories SEPARATE — caller picks which category(ies) to pull from.
        Applies a 100K character budget: full text for top entries, abstracts/titles for the rest.
        """
        try:
            import os
            from modules.knowledge.auto_store import _load_index

            category = input.get("category", "literature")        # single category or "all"
            categories = input.get("categories", [])                # OR list of categories
            max_chars = int(input.get("max_chars", 100000))         # 100K char budget
            max_entries = int(input.get("max_entries", 300))

            if categories:
                target_cats = set(categories)
            elif category and category != "all":
                target_cats = {category}
            else:
                target_cats = None  # all categories

            idx = _load_index()
            entries = idx.get("entries", [])

            # Filter by category
            if target_cats is not None:
                entries = [e for e in entries if e.get("category") in target_cats]

            # Sort newest first
            entries.sort(key=lambda e: e.get("created_at", ""), reverse=True)
            entries = entries[:max_entries]

            if not entries:
                return {
                    "status": "ok",
                    "sources": [],
                    "count": 0,
                    "total_chars": 0,
                    "message": f"No entries found in category '{category}'",
                }

            # ── Budget loading: full text first, then abstracts, then titles only ──
            sources = []
            total_chars = 0
            FULL_BUDGET = int(max_chars * 0.7)   # 70% for full content
            ABS_BUDGET = int(max_chars * 0.25)   # 25% for abstracts
            # 5% reserved for titles

            # Pass 1: load full content until FULL_BUDGET reached
            full_count = 0
            for e in entries:
                if total_chars >= FULL_BUDGET:
                    break
                filepath = e.get("file", "")
                content = ""
                if filepath and os.path.exists(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read(max_chars)
                    except Exception:
                        pass
                if content and len(content) > 100:
                    # Truncate if this entry would blow the budget
                    remaining = FULL_BUDGET - total_chars
                    if len(content) > remaining:
                        content = content[:remaining] + "\n...[truncated]"
                    sources.append({
                        "title": e.get("title", "Untitled"),
                        "category": e.get("category", ""),
                        "source": e.get("source", ""),
                        "content": content,
                        "content_type": "full",
                        "created_at": e.get("created_at", ""),
                    })
                    total_chars += len(content)
                    full_count += 1

            # Pass 2: for entries not loaded as full, add abstract/summary if budget allows
            loaded_titles = {s["title"] for s in sources}
            abs_count = 0
            for e in entries:
                if total_chars >= FULL_BUDGET + ABS_BUDGET:
                    break
                if e.get("title") in loaded_titles:
                    continue
                # Try to extract abstract (first 500-2000 chars after metadata)
                filepath = e.get("file", "")
                snippet = ""
                if filepath and os.path.exists(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            text = f.read(3000)
                        # Find abstract section
                        if "## Abstract" in text:
                            snippet = text.split("## Abstract", 1)[1][:1500].strip()
                        elif "## Full Text" in text:
                            snippet = text.split("## Full Text", 1)[1][:1500].strip()
                        else:
                            snippet = text[:1000]
                    except Exception:
                        pass
                if snippet:
                    remaining = (FULL_BUDGET + ABS_BUDGET) - total_chars
                    if len(snippet) > remaining:
                        snippet = snippet[:remaining] + "...[truncated]"
                    sources.append({
                        "title": e.get("title", "Untitled"),
                        "category": e.get("category", ""),
                        "source": e.get("source", ""),
                        "content": snippet,
                        "content_type": "abstract",
                        "created_at": e.get("created_at", ""),
                    })
                    total_chars += len(snippet)
                    abs_count += 1
                    loaded_titles.add(e["title"])

            # Pass 3: titles-only for the rest (citations)
            title_count = 0
            for e in entries:
                if e.get("title") in loaded_titles:
                    continue
                sources.append({
                    "title": e.get("title", "Untitled"),
                    "category": e.get("category", ""),
                    "source": e.get("source", ""),
                    "content": "",
                    "content_type": "title_only",
                    "created_at": e.get("created_at", ""),
                })
                title_count += 1

            return {
                "status": "ok",
                "sources": sources,
                "count": len(sources),
                "category": category,
                "full_text_count": full_count,
                "abstract_count": abs_count,
                "title_only_count": title_count,
                "total_chars": total_chars,
                "budget_chars": max_chars,
                "message": (
                    f"Loaded {len(sources)} sources from '{category}': "
                    f"{full_count} full text, {abs_count} abstracts, {title_count} titles only. "
                    f"Total {total_chars:,} chars (budget {max_chars:,})."
                ),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


    def _export_latex(self, input: dict):
        title = input.get("title", "")
        sections = input.get("sections", [])
        abstract = input.get("abstract", "")
        authors = input.get("authors", "")
        try:
            doc = (
                f"\\documentclass{{article}}\n"
                f"\\usepackage{{hyperref}}\n"
                f"\\title{{{_sanitize(title)}}}\n"
                f"\\author{{{_sanitize(authors)}}}\n"
                f"\\begin{{document}}\n\\maketitle\n"
            )
            if abstract:
                doc += f"\\begin{{abstract}}\n{_sanitize(abstract)}\n\\end{{abstract}}\n"
            for s in sections:
                h = s.get("heading", "Section")
                c = s.get("content", "")
                doc += f"\\section{{{_sanitize(h)}}}\n{c}\n"
            doc += "\\end{document}"
            return {"status": "ok", "latex": doc}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _export_docx(self, input: dict):
        title = input.get("title", "Manuscript")
        content = input.get("content", "")
        try:
            from docx import Document
            from docx.shared import Pt, Inches
            import base64, io
            doc = Document()
            doc.styles['Normal'].font.size = Pt(11)
            doc.add_heading(title, level=0)
            for para in content.split("\n\n"):
                if para.strip():
                    p = doc.add_paragraph(para.strip())
                    p.style.font.size = Pt(11)
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)
            return {"status": "ok", "docx_base64": base64.b64encode(buf.read()).decode()}
        except ImportError:
            return {"status": "error", "error": "python-docx not installed. Run: pip install python-docx"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _gap_analysis(self, input: dict):
        topic = input.get("topic", "")
        try:
            from nlp.gap_analyzer import PreclinicalGapAnalyzer
            analyzer = PreclinicalGapAnalyzer()
            gaps = analyzer.detect_research_gaps([], topic=topic or "Pharmaceutical Research")
            report = analyzer.generate_gap_report(gaps, top_n=10)
            return {"status": "ok", "gaps": gaps[:10], "report": report}
        except ImportError:
            return {"status": "error", "error": "Gap analyzer requires numpy. Install dependencies."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _lit_matrix(self, input: dict):
        papers = input.get("papers", [])
        try:
            from modules.writing.lit_matrix import generate_lit_matrix
            return {"status": "ok", "matrix": generate_lit_matrix(papers)}
        except ImportError:
            return {"status": "error", "error": "Literature matrix module not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _prisma_flowchart(self, input: dict):
        try:
            from modules.writing.prisma_flowchart import generate_prisma
            result = generate_prisma(
                identification=input.get("identification", 100),
                screening=input.get("screening", 80),
                eligibility=input.get("eligibility", 40),
                included=input.get("included", 15),
                exclusion_reasons=input.get("reasons", {}),
                topic=input.get("topic", "Systematic Review")
            )
            return {"status": "ok", "prisma": result}
        except ImportError:
            return {"status": "error", "error": "PRISMA module not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _faculty_review(self, input: dict):
        content = input.get("content", "")
        title = input.get("title", "")
        try:
            from modules.writing.review_checker import review_manuscript
            return {"status": "ok", "review": review_manuscript(content, title)}
        except ImportError:
            return {"status": "error", "error": "Review checker not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _verify_citations(self, input: dict):
        text = input.get("text", "")
        try:
            from api.verification import extract_citations, verify_citation
            cites = extract_citations(text)
            results = []
            for c in cites:
                v = verify_citation(c)
                results.append({"citation": c, "verified": v.get("verified", False), "details": v})
            verified = sum(1 for r in results if r["verified"])
            confidence = round(verified / max(len(results), 1), 2)
            return {"status": "ok", "confidence": confidence, "total": len(results), "verified": verified, "results": results}
        except ImportError:
            return {"status": "error", "error": "Verification module not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _suggest_journals(self, input: dict):
        title = input.get("title", "")
        abstract = input.get("abstract", "")
        try:
            from api.journal_finder import JournalFinder
            finder = JournalFinder()
            result = finder.suggest(title=title, abstract=abstract)
            return {"status": "ok", "journals": result}
        except Exception:
            return {"status": "ok", "journals": [
                {"name": "Journal of Pharmaceutical Sciences", "quartile": "Q1", "if": "3.5", "issn": "0022-3549"},
                {"name": "European Journal of Pharmacology", "quartile": "Q2", "if": "2.8", "issn": "0014-2999"},
                {"name": "Bioorganic & Medicinal Chemistry", "quartile": "Q2", "if": "2.5", "issn": "0968-0896"},
                {"name": "Chemical Biology & Drug Design", "quartile": "Q3", "if": "1.9", "issn": "1747-0277"},
                {"name": "Drug Development Research", "quartile": "Q3", "if": "1.5", "issn": "0272-4391"},
            ]}


    # ═══════════════════════════════════════════════════════════════
    # Pharma Research Tools (extracted from OpenDraft + RE-paper-writing)
    # ═══════════════════════════════════════════════════════════════

    async def _pharma_citation_verify(self, input: dict) -> dict:
        """Verify pharmaceutical citations against real databases.
        Pharma-focused: prioritizes PubMed, Europe PMC, CrossRef.
        Returns per-citation status: verified/suspicious/hallucinated."""
        import re, urllib.request, json as _json, time as _time

        text = input.get("text", "")
        citations = input.get("citations", [])  # [{doi, pmid, title, authors, year}]

        # Extract citations from text if not provided
        if not citations and text:
            # Find DOIs in text
            dois = re.findall(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text, re.I)
            # Find PMIDs
            pmids = re.findall(r'PMID[:\s]*(\d{6,8})', text, re.I)
            # Find author-year patterns: (Smith et al., 2020) or (Smith, 2020)
            author_years = re.findall(r'\(([A-Z][a-z]+(?:\s+(?:et\s+al|and\s+[A-Z][a-z]+))?)\s*,?\s*(\d{4})\)', text)

            for doi in dois[:50]:
                citations.append({"doi": doi})
            for pmid in pmids[:50]:
                citations.append({"pmid": pmid})
            for author, year in author_years[:30]:
                citations.append({"authors": [author], "year": year})

        if not citations:
            return {"status": "error", "error": "No citations found. Provide text with DOIs/PMIDs or a citations list."}

        results = []
        verified = suspicious = hallucinated = 0

        for cite in citations[:100]:
            result = {"input": cite, "status": "unknown", "source": None}
            doi = cite.get("doi", "")
            pmid = cite.get("pmid", "")
            title = cite.get("title", "")

            try:
                if doi:
                    # CrossRef DOI lookup
                    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
                    req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.5.2"})
                    raw = await _async_urlopen(req, timeout=10)
                    data = _json.loads(raw)
                    work = data.get("message", {})
                    result["status"] = "verified"
                    result["source"] = "CrossRef"
                    result["title"] = work.get("title", [None])[0]
                    result["journal"] = work.get("container-title", [None])[0]
                    result["year"] = work.get("published-print", {}).get("date-parts", [[None]])[0][0]
                    result["authors"] = [a.get("family", "") for a in work.get("author", [])[:5]]
                    result["pmid"] = next((l.get("id") for l in work.get("link", []) if "pubmed" in l.get("URL", "")), "")
                    verified += 1

                elif pmid:
                    # PubMed PMID lookup
                    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
                    req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.5.2"})
                    raw = await _async_urlopen(req, timeout=10)
                    data = _json.loads(raw)
                    result_data = data.get("result", {}).get(pmid, {})
                    if result_data.get("title"):
                        result["status"] = "verified"
                        result["source"] = "PubMed"
                        result["title"] = result_data.get("title")
                        result["journal"] = result_data.get("fulljournalname", "")
                        result["year"] = result_data.get("pubdate", "")[:4]
                        verified += 1
                    else:
                        result["status"] = "suspicious"
                        suspicious += 1

                elif title:
                    # Title search via CrossRef
                    url = f"https://api.crossref.org/works?query={urllib.parse.quote(title[:200])}&rows=3"
                    req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.5.2"})
                    raw = await _async_urlopen(req, timeout=10)
                    data = _json.loads(raw)
                    items = data.get("message", {}).get("items", [])
                    if items:
                        best = items[0]
                        best_title = (best.get("title", [""])[0]).lower()
                        if title.lower()[:50] in best_title or best_title[:50] in title.lower():
                            result["status"] = "verified"
                            result["source"] = "CrossRef (title match)"
                            result["doi"] = best.get("DOI", "")
                            result["title"] = best.get("title", [None])[0]
                            verified += 1
                        else:
                            result["status"] = "suspicious"
                            result["best_match"] = best.get("title", [""])[0]
                            suspicious += 1
                    else:
                        result["status"] = "hallucinated"
                        hallucinated += 1
                else:
                    result["status"] = "skipped"

            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)[:200]

            results.append(result)
            _time.sleep(0.15)  # Rate limit

        total = len(results)
        score = round(verified / max(total, 1) * 100, 1)

        out = {
            "status": "ok",
            "total": total,
            "verified": verified,
            "suspicious": suspicious,
            "hallucinated": hallucinated,
            "integrity_score": score,
            "results": results,
            "pharma_note": "Citations verified against PubMed + CrossRef. PubMed-indexed citations preferred for pharmaceutical research.",
        }
        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("writing", f"Citation Verification — {verified}/{total} verified", out,
                       source="Pharma Citation Verify", tags=["citation", "verification", "pharma"])
        except Exception:
            pass
        return out

    def _pharma_reporting_check(self, input: dict) -> dict:
        """Check pharmaceutical study compliance with ICH/FDA/EMA reporting guidelines."""
        study_type = input.get("study_type", "clinical_trial")
        sections = input.get("sections", [])  # [{section_name, content}]

        # Pharma-specific reporting guideline checklists
        GUIDELINES = {
            "clinical_trial": {
                "name": "CONSORT 2021 (RCTs)",
                "ref": "Schulz et al., BMJ 2010;340:c869",
                "items": [
                    {"id": "1a", "item": "Title identifies as RCT", "section": "title"},
                    {"id": "1b", "item": "Structured abstract", "section": "abstract"},
                    {"id": "2a", "item": "Scientific background and explanation", "section": "introduction"},
                    {"id": "3a", "item": "Trial design (parallel/crossover/factorial)", "section": "methods"},
                    {"id": "4a", "item": "Eligibility criteria for participants", "section": "methods"},
                    {"id": "4b", "item": "Settings and locations", "section": "methods"},
                    {"id": "5", "item": "Interventions for each group (detailed)", "section": "methods"},
                    {"id": "6a", "item": "Completely defined primary outcome", "section": "methods"},
                    {"id": "6b", "item": "Secondary outcomes", "section": "methods"},
                    {"id": "7a", "item": "Sample size determination", "section": "methods"},
                    {"id": "8a", "item": "Randomization sequence generation", "section": "methods"},
                    {"id": "9", "item": "Allocation concealment mechanism", "section": "methods"},
                    {"id": "10", "item": "Implementation (who generated/enrolled)", "section": "methods"},
                    {"id": "11a", "item": "Blinding (who was blinded)", "section": "methods"},
                    {"id": "12a", "item": "Statistical methods for primary outcome", "section": "methods"},
                    {"id": "13a", "item": "Participant flow diagram (CONSORT)", "section": "results"},
                    {"id": "13b", "item": "Losses and exclusions per group", "section": "results"},
                    {"id": "14a", "item": "Baseline characteristics table", "section": "results"},
                    {"id": "15", "item": "Numbers analyzed per group", "section": "results"},
                    {"id": "17a", "item": "Primary outcome estimates + CI", "section": "results"},
                    {"id": "17b", "item": "Secondary outcomes", "section": "results"},
                    {"id": "18", "item": "Harms/adverse events", "section": "results"},
                    {"id": "20", "item": "Trial limitations", "section": "discussion"},
                    {"id": "21", "item": "Generalizability", "section": "discussion"},
                    {"id": "22", "item": "Registration number and protocol", "section": "other"},
                    {"id": "24", "item": "Funding source", "section": "other"},
                ]
            },
            "observational": {
                "name": "STROBE (Observational Studies)",
                "ref": "von Elm et al., Lancet 2007;370:1453-7",
                "items": [
                    {"id": "1", "item": "Title indicates study design", "section": "title"},
                    {"id": "2", "item": "Abstract — informative structured", "section": "abstract"},
                    {"id": "3", "item": "Background/rationale", "section": "introduction"},
                    {"id": "4", "item": "Objectives and hypotheses", "section": "introduction"},
                    {"id": "5", "item": "Study design", "section": "methods"},
                    {"id": "6", "item": "Setting (locations, dates)", "section": "methods"},
                    {"id": "7", "item": "Participants (eligibility, sources)", "section": "methods"},
                    {"id": "8", "item": "Variables (exposures, outcomes, confounders)", "section": "methods"},
                    {"id": "9", "item": "Data sources/measurement", "section": "methods"},
                    {"id": "10", "item": "Bias (efforts to address)", "section": "methods"},
                    {"id": "11", "item": "Study size", "section": "methods"},
                    {"id": "12", "item": "Quantitative variables", "section": "methods"},
                    {"id": "13", "item": "Statistical methods", "section": "methods"},
                    {"id": "14a", "item": "Participants (numbers, characteristics)", "section": "results"},
                    {"id": "15", "item": "Descriptive data", "section": "results"},
                    {"id": "16", "item": "Main results (estimates + CI)", "section": "results"},
                    {"id": "17", "item": "Other analyses (subgroup, sensitivity)", "section": "results"},
                    {"id": "18", "item": "Key results + limitations", "section": "discussion"},
                    {"id": "19", "item": "Generalizability", "section": "discussion"},
                    {"id": "21", "item": "Funding source", "section": "other"},
                ]
            },
            "systematic_review": {
                "name": "PRISMA 2020 (Systematic Reviews)",
                "ref": "Page et al., BMJ 2021;372:n71",
                "items": [
                    {"id": "1", "item": "Title identifies as systematic review", "section": "title"},
                    {"id": "2", "item": "Structured abstract", "section": "abstract"},
                    {"id": "3", "item": "Rationale", "section": "introduction"},
                    {"id": "4", "item": "Objectives", "section": "introduction"},
                    {"id": "5", "item": "Eligibility criteria (PICO)", "section": "methods"},
                    {"id": "6", "item": "Information sources", "section": "methods"},
                    {"id": "7", "item": "Search strategy", "section": "methods"},
                    {"id": "8", "item": "Selection process", "section": "methods"},
                    {"id": "9", "item": "Data collection process", "section": "methods"},
                    {"id": "10", "item": "Risk of bias assessment", "section": "methods"},
                    {"id": "11", "item": "Effect measures", "section": "methods"},
                    {"id": "12", "item": "Synthesis methods", "section": "methods"},
                    {"id": "13", "item": "Reporting bias assessment", "section": "methods"},
                    {"id": "14", "item": "Certainty assessment (GRADE)", "section": "methods"},
                    {"id": "16", "item": "Study selection flow diagram", "section": "results"},
                    {"id": "17", "item": "Study characteristics", "section": "results"},
                    {"id": "18", "item": "Risk of bias results", "section": "results"},
                    {"id": "19", "item": "Synthesis results (forest plots)", "section": "results"},
                    {"id": "20", "item": "Reporting biases", "section": "results"},
                    {"id": "21", "item": "Certainty of evidence", "section": "results"},
                    {"id": "22", "item": "Discussion — interpretation, limitations", "section": "discussion"},
                    {"id": "24", "item": "Registration and protocol", "section": "other"},
                    {"id": "25", "item": "Funding", "section": "other"},
                ]
            },
            "animal_study": {
                "name": "ARRIVE 2.0 (Animal Studies)",
                "ref": "Percie du Sert et al., PLoS Biol 2020;18:e3000411",
                "items": [
                    {"id": "1", "item": "Study design (groups, controls)", "section": "methods"},
                    {"id": "2", "item": "Sample size (calculation/justification)", "section": "methods"},
                    {"id": "3", "item": "Inclusion/exclusion criteria", "section": "methods"},
                    {"id": "4", "item": "Randomization", "section": "methods"},
                    {"id": "5", "item": "Blinding", "section": "methods"},
                    {"id": "6", "item": "Outcome measures (primary/secondary)", "section": "methods"},
                    {"id": "7", "item": "Statistical methods", "section": "methods"},
                    {"id": "8", "item": "Experimental animals (species, strain, sex, age)", "section": "methods"},
                    {"id": "9", "item": "Experimental procedures (anesthesia, analgesia)", "section": "methods"},
                    {"id": "10", "item": "Results — numbers analyzed", "section": "results"},
                    {"id": "11", "item": "Results — adverse events", "section": "results"},
                    {"id": "12", "item": "Discussion — interpretation, 3Rs", "section": "discussion"},
                ]
            },
            "bioequivalence": {
                "name": "FDA/EMA Bioequivalence Guidelines",
                "ref": "FDA Guidance for Industry: Bioequivalence Studies, 2021",
                "items": [
                    {"id": "1", "item": "Study design (crossover/parallel)", "section": "methods"},
                    {"id": "2", "item": "Reference listed drug (RLD) specification", "section": "methods"},
                    {"id": "3", "item": "Washout period justification", "section": "methods"},
                    {"id": "4", "item": "Analytical method validation (ICH Q2)", "section": "methods"},
                    {"id": "5", "item": "PK parameters: AUC, Cmax, Tmax", "section": "results"},
                    {"id": "6", "item": "90% CI for GMR (80.00-125.00%)", "section": "results"},
                    {"id": "7", "item": "Statistical model (ANOVA, mixed effects)", "section": "methods"},
                    {"id": "8", "item": "Subject dropout handling", "section": "results"},
                    {"id": "9", "item": "Incurred sample reanalysis (ISR)", "section": "results"},
                    {"id": "10", "item": "Compliance with ICH E6(R2) GCP", "section": "other"},
                ]
            },
        }

        guideline = GUIDELINES.get(study_type)
        if not guideline:
            return {"status": "error", "error": f"Unknown study type: {study_type}. Choose from: {list(GUIDELINES.keys())}"}

        # Build section text map
        section_text = {}
        if sections:
            for s in sections:
                name = s.get("section_name", "").lower()
                section_text[name] = s.get("content", "")

        # Check each item against provided sections
        checks = []
        present = missing = partial = 0
        for item in guideline["items"]:
            status = "not_checked"
            if sections:
                target_section = item["section"]
                relevant_text = section_text.get(target_section, "")
                # Simple keyword matching
                keywords = item["item"].lower().split()[:4]
                match_count = sum(1 for kw in keywords if kw in relevant_text.lower())
                if match_count >= 3:
                    status = "present"
                    present += 1
                elif match_count >= 1:
                    status = "partial"
                    partial += 1
                else:
                    status = "missing"
                    missing += 1
            checks.append({"id": item["id"], "item": item["item"], "section": item["section"], "status": status})

        total = len(checks)
        compliance = round((present + partial * 0.5) / max(total, 1) * 100, 1) if sections else None

        out = {
            "status": "ok",
            "study_type": study_type,
            "guideline": guideline["name"],
            "reference": guideline["ref"],
            "total_items": total,
            "present": present,
            "partial": partial,
            "missing": missing,
            "compliance_score": compliance,
            "checks": checks,
            "pharma_note": f"Compliance check against {guideline['name']} — essential for pharmaceutical regulatory submissions.",
        }
        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("writing", f"Reporting Check — {study_type} ({compliance}%)", out,
                       source="Pharma Reporting Guidelines", tags=["reporting", study_type, "pharma"])
        except Exception:
            pass
        return out

    def _pharma_scorecard(self, input: dict) -> dict:
        """Pharma-specific 8-dimension manuscript quality scoring.
        Returns per-dimension scores (1-5), overall score, quality level."""
        import re

        content = input.get("content", "")
        doc_type = input.get("doc_type", "paper")
        title = input.get("title", "")

        if not content:
            return {"status": "error", "error": "Content required for scoring"}

        text = content.lower()
        word_count = len(content.split())

        # ── 8 Pharma-Specific Dimensions ──
        dimensions = {}

        # 1. Study Design Rigor (20%)
        design_score = 3  # baseline
        design_notes = []
        if any(w in text for w in ["randomized", "randomised", "random allocation"]):
            design_score += 0.5; design_notes.append("randomization mentioned")
        if any(w in text for w in ["double-blind", "single-blind", "blinded", "blinding"]):
            design_score += 0.5; design_notes.append("blinding mentioned")
        if any(w in text for w in ["power analysis", "sample size calculation", "power calculation"]):
            design_score += 0.5; design_notes.append("power analysis present")
        if any(w in text for w in ["primary endpoint", "primary outcome", "main outcome"]):
            design_score += 0.3; design_notes.append("primary endpoint defined")
        if any(w in text for w in ["inclusion criteria", "exclusion criteria", "eligibility criteria"]):
            design_score += 0.3; design_notes.append("eligibility criteria defined")
        if any(w in text for w in ["placebo", "positive control", "vehicle control"]):
            design_score += 0.2; design_notes.append("control group described")
        dimensions["study_design_rigor"] = {"score": min(5.0, round(design_score, 1)), "weight": 0.20, "notes": design_notes}

        # 2. Statistical Analysis (15%)
        stat_score = 3
        stat_notes = []
        if any(w in text for w in ["confidence interval", "95% ci", "ci:", "confidence intervals"]):
            stat_score += 0.5; stat_notes.append("confidence intervals reported")
        if any(w in text for w in ["p-value", "p < ", "p = ", "p<", "p="]):
            stat_score += 0.3; stat_notes.append("p-values reported")
        if any(w in text for w in ["effect size", "cohens d", "cohen", "hedges g"]):
            stat_score += 0.5; stat_notes.append("effect sizes reported")
        if any(w in text for w in ["anova", "t-test", "chi-square", "regression", "mixed model"]):
            stat_score += 0.4; stat_notes.append("appropriate statistical test")
        if any(w in text for w in ["intention-to-treat", "itt", "per-protocol", "pp"]):
            stat_score += 0.3; stat_notes.append("ITT/PP analysis population defined")
        if any(w in text for w in ["multiple comparison", "bonferroni", "tukey", "holm"]):
            stat_score += 0.2; stat_notes.append("multiple comparison correction")
        dimensions["statistical_analysis"] = {"score": min(5.0, round(stat_score, 1)), "weight": 0.15, "notes": stat_notes}

        # 3. Safety Reporting (15%)
        safety_score = 3
        safety_notes = []
        if any(w in text for w in ["adverse event", "adverse events", "ae ", "aes "]):
            safety_score += 0.5; safety_notes.append("adverse events reported")
        if any(w in text for w in ["serious adverse event", "sae", "saes"]):
            safety_score += 0.4; safety_notes.append("SAEs reported")
        if any(w in text for w in ["dose-limiting toxicity", "dlt", "maximum tolerated dose", "mtd"]):
            safety_score += 0.3; safety_notes.append("dose-limiting toxicity/MTD")
        if any(w in text for w in ["laboratory", "biochemistry", "hematology", "hemogram"]):
            safety_score += 0.2; safety_notes.append("laboratory safety data")
        if any(w in text for w in ["vital signs", "ecg", "electrocardiogram"]):
            safety_score += 0.2; safety_notes.append("vital signs/ECG monitoring")
        if any(w in text for w in ["causality", "naranjo", "who-umc", "drug-related"]):
            safety_score += 0.2; safety_notes.append("causality assessment")
        dimensions["safety_reporting"] = {"score": min(5.0, round(safety_score, 1)), "weight": 0.15, "notes": safety_notes}

        # 4. Efficacy Evidence (15%)
        eff_score = 3
        eff_notes = []
        if any(w in text for w in ["primary endpoint", "primary outcome met", "statistically significant"]):
            eff_score += 0.5; eff_notes.append("primary endpoint addressed")
        if any(w in text for w in ["clinical significance", "clinically meaningful", "minimal clinically important"]):
            eff_score += 0.5; eff_notes.append("clinical significance discussed")
        if any(w in text for w in ["dose-response", "dose-response relationship"]):
            eff_score += 0.3; eff_notes.append("dose-response relationship")
        if any(w in text for w in ["number needed to treat", "nnt", "absolute risk reduction", "arr"]):
            eff_score += 0.3; eff_notes.append("NNT/ARR reported")
        if any(w in text for w in ["non-inferiority", "superiority", "equivalence"]):
            eff_score += 0.2; eff_notes.append("inferential framework stated")
        dimensions["efficacy_evidence"] = {"score": min(5.0, round(eff_score, 1)), "weight": 0.15, "notes": eff_notes}

        # 5. PK/PD Integration (10%)
        pk_score = 3
        pk_notes = []
        if any(w in text for w in ["pharmacokinetic", "pk", "absorption", "distribution", "metabolism", "excretion"]):
            pk_score += 0.4; pk_notes.append("PK parameters discussed")
        if any(w in text for w in ["auc", "cmax", "tmax", "half-life", "clearance"]):
            pk_score += 0.4; pk_notes.append("PK endpoints reported")
        if any(w in text for w in ["pharmacodynamic", "pd", "receptor", "binding", "ic50", "ec50"]):
            pk_score += 0.3; pk_notes.append("PD parameters reported")
        if any(w in text for w in ["therapeutic window", "therapeutic index", "exposure-response"]):
            pk_score += 0.3; pk_notes.append("therapeutic window considered")
        dimensions["pk_pd_integration"] = {"score": min(5.0, round(pk_score, 1)), "weight": 0.10, "notes": pk_notes}

        # 6. Regulatory Compliance (10%)
        reg_score = 3
        reg_notes = []
        if any(w in text for w in ["ich", "international council for harmonisation"]):
            reg_score += 0.4; reg_notes.append("ICH guidelines referenced")
        if any(w in text for w in ["gcp", "good clinical practice", "glp", "good laboratory practice"]):
            reg_score += 0.3; reg_notes.append("GLP/GCP compliance mentioned")
        if any(w in text for w in ["consort", "strobe", "prisma", "arrive"]):
            reg_score += 0.3; reg_notes.append("reporting guideline followed")
        if any(w in text for w in ["clinicaltrials.gov", "nct", "isrctn", "trial registration"]):
            reg_score += 0.3; reg_notes.append("trial registration cited")
        if any(w in text for w in ["ethics committee", "institutional review board", "irb", "ethics approval"]):
            reg_score += 0.2; reg_notes.append("ethics approval mentioned")
        dimensions["regulatory_compliance"] = {"score": min(5.0, round(reg_score, 1)), "weight": 0.10, "notes": reg_notes}

        # 7. Citation Quality (10%)
        cite_score = 3
        cite_notes = []
        # Count citations
        doi_count = len(re.findall(r'10\.\d{4,9}/', content))
        pmid_count = len(re.findall(r'PMID[:\s]*\d{6,8}', content, re.I))
        total_cites = doi_count + pmid_count
        if total_cites >= 20:
            cite_score += 0.5; cite_notes.append(f"good citation density ({total_cites} DOIs/PMIDs)")
        elif total_cites >= 10:
            cite_score += 0.3; cite_notes.append(f"moderate citations ({total_cites})")
        if doi_count > pmid_count:
            cite_score += 0.2; cite_notes.append("DOI-based citations (verifiable)")
        if any(w in text for w in ["pubmed", "scopus", "web of science"]):
            cite_score += 0.2; cite_notes.append("indexed database cited")
        dimensions["citation_quality"] = {"score": min(5.0, round(cite_score, 1)), "weight": 0.10, "notes": cite_notes}

        # 8. Writing Clarity (5%)
        write_score = 3
        write_notes = []
        # Check word count is appropriate
        if word_count >= 3000:
            write_score += 0.3; write_notes.append(f"adequate length ({word_count} words)")
        elif word_count >= 1000:
            write_score += 0.1; write_notes.append(f"moderate length ({word_count} words)")
        # Check for structured headings
        heading_count = len(re.findall(r'^#{1,4}\s', content, re.M))
        if heading_count >= 5:
            write_score += 0.3; write_notes.append(f"well-structured ({heading_count} headings)")
        # Check for tables/figures
        if any(w in text for w in ["table 1", "table 2", "figure 1", "fig. 1"]):
            write_score += 0.2; write_notes.append("tables/figures referenced")
        dimensions["writing_clarity"] = {"score": min(5.0, round(write_score, 1)), "weight": 0.05, "notes": write_notes}

        # ── Overall Score ──
        weighted_sum = sum(d["score"] * d["weight"] for d in dimensions.values())
        overall_score = round(weighted_sum, 2)

        quality_levels = [
            (4.5, "Exceptional"),
            (4.0, "Strong"),
            (3.5, "Good"),
            (3.0, "Acceptable"),
            (2.0, "Weak"),
            (0.0, "Poor"),
        ]
        quality_level = "Poor"
        for threshold, label in quality_levels:
            if overall_score >= threshold:
                quality_level = label
                break

        # Generate improvement suggestions
        suggestions = []
        for dim_name, dim in dimensions.items():
            if dim["score"] < 3.5:
                readable = dim_name.replace("_", " ").title()
                suggestions.append(f"Improve {readable} (scored {dim['score']}/5): {'; '.join(dim['notes'][:2])}")
            elif dim["score"] < 4.0:
                readable = dim_name.replace("_", " ").title()
                suggestions.append(f"Strengthen {readable} (scored {dim['score']}/5)")

        out = {
            "status": "ok",
            "doc_type": doc_type,
            "word_count": word_count,
            "overall_score": overall_score,
            "quality_level": quality_level,
            "dimensions": dimensions,
            "suggestions": suggestions[:8],
            "pharma_note": "Scoring uses 8 pharma-specific dimensions weighted by importance for pharmaceutical research submissions.",
        }
        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("writing", f"Pharma Scorecard — {quality_level} ({overall_score}/5)", out,
                       source="Pharma Manuscript Scorecard", tags=["scorecard", "quality", "pharma"])
        except Exception:
            pass
        return out


def _sanitize(text: str) -> str:
    if not text:
        return ""
    for c, r in [("\\", "\\textbackslash "), ("&", "\\&"), ("%", "\\%"), ("$", "\\$"),
                  ("#", "\\#"), ("_", "\\_"), ("{", "\\{"), ("}", "\\}"),
                  ("~", "\\textasciitilde "), ("^", "\\textasciicircum ")]:
        text = text.replace(c, r)
    return text


# ═══════════════════════════════════════════════════════════════════════════
# Advanced Research Skills (v7.7.1+) — EQUATOR, AI Disclosure, PRISMA,
# Peer Review Simulator, Integrity Gate
# ═══════════════════════════════════════════════════════════════════════════

    def _equator_checklist(self, input: dict) -> dict:
        """Skill 1: EQUATOR reporting guidelines compliance checklist.

        Returns the full checklist for a study type, or lists all available guidelines.
        """
        from modules.writing.equator_guidelines import get_guideline, list_all_guidelines

        study_type = input.get("study_type", "")
        if not study_type or study_type == "list":
            return {"status": "ok", "guidelines": list_all_guidelines()}

        guideline = get_guideline(study_type)
        return {
            "status": "ok",
            "guideline": guideline["name"],
            "full_name": guideline["full_name"],
            "applies_to": guideline["applies_to"],
            "url": guideline["url"],
            "items": guideline["items"],
            "total_items": len(guideline["items"]),
        }

    def _ai_disclosure(self, input: dict) -> dict:
        """Skill 2: AI usage disclosure statement generator.

        Generates a venue-specific AI-usage statement for publication.
        """
        from modules.writing.academic_skills import generate_ai_disclosure, VENUE_AI_POLICIES

        venue = input.get("venue", "icmje")
        tool_name = input.get("tool_name", "BioDockify AI Engine")
        tasks = input.get("tasks", ["literature screening", "data analysis assistance"])
        author_role = input.get("author_role", "reviewed and edited")

        if venue == "list":
            venues = []
            for key, v in VENUE_AI_POLICIES.items():
                venues.append({
                    "key": key,
                    "name": v["name"],
                    "requires_disclosure": v["requires_disclosure"],
                    "placement": v["placement"],
                })
            return {"status": "ok", "venues": venues}

        result = generate_ai_disclosure(venue, tool_name, tasks, author_role)
        return {"status": "ok", **result}

    def _prisma_pipeline(self, input: dict) -> dict:
        """Skill 3: PRISMA systematic review + meta-analysis pipeline.

        Returns PRISMA checklist, RoB template, or GRADE template.
        """
        from modules.writing.academic_skills import (
            PRISMA_2020_CHECKLIST, build_prisma_flow_diagram,
            risk_of_bias_checklist, grade_assessment_template
        )

        sub = input.get("sub", "checklist")

        if sub == "checklist":
            return {"status": "ok", "checklist": PRISMA_2020_CHECKLIST,
                    "total_items": len(PRISMA_2020_CHECKLIST)}

        if sub == "flow_diagram":
            result = build_prisma_flow_diagram(
                identified=input.get("identified", 0),
                screened=input.get("screened", 0),
                excluded_title=input.get("excluded_title", 0),
                full_text_assessed=input.get("full_text_assessed", 0),
                excluded_full_text=input.get("excluded_full_text", 0),
                included=input.get("included", 0),
                reasons_excluded=input.get("reasons_excluded", []),
            )
            return {"status": "ok", **result}

        if sub == "risk_of_bias":
            study_type = input.get("study_type", "rct")
            return {"status": "ok", **risk_of_bias_checklist(study_type)}

        if sub == "grade":
            return {"status": "ok", **grade_assessment_template()}

        return {"status": "ok", "sub_actions": ["checklist", "flow_diagram", "risk_of_bias", "grade"]}

    def _peer_review(self, input: dict) -> dict:
        """Skill 4: Multi-perspective peer review simulator.

        Returns review panel config or generates a review prompt for the LLM.
        """
        from modules.writing.academic_skills import PEER_REVIEW_PANEL, build_review_prompt

        manuscript = input.get("manuscript", "")
        reviewer = input.get("reviewer", "")

        if not manuscript and not reviewer:
            return {
                "status": "ok",
                "panel": [
                    {"role": r["role"], "persona": r["persona"],
                     "focus_areas": r["focus_areas"],
                     "scoring_dimensions": r["scoring_dimensions"]}
                    for r in PEER_REVIEW_PANEL["reviewers"]
                ],
            }

        if reviewer and manuscript:
            prompt = build_review_prompt(manuscript, reviewer)
            return {"status": "ok", "reviewer": reviewer, "prompt": prompt}

        if manuscript:
            # Generate prompts for all reviewers
            prompts = {}
            for r in PEER_REVIEW_PANEL["reviewers"]:
                role_key = r["role"].lower().replace(" ", "_")
                prompts[role_key] = build_review_prompt(manuscript, r["role"])
            return {"status": "ok", "prompts": prompts}

        return {"status": "error", "error": "Provide manuscript text and/or reviewer role"}

    def _integrity_audit(self, input: dict) -> dict:
        """Skill 5: L3 claim-faithfulness integrity gate.

        Audits manuscript text for uncited claims, overclaiming, and integrity issues.
        """
        from modules.writing.academic_skills import audit_claims

        text = input.get("text", input.get("manuscript", ""))
        if not text or len(text) < 50:
            return {"status": "error", "error": "Provide manuscript text (min 50 chars)"}

        citations = input.get("citations", [])
        result = audit_claims(text, citations)
        return {"status": "ok", **result}

    def _citation_network(self, input: dict) -> dict:
        """Skill 6: Citation Network Visualization (Research Rabbit-inspired).

        Builds a citation network from KB entries showing connections between papers.
        """
        from modules.writing.academic_skills import build_citation_network, generate_citation_graph_mermaid

        # Load KB entries
        index_path = "/a0/data/knowledge_base/index.json"
        try:
            import json
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
            entries = index.get("entries", [])
        except Exception as e:
            return {"status": "error", "error": f"Failed to load KB index: {e}"}

        # Filter by category if specified
        category = input.get("category")
        if category:
            entries = [e for e in entries if e.get("category") == category]

        if not entries:
            return {"status": "ok", "message": "No KB entries found", "nodes": [], "edges": []}

        # Build citation network
        network = build_citation_network(entries)

        # Generate Mermaid diagram
        mermaid = generate_citation_graph_mermaid(entries)

        return {
            "status": "ok",
            **network,
            "mermaid": mermaid,
            "message": f"Found {network['stats']['total_papers']} papers with {network['stats']['total_connections']} connections",
        }

    # ─────────────────────────────────────────────────────────────────────
    # Advanced Writing Skills (v7.8.0+) — PaperForge + Rigorous inspired
    # ─────────────────────────────────────────────────────────────────────

    def _de_aigc(self, input: dict) -> dict:
        """Skill 1: De-AIGC rewrite (anti-AI-tone polishing).

        Detects AI-typical patterns and suggests human-sounding rewrites.
        """
        from modules.writing.advanced_writing import de_aigc_rewrite

        text = input.get("text", "")
        aggressiveness = input.get("aggressiveness", "moderate")

        if not text or len(text) < 50:
            return {"status": "error", "error": "Provide text (min 50 chars)"}

        result = de_aigc_rewrite(text, aggressiveness)
        return {"status": "ok", **result}

    def _section_analysis(self, input: dict) -> dict:
        """Skill 2: Section-by-section analysis (S1-S10).

        Analyzes each manuscript section against quality criteria.
        """
        from modules.writing.advanced_writing import analyze_sections

        text = input.get("text", "")
        if not text or len(text) < 100:
            return {"status": "error", "error": "Provide manuscript text (min 100 chars)"}

        result = analyze_sections(text)
        return {"status": "ok", **result}

    def _citation_gaps(self, input: dict) -> dict:
        """Skill 3: Citation gap identification.

        Finds claims that lack citations (gaps in the reference list).
        """
        from modules.writing.advanced_writing import find_citation_gaps

        text = input.get("text", "")
        if not text or len(text) < 100:
            return {"status": "error", "error": "Provide manuscript text (min 100 chars)"}

        result = find_citation_gaps(text)
        return {"status": "ok", **result}

    def _terminology_check(self, input: dict) -> dict:
        """Skill 4: Terminology consistency checker.

        Detects inconsistent drug names, abbreviations, and notation.
        """
        from modules.writing.advanced_writing import check_terminology

        text = input.get("text", "")
        if not text or len(text) < 100:
            return {"status": "error", "error": "Provide manuscript text (min 100 chars)"}

        result = check_terminology(text)
        return {"status": "ok", **result}

    def _scientific_rigor(self, input: dict) -> dict:
        """Skill 5: Scientific rigor review (R1-R7).

        Reviews manuscript for scientific rigor across 7 dimensions.
        """
        from modules.writing.advanced_writing import scientific_rigor_review

        text = input.get("text", "")
        if not text or len(text) < 100:
            return {"status": "error", "error": "Provide manuscript text (min 100 chars)"}

        result = scientific_rigor_review(text)
        return {"status": "ok", **result}

    def _quality_control(self, input: dict) -> dict:
        """Skill 6: Quality control validation layer.

        Validates and deduplicates outputs from multiple review agents.
        """
        from modules.writing.advanced_writing import validate_review_outputs

        review_results = input.get("review_results", [])
        if not review_results:
            return {"status": "error", "error": "Provide review_results list"}

        result = validate_review_outputs(review_results)
        return {"status": "ok", **result}

    def _executive_summary(self, input: dict) -> dict:
        """Skill 7: Executive summary generator.

        Generates a 2-step executive summary of all review results.
        """
        from modules.writing.advanced_writing import generate_executive_summary

        section_analysis = input.get("section_analysis", {})
        terminology_check = input.get("terminology_check", {})
        rigor_review = input.get("rigor_review", {})
        citation_gaps = input.get("citation_gaps", {})
        aigc_check = input.get("aigc_check", {})

        result = generate_executive_summary(
            section_analysis, terminology_check, rigor_review, citation_gaps, aigc_check
        )
        return {"status": "ok", **result}

"""Journal Recommender API — queries 36,145 Scopus/WoS-indexed journals database."""
from helpers.api import ApiHandler, Request, Response
import sqlite3, os, logging

log = logging.getLogger("journal_recommender")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "journal-recommender", "assets", "journals.db")


def _query(where_clause="1=1", params=(), limit=50, offset=0):
    if not os.path.exists(DB_PATH):
        return {"error": f"Journal database not found at {DB_PATH}", "results": [], "total": 0}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM journals WHERE {where_clause}", params).fetchone()[0]
        rows = conn.execute(f"SELECT * FROM journals WHERE {where_clause} ORDER BY title LIMIT ? OFFSET ?", (*params, limit, offset)).fetchall()
        return {"results": [dict(r) for r in rows], "total": count, "offset": offset, "limit": limit}
    finally:
        conn.close()


class JournalRecommenderHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "search")

        if action == "search":
            query = input.get("query", "")
            scopus = input.get("scopus", input.get("scopus_only", False))
            wos = input.get("wos", input.get("wos_only", False))
            oa = input.get("oa", input.get("open_access", None))
            subject = input.get("subject", "")
            limit = int(input.get("limit", 50))
            offset = int(input.get("offset", 0))

            where = ["1=1"]
            params = []
            if query:
                where.append("(title LIKE ? OR issn LIKE ? OR eissn LIKE ?)")
                like = f"%{query}%"
                params.extend([like, like, like])
            if scopus:
                where.append("scopus_indexed = 1")
            if wos:
                where.append("wos_indexed = 1")
            if oa is not None:
                where.append("oa_status = ?")
                params.append(oa)
            if subject:
                where.append("(scopus_subjects LIKE ? OR asjc_codes LIKE ? OR wos_categories LIKE ?)")
                like_s = f"%{subject}%"
                params.extend([like_s, like_s, like_s])

            return {"success": True, **_query(" AND ".join(where), tuple(params), limit, offset)}

        if action == "detail":
            issn = input.get("issn", "")
            if not issn:
                return {"error": "issn required"}
            result = _query("issn = ? OR eissn = ?", (issn, issn), limit=1)
            if result["total"] > 0:
                return {"success": True, "journal": result["results"][0]}
            return {"success": False, "error": f"Journal with ISSN {issn} not found"}

        if action == "info":
            exists = os.path.exists(DB_PATH)
            total = 0
            if exists:
                conn = sqlite3.connect(DB_PATH)
                total = conn.execute("SELECT COUNT(*) FROM journals").fetchone()[0]
                conn.close()
            return {
                "success": True,
                "database": "Scopus (Mar 2025) + WoS (Mar 2024) master lists",
                "total_journals": total,
                "db_exists": exists,
                "db_path": DB_PATH,
                "schema": ["title", "issn", "eissn", "publisher", "oa_status", "asjc_codes", "scopus_subjects", "wos_indexed", "scopus_indexed", "wos_categories", "source_type"],
            }

        if action == "subjects":
            if not os.path.exists(DB_PATH):
                return {"error": "Database not found"}
            conn = sqlite3.connect(DB_PATH)
            subjects = [r[0] for r in conn.execute("SELECT DISTINCT scopus_subjects FROM journals WHERE scopus_subjects != '' ORDER BY scopus_subjects LIMIT 500").fetchall()]
            conn.close()
            return {"success": True, "subjects": subjects, "count": len(subjects)}

        if action == "stats":
            if not os.path.exists(DB_PATH):
                return {"error": "Database not found"}
            conn = sqlite3.connect(DB_PATH)
            total = conn.execute("SELECT COUNT(*) FROM journals").fetchone()[0]
            scopus_count = conn.execute("SELECT COUNT(*) FROM journals WHERE scopus_indexed=1").fetchone()[0]
            wos_count = conn.execute("SELECT COUNT(*) FROM journals WHERE wos_indexed=1").fetchone()[0]
            dual_count = conn.execute("SELECT COUNT(*) FROM journals WHERE scopus_indexed=1 AND wos_indexed=1").fetchone()[0]
            oa_count = conn.execute("SELECT COUNT(*) FROM journals WHERE oa_status LIKE '%Open Access%'").fetchone()[0]
            conn.close()
            return {"success": True, "total": total, "scopus_indexed": scopus_count, "wos_indexed": wos_count, "dual_indexed": dual_count, "open_access": oa_count}

        return {"error": f"Unknown action: {action}"}

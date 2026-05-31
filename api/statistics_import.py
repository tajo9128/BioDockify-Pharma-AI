"""Statistics Import API — Flask handler for CSV/JSON data import."""
from helpers.api import ApiHandler, Request, Response
import logging, csv, io, json

log = logging.getLogger("statistics_import")

# Store imported data in memory (shared with other statistics handlers)
_imported_data = {}


class StatisticsImport(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "import")

        if action == "import":
            return self._import_data(input)
        elif action == "import_file":
            return self._import_from_content(input)
        elif action == "get_columns":
            return {"status": "ok", "columns": list(_imported_data.get("columns", [])), "rows": _imported_data.get("rows", 0)}

        return {"status": "error", "error": f"Unknown action: {action}"}

    def _import_from_content(self, input: dict) -> dict:
        """Import data from file content (JSON/CSV string)."""
        content = input.get("content", "")
        filename = input.get("filename", "data.csv")
        if not content:
            return {"status": "error", "error": "No content provided"}

        try:
            if filename.endswith(".json"):
                obj = json.loads(content)
                rows = obj if isinstance(obj, list) else (obj.get("data", []) or list(obj.values())[0] if isinstance(obj, dict) else [])
                if rows:
                    columns = list(rows[0].keys())
                    _imported_data["columns"] = columns
                    _imported_data["rows"] = len(rows)
                    _imported_data["data"] = rows
                    return {"status": "success", "data_summary": {"column_names": columns, "rows": len(rows), "filename": filename}}
            else:
                # CSV parsing
                reader = csv.DictReader(io.StringIO(content))
                rows = [row for row in reader]
                if not rows:
                    return {"status": "error", "error": "No data rows found"}
                columns = list(rows[0].keys())
                _imported_data["columns"] = columns
                _imported_data["rows"] = len(rows)
                _imported_data["data"] = rows
                return {"status": "success", "data_summary": {"column_names": columns, "rows": len(rows), "filename": filename}}
        except Exception as e:
            return {"status": "error", "error": f"Parse error: {str(e)}"}

    def _import_data(self, input: dict) -> dict:
        """Import data from multipart form (file upload)."""
        content = input.get("content", "")
        filename = input.get("filename", "data.csv")
        if content:
            return self._import_from_content({"content": content, "filename": filename})
        return {"status": "error", "error": "No data provided. Upload a CSV or JSON file."}


from .dirty_json import DirtyJson
import regex, re
from helpers.modules import load_classes_from_file, load_classes_from_folder # keep here for backwards compatibility
from typing import Any


def _parse_dsml_tool_calls(text: str) -> dict[str, Any] | None:
    """Convert DSML/XML-style tool calls (DeepSeek native format) to the
    JSON dict the framework expects.

    DeepSeek sometimes emits tool calls as XML-ish tags instead of JSON:
        <｜｜DSML｜｜tool_calls>
        <｜｜DSML｜｜invoke name="text_editor:read">
        <｜｜DSML｜｜parameter name="path" string="true">/a0/file.md</｜｜DSML｜｜parameter>
        <｜｜DSML｜｜parameter name="line_from" string="false">1</｜｜DSML｜｜parameter>
        </｜｜DSML｜｜invoke>
        </｜｜DSML｜｜tool_calls>

    This also handles plain XML variants:
        <tool_calls><invoke name="..."><parameter name="...">...</parameter></invoke></tool_calls>
        <function_call>{"name":...,"arguments":...}</function_call>

    Returns {"tool_name": ..., "tool_args": {...}} or None.
    """
    if not text or not isinstance(text, str):
        return None

    # --- Variant 1: DeepSeek DSML tags (｜｜DSML｜｜ with fullwidth pipes) ---
    # Normalize the fullwidth pipe characters to regular ones for matching
    norm = text.replace("\uff5c\uff5c", "||").replace("\uff5c", "|")
    # Pattern: <||DSML||invoke name="TOOL"> ... params ... </||DSML||invoke>
    dsml_invoke = re.search(
        r'<\|\|DSML\|\|invoke\s+name=["\']([^"\']+)["\']\s*>(.*?)</\|\|DSML\|\|invoke>',
        norm, re.DOTALL | re.IGNORECASE,
    )
    if dsml_invoke:
        tool_name = dsml_invoke.group(1).strip()
        body = dsml_invoke.group(2)
        args: dict[str, Any] = {}
        # Extract each parameter
        for pm in re.finditer(
            r'<\|\|DSML\|\|parameter\s+name=["\']([^"\']+)["\']\s*(?:string=["\'][^"\']*["\'])?\s*>(.*?)</\|\|DSML\|\|parameter>',
            body, re.DOTALL | re.IGNORECASE,
        ):
            pname = pm.group(1).strip()
            pval = pm.group(2).strip()
            # Try to convert numeric/bool values
            if pval.lower() in ("true", "false"):
                args[pname] = pval.lower() == "true"
            else:
                try:
                    args[pname] = int(pval)
                except ValueError:
                    try:
                        args[pname] = float(pval)
                    except ValueError:
                        args[pname] = pval
        return {"tool_name": tool_name, "tool_args": args}

    # --- Variant 2: plain XML <invoke name="..."> tags ---
    xml_invoke = re.search(
        r'<invoke\s+name=["\']([^"\']+)["\']\s*>(.*?)</invoke>',
        text, re.DOTALL | re.IGNORECASE,
    )
    if xml_invoke:
        tool_name = xml_invoke.group(1).strip()
        body = xml_invoke.group(2)
        args = {}
        for pm in re.finditer(
            r'<parameter\s+name=["\']([^"\']+)["\']\s*>(.*?)</parameter>',
            body, re.DOTALL | re.IGNORECASE,
        ):
            pname = pm.group(1).strip()
            pval = pm.group(2).strip()
            if pval.lower() in ("true", "false"):
                args[pname] = pval.lower() == "true"
            else:
                try:
                    args[pname] = int(pval)
                except ValueError:
                    try:
                        args[pname] = float(pval)
                    except ValueError:
                        args[pname] = pval
        return {"tool_name": tool_name, "tool_args": args}

    # --- Variant 3: <function_call>{"name":...,"arguments":{...}}</function_call> ---
    fc_match = re.search(
        r'<function_call>\s*(\{.*?\})\s*</function_call>',
        text, re.DOTALL | re.IGNORECASE,
    )
    if fc_match:
        import json as _json
        try:
            data = _json.loads(fc_match.group(1))
            name = data.get("name") or data.get("tool_name")
            args_raw = data.get("arguments") or data.get("tool_args") or {}
            if isinstance(args_raw, str):
                args_raw = _json.loads(args_raw)
            if name:
                return {"tool_name": name, "tool_args": args_raw}
        except Exception:
            pass

    return None


def json_parse_dirty(json: str) -> dict[str, Any] | None:
    if not json or not isinstance(json, str):
        return None

    # First, try the standard JSON extraction
    ext_json = extract_json_object_string(json.strip())
    if ext_json:
        try:
            data = DirtyJson.parse_string(ext_json)
            if isinstance(data, dict):
                return data
        except Exception:
            pass  # fall through to DSML/XML parsing

    # Fallback: parse DSML/XML-style tool calls (DeepSeek and other models
    # that emit native XML tool-call formats instead of JSON)
    dsml_result = _parse_dsml_tool_calls(json)
    if dsml_result:
        return dsml_result

    return None


def normalize_tool_request(tool_request: Any) -> tuple[str, dict]:
    if not isinstance(tool_request, dict):
        raise ValueError("Tool request must be a dictionary")
    tool_name = tool_request.get("tool_name")
    if not tool_name or not isinstance(tool_name, str):
        tool_name = tool_request.get("tool")
    if not tool_name or not isinstance(tool_name, str):
        raise ValueError("Tool request must have a tool_name (type string) field")
    tool_args = tool_request.get("tool_args")
    if not isinstance(tool_args, dict):
        tool_args = tool_request.get("args")
    if not isinstance(tool_args, dict):
        raise ValueError("Tool request must have a tool_args (type dictionary) field")
    return tool_name, tool_args


def extract_json_root_string(content: str) -> str | None:
    if not content or not isinstance(content, str):
        return None

    start = content.find("{")
    if start == -1:
        return None
    first_array = content.find("[")
    if first_array != -1 and first_array < start:
        return None

    parser = DirtyJson()
    try:
        parser.parse(content[start:])
    except Exception:
        return None

    if not parser.completed:
        return None

    return content[start : start + parser.index]


def extract_json_object_string(content):
    """Extract the first complete JSON object using brace-balanced matching.
    
    Correctly handles nested braces and string literals containing braces,
    unlike the naive rfind('}') approach which grabs everything from first
    '{' to last '}' — a common cause of parsing failures when the LLM
    output contains braces in explanations or code snippets.
    """
    start = content.find("{")
    if start == -1:
        return ""

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(content)):
        char = content[i]

        if escape:
            escape = False
            continue

        if char == '\\' and in_string:
            escape = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if not in_string:
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return content[start:i + 1]

    return content[start:]


def extract_json_string(content):
    # Regular expression pattern to match a JSON object
    pattern = r'\{(?:[^{}]|(?R))*\}|\[(?:[^\[\]]|(?R))*\]|"(?:\\.|[^"\\])*"|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'

    # Search for the pattern in the content
    match = regex.search(pattern, content)

    if match:
        # Return the matched JSON string
        return match.group(0)
    else:
        return ""


def fix_json_string(json_string):
    # Function to replace unescaped line breaks within JSON string values
    def replace_unescaped_newlines(match):
        return match.group(0).replace("\n", "\\n")

    # Use regex to find string values and apply the replacement function
    fixed_string = re.sub(
        r'(?<=: ")(.*?)(?=")', replace_unescaped_newlines, json_string, flags=re.DOTALL
    )
    return fixed_string

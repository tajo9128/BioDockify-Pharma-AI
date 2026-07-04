
from .dirty_json import DirtyJson
import regex, re
from helpers.modules import load_classes_from_file, load_classes_from_folder # keep here for backwards compatibility
from typing import Any

def json_parse_dirty(json: str) -> dict[str, Any] | None:
    if not json or not isinstance(json, str):
        return None

    ext_json = extract_json_object_string(json.strip())
    if ext_json:
        try:
            data = DirtyJson.parse_string(ext_json)
            if isinstance(data, dict):
                return data
        except Exception:
            # If parsing fails, return None instead of crashing
            return None
    return None

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



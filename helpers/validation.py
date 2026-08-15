"""Shared input validation helpers — prevent path traversal and injection.

All user-supplied identifiers (job_id, session_id, model_id, backup_id,
category, notebook_id) MUST pass through these before being used in any
filesystem path construction or command.
"""
import os
import re
import logging

log = logging.getLogger("validation")

# ── Safe identifier patterns ─────────────────────────────────────────────────

# Generic safe ID: alphanumeric + underscore + hyphen, max 128 chars.
# Blocks path traversal (../), null bytes, shell metacharacters, unicode.
SAFE_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,128}$')

# Session IDs from deep_research: date_time format like "20240115_143022"
SESSION_ID_RE = re.compile(r'^\d{8}_\d{6}$')

# Backup IDs: "backup_YYYYMMDD_HHMMSS" or "uploaded_YYYYMMDD_HHMMSS"
BACKUP_ID_RE = re.compile(r'^(backup|uploaded)_\d{8}_\d{6}$')

# Model IDs for QSAR: alphanumeric + underscore + hyphen
MODEL_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


def is_safe_id(value: str, pattern: re.Pattern = None) -> bool:
    """Check if a value matches the safe ID pattern (or a custom pattern)."""
    if not value or not isinstance(value, str):
        return False
    if pattern:
        return bool(pattern.match(value))
    return bool(SAFE_ID_RE.match(value))


def safe_join(base_dir: str, *path_parts: str, pattern: re.Pattern = None) -> str | None:
    """Safely join path parts under base_dir, rejecting traversal.

    Returns the joined path if safe, None if any part fails validation.
    The result is guaranteed to be under base_dir (realpath-checked).
    """
    # Validate each user-supplied part
    for part in path_parts:
        if not part or not isinstance(part, str):
            return None
        if pattern and not pattern.match(part):
            log.warning(f"safe_join: rejected part {part!r} (pattern mismatch)")
            return None
        if not SAFE_ID_RE.match(part) and not pattern:
            log.warning(f"safe_join: rejected part {part!r} (unsafe characters)")
            return None

    result = os.path.join(base_dir, *path_parts)

    # Realpath containment check — result must be under base_dir
    base_real = os.path.realpath(base_dir)
    result_real = os.path.realpath(result)
    if not result_real.startswith(base_real + os.sep) and result_real != base_real:
        log.warning(f"safe_join: {result_real} escapes base {base_real}")
        return None

    return result


def sanitize_category(category: str, allowed: dict) -> str:
    """Return category if it's in the allowed dict, else 'misc'.

    Prevents directory traversal via the category field in KB store/upload.
    """
    if category and isinstance(category, str) and category in allowed:
        return category
    return "misc"


def sanitize_filename(filename: str) -> str:
    """Strip any path components and dangerous characters from a filename."""
    if not filename or not isinstance(filename, str):
        return "file"
    # Take only the basename (strips any directory components)
    name = os.path.basename(filename)
    # Remove null bytes and control characters
    name = re.sub(r'[\x00-\x1f]', '', name)
    # Limit length
    if len(name) > 255:
        name = name[:255]
    return name or "file"

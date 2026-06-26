from helpers import git, runtime
import hashlib

# BioDockify Pharma AI — update check against our own GitHub releases.
# Queries tajo9128/BioDockify-Pharma-AI (NOT agent-zero) so notifications
# are always about BioDockify versions and never mention "Agent Zero".

BIODOCKIFY_REPO_AUTHOR = "tajo9128"
BIODOCKIFY_REPO_NAME = "BioDockify-Pharma-AI"


async def check_version():
    import httpx

    current_version = git.get_version()

    anonymized_id = hashlib.sha256(runtime.get_persistent_id().encode()).hexdigest()[:20]

    # Fetch BioDockify's latest release from the GitHub API
    release_url = f"https://api.github.com/repos/{BIODOCKIFY_REPO_AUTHOR}/{BIODOCKIFY_REPO_NAME}/releases/latest"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            release_url,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        if response.status_code != 200:
            return {"current_version": current_version, "latest_version": current_version}
        data = response.json()

    latest_tag = data.get("tag_name", "") or ""
    latest_version = latest_tag.lstrip("v")
    release_url_html = data.get("html_url", "") or f"https://github.com/{BIODOCKIFY_REPO_AUTHOR}/{BIODOCKIFY_REPO_NAME}/releases"

    # Determine if a newer version is available.
    # Compare loosely on the numeric tag (current_version may be a git describe string).
    is_newer = _is_newer(current_version, latest_version)

    notification = None
    if is_newer:
        # Detect major-version bumps for a distinct message
        is_major = _is_major_bump(current_version, latest_version)
        if is_major:
            notification = {
                "id": "biodockify_major_update",
                "title": "New major version available",
                "message": (
                    f"A new major version ({latest_tag}) of BioDockify Pharma AI has been released "
                    f"that requires updating and using a newer Docker image."
                ),
                "type": "info",
                "detail": f"View update instructions: {release_url_html}",
            }
        else:
            notification = {
                "id": f"biodockify_update_{latest_tag}",
                "title": "Newer version available",
                "message": f"A newer version ({latest_tag}) of BioDockify Pharma AI is available. Please update to the latest version.",
                "type": "info",
                "detail": release_url_html,
            }

    return {
        "current_version": current_version,
        "latest_version": latest_version,
        "latest_tag": latest_tag,
        "release_url": release_url_html,
        "notification": notification,
    }


def _parse_version_tuple(version: str):
    """Extract leading numeric version components as a tuple of ints."""
    import re
    if not version:
        return ()
    # Strip non-numeric prefix (e.g. "v", "fork-")
    match = re.search(r"(\d+(?:\.\d+)*)", version)
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def _is_newer(current: str, latest: str) -> bool:
    cur = _parse_version_tuple(current)
    lat = _parse_version_tuple(latest)
    if not lat:
        return False
    if not cur:
        return True
    # Pad to equal length
    length = max(len(cur), len(lat))
    cur = cur + (0,) * (length - len(cur))
    lat = lat + (0,) * (length - len(lat))
    return lat > cur


def _is_major_bump(current: str, latest: str) -> bool:
    """True when the major version number increases (e.g. v1.x -> v2.x)."""
    cur = _parse_version_tuple(current)
    lat = _parse_version_tuple(latest)
    if not cur or not lat:
        return False
    return lat[0] > cur[0]

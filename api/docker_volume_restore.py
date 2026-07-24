"""Docker Volume Restore — recover data from orphaned Docker volumes.

When a container is deleted, its Docker volumes may persist with user data.
This handler scans all Docker volumes, identifies orphaned ones containing
BioDockify data, and allows one-click restore.

Uses Docker socket directly (no Docker CLI required).
"""
import json
import logging
import os
import shutil
import datetime
import http.client
import socket
from helpers.api import ApiHandler, Request, Response

log = logging.getLogger("docker_volume_restore")

DOCKER_SOCKET = "/var/run/docker.sock"

# Paths that indicate a volume contains BioDockify data
BIO_MARKERS = [
    "usr", ".a0proj", "data", "backups", "settings.json",
    "workdir", "knowledge", "plugins", "projects",
]

# Restore targets inside the container
RESTORE_TARGETS = {
    "usr": "/a0/usr",
    ".a0proj": "/a0/.a0proj",
    "data": "/a0/data",
    "backups": "/a0/usr/backups",
    "settings.json": "/a0/usr/settings.json",
    "workdir": "/a0/usr/workdir",
    "knowledge": "/a0/data/knowledge_base",
    "plugins": "/a0/usr/plugins",
    "projects": "/a0/usr/projects",
}


class _UnixHTTPConnection(http.client.HTTPConnection):
    """HTTP connection over a Unix socket."""

    def __init__(self, socket_path, timeout=10):
        super().__init__("localhost", timeout=timeout)
        self._socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._socket_path)


def _docker_api(method, path, body=None):
    """Call Docker Engine API via Unix socket. Returns parsed JSON or None."""
    if not os.path.exists(DOCKER_SOCKET):
        return None, "Docker socket not found. Mount /var/run/docker.sock to enable."
    try:
        conn = _UnixHTTPConnection(DOCKER_SOCKET, timeout=15)
        headers = {"Content-Type": "application/json"}
        conn.request(method, f"http://localhost{path}", body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode()
        conn.close()
        if resp.status >= 400:
            return None, f"Docker API error {resp.status}: {data[:200]}"
        return json.loads(data) if data else {}, None
    except FileNotFoundError:
        return None, "Docker socket not available. Mount /var/run/docker.sock to enable volume restore."
    except ConnectionRefusedError:
        return None, "Docker daemon not responding."
    except Exception as e:
        return None, f"Docker API error: {e}"


def _is_bio_volume(contents):
    """Check if volume contents match BioDockify data patterns."""
    if not contents:
        return False, []
    found = [m for m in BIO_MARKERS if m in contents]
    return len(found) >= 1, found


def _get_dir_size(path):
    """Get directory size in MB."""
    total = 0
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except OSError:
        pass
    return round(total / (1024 * 1024), 2)


def _count_files(path):
    """Count files recursively."""
    count = 0
    try:
        for _, _, files in os.walk(path):
            count += len(files)
    except OSError:
        pass
    return count


class DockerVolumeRestoreHandler(ApiHandler):
    """Scan orphaned Docker volumes and restore BioDockify data from them."""

    @classmethod
    def requires_auth(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "scan")

        if action == "scan":
            return self._scan_volumes()
        elif action == "inspect":
            return self._inspect_volume(input.get("volume_name", ""))
        elif action == "restore":
            return self._restore_from_volume(
                input.get("volume_name", ""),
                input.get("overwrite_policy", "skip"),
                input.get("selected_items", []),
            )
        elif action == "download":
            return self._download_from_volume(
                input.get("volume_name", ""),
                input.get("item", ""),
            )

        return {
            "actions": ["scan", "inspect", "restore", "download"],
            "description": "Scan, inspect, and restore from Docker volumes",
        }

    def _check_docker(self):
        """Check if Docker socket is available."""
        if not os.path.exists(DOCKER_SOCKET):
            return None, (
                "Docker socket not available. "
                "Add `-v /var/run/docker.sock:/var/run/docker.sock` to your docker run command to enable volume restore."
            )
        # Quick version check
        data, err = _docker_api("GET", "/version")
        if err:
            return None, err
        return data, None

    def _scan_volumes(self):
        """Scan all Docker volumes for orphaned ones with BioDockify data."""
        # Check Docker availability
        version_info, err = self._check_docker()
        if err:
            return {
                "success": False,
                "error": err,
                "docker_available": False,
            }

        # List all volumes
        data, err = _docker_api("GET", "/volumes")
        if err:
            return {"success": False, "error": f"Failed to list volumes: {err}"}

        volumes_raw = data.get("Volumes", [])
        volumes = []

        for vol in volumes_raw:
            vol_name = vol.get("Name", "")
            mountpoint = vol.get("Mountpoint", "")
            created = vol.get("CreatedAt", "")
            labels = vol.get("Labels") or {}

            # Check if attached to any container
            containers_data, _ = _docker_api(
                "GET", f"/containers/json?all=true&filters={json.dumps({'volume': [vol_name]})}"
            )
            containers = []
            if containers_data:
                for c in containers_data:
                    containers.append({
                        "name": c.get("Names", [""])[0].lstrip("/"),
                        "status": c.get("Status", ""),
                        "image": c.get("Image", ""),
                    })

            # List contents
            contents = []
            if mountpoint and os.path.isdir(mountpoint):
                try:
                    contents = os.listdir(mountpoint)
                except PermissionError:
                    contents = ["(permission denied)"]

            is_orphan = len(containers) == 0
            has_bio, markers = _is_bio_volume(contents)

            # Calculate size
            size_mb = _get_dir_size(mountpoint) if mountpoint and os.path.isdir(mountpoint) else 0
            file_count = _count_files(mountpoint) if mountpoint and os.path.isdir(mountpoint) else 0

            volumes.append({
                "name": vol_name,
                "mountpoint": mountpoint,
                "containers": containers,
                "is_orphan": is_orphan,
                "has_bio_data": has_bio,
                "bio_markers": markers,
                "contents": contents[:20],
                "content_count": len(contents),
                "size_mb": size_mb,
                "file_count": file_count,
                "created": created,
                "labels": labels,
            })

        # Sort: orphaned with BioDockify data first
        volumes.sort(key=lambda v: (
            not (v["is_orphan"] and v["has_bio_data"]),
            not v["is_orphan"],
            -v["size_mb"],
        ))

        orphaned_count = sum(1 for v in volumes if v["is_orphan"])
        bio_count = sum(1 for v in volumes if v["has_bio_data"])

        return {
            "success": True,
            "docker_available": True,
            "volumes": volumes,
            "total": len(volumes),
            "orphaned_count": orphaned_count,
            "bio_data_count": bio_count,
            "message": f"Found {len(volumes)} volumes: {orphaned_count} orphaned, {bio_count} with BioDockify data.",
        }

    def _inspect_volume(self, volume_name):
        """Deep inspect a specific volume."""
        if not volume_name:
            return {"success": False, "error": "No volume name provided"}

        # Get volume details
        data, err = _docker_api("GET", f"/volumes/{volume_name}")
        if err:
            return {"success": False, "error": f"Volume not found: {err}"}

        mountpoint = data.get("Mountpoint", "")
        if not mountpoint or not os.path.isdir(mountpoint):
            return {"success": False, "error": f"Mount point not accessible: {mountpoint}"}

        # Build directory tree
        tree = []
        for root, dirs, files in os.walk(mountpoint):
            rel = os.path.relpath(root, mountpoint)
            depth = rel.count(os.sep) if rel != "." else 0
            if depth > 4:
                continue
            for d in dirs:
                tree.append({
                    "path": os.path.join(rel, d) if rel != "." else d,
                    "type": "dir",
                    "depth": depth,
                })
            for f in files:
                fpath = os.path.join(root, f)
                tree.append({
                    "path": os.path.join(rel, f) if rel != "." else f,
                    "type": "file",
                    "depth": depth,
                    "size": os.path.getsize(fpath) if os.path.exists(fpath) else 0,
                })

        # Check for specific BioDockify data
        bio_data_found = {}
        for marker in BIO_MARKERS:
            marker_path = os.path.join(mountpoint, marker)
            if os.path.exists(marker_path):
                bio_data_found[marker] = {
                    "exists": True,
                    "is_dir": os.path.isdir(marker_path),
                    "size_mb": _get_dir_size(marker_path) if os.path.isdir(marker_path) else round(os.path.getsize(marker_path) / (1024 * 1024), 2),
                    "file_count": _count_files(marker_path) if os.path.isdir(marker_path) else 1,
                }

        return {
            "success": True,
            "volume_name": volume_name,
            "mountpoint": mountpoint,
            "tree": tree[:500],
            "bio_data_found": bio_data_found,
            "total_size_mb": _get_dir_size(mountpoint),
            "total_files": _count_files(mountpoint),
        }

    def _restore_from_volume(self, volume_name, overwrite_policy="skip", selected_items=None):
        """Restore data from a Docker volume to the container."""
        if not volume_name:
            return {"success": False, "error": "No volume name provided"}

        # Get volume details
        data, err = _docker_api("GET", f"/volumes/{volume_name}")
        if err:
            return {"success": False, "error": f"Volume not found: {err}"}

        src_root = data.get("Mountpoint", "")
        if not src_root or not os.path.isdir(src_root):
            return {"success": False, "error": f"Mount point not accessible: {src_root}"}

        restored = []
        skipped = []
        errors = []

        # Determine what to restore
        if selected_items:
            items_to_restore = selected_items
        else:
            items_to_restore = [
                item for item in os.listdir(src_root)
                if item in RESTORE_TARGETS
            ]

        for item in items_to_restore:
            src_path = os.path.join(src_root, item)
            dst_path = RESTORE_TARGETS.get(item)

            if not dst_path:
                if item.startswith("a0/"):
                    dst_path = "/" + item
                else:
                    dst_path = f"/a0/usr/{item}"

            if not os.path.exists(src_path):
                skipped.append({"item": item, "reason": "source not found"})
                continue

            try:
                if os.path.isdir(src_path):
                    if os.path.exists(dst_path):
                        if overwrite_policy == "skip":
                            skipped.append({"item": item, "reason": "exists, skip policy"})
                            continue
                        elif overwrite_policy == "overwrite":
                            file_count = 0
                            for root, dirs, files in os.walk(src_path):
                                rel = os.path.relpath(root, src_path)
                                target_dir = os.path.join(dst_path, rel)
                                os.makedirs(target_dir, exist_ok=True)
                                for f in files:
                                    src_file = os.path.join(root, f)
                                    dst_file = os.path.join(target_dir, f)
                                    if not os.path.exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
                                        shutil.copy2(src_file, dst_file)
                                        file_count += 1
                            restored.append({"item": item, "files": file_count, "action": "merged"})
                    else:
                        shutil.copytree(src_path, dst_path)
                        file_count = sum(1 for _, _, files in os.walk(src_path) for f in files)
                        restored.append({"item": item, "files": file_count, "action": "copied"})
                else:
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    if os.path.exists(dst_path) and overwrite_policy == "skip":
                        skipped.append({"item": item, "reason": "exists, skip policy"})
                        continue
                    shutil.copy2(src_path, dst_path)
                    restored.append({"item": item, "files": 1, "action": "copied"})
            except Exception as e:
                errors.append({"item": item, "error": str(e)})
                log.error(f"Failed to restore {item}: {e}")

        total_files = sum(r.get("files", 0) for r in restored)

        return {
            "success": len(restored) > 0,
            "volume_name": volume_name,
            "restored": restored,
            "skipped": skipped,
            "errors": errors,
            "total_files": total_files,
            "message": f"Restored {total_files} files from volume {volume_name}."
                       + (" Restart container to apply." if total_files > 0 else ""),
        }

    def _download_from_volume(self, volume_name, item):
        """Download a specific file from a Docker volume."""
        from flask import send_file

        if not volume_name or not item:
            return {"success": False, "error": "Volume name and item required"}

        data, err = _docker_api("GET", f"/volumes/{volume_name}")
        if err:
            return {"success": False, "error": f"Volume not found: {err}"}

        mountpoint = data.get("Mountpoint", "")
        file_path = os.path.join(mountpoint, item)

        # Security: prevent path traversal
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(os.path.realpath(mountpoint)):
            return {"success": False, "error": "Invalid path"}

        if not os.path.isfile(real_path):
            return {"success": False, "error": f"File not found: {item}"}

        return send_file(
            real_path,
            as_attachment=True,
            download_name=os.path.basename(item),
        )

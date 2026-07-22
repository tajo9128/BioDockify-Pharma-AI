"""Docker Volume Restore — recover data from orphaned Docker volumes.

When a container is deleted, its Docker volumes may persist with user data.
This handler scans all Docker volumes, identifies orphaned ones containing
BioDockify data, and allows one-click restore.
"""
import asyncio
import json
import logging
import os
import shutil
import datetime
from helpers.api import ApiHandler, Request, Response

log = logging.getLogger("docker_volume_restore")

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


async def _run_docker(*args):
    """Run a docker command asynchronously and return stdout."""
    proc = await asyncio.create_subprocess_exec(
        "docker", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode().strip(), stderr.decode().strip(), proc.returncode


def _is_bio_volume(contents):
    """Check if volume contents match BioDockify data patterns."""
    if not contents:
        return False, []
    found = [m for m in BIO_MARKERS if m in contents]
    score = len(found)
    return score >= 1, found


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
            return await self._scan_volumes()
        elif action == "inspect":
            return await self._inspect_volume(input.get("volume_name", ""))
        elif action == "restore":
            return await self._restore_from_volume(
                input.get("volume_name", ""),
                input.get("overwrite_policy", "skip"),
                input.get("selected_items", []),
            )
        elif action == "download":
            return await self._download_from_volume(
                input.get("volume_name", ""),
                input.get("item", ""),
            )

        return {
            "actions": ["scan", "inspect", "restore", "download"],
            "description": "Scan, inspect, and restore from Docker volumes",
        }

    async def _scan_volumes(self):
        """Scan all Docker volumes for orphaned ones with BioDockify data."""
        # Check if docker is available
        stdout, stderr, rc = await _run_docker("version", "--format", "{{.Server.Version}}")
        if rc != 0:
            return {
                "success": False,
                "error": "Docker not available. Mount /var/run/docker.sock to enable volume restore.",
                "docker_available": False,
            }

        # List all volumes
        stdout, stderr, rc = await _run_docker("volume", "ls", "--format", "{{.Name}}")
        if rc != 0:
            return {"success": False, "error": f"Failed to list volumes: {stderr}"}

        volume_names = [v.strip() for v in stdout.split("\n") if v.strip()]
        volumes = []

        for vol_name in volume_names:
            # Check if attached to any container
            ctrs_out, _, _ = await _run_docker(
                "ps", "-a", "--filter", f"volume={vol_name}",
                "--format", "{{.Names}}|{{.Status}}|{{.Image}}"
            )
            containers = []
            if ctrs_out.strip():
                for line in ctrs_out.strip().split("\n"):
                    parts = line.split("|")
                    containers.append({
                        "name": parts[0] if len(parts) > 0 else "",
                        "status": parts[1] if len(parts) > 1 else "",
                        "image": parts[2] if len(parts) > 2 else "",
                    })

            # Get mountpoint
            inspect_out, _, _ = await _run_docker(
                "volume", "inspect", vol_name,
                "--format", "{{.Mountpoint}}"
            )
            mountpoint = inspect_out.strip()

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
            size_mb = 0
            file_count = 0
            if mountpoint and os.path.isdir(mountpoint):
                size_mb = _get_dir_size(mountpoint)
                file_count = _count_files(mountpoint)

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
            })

        # Sort: orphaned with BioDockify data first, then orphaned, then rest
        volumes.sort(key=lambda v: (
            not (v["is_orphan"] and v["has_bio_data"]),
            not v["is_orphan"],
            -v["size_mb"],
        ))

        orphaned_count = sum(1 for v in volumes if v["is_orphan"])
        bio_count = sum(1 for v in volumes if v["has_bio_data"])

        return {
            "success": True,
            "volumes": volumes,
            "total": len(volumes),
            "orphaned_count": orphaned_count,
            "bio_data_count": bio_count,
            "message": f"Found {len(volumes)} volumes: {orphaned_count} orphaned, {bio_count} with BioDockify data.",
        }

    async def _inspect_volume(self, volume_name):
        """Deep inspect a specific volume — list full directory tree."""
        if not volume_name:
            return {"success": False, "error": "No volume name provided"}

        # Get mountpoint
        stdout, stderr, rc = await _run_docker(
            "volume", "inspect", volume_name,
            "--format", "{{.Mountpoint}}"
        )
        if rc != 0:
            return {"success": False, "error": f"Volume not found: {volume_name}"}

        mountpoint = stdout.strip()
        if not os.path.isdir(mountpoint):
            return {"success": False, "error": f"Mount point not accessible: {mountpoint}"}

        # Build directory tree
        tree = []
        for root, dirs, files in os.walk(mountpoint):
            rel = os.path.relpath(root, mountpoint)
            depth = rel.count(os.sep) if rel != "." else 0
            if depth > 4:  # Limit depth
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
            "tree": tree[:500],  # Limit to 500 entries
            "bio_data_found": bio_data_found,
            "total_size_mb": _get_dir_size(mountpoint),
            "total_files": _count_files(mountpoint),
        }

    async def _restore_from_volume(self, volume_name, overwrite_policy="skip", selected_items=None):
        """Restore data from a Docker volume to the container."""
        if not volume_name:
            return {"success": False, "error": "No volume name provided"}

        # Get mountpoint
        stdout, stderr, rc = await _run_docker(
            "volume", "inspect", volume_name,
            "--format", "{{.Mountpoint}}"
        )
        if rc != 0:
            return {"success": False, "error": f"Volume not found: {volume_name}"}

        src_root = stdout.strip()
        if not os.path.isdir(src_root):
            return {"success": False, "error": f"Mount point not accessible: {src_root}"}

        restored = []
        skipped = []
        errors = []

        # Determine what to restore
        if selected_items:
            # Restore only selected items
            items_to_restore = selected_items
        else:
            # Restore all recognized BioDockify data
            items_to_restore = [
                item for item in os.listdir(src_root)
                if item in RESTORE_TARGETS
            ]

        for item in items_to_restore:
            src_path = os.path.join(src_root, item)
            dst_path = RESTORE_TARGETS.get(item)

            if not dst_path:
                # Try to figure out destination from item name
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
                            # Merge: copy newer files
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
                    # Single file
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

    async def _download_from_volume(self, volume_name, item):
        """Download a specific file from a Docker volume."""
        from flask import send_file

        if not volume_name or not item:
            return {"success": False, "error": "Volume name and item required"}

        stdout, stderr, rc = await _run_docker(
            "volume", "inspect", volume_name,
            "--format", "{{.Mountpoint}}"
        )
        if rc != 0:
            return {"success": False, "error": f"Volume not found: {volume_name}"}

        mountpoint = stdout.strip()
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

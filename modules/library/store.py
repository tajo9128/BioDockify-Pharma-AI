import os
import json
import shutil
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger("biodockify_library")

class LibraryStore:
    """
    Manages the physical storage of files and their metadata.
    Data is stored in 'library_data/' relative to the app root.
    Metadata is persisted in 'library_data/index.json'.
    """
    def __init__(self, base_path: str = "library_data"):
        self.base_path = Path(base_path)
        self.files_dir = self.base_path / "files"
        self.index_path = self.base_path / "index.json"
        
        self._initialize_storage()

    def _initialize_storage(self):
        """Creates necessary directories and files."""
        self.files_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._save_index({})

    def _load_index(self) -> Dict:
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load library index: {e}")
            return {}

    def _save_index(self, data: Dict):
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_file(self, file_path_or_content, original_filename: str, meta: Dict = None) -> Dict:
        """
        Saves a file to the library and returns its record.
        Accepts bytes (content) or a Path (to copy).
        """
        file_id = str(uuid.uuid4())
        ext = Path(original_filename).suffix.lower()
        stored_filename = f"{file_id}{ext}"
        target_path = self.files_dir / stored_filename
        
        # Write File
        if isinstance(file_path_or_content, bytes):
            with open(target_path, "wb") as f:
                f.write(file_path_or_content)
        elif isinstance(file_path_or_content, (str, Path)):
             shutil.copy2(file_path_or_content, target_path)
        
        # Create Metadata Record
        record = {
            "id": file_id,
            "filename": original_filename,
            "stored_filename": stored_filename,
            "size_bytes": target_path.stat().st_size,
            "added_at": datetime.now().isoformat(),
            "processed": False,
            "metadata": meta or {}
        }
        
        # Update Index
        index = self._load_index()
        index[file_id] = record
        self._save_index(index)
        
        return record

    def list_files(self) -> List[Dict]:
        index = self._load_index()
        # Return list sorted by date desc
        return sorted(index.values(), key=lambda x: x['added_at'], reverse=True)

    def get_file_record(self, file_id: str) -> Optional[Dict]:
        index = self._load_index()
        return index.get(file_id)

    def get_file_path(self, file_id: str) -> Optional[Path]:
        record = self.get_file_record(file_id)
        if record:
            return self.files_dir / record['stored_filename']
        return None

    def remove_file(self, file_id: str) -> bool:
        index = self._load_index()
        if file_id in index:
            record = index[file_id]
            target_path = self.files_dir / record['stored_filename']
            try:
                if target_path.exists():
                    os.remove(target_path)
                del index[file_id]
                self._save_index(index)
                return True
            except Exception as e:
                logger.error(f"Error removing file {file_id}: {e}")
                return False
        return False

    def update_metadata(self, file_id: str, updates: Dict):
        index = self._load_index()
        if file_id in index:
            index[file_id].update(updates)
            self._save_index(index)

# Singleton
library_store = LibraryStore()

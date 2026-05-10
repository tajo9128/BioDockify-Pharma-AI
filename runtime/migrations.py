"""
Database Migration Manager
Handles schema versioning and automatic upgrades for SQLite databases.
"""

import logging
import sqlite3
from typing import List, Callable, Dict

logger = logging.getLogger("migration_manager")

class Migration:
    def __init__(self, version: int, description: str, up_func: Callable[[sqlite3.Connection], None]):
        self.version = version
        self.description = description
        self.up_func = up_func

class MigrationManager:
    """Manages database schema migrations for SQLite."""
    
    def __init__(self, db_path: str, migrations: List[Migration]):
        self.db_path = db_path
        self.migrations = sorted(migrations, key=lambda m: m.version)
        self._ensure_migration_table()

    def _ensure_migration_table(self):
        """Create the schema_version table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def get_current_version(self) -> int:
        """Get the latest applied migration version."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def run_migrations(self):
        """Run all pending migrations."""
        current_version = self.get_current_version()
        logger.info(f"Current database version: {current_version}")
        
        conn = sqlite3.connect(self.db_path)
        try:
            for migration in self.migrations:
                if migration.version > current_version:
                    logger.info(f"Applying migration v{migration.version}: {migration.description}")
                    migration.up_func(conn)
                    conn.execute(
                        "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                        (migration.version, migration.description)
                    )
                    conn.commit()
                    logger.info(f"Successfully applied v{migration.version}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Migration failed at v{migration.version}: {e}")
            raise
        finally:
            conn.close()

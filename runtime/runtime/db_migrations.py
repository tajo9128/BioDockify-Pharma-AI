
import sqlite3
import logging
from runtime.migrations import Migration, MigrationManager

logger = logging.getLogger("db_migrations")

def migration_v1_init(conn: sqlite3.Connection):
    """Initial schema for Task Store."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT,
            status TEXT,
            progress INTEGER,
            logs TEXT,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Add indices if needed
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")

def get_all_migrations() -> list[Migration]:
    return [
        Migration(1, "Initial Task Store Schema", migration_v1_init),
    ]

def run_database_migrations(db_path: str):
    """Run all defined migrations against the target database."""
    logger.info(f"Checking migrations for {db_path}...")
    migrations = get_all_migrations()
    manager = MigrationManager(db_path, migrations)
    manager.run_migrations()

"""
Audit Logger Module
Tracks user actions for security and compliance.
"""

import os
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def get_audit_db_path() -> Path:
    """Get the path to the audit database."""
    app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
    audit_dir = Path(app_data) / 'BioDockify' / 'logs'
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir / 'audit.db'


class AuditLogger:
    """
    Logs user actions to a local SQLite database for security auditing.
    
    Tracks:
    - Login attempts (success/failure)
    - Research operations (search, export, backup)
    - File access events
    - Settings changes
    """
    
    # Action categories
    AUTH = 'auth'
    RESEARCH = 'research'
    FILE = 'file'
    SETTINGS = 'settings'
    SYSTEM = 'system'
    
    def __init__(self):
        self.db_path = get_audit_db_path()
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database with audit table."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    action TEXT NOT NULL,
                    user_email TEXT,
                    details TEXT,
                    ip_address TEXT,
                    success INTEGER DEFAULT 1
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_category ON audit_log(category)
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Audit database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize audit database: {e}")
    
    def log(self, category: str, action: str, details: Optional[Dict[str, Any]] = None,
            user_email: Optional[str] = None, success: bool = True):
        """
        Log an audit event.
        
        Args:
            category: Event category (auth, research, file, settings, system)
            action: Specific action (login, search, export, etc.)
            details: Optional dictionary of additional details
            user_email: User's email if known
            success: Whether the action succeeded
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO audit_log (timestamp, category, action, user_email, details, success)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                category,
                action,
                user_email,
                json.dumps(details) if details else None,
                1 if success else 0
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def log_login(self, email: str, success: bool, reason: Optional[str] = None):
        """Log a login attempt."""
        self.log(
            category=self.AUTH,
            action='login',
            user_email=email,
            details={'reason': reason} if reason else None,
            success=success
        )
    
    def log_research(self, action: str, query: Optional[str] = None, 
                     result_count: Optional[int] = None, user_email: Optional[str] = None):
        """Log a research action (search, export, etc.)."""
        self.log(
            category=self.RESEARCH,
            action=action,
            user_email=user_email,
            details={
                'query': query[:100] if query else None,  # Truncate long queries
                'result_count': result_count
            }
        )
    
    def log_file_access(self, action: str, file_path: str, user_email: Optional[str] = None):
        """Log a file access event."""
        self.log(
            category=self.FILE,
            action=action,
            user_email=user_email,
            details={'file': Path(file_path).name}  # Only log filename, not full path
        )
    
    def log_settings_change(self, setting: str, user_email: Optional[str] = None):
        """Log a settings change."""
        self.log(
            category=self.SETTINGS,
            action='change',
            user_email=user_email,
            details={'setting': setting}
        )
    
    def get_recent_events(self, limit: int = 100, category: Optional[str] = None) -> List[Dict]:
        """Get recent audit events."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT timestamp, category, action, user_email, details, success
                    FROM audit_log
                    WHERE category = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (category, limit))
            else:
                cursor.execute('''
                    SELECT timestamp, category, action, user_email, details, success
                    FROM audit_log
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'timestamp': row[0],
                    'category': row[1],
                    'action': row[2],
                    'user_email': row[3],
                    'details': json.loads(row[4]) if row[4] else None,
                    'success': bool(row[5])
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get audit events: {e}")
            return []
    
    def get_login_attempts(self, email: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get login attempts, optionally filtered by email."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if email:
                cursor.execute('''
                    SELECT timestamp, user_email, success, details
                    FROM audit_log
                    WHERE category = 'auth' AND action = 'login' AND user_email = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (email, limit))
            else:
                cursor.execute('''
                    SELECT timestamp, user_email, success, details
                    FROM audit_log
                    WHERE category = 'auth' AND action = 'login'
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'timestamp': row[0],
                    'email': row[1],
                    'success': bool(row[2]),
                    'details': json.loads(row[3]) if row[3] else None
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get login attempts: {e}")
            return []


# Singleton instance
audit_logger = AuditLogger()

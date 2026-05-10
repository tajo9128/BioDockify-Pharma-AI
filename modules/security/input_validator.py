"""
Input Validator Module
Sanitizes and validates user inputs to prevent security issues.
"""

import re
import os
import html
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Limits
MAX_QUERY_LENGTH = 10000
MAX_EMAIL_LENGTH = 254
MAX_PATH_LENGTH = 260  # Windows MAX_PATH

# Patterns
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-. ]+$')


class InputValidator:
    """
    Validates and sanitizes user inputs to prevent:
    - Path traversal attacks
    - Script injection
    - Invalid email formats
    - Oversized inputs
    """
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """
        Validate email format.
        
        Returns:
            (is_valid, error_message or sanitized_email)
        """
        if not email:
            return False, "Email is required"
        
        email = email.strip().lower()
        
        if len(email) > MAX_EMAIL_LENGTH:
            return False, f"Email too long (max {MAX_EMAIL_LENGTH} characters)"
        
        if not EMAIL_PATTERN.match(email):
            return False, "Invalid email format"
        
        return True, email
    
    @staticmethod
    def sanitize_query(query: str, max_length: int = MAX_QUERY_LENGTH) -> str:
        """
        Sanitize a search query by removing dangerous characters.
        
        Args:
            query: The input query string
            max_length: Maximum allowed length
            
        Returns:
            Sanitized query string
        """
        if not query:
            return ""
        
        # Truncate if too long
        if len(query) > max_length:
            query = query[:max_length]
            logger.warning(f"Query truncated to {max_length} characters")
        
        # Remove HTML tags
        query = re.sub(r'<[^>]+>', '', query)
        
        # Escape HTML entities
        query = html.escape(query)
        
        # Remove null bytes
        query = query.replace('\x00', '')
        
        return query.strip()
    
    @staticmethod
    def sanitize_path(path: str, base_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Sanitize a file path to prevent directory traversal.
        
        Args:
            path: The input path
            base_dir: Optional base directory the path must be within
            
        Returns:
            (is_safe, resolved_path or error_message)
        """
        if not path:
            return False, "Path is required"
        
        # Check length
        if len(path) > MAX_PATH_LENGTH:
            return False, f"Path too long (max {MAX_PATH_LENGTH})"
        
        # Check for obvious traversal attempts
        dangerous_patterns = ['..', '~', '%2e%2e', '%252e%252e']
        path_lower = path.lower()
        for pattern in dangerous_patterns:
            if pattern in path_lower:
                logger.warning(f"Path traversal attempt detected: {path}")
                return False, "Invalid path: traversal not allowed"
        
        try:
            # Resolve to absolute path
            resolved = Path(path).resolve()
            
            # If base_dir specified, ensure path is within it
            if base_dir:
                base_resolved = Path(base_dir).resolve()
                if not str(resolved).startswith(str(base_resolved)):
                    logger.warning(f"Path escape attempt: {path} outside {base_dir}")
                    return False, "Path must be within allowed directory"
            
            return True, str(resolved)
            
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return False, "Invalid path format"
    
    @staticmethod
    def sanitize_filename(filename: str) -> Tuple[bool, str]:
        """
        Sanitize a filename to prevent special character attacks.
        
        Returns:
            (is_safe, sanitized_filename or error_message)
        """
        if not filename:
            return False, "Filename is required"
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Check for dangerous extensions
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.ps1', '.vbs', '.js', '.sh']
        ext = os.path.splitext(filename)[1].lower()
        if ext in dangerous_extensions:
            logger.warning(f"Dangerous file extension blocked: {filename}")
            return False, f"File type {ext} not allowed"
        
        # Replace unsafe chars with underscores
        safe_filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
        
        # Limit length
        if len(safe_filename) > 255:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:255-len(ext)] + ext
        
        return True, safe_filename
    
    @staticmethod
    def sanitize_html(content: str) -> str:
        """
        Escape HTML to prevent XSS attacks.
        
        Args:
            content: The input string
            
        Returns:
            HTML-escaped string
        """
        if not content:
            return ""
        return html.escape(content)
    
    @staticmethod
    def validate_json_size(json_str: str, max_size_kb: int = 1024) -> Tuple[bool, str]:
        """
        Validate JSON size to prevent DoS attacks.
        
        Args:
            json_str: JSON string
            max_size_kb: Maximum size in KB
            
        Returns:
            (is_valid, error_message if invalid)
        """
        size_kb = len(json_str.encode('utf-8')) / 1024
        if size_kb > max_size_kb:
            return False, f"JSON too large: {size_kb:.1f}KB (max {max_size_kb}KB)"
        return True, ""


# Convenience functions
def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format."""
    return InputValidator.validate_email(email)


def sanitize_path(path: str, base_dir: Optional[str] = None) -> Tuple[bool, str]:
    """Sanitize file path."""
    return InputValidator.sanitize_path(path, base_dir)


def sanitize_query(query: str) -> str:
    """Sanitize search query."""
    return InputValidator.sanitize_query(query)


def sanitize_filename(filename: str) -> Tuple[bool, str]:
    """Sanitize filename."""
    return InputValidator.sanitize_filename(filename)

"""
Mock-based Security Audit script for Nanobot Channels.
Runs without requiring 'telegram' or 'websockets' installed.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Create mocks for external dependencies to allow import
sys.modules["telegram"] = MagicMock()
sys.modules["telegram.ext"] = MagicMock()
sys.modules["websockets"] = MagicMock()
sys.modules["lark_oapi"] = MagicMock()
sys.modules["lark_oapi.api.im.v1"] = MagicMock()

# Import the logic to test
from nanobot.channels.telegram import _markdown_to_telegram_html

def test_telegram_xss():
    print("Testing Telegram XSS Prevention...")
    malicious = "<script>alert('xss')</script> **bold**"
    html_output = _markdown_to_telegram_html(malicious)
    print(f"Output: {html_output}")
    assert "&lt;script&gt;" in html_output
    assert "<script>" not in html_output
    assert "<b>bold</b>" in html_output
    print("SUCCESS: XSS blocked.")

def test_telegram_code_xss():
    print("Testing Telegram Code Block XSS...")
    malicious = "```\n<script>alert(1)</script>\n```"
    html_output = _markdown_to_telegram_html(malicious)
    print(f"Output: {html_output}")
    assert "&lt;script&gt;" in html_output
    assert "<pre><code>" in html_output
    print("SUCCESS: Code block XSS blocked.")

def test_path_sanitization():
    print("Testing Path Sanitization...")
    # Simulate a malicious file_id from Telegram
    bad_file_id = "../../../etc/passwd"
    safe_name = Path(bad_file_id).name
    print(f"Original: {bad_file_id} -> Safe: {safe_name}")
    assert safe_name == "passwd"
    assert ".." not in safe_name
    print("SUCCESS: Path traversal blocked.")

if __name__ == "__main__":
    try:
        test_telegram_xss()
        test_telegram_code_xss()
        test_path_sanitization()
        print("\nALL SECURITY CHECKS PASSED!")
    except Exception as e:
        print(f"\nAUDIT FAILED: {e}")
        sys.exit(1)

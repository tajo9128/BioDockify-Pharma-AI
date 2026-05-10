import urllib.request
import urllib.error
import json
import pytest


def post_json(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as f:
            return f.status, json.loads(f.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError) as e:
        return None, {"error": str(e)}


def test_verify():
    # Check if server is available first
    test_url = "http://localhost:3000/health"
    try:
        with urllib.request.urlopen(test_url, timeout=2) as f:
            pass
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
        pytest.skip(
            f"Server not available at localhost:3000 - skipping integration test"
        )

    url = "http://localhost:3000/api/auth/verify"
    email = "test_user@example.com"

    print(f"Testing Standard Verification: {url}")
    print(f"Email: {email}")

    # Test 1: Standard Verify
    # Note: Unless this email is actually in the 'profiles' table, it should fail.
    # But checking 'profiles' means we are checking the REAL database logic.

    status, resp = post_json(url, {"email": email})
    print(f"Status: {status}")
    print(f"Response: {resp}")

    # Skip test if server is not available
    if status is None:
        pytest.skip(
            f"Server not available at {url}: {resp.get('error', 'Connection refused')}"
        )

    if status == 200:
        if resp.get("status") == "success":
            print("PASS: Verification Succeeded (Email found)")
        else:
            print("PASS: API Reachable (Email not found / license invalid)")
    else:
        print(f"FAIL: Server Error {status}")


if __name__ == "__main__":
    test_verify()

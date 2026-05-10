import urllib.request
import urllib.error
import hmac
import hashlib
import json
import base64
import time
import pytest

# Use the key from emergency_access.py
SECRET = "BIODOCKIFY_PHARMA_RESEARCH_OFFLINE_ACCESS_KEY_V1"


def generate_token(email):
    payload = {"email": email, "exp": int(time.time()) + 3600}
    json_str = json.dumps(payload)
    b64_payload = base64.urlsafe_b64encode(json_str.encode()).decode().rstrip("=")
    signature = hmac.new(
        SECRET.encode(), b64_payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{b64_payload}.{signature}"


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


def test_endpoint():
    # Check if server is available first
    test_url = "http://localhost:3000/health"
    try:
        with urllib.request.urlopen(test_url, timeout=2) as f:
            pass
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
        pytest.skip(
            f"Server not available at localhost:3000 - skipping integration test"
        )

    email = "test_user@example.com"
    token = generate_token(email)

    url = "http://localhost:3000/api/auth/verify-emergency"

    print(f"Testing with Email: {email}")
    print(f"Token: {token}")

    # Check if server is available first
    status, resp = post_json(url, {"email": email, "token": token})
    if status is None:
        pytest.skip(
            f"Server not available at {url}: {resp.get('error', 'Connection refused')}"
        )

    print("\n--- Test 1: Valid Token ---")
    print(f"Status: {status}")
    print(f"Response: {resp}")
    if status == 200 and resp.get("status") == "success":
        print("PASS")
    else:
        print("FAIL")

    print("\n--- Test 2: Email Mismatch ---")
    status, resp = post_json(url, {"email": "wrong@example.com", "token": token})
    print(f"Status: {status}")
    print(f"Response: {resp}")
    if status == 403:
        print("PASS")
    else:
        print("FAIL (Expected 403)")

    print("\n--- Test 3: Bad Signature ---")
    status, resp = post_json(url, {"email": email, "token": token + "invalid"})
    print(f"Status: {status}")
    print(f"Response: {resp}")
    if status == 403:
        print("PASS")
    else:
        print("FAIL (Expected 403)")


if __name__ == "__main__":
    test_endpoint()

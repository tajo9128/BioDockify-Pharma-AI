from nacl import public
import base64
import requests
import sys

token = sys.argv[1]
docker_password = sys.argv[2]
repo = "tajo9128/BioDockify-Pharma-AI"
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

r = requests.get(f"https://api.github.com/repos/{repo}/actions/secrets/public-key", headers=headers)
pk = r.json()
key_id = pk["key_id"]
pub_key = public.PublicKey(base64.b64decode(pk["key"]))

def add_secret(name, value):
    sealed = public.SealedBox(pub_key).encrypt(value.encode())
    enc = base64.b64encode(sealed).decode()
    body = {"encrypted_value": enc, "key_id": key_id}
    r = requests.put(f"https://api.github.com/repos/{repo}/actions/secrets/{name}", headers=headers, json=body)
    print(f"{name}: {r.status_code} {r.text}")

add_secret("DOCKER_USERNAME", "tajo9128")
add_secret("DOCKER_PASSWORD", docker_password)

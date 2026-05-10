import subprocess
import sys
import os

def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def main():
    image_name = "tajo9128/biodockify-ai:latest"
    print(f"--- BioDockify Docker Diagnostic ---")
    print(f"Target Image: {image_name}\n")

    # 1. Check if Docker is running
    print("[1] Checking Docker Status...")
    code, out, err = run_command("docker info")
    if code != 0:
        print("[X] Docker is not running or not accessible.")
        print(f"Error: {err.strip()}")
        return
    print("[OK] Docker is running.\n")

    # 2. Check current Docker user
    print("[2] Checking Docker Authentication...")
    code, out, err = run_command("docker system info --format '{{.Name}}'")
    if code == 0:
        print(f"Current Node: {out.strip()}")
    
    # 3. Attempt to inspect the image on the registry (if possible)
    print("\n[3] Testing Registry Access...")
    # This might fail with 401 if it's private, which is what we're testing
    code, out, err = run_command(f"docker manifest inspect {image_name}")
    if code == 0:
        print(f"[OK] Image found and accessible on registry!")
    else:
        print(f"[X] Registry access failed (HTTP {code}).")
        if "401" in err or "unauthorized" in err.lower():
            print("[!] AUTHENTICATION ERROR (401): The repository is private or credentials are invalid.")
        elif "404" in err or "not found" in err.lower():
            print("[!] NOT FOUND (404): The image or tag does not exist.")
        else:
            print(f"Error Message: {err.strip()}")

    print("\n--- Recommendations ---")
    print("1. If 401: Go to hub.docker.com and ensure 'tajo9128/biodockify-ai' is PUBLIC.")
    print("2. Run 'docker logout' and try pulling again to verify public access.")
    print("3. Check your .github/workflows/docker-release.yml secrets if the push is failing.")

if __name__ == "__main__":
    main()

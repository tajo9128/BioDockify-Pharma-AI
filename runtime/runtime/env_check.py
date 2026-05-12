import sys
import shutil
import socket
import requests

def check_command(cmd):
    """Check if a command exists in PATH."""
    return shutil.which(cmd) is not None

def check_port(host, port):
    """Check if a port is open."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0

def main():
    print("="*40)
    print("BioDockify Environment Check")
    print("="*40)
    
    # 1. System Tools
    tools = {
        "Python": "python",
        "Pip": "pip",
        "Docker": "docker",
        "Node.js": "node",
        "NPM": "npm"
    }
    
    print("\n[Tool Availability]")
    for name, cmd in tools.items():
        status = "✓ Found" if check_command(cmd) else "X Missing"
        print(f"{name:<10}: {status}")

    # 2. Services
    services = {
        "Ollama (11434)": ("localhost", 11434),
        "Backend (8000)": ("localhost", 8000)
    }
    
    print("\n[Service Connectivity]")
    for name, (host, port) in services.items():
        is_open = check_port(host, port)
        status = "✓ Online" if is_open else "- Offline"
        print(f"{name:<15}: {status}")

    # 3. Model Check (Ollama)
    print("\n[AI Models]")
    if check_port("localhost", 11434):
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m['name'] for m in resp.json().get('models', [])]
                print(f"Ollama Models: {', '.join(models)}")
            else:
                print("Ollama API Error")
        except:
            print("Could not query Ollama")
    else:
        print("Ollama not running")

if __name__ == "__main__":
    main()

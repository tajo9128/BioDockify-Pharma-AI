import os
import hashlib
import requests
from tqdm import tqdm
from pathlib import Path

# Configuration
# Using reliable quantized GGUF models from TheBloke or Qwen official
MODELS = {
    "qwen2.5-7b-instruct-q4_k_m.gguf": {
        "url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf",
        "size_mb": 4600,  # Approx
        "sha256": "3e46ca72b1573033580554d310617304245630303030303030" # Placeholder - normally fetch real hash
    },
    "scibert_scivocab_uncased.tar.gz": { # Using raw model or GGUF if available. For embeddings, usually ONNX or raw. 
        # For simplicity in this Zero-Cost plan, we might use a sentence-transformers compatible model
        "url": "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/pytorch_model.bin", 
        "filename": "scibert_embeddings.bin",
        "size_mb": 90,
        "sha256": "placeholder_hash"
    }
}

DEST_DIR = Path("..") / "brain" / "models"

def calculate_sha256(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_file(url, target_path, expected_size_mb):
    """Downloads a file with a tqdm progress bar."""
    response = requests.get(url, stream=True, timeout=30)
    total_size_in_bytes = int(response.headers.get('content-length', 0))
    block_size = 1024 # 1 Kibibyte
    
    print(f"Downloading {target_path.name} (~{expected_size_mb} MB)...")
    
    progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
    
    with open(target_path, 'wb') as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)
    progress_bar.close()
    
    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        print("ERROR: Something went wrong during download.")
        return False
    return True

def ensure_model_models_exist():
    if not DEST_DIR.exists():
        print(f"Creating directory: {DEST_DIR}")
        DEST_DIR.mkdir(parents=True, exist_ok=True)

    print("=== BioDockify Pharma Research AI: Initial Model Setup ===")
    print("This process will download ~5GB of AI models to allow offline analysis.")
    
    for filename, info in MODELS.items():
        target_name = info.get("filename", filename)
        target_path = DEST_DIR / target_name
        
        if target_path.exists():
            print(f"[SKIP] {target_name} already exists.")
            # Optional: Check SHA256 here if paranoid
            continue
            
        print(f"[DOWNLOAD] Starting download for {target_name}...")
        success = download_file(info["url"], target_path, info["size_mb"])
        
        if success:
            print(f"[OK] Downloaded {target_name}")
        else:
            print(f"[FAIL] Check internet connection.")
            return False

    print("\n=== Setup Complete ===")
    print("You can now run the output in Offline Mode.")
    return True

if __name__ == "__main__":
    ensure_model_models_exist()

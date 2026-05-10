"""
Backup Encryption Module
Optional encryption for cloud backups using cryptography library.
"""

import os
import base64
import logging

logger = logging.getLogger(__name__)

# Make cryptography optional
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    Fernet = None
    logger.warning("cryptography package not installed. Encrypted backups disabled.")


class BackupCrypto:
    def __init__(self, password: str = None, key_path: str = "backup_key.key"):
        """
        Initialize crypto with a password or load/generate a key file.
        If cryptography is not installed, encryption is disabled.
        """
        if not CRYPTO_AVAILABLE:
            self.cipher = None
            self.key = None
            logger.warning("BackupCrypto initialized without encryption (cryptography not installed)")
            return
            
        self.key = self._load_or_generate_key(password, key_path)
        self.cipher = Fernet(self.key)

    def _load_or_generate_key(self, password: str, key_path: str) -> bytes:
        if not CRYPTO_AVAILABLE:
            return None
            
        if password:
            # Derive key from password
            salt = b'biodockify_salt_static' # In prod, store random salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            return base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(key)
            return key

    def encrypt_file(self, file_path: str, output_path: str):
        """Encrypts a file and saves it to output_path."""
        if not self.cipher:
            # No encryption - just copy
            import shutil
            shutil.copy(file_path, output_path)
            return
            
        with open(file_path, 'rb') as f:
            data = f.read()
        encrypted = self.cipher.encrypt(data)
        with open(output_path, 'wb') as f:
            f.write(encrypted)

    def decrypt_file(self, file_path: str, output_path: str):
        """Decrypts a file and saves it to output_path."""
        if not self.cipher:
            # No encryption - just copy
            import shutil
            shutil.copy(file_path, output_path)
            return
            
        with open(file_path, 'rb') as f:
            data = f.read()
        decrypted = self.cipher.decrypt(data)
        with open(output_path, 'wb') as f:
            f.write(decrypted)


def is_crypto_available() -> bool:
    """Check if encryption is available."""
    return CRYPTO_AVAILABLE

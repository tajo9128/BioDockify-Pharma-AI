"""
Dependency Manager - Auto-install missing Python packages

This module provides safe, controlled automatic installation of missing
dependencies when detected during research task execution.

Security: Only packages in the WHITELIST can be auto-installed.
"""

import subprocess
import sys
import importlib
import logging
from typing import Optional, List, Set

logger = logging.getLogger(__name__)

# Whitelist of packages that can be auto-installed
# These are research-related packages that are safe to install
SAFE_PACKAGES: Set[str] = {
    # Scientific Computing
    "numpy", "scipy", "pandas", "statsmodels",
    
    # Chemistry & Biology
    "rdkit", "biopython", "pubchempy", "chembl_webresource_client",
    
    # NLP & Text Processing
    "nltk", "spacy", "transformers", "sentence-transformers",
    
    # Literature Search
    "arxiv", "semanticscholar", "habanero", "crossrefapi",
    
    # PDF & Document Processing
    "pypdf", "pdfminer.six", "pdf2image", "pymupdf",
    
    # Web & API
    "requests", "httpx", "aiohttp", "beautifulsoup4",
    
    # Data Visualization
    "matplotlib", "seaborn", "plotly",
    
    # Machine Learning (lightweight)
    "scikit-learn", "faiss-cpu",
    
    # Utilities
    "tqdm", "pyyaml", "python-dotenv"
}

# Map common import names to pip package names
IMPORT_TO_PACKAGE: dict = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "yaml": "pyyaml",
    "Bio": "biopython",
    "rdkit": "rdkit",
    "faiss": "faiss-cpu",
}


class DependencyManager:
    """
    Manages automatic installation of missing dependencies.
    
    Features:
    - Detects missing modules from import errors
    - Only installs whitelisted packages for security
    - Logs all installation attempts
    - Supports async operation
    """
    
    def __init__(self, whitelist: Optional[Set[str]] = None):
        """
        Initialize the dependency manager.
        
        Args:
            whitelist: Custom whitelist of allowed packages.
                       Defaults to SAFE_PACKAGES if not provided.
        """
        self.whitelist = whitelist or SAFE_PACKAGES
        self.installed: List[str] = []
        self.failed: List[str] = []
        
    def is_available(self, module_name: str) -> bool:
        """
        Check if a module is available for import.
        
        Args:
            module_name: The module name (e.g., 'numpy', 'Bio')
            
        Returns:
            True if module can be imported
        """
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False
            
    def get_package_name(self, module_name: str) -> str:
        """
        Convert module name to pip package name.
        
        Args:
            module_name: The import module name
            
        Returns:
            The pip package name
        """
        return IMPORT_TO_PACKAGE.get(module_name, module_name)
        
    def is_whitelisted(self, package_name: str) -> bool:
        """
        Check if a package is in the whitelist.
        
        Args:
            package_name: The pip package name
            
        Returns:
            True if package is allowed to be installed
        """
        return package_name.lower() in {p.lower() for p in self.whitelist}
        
    def install(self, package_name: str, upgrade: bool = False, max_retries: int = 2) -> bool:
        """
        Install a package using pip with error recovery.
        
        Error Recovery Heuristics:
        1. Retry with exponential backoff
        2. Try alternative package names
        3. Fallback to conda for scientific packages
        
        Args:
            package_name: The pip package name
            upgrade: Whether to upgrade if already installed
            max_retries: Maximum retry attempts
            
        Returns:
            True if installation succeeded
        """
        if not self.is_whitelisted(package_name):
            logger.warning(f"Package '{package_name}' not in whitelist. Skipping.")
            return False
        
        # Error recovery: Alternative package names
        alternatives = self._get_alternative_packages(package_name)
        packages_to_try = [package_name] + alternatives
        
        for pkg in packages_to_try:
            for attempt in range(max_retries + 1):
                if self._try_pip_install(pkg, upgrade, attempt):
                    self.installed.append(package_name)
                    return True
                    
                # Exponential backoff between retries
                if attempt < max_retries:
                    import time
                    wait_time = 2 ** attempt  # 1s, 2s, 4s...
                    logger.info(f"Retry {attempt + 1}/{max_retries} for {pkg} in {wait_time}s...")
                    time.sleep(wait_time)
        
        # Final fallback: Try conda for scientific packages
        if package_name in {"rdkit", "scipy", "scikit-learn", "numpy", "pandas", "faiss-cpu"}:
            logger.info(f"Attempting conda fallback for {package_name}...")
            if self._try_conda_install(package_name):
                self.installed.append(package_name)
                return True
        
        self.failed.append(package_name)
        return False
    
    def _try_pip_install(self, package_name: str, upgrade: bool, attempt: int) -> bool:
        """Single pip install attempt with error parsing."""
        cmd = [sys.executable, "-m", "pip", "install", "--quiet"]
        if upgrade:
            cmd.append("--upgrade")
        
        # Add version constraint for known compatibility issues
        version_constraint = self._get_version_constraint(package_name)
        cmd.append(f"{package_name}{version_constraint}")
        
        logger.info(f"Installing: {' '.join(cmd[-1:])}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully installed: {package_name}")
                return True
            else:
                error_msg = result.stderr.lower()
                
                # Check for specific errors and provide guidance
                if "no matching distribution" in error_msg:
                    logger.warning(f"No matching distribution for {package_name} - trying alternatives")
                elif "permission denied" in error_msg:
                    logger.error(f"Permission denied - try running with --user flag")
                elif "externally-managed-environment" in error_msg:
                    logger.warning(f"Externally managed environment - use venv or conda")
                else:
                    logger.error(f"Install failed: {result.stderr[:200]}")
                    
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Installation timed out (attempt {attempt + 1})")
            return False
        except Exception as e:
            logger.error(f"Installation error: {e}")
            return False
    
    def _try_conda_install(self, package_name: str) -> bool:
        """Fallback to conda for scientific packages."""
        try:
            # Check if conda is available
            result = subprocess.run(
                ["conda", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.warning("Conda not available for fallback")
                return False
            
            # Try conda install
            cmd = ["conda", "install", "-y", "-q", package_name]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # Conda can be slow
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully installed {package_name} via conda")
                return True
                
            return False
            
        except Exception as e:
            logger.warning(f"Conda fallback failed: {e}")
            return False
    
    def _get_alternative_packages(self, package_name: str) -> List[str]:
        """Get alternative package names for common packages."""
        alternatives_map = {
            "scikit-learn": ["sklearn"],
            "opencv-python": ["opencv-python-headless", "opencv-contrib-python"],
            "pillow": ["PIL", "pillow-simd"],
            "faiss-cpu": ["faiss-gpu"],
            "tensorflow": ["tensorflow-cpu", "tensorflow-gpu"],
            "torch": ["pytorch"],
            "beautifulsoup4": ["bs4"],
        }
        return alternatives_map.get(package_name.lower(), [])
    
    def _get_version_constraint(self, package_name: str) -> str:
        """Get version constraints for known compatibility issues."""
        # Known version constraints for Python 3.12+
        constraints = {
            "numpy": "<2.0",  # numpy 2.0 has breaking changes
            "scipy": ">=1.11.0",
            "scikit-learn": ">=1.3.0",
        }
        return constraints.get(package_name.lower(), "")
            
    def install_if_missing(self, module_name: str) -> bool:
        """
        Install a module if it's not available.
        
        Args:
            module_name: The module to check and install
            
        Returns:
            True if module is available (was already installed or just installed)
        """
        if self.is_available(module_name):
            return True
            
        package_name = self.get_package_name(module_name)
        
        if not self.is_whitelisted(package_name):
            logger.warning(
                f"Module '{module_name}' (package: {package_name}) "
                f"is not in the whitelist and will not be auto-installed."
            )
            return False
            
        logger.info(f"Module '{module_name}' not found. Attempting to install '{package_name}'...")
        
        success = self.install(package_name)
        
        if success:
            # Verify the module can now be imported
            try:
                importlib.invalidate_caches()
                importlib.import_module(module_name)
                return True
            except ImportError:
                logger.warning(f"Package installed but module still not importable: {module_name}")
                return False
                
        return False
        
    def extract_module_from_error(self, error: Exception) -> Optional[str]:
        """
        Extract the missing module name from a ModuleNotFoundError.
        
        Args:
            error: The exception (typically ModuleNotFoundError)
            
        Returns:
            The module name, or None if not extractable
        """
        if isinstance(error, ModuleNotFoundError):
            # Error message format: "No module named 'xyz'"
            msg = str(error)
            if "No module named" in msg:
                # Extract module name from quotes
                parts = msg.split("'")
                if len(parts) >= 2:
                    return parts[1].split(".")[0]  # Get root module
        return None
        
    def get_installation_report(self) -> dict:
        """
        Get a report of all installation attempts.
        
        Returns:
            Dict with installed and failed packages
        """
        return {
            "installed": self.installed.copy(),
            "failed": self.failed.copy(),
            "total_installed": len(self.installed),
            "total_failed": len(self.failed)
        }


# Global instance for convenience
_manager: Optional[DependencyManager] = None


def get_manager() -> DependencyManager:
    """Get the global dependency manager instance."""
    global _manager
    if _manager is None:
        _manager = DependencyManager()
    return _manager


def auto_install(module_name: str) -> bool:
    """
    Convenience function to auto-install a missing module.
    
    Args:
        module_name: The module to install if missing
        
    Returns:
        True if module is available after this call
    """
    return get_manager().install_if_missing(module_name)

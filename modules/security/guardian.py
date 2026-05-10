"""
Guardian - Security Hardening Module
BioDockify Pharma Research AI

Provides automated security checks:
1. Static Code Analysis (Bandit)
2. Dependency Vulnerability Scanning (Safety)
3. Secret Detection (Regex)
"""

import os
import re
import logging
import subprocess
import json
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("BioDockify.Guardian")

class Guardian:
    """
    Central security controller for the application.
    """
    
    # Common patterns for API keys and secrets
    SECRET_PATTERNS = {
        "AWS Access Key": r"AKIA[0-9A-Z]{16}",
        "Generic Private Key": r"-----BEGIN PRIVATE KEY-----",
        "Slack Token": r"xox[baprs]-([0-9a-zA-Z]{10,48})?",
        "Google API Key": r"AIza[0-9A-Za-z\\-_]{35}",
        "Generic Secret": r"(?i)(api_key|secret|token|password)[\s]*=[\s]*['\"][a-zA-Z0-9_\-]{16,}['\"]"
    }

    def __init__(self):
        pass

    def scan_code(self, target_path: str = ".") -> Dict[str, Any]:
        """
        Run Bandit static analysis on the target path.
        Returns a summary dictionary.
        """
        logger.info(f"Starting Bandit scan on {target_path}...")
        
        # We use subprocess to run bandit JSON output
        try:
            # -r: recursive, -f json: format json
            cmd = ["bandit", "-r", target_path, "-f", "json", "-q"]
            
            # Bandit returns exit code 1 if issues found, so we suppress check=True errors 
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            if not result.stdout.strip():
                return {"status": "error", "message": "No output from Bandit"}

            try:
                data = json.loads(result.stdout)
                stats = data.get("metrics", {}).get("_totals", {})
                issues = data.get("results", [])
                
                summary = {
                    "total_issues": len(issues),
                    "high_severity": sum(1 for i in issues if i['issue_severity'] == 'HIGH'),
                    "medium_severity": sum(1 for i in issues if i['issue_severity'] == 'MEDIUM'),
                    "stats": stats,
                    "issues": issues[:5] # Return top 5 for brevity in summary
                }
                logger.info(f"Bandit scan complete. Found {len(issues)} issues.")
                return summary

            except json.JSONDecodeError:
                return {"status": "error", "message": "Failed to parse Bandit JSON output"}

        except FileNotFoundError:
            return {"status": "error", "message": "Bandit not installed or not in PATH"}

    def scan_dependencies(self) -> Dict[str, Any]:
        """
        Run pip-audit check on installed dependencies.
        """
        logger.info("Starting pip-audit dependency scan...")
        
        try:
            # pip-audit -f json
            cmd = ["pip-audit", "-f", "json"]
            
            # pip-audit returns non-zero exit code if vulnerabilities found
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if not result.stdout.strip():
                 return {"status": "error", "message": "No output from pip-audit"}

            try:
                data = json.loads(result.stdout)
                
                # pip-audit json format:
                # { "dependencies": [...], "vulnerabilities": [...] } or list of vulns?
                # Actually commonly it is list of dependencies with 'vulns' key.
                # Let's check structure. Usually it's a list or dict with 'dependencies'.
                
                # Check for direct 'vulnerabilities' key or iterate
                vulnerable_count = 0
                vuln_details = []
                
                if isinstance(data, list):
                     # Older format? 
                     pass 
                elif isinstance(data, dict):
                    # "dependencies": [ { "name": "x", "vulns": [...] } ]
                    if "dependencies" in data:
                        for dep in data["dependencies"]:
                            if dep.get("vulns"):
                                vulnerable_count += 1
                                vuln_details.append({
                                    "package": dep["name"],
                                    "version": dep["version"],
                                    "vulns": dep["vulns"]
                                })

                summary = {
                    "vulnerable_packages": vulnerable_count,
                    "details": vuln_details
                }
                logger.info(f"pip-audit scan complete. Found {vulnerable_count} vulnerable packages.")
                return summary

            except json.JSONDecodeError:
                 return {"status": "error", "message": "Failed to parse pip-audit JSON output"}

        except FileNotFoundError:
             return {"status": "error", "message": "pip-audit not installed"}

    def scan_for_secrets(self, content: str) -> List[Dict[str, str]]:
        """
        Scan a text string for potential secrets using regex.
        """
        findings = []
        for name, pattern in self.SECRET_PATTERNS.items():
            matches = re.finditer(pattern, content)
            for m in matches:
                findings.append({
                    "type": name,
                    "match": m.group(0)[:15] + "***" # Mask log output
                })
        
        if findings:
            logger.warning(f"Potential secrets detected: {len(findings)}")
            
        return findings

if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    g = Guardian()
    
    # Create a dummy file with a fake secret to test
    with open("dummy_secret_test.py", "w") as f:
        f.write("api_key = 'AIza12345678901234567890123456789012345'")
    
    print("\n--- Testing Secret Scan ---")
    with open("dummy_secret_test.py", "r") as f:
        print(g.scan_for_secrets(f.read()))
        
    print("\n--- Testing Code Scan (Bandit) ---")
    print(g.scan_code("dummy_secret_test.py"))
    
    # Clean up
    if os.path.exists("dummy_secret_test.py"):
        os.remove("dummy_secret_test.py")

    print("\n--- Testing Dependency Scan (Safety) ---")
    # This might take a moment
    print(g.scan_dependencies())

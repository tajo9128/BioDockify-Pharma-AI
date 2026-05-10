"""
Simple Version Verification Script
Checks if version and title updates were applied correctly
"""

import os
import re

def check_file_version(filepath, pattern):
    """Check if file contains expected version"""
    try:
        if not os.path.exists(filepath):
            print(f"   MISSING FILE: {filepath}")
            return False
            
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            matches = re.findall(pattern, content)
            if matches:
                print(f"   OK: {filepath}")
                # Avoid printing matches that might contain non-encodable characters in some consoles
                return True
            else:
                print(f"   FAILED: {filepath}")
                print(f"      Pattern not found: {pattern}")
                return False
    except Exception as e:
        print(f"   ERROR: {filepath} - {e}")
        return False

def main():
    print("="*60)
    print("BioDockify Version Verification (v2.4.9)")
    print("="*60)
    
    expected_v = "2.4.9"
    expected_v_regex = r'2\.4\.9|v2\.4\.9'
    
    results = []
    
    # 1. version_info.txt
    print("\n[1] Checking version_info.txt...")
    results.append(check_file_version("version_info.txt", expected_v_regex))
    
    # 2. package.json
    print("\n[2] Checking package.json...")
    results.append(check_file_version("package.json", r'"version":\s*"2\.4\.9"'))
    
    # 3. ui/package.json
    print("\n[3] Checking ui/package.json...")
    results.append(check_file_version("ui/package.json", r'"version":\s*"2\.4\.9"'))

    # 4. api/main.py
    print("\n[4] Checking api/main.py...")
    results.append(check_file_version("api/main.py", r'version="2\.4\.9"'))

    # 5. runtime/config_loader.py
    print("\n[5] Checking runtime/config_loader.py...")
    results.append(check_file_version("runtime/config_loader.py", r'"version":\s*"2\.4\.9"'))

    # 6. README.md
    print("\n[6] Checking README.md...")
    results.append(check_file_version("README.md", r'v2\.4\.9|version-2\.4\.9'))

    # 7. INSTALLATION.md
    print("\n[7] Checking INSTALLATION.md...")
    results.append(check_file_version("INSTALLATION.md", expected_v_regex))

    # 8. Dockerfile
    print("\n[8] Checking Dockerfile...")
    results.append(check_file_version("Dockerfile", expected_v_regex))
    
    # 9. NanoBotPanel.tsx
    print("\n[9] Checking ui/src/components/NanoBotPanel.tsx...")
    results.append(check_file_version("ui/src/components/NanoBotPanel.tsx", expected_v_regex))

    # 10. HomeDashboard.tsx
    print("\n[10] Checking ui/src/components/HomeDashboard.tsx...")
    results.append(check_file_version("ui/src/components/HomeDashboard.tsx", expected_v_regex))
    
    # 11. CHANGELOG.md
    print("\n[11] Checking CHANGELOG.md...")
    results.append(check_file_version("CHANGELOG.md", r'\[v2\.4\.9\]'))

    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\nSUCCESS: All version updates verified!")
        return 0
    else:
        print(f"\nFAILED: {total - passed} check(s) failed")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())

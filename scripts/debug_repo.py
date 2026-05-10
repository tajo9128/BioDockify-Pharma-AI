#!/usr/bin/env python3
"""
BioDockify Pharma Research AI - Full Repository Debugger
Checks for syntax errors, import issues, and common problems.
"""

import os
import sys
import ast
import json
from pathlib import Path
from datetime import datetime

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}[PASS] {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}[WARN] {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}[FAIL] {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}[INFO] {text}{Colors.ENDC}")

def check_python_syntax(repo_path='.'):
    """Check all Python files for syntax errors"""
    print_header("CHECKING PYTHON SYNTAX")
    
    repo_path = Path(repo_path).resolve()
    # optimized globbing
    python_files = []
    exclude_dirs = {'.venv', '.venv311', 'node_modules', '_external', 'external_repos', '.git', '__pycache__', 'site-packages'}
    
    for root, dirs, files in os.walk(repo_path):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    print_info(f"Found {len(python_files)} Python files to check")
    
    errors_found = []
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                source = f.read()
            
            if not source.strip():
                continue
            
            ast.parse(source)
            
        except SyntaxError as e:
            rel_path = py_file.relative_to(repo_path)
            error_msg = f"{rel_path}: Line {e.lineno} - {e.msg}"
            errors_found.append((rel_path, e))
            print_error(error_msg)
        except Exception as e:
            rel_path = py_file.relative_to(repo_path)
            error_msg = f"{rel_path}: {str(e)}"
            errors_found.append((rel_path, e))
            print_error(error_msg)
    
    if not errors_found:
        print_success(f"All {len(python_files)} Python files have valid syntax")
        return True
    else:
        print_error(f"Found {len(errors_found)} Python files with syntax errors")
        return False

def check_imports(repo_path='.'):
    """Check key files for import issues"""
    print_header("CHECKING KEY IMPORTS")
    
    repo_path = Path(repo_path).resolve()
    key_files = [
        'api/main.py',
        'server.py',
        'main_research.py',
        'orchestration/planner/orchestrator.py',
        'orchestration/executor.py',
    ]
    
    import_errors = []
    
    for file_path in key_files:
        full_path = repo_path / file_path
        if not full_path.exists():
            print_warning(f"File not found: {file_path}")
            continue
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    imports.append(module)
            
            print_success(f"{file_path}: {len(imports)} imports parsed successfully")
            
        except Exception as e:
            print_error(f"{file_path}: Failed to parse imports - {e}")
            import_errors.append((file_path, e))
    
    if not import_errors:
        print_success("All key files have valid import statements")
        return True
    else:
        print_error(f"Found {len(import_errors)} files with import issues")
        return False

def check_config_files(repo_path='.'):
    """Check configuration files"""
    print_header("CHECKING CONFIGURATION FILES")
    
    repo_path = Path(repo_path).resolve()
    
    config_checks = [
        ('package.json', 'json'),
        ('requirements.txt', 'text'),
        ('Dockerfile', 'text'),
        ('README.md', 'text'),
    ]
    
    issues = []
    
    for config_file, file_type in config_checks:
        full_path = repo_path / config_file
        if not full_path.exists():
            print_warning(f"Config file not found: {config_file}")
            continue
        
        try:
            if file_type == 'json':
                with open(full_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                print_success(f"{config_file}: Valid JSON")
            else:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content.strip():
                    print_success(f"{config_file}: File exists and has content")
                else:
                    print_warning(f"{config_file}: File is empty")
                    
        except json.JSONDecodeError as e:
            print_error(f"{config_file}: Invalid JSON - {e}")
            issues.append((config_file, e))
        except Exception as e:
            print_error(f"{config_file}: {e}")
            issues.append((config_file, e))
    
    if not issues:
        print_success("All configuration files are valid")
        return True
    else:
        return False

def check_common_issues(repo_path='.'):
    """Check for common coding issues"""
    print_header("CHECKING FOR COMMON ISSUES")
    
    repo_path = Path(repo_path).resolve()
    python_files = []
    exclude_dirs = {'.venv', '.venv311', 'node_modules', '_external', 'external_repos', '.git', '__pycache__', 'site-packages'}
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    
    issues = []
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Check for bare except clauses
                if 'except:' in line and 'except Exception' not in line and 'except (' not in line:
                    rel_path = py_file.relative_to(repo_path)
                    issues.append((rel_path, i, "Bare except clause (use 'except Exception:')"))
                
                # Check for TODO/FIXME comments
                if '# TODO' in line or '# FIXME' in line:
                    rel_path = py_file.relative_to(repo_path)
                    issues.append((rel_path, i, f"TODO/FIXME found: {line.strip()}"))
                
                # Check for print statements (should use logging in production)
                if 'print(' in line and not line.strip().startswith('#'):
                    # rel_path = py_file.relative_to(repo_path) 
                    # Just info, not an error - skipping for now to reduce noise
                    pass
                    
        except Exception as e:
            pass
    
    if issues:
        print_warning(f"Found {len(issues)} potential issues:")
        for path, line, issue in issues[:20]:
            print_warning(f"  {path}:{line} - {issue}")
        if len(issues) > 20:
            print_warning(f"  ... and {len(issues) - 20} more")
    else:
        print_success("No common issues found")
    
    return True

def main():
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("="*70)
    print("     BioDockify Pharma Research AI - Repository Debugger")
    print("="*70)
    print(f"{Colors.ENDC}")
    print()
    print_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Repository path: {Path('.').resolve()}")
    print()
    
    # Run all checks
    results = []
    results.append(("Python Syntax", check_python_syntax()))
    results.append(("Python Imports", check_imports()))
    results.append(("Configuration Files", check_config_files()))
    results.append(("Common Issues", check_common_issues()))
    
    # Summary
    print_header("CHECK RESULTS")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.OKGREEN}PASS{Colors.ENDC}" if result else f"{Colors.FAIL}FAIL{Colors.ENDC}"
        print(f"{name:.<50} {status}")
    
    print()
    print(f"{Colors.BOLD}Total: {passed}/{total} checks passed{Colors.ENDC}")
    print()
    
    # Exit code
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fix Python 2 to Python 3 syntax errors in the repository.
Uses lib2to3 and manual fixes for common issues.
"""

import os
import sys
import subprocess
from pathlib import Path
import re  # Added missing import

def fix_file_with_lib2to3(filepath):
    """Try to fix a file using lib2to3"""
    try:
        # 2to3 might not be installed or on path as a module in some environments, 
        # but we'll try standard approach.
        # If '2to3' is an executable, subprocess call might be better, but -m lib2to3 is standard for python libs.
        result = subprocess.run(
            [sys.executable, '-m', 'lib2to3', '-w', '-n', str(filepath)],
            capture_output=True,
            text=True,
            timeout=30
        )
        # lib2to3 returns 0 on success, or non-zero if changes needed (sometimes). 
        # Actually it returns 0 if successful, 1 if error. 
        # Note: lib2to3 might output warnings to stderr.
        return result.returncode == 0
    except Exception as e:
        print(f"  lib2to3 failed for {filepath}: {e}")
        return False

def manual_fix_file(filepath):
    """Manually fix common Python 2 to 3 issues"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        
        # Fix 1: print "msg" -> print("msg")
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            stripped = line.lstrip()
            # Simple heuristic for print statements
            if stripped.startswith('print ') and not stripped.startswith('print(') and not stripped.startswith('print ('):
                indent = len(line) - len(line.lstrip())
                after_print = stripped[6:]  # Get content after "print "
                # Attempt to handle simple cases. Complex cases like 'print >> stderr, ...' might need more care but this is a heuristic.
                line = ' ' * indent + 'print(' + after_print + ')'
            new_lines.append(line)
        content = '\n'.join(new_lines)
        
        # Fix 2: except Exception, e: -> except Exception as e:
        content = re.sub(r'except\s+(\w+),\s*(\w+):', r'except \1 as \2:', content)
        
        # Fix 3: Multiple exception types must be parenthesized
        # except A, B: -> except (A, B):
        # This is tricky without parsing, but we can catch common patterns
        content = re.sub(r'except\s+([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s*:', r'except (\1, \2):', content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"  Manual fix failed for {filepath}: {e}")
        return False

def main():
    repo_path = Path('.')
    
    # Files with known Python 2 syntax errors (from previous scan)
    problematic_files = [
        'agent_zero/skills/deep_drive/clef12/source-retrieval/pan12-source-retrieval-baseline.py',
        'agent_zero/skills/deep_drive/clef12/text-alignment/pan12-text-alignment-baseline.py',
        'agent_zero/skills/deep_drive/clef13/authorship-verification/pan13-authorship-verification-eval.py',
        'agent_zero/skills/deep_drive/clef13/authorship-verification/pan13-authorship-verification-example.py',
        'agent_zero/skills/deep_drive/clef13/text-alignment/pan13-text-alignment-eval.py',
        'agent_zero/skills/deep_drive/clef13/text-alignment/pan13-text-alignment-eval2.py',
        'agent_zero/skills/deep_drive/clef13/text-alignment/pan13-text-alignment-perfmeasures.py',
        'agent_zero/skills/deep_drive/clef14/author-profiling/pan14-author-profiling-eval.py',
        'agent_zero/skills/deep_drive/clef14/author-profiling/pan14-author-profiling-validator.py',
        'agent_zero/skills/deep_drive/clef14/authorship-verification/pan14-authorship-verification-validator.py',
        'agent_zero/skills/deep_drive/clef14/source-retrieval/pan14-source-retrieval-eval.py',
        'agent_zero/skills/deep_drive/clef14/text-alignment/pan14-text-alignment-eval.py',
        'agent_zero/skills/deep_drive/clef14/text-alignment/pan14-text-alignment-validator.py',
        'agent_zero/skills/deep_drive/clef15/text-alignment/pan15_text_alignment_evaluator.py',
        'agent_zero/skills/deep_drive/clef15/text-alignment/pan15_text_alignment_evaluator_case_level.py',
        'agent_zero/skills/deep_drive/clef15/text-alignment/pan15_text_alignment_evaluator_character_level.py',
        'agent_zero/skills/deep_drive/fire13/soco14-update.py',
        'agent_zero/skills/deep_drive/fire14/soco14-update.py',
        'agent_zero/skills/deep_drive/fire15/clsoco15-eval.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/mt-diff/mt-diff.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/agg.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/bleu.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/build_wordnet_files.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/combine_segcor_trainset.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/delete_stray_matches.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/filter_merge_rank_set.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/freq.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/meteorToMosesAlign.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/meteor_shower.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/sgmlize.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/ter.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/wmt_bleu.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/wmt_fmt.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/scripts/wmt_ter.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/xray/Generation.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/xray/MeteorAlignment.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/xray/visualize_alignments.py',
        'agent_zero/skills/deep_drive/semeval23/evaluation/meteor-1.5/xray/xray.py',
        'agent_zero/skills/deep_drive/sepln09/pan09-plagiarism-detection-performance-measures.py',
        # Added based on logs
        'modules/web_research/__init__.py'
    ]
    
    print("=" * 70)
    print("Fixing Python 2 to Python 3 Syntax Errors")
    print("=" * 70)
    print()
    
    fixed_count = 0
    failed_count = 0
    
    for file_path in problematic_files:
        full_path = repo_path / file_path
        if not full_path.exists():
            print(f"[SKIP] File not found: {file_path}")
            continue
        
        print(f"[FIXING] {file_path}")
        
        # Try manual fix first as it handles simple prints well and lib2to3 can be slow/unavailable
        if manual_fix_file(full_path):
            print(f"  [OK] Fixed manually")
            fixed_count += 1
            # Run lib2to3 after for other things? Maybe not needed for simple fixes.
        elif fix_file_with_lib2to3(full_path):
             print(f"  [OK] Fixed with lib2to3")
             fixed_count += 1
        else:
            print(f"  [FAIL] Could not fix (or no changes needed)")
            failed_count += 1
    
    print()
    print("=" * 70)
    print(f"Results: {fixed_count} fixed, {failed_count} failed/skipped")
    print("=" * 70)

if __name__ == "__main__":
    main()

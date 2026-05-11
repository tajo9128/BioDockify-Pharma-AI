#!/bin/bash
# Patch /a0/ → /bio/ paths at startup for full compatibility
echo "Patching /a0/ → /bio/ for full compatibility..."

# Replace /a0/ references in all Python files
find /a0 -type f -name "*.py" 2>/dev/null | while read f; do
    sed -i 's|/a0/|/bio/|g' "$f" 2>/dev/null || true
done

# Replace /a0/ references in all JavaScript files  
find /a0 -type f -name "*.js" 2>/dev/null | while read f; do
    sed -i 's|/a0/|/bio/|g' "$f" 2>/dev/null || true
done

# Replace /a0/ references in all HTML files
find /a0 -type f -name "*.html" 2>/dev/null | while read f; do
    sed -i 's|/a0/|/bio/|g' "$f" 2>/dev/null || true
done

# Rename directories with a0 in name
find /a0 -type d -name "*a0*" 2>/dev/null | while read d; do
    mv "$d" "$(echo $d | sed s/a0/bio/g)" 2>/dev/null || true
done

# Also fix /git/agent-zero/ path
find /git -type d -name "*agent-zero*" 2>/dev/null | while read d; do
    mv "$d" "$(echo $d | sed s/agent-zero/biodockify/g)" 2>/dev/null || true
done

# Run with default branch
echo "Starting BioDockify..."
exec /exe/initialize.sh "main"
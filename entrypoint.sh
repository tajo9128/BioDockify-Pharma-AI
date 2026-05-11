#!/bin/bash
# Patch /a0/ → /bio/ paths at startup
echo "Patching paths /a0/ → /bio/..."
find /a0 -type f -name "*.py" -exec sed -i 's|/a0/|/bio/|g' {} \; 2>/dev/null || true
find /a0 -type d -name "*a0*" -exec sh -c 'mv "$1" "$(echo $1 | sed s/a0/bio/g)"' _ {} \; 2>/dev/null || true

# Run default command
exec /exe/initialize.sh "$@"
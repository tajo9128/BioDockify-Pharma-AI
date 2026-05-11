#!/bin/bash
cd /bio

# Replace /a0/ with /bio/ everywhere
find . -type f -exec sed -i 's|/a0/|/bio/|g' {} \;
find . -type f -exec sed -i 's|/git/agent-zero/|/git/biodockify/|g' {} \;
find . -type f -exec sed -i 's|agent-zero|biodockify|g' {} \;
find . -type f -exec sed -i 's|agent0ai/agent-zero|tajo9128/biodockify|g' {} \;
find . -type f -exec sed -i 's|Agent Zero|BioDockify AI|g' {} \;
find . -type f -exec sed -i 's|agent\.zero|biodockify\.ai|g' {} \;
find . -type f -exec sed -i 's|a0-self-update|bio-self-update|g' {} \;
find . -type f -exec sed -i 's|a0_|bio_|g' {} \;
find . -type f -exec sed -i 's|A0_|BIO_|g' {} \;

echo "Phase 1 complete - paths and names"
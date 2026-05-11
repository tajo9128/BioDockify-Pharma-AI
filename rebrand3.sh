#!/bin/bash
cd /bio

# HTML/CSS specific replacements
find . -type f \( -name "*.html" -o -name "*.css" -o -name "*.js" \) -exec sed -i 's|/a0/|/bio/|g' {} \;
find . -type f \( -name "*.html" -o -name "*.css" -o -name "*.js" \) -exec sed -i 's|Agent Zero|BioDockify AI|g' {} \;
find . -type f \( -name "*.html" -o -name "*.css" -o -name "*.js" \) -exec sed -i 's|a0-|bio-|g' {} \;
find . -type f \( -name "*.html" -o -name "*.css" -o -name "*.js" \) -exec sed -i 's|#a0-|#bio-|g' {} \;

# Knowledge files
find ./knowledge -type f -exec sed -i 's|Agent Zero|BioDockify AI|g' {} \;
find ./knowledge -type f -exec sed -i 's|agent.zero|biodockify.ai|g' {} \;

# Prompts
find ./prompts -type f -exec sed -i 's|Agent Zero|BioDockify AI|g' {} \;

echo "Phase 3 complete - webui and knowledge"
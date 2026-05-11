#!/bin/bash
# Replace all /a0/ with /bio/ in all files
find /bio -type f -exec sed -i 's|/a0/|/bio/|g' {} \;
find /bio -type f -exec sed -i 's|/git/agent-zero/|/git/biodockify/|g' {} \;
find /bio -type f -exec sed -i 's|agent0ai/agent-zero|tajo9128/biodockify|g' {} \;
find /bio -type f -exec sed -i 's|Agent Zero|BioDockify AI|g' {} \;
find /bio -type f -exec sed -i 's|agent.zero|biodockify.ai|g' {} \;
echo "Done"
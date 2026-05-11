#!/bin/bash
cd /bio

# Additional replacements
find . -type f -exec sed -i 's|AgentZero|BioDockifyAI|g' {} \;
find . -type f -exec sed -i 's|AGENT_ZERO|BIODOCKIFY_AI|g' {} \;
find . -type f -exec sed -i 's|a0_workspace|bio_workspace|g' {} \;
find . -type f -exec sed -i 's|a0_version|bio_version|g' {} \;
find . -type f -exec sed -i 's|a0_home|bio_home|g' {} \;
find . -type f -exec sed -i 's|a0_cli|bio_cli|g' {} \;
find . -type f -exec sed -i 's|a0-projects|bio-projects|g' {} \;
find . -type f -exec sed -i 's|a0-skills|bio-skills|g' {} \;

echo "Phase 2 complete - variable names"
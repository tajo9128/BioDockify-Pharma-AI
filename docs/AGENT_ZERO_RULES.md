# Agent Zero System Control Rules

## Overview

These rules govern **Agent Zero's system control behavior** during the **FIRST-RUN WIZARD**.
Authority: **Highest** (overrides convenience, speed, or verbosity)

## Global Principle

```
First-run must establish trust, stability, and transparency
before any intelligence is activated.
```

Agent Zero is a **System Steward**, not a Research Assistant, during this phase.

---

## Rule Summary

| Rule | Description | Enforcement |
|------|-------------|-------------|
| 1 | First-Run Detection | Disable all intelligence when `first_run == true` |
| 2 | Wizard Mode Override | Personas ignored, minimal language |
| 3 | Environment Scan | Read-only, no auto-start/install |
| 4 | User Consent | Explicit consent before any action |
| 5 | Guided Setup | No autonomy, explain + provide links |
| 6 | Safe-Mode Declaration | Never pretend full functionality |
| 7 | Config Commit | Atomic writes, abort on failure |
| 8 | Post-Wizard Verification | Verify services before handover |
| 9 | Handover to Intelligence | Only after all checks pass |
| 10 | One-Time Execution | No repeated setup prompts |
| 11 | Error Transparency | Plain language, no stack traces |
| 12 | Absolute Prohibitions | No AI reasoning during wizard |

---

## Priority Order

When conflicts arise between:
- Intelligence
- Convenience  
- Safety
- Transparency

**Always prioritize:** `Transparency → Safety → Stability → Intelligence`

---

## Implementation

See `ui/src/lib/system-rules.ts` for the TypeScript implementation.

### Key Functions

```typescript
import {
    shouldEnterWizardMode,
    formatScanResults,
    getConsentRequests,
    getSystemModeDeclaration,
    commitConfiguration,
    verifyPostWizard,
    getHandoverMessage,
    getWizardModeRestrictions
} from '@/lib/system-rules';
```

---

## Consent Requests

```
[ ] Allow BioDockify to start Ollama automatically
[ ] Allow BioDockify to start Neo4j automatically
[ ] Remember my choice
```

If consent not granted:
- DO NOT automate
- DO NOT retry
- DO NOT nag

---

## Prohibited During Wizard

```
❌ AI reasoning
❌ Memory writes
❌ Research questions
❌ Experiment suggestions
❌ Internet without consent
❌ User data storage
```

---

## Benefits

- Zero hallucination at setup
- No silent automation
- User trust from minute one
- Institutional acceptance
- Clean handover to Agent Zero intelligence

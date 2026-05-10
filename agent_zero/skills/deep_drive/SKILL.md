---
name: Deep Drive (PAN Code Integration)
description: |
  A shared code repository for the PAN (Digital Text Forensics) research community.
  Includes tools for authorship attribution, profiling, and style analysis.
author: Webis PAN (Integrated by BioDockify)
version: 1.0.0
---

# Deep Drive (PAN Code) Skill

This skill integrates the [PAN Code](https://github.com/pan-webis-de/pan-code) repository, which contains a collection of code used for Digital Text Forensics.

## Capabilities

1.  **Authorship Attribution**: Tools to identify the author of a given text.
2.  **Author Profiling**: Predicting author demographics (age, gender, etc.) from text.
3.  **Style Analysis**: Analyzing writing styles for forensic purposes.

## Usage in Agent Zero

This skill provides a foundation for forensic text analysis within the BioDockify research suite.

```python
# Usage examples pending specific module integration
```

## 🏗️ Structure and Function (Legacy Forensics)

The Deep Drive skill integrates the core documentation and logic from the PAN Code repository. Its primary functional mechanism is the `plagdet_score`, which is structured to evaluate:

1.  **Recall**: Ability to identify all instances of reused text.
2.  **Precision**: Accuracy in distinguishing between original and reused content.
3.  **Granularity**: Measuring if detection occurred at the appropriate hierarchical level.

These functions allow Agent Zero Hybrid to perform complex **Authorship Attribution** and rank detection algorithms with academic rigor.

## Note
This skill is a direct clone of the PAN Code repository. Performance and results depend on the specific forensic models used.

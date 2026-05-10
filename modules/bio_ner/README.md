# Bio-NER Engine

A hybrid Named Entity Recognition engine for extracting Drugs, Diseases, and Genes.

## Features

- **Hybrid Mode**: Automatically detects if a HuggingFace model is available in `brain/models`.
- **Regex Fallback**: Uses robust regex patterns if no AI model is present (Zero-Cost / Offline default).
- **Categories**:
  - **Drugs**: suffixes like -vir, -mab, -ib
  - **Diseases**: -itis, -osis, cancer, etc.
  - **Genes**: Standard gene symbol patterns (e.g., BRCA1)

## Usage

```python
from modules.bio_ner import BioNER

ner = BioNER()
text = "Patient treated with Rituximab."
entities = ner.extract_entities(text)
# {'drugs': ['Rituximab'], ...}
```

There are several ways to install LatteReview:

## 1. Install from PyPI (Recommended)

```bash
pip install lattereview
```

You can also install additional features using these extras:

```bash
# Development tools
pip install "lattereview[dev]"

# Documentation tools
pip install "lattereview[docs]"

# All extras
pip install "lattereview[all]"
```

## 2. Install from Source Code

#### Option A: Using Git

```bash
# Clone the repository
git clone https://github.com/PouriaRouzrokh/LatteReview.git
cd LatteReview
```

#### Option B: Using ZIP Download

1. Go to https://github.com/PouriaRouzrokh/LatteReview
2. Click the green "Code" button
3. Select "Download ZIP"
4. Extract the ZIP file and navigate to the directory:

```bash
cd path/to/LatteReview-main
```

After obtaining the source code through either option, you can install it using one of these methods:

```bash
# Basic installation
pip install .

# Install from specific versions of dependencies mentioned in requirements.txt
pip install -r requirements.txt

# Development installation (all optional dependencies)
pip install -e ".[all]"
```

## Verify Installation

```python
import lattereview
print(lattereview.__version__)
```

## Requirements

- Python 3.9 or later
- Core dependencies (automatically installed):
  - litellm (>=1.55.2)
  - openai (>=1.57.4)
  - pandas (>=2.2.3)
  - pydantic (>=2.10.3)
  - And others as specified in `setup.py`

## Troubleshooting

If you encounter installation issues:

```bash
# Check Python version
python --version  # Should be 3.9 or later

# Update pip
pip install --upgrade pip

# Install build dependencies
pip install build wheel setuptools
```

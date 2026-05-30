# Chapter 13: Benchmark Suite

## 13.1 Overview
System validation suite for verifying all dependencies and performance before large campaigns.

### Access Path
**All Tools → Benchmark**

---

## 13.2 What It Checks

| Check | Description |
|-------|-------------|
| API Health | Response time for all endpoints |
| Storage | Disk space available |
| Memory | RAM utilization |
| RDKit | Molecular descriptor calculation |
| Vina | AutoDock Vina binary |
| GNINA | GNINA CNN binary (Docker only) |
| ChromaDB | Vector store availability |

---

## 13.3 When to Run

- Before large docking campaigns (>100 ligands)
- Before QSAR training on large datasets
- After Docker image updates
- After system configuration changes

---

## 13.4 Interpreting Results

| Status | Meaning |
|--------|---------|
| PASS | Component working correctly |
| WARN | Component degraded but functional |
| FAIL | Component not available |
| SKIP | Component not applicable to current platform |

---

## 13.5 Performance Tips

- **Docking**: Reduce exhaustiveness for faster results (default 8 → 4)
- **QSAR**: Use fewer descriptors for faster training
- **Large libraries**: Process in batches of 100-500 compounds
- **Memory**: Restart container if memory usage >80%

# Chapter 28: Version History & Roadmap

## 28.1 Release History

| Version | Date | Key Features |
|---------|------|--------------|
| v6.8.1 | 2026-05-25 | GNINA conda-forge fix, Meeko PDBQT fallback, ProLIF fingerprints, consensus Z-score |
| v6.8.0 | 2026-05-25 | Module consolidation (29→15), molecule editor 4-tab, docking analysis inline, QSAR v2 |
| v6.7.0 | 2026-05-24 | Pharmacophore overhaul, SwissADME, PDBQT sanitize fix, GNINA health badges |
| v6.6.0 | 2026-05-23 | 18 bug fixes, QSAR batch prediction, read-across, Williams Plot |
| v6.5.0 | 2026-05-22 | Molecular editor 3D viewer, PDB protein upload, distance measurement |
| v6.4.0 | 2026-05-21 | Journal finder deep research, fake website detector, full dossier |
| v6.3.0 | 2026-05-20 | Drug properties v2, hERG, AMES, pKa, BBB, melting point |
| v6.2.0 | 2026-05-19 | QSAR v2, classification models, batch predict, feature selection |
| v6.1.0 | 2026-05-18 | Docking analysis upgrade, 3D viewer, H-bond visualization |
| v6.0.0 | 2026-05-17 | Initial Pharma AI release |

---

## 28.2 Roadmap

### Planned Features

| Feature | Priority | Description |
|---------|----------|-------------|
| MM-GBSA free energy | High | Physics-based binding free energy calculation |
| Protein preparation | High | pH 7.4 protonation, H-bond optimization |
| Binding site detection | High | Auto-detect pockets (P2Rank/fpocket) |
| MD trajectory viewer | Medium | 3Dmol.js native support |
| Covalent docking | Medium | Targeted covalent inhibitors |
| Ultra-large screening | Medium | >1M compound virtual screening |
| Multi-language UI | Low | Chinese, Spanish, French translations |

---

## 28.3 Contributing

### Development Setup
```bash
git clone https://github.com/tajo9128/BioDockify-Pharma-AI.git
cd BioDockify-Pharma-AI
pip install -r requirements.txt
python run_ui.py
```

### Code Style
- Python: PEP 8, type hints
- JavaScript: ES modules, Alpine.js patterns
- HTML: Self-contained components

### Pull Request Process
1. Fork repository
2. Create feature branch
3. Write tests
4. Update documentation
5. Submit PR with description

---

## 28.4 License

BioDockify Pharma AI is licensed under the MIT License.

Built on [Agent Zero](https://github.com/agent0ai/agent-zero) by Jan Tomasek.

---

## 28.5 Citation

```bibtex
@software{biodockify2026,
  title={BioDockify Pharma AI: AI-Powered Pharmaceutical Research Platform},
  author={BioDockify Team},
  year={2026},
  url={https://github.com/tajo9128/BioDockify-Pharma-AI},
  version={6.8.1}
}
```

---

## 28.6 Contact

- **GitHub Issues**: https://github.com/tajo9128/BioDockify-Pharma-AI/issues
- **Documentation**: docs/user-guide/
- **Docker Hub**: hub.docker.com/r/tajo9128/biodockify-pharma-ai

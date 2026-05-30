# Appendix C: Troubleshooting

## Common Issues

### Installation
| Problem | Solution |
|---------|---------|
| Port 50001 already in use | Change port in docker-compose.yml: `"50002:50001"` |
| Docker build fails | Run `docker compose build --no-cache` |
| Image pull fails | Check internet connection, try `docker login` |
| Container won't start | Check logs: `docker compose logs` |

### Molecular Docking
| Problem | Solution |
|---------|---------|
| GNINA shows yellow/warn | Normal on Windows — GNINA requires Docker (Linux) |
| Vina not found | Rebuild image: `docker compose build --no-cache` |
| PDBQT conversion fails | Check PDB format, try different ligand format |
| No poses found | Check protein PDB quality, expand grid box |
| Docking times out | Reduce exhaustiveness or grid size |

### QSAR
| Problem | Solution |
|---------|---------|
| Training fails | Check CSV format — need SMILES + numeric activity columns |
| Invalid SMILES | Verify SMILES syntax, check for special characters |
| Model not found | Check volume mount, model saved in `data/qsar_models/` |
| Feature count mismatch | Re-process dataset after changing descriptor groups |

### Pharmacophore
| Problem | Solution |
|---------|---------|
| No features generated | Check SMILES validity, ensure 3D conformer generation works |
| Empty screening results | Verify library SMILES format (one per line) |
| Protein model fails | Check PDB content format (ATOM/HETATM records) |

### Journal Finder
| Problem | Solution |
|---------|---------|
| No search results | Try broader search terms, remove filters |
| Deep research fails | Check internet connection, PubMed/SCImago APIs may be rate-limited |
| Verify returns no data | Journal may not be in database — try ISSN instead of title |

### 3D Viewer
| Problem | Solution |
|---------|---------|
| 3Dmol.js not loading | Check internet connection (CDN load) |
| Blank 3D view | Check browser console for errors, try refreshing |
| Snapshot fails | Some browsers block canvas export — try different browser |

### Performance
| Problem | Solution |
|---------|---------|
| Slow docking | Reduce exhaustiveness (default 8), smaller grid box |
| High memory usage | Restart container, reduce concurrent jobs |
| QSAR training slow | Use fewer descriptors, reduce dataset size for testing |

## Getting Help

- **GitHub Issues**: https://github.com/tajo9128/BioDockify-Pharma-AI/issues
- **Health Check**: http://localhost:50001/api/health
- **Logs**: `docker compose logs -f --tail=100`

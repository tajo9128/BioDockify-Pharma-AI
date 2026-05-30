# Appendix A: API Reference

## API Architecture
All endpoints accessible at `http://localhost:50001/api/<endpoint>` via POST with JSON body.

## Core Endpoints

| Endpoint | Module | Key Actions |
|----------|--------|-------------|
| `/api/health` | System | Health check (GET/POST) |
| `/api/drug_properties` | Molecule Editor | `analyze` — full property calculation |
| `/api/drug_analysis` | Molecule Editor | `check` — PAINS/Brenk/NIH filters |
| `/api/structure_3d` | Molecule Editor | Generate 3D SDF from SMILES |
| `/api/structure_export` | Molecule Editor | Export PNG/SVG/MOL/SDF |
| `/api/molecular_similarity` | Mol Toolkit | Tanimoto similarity |
| `/api/chemical_space_map` | Mol Toolkit | PCA chemical space |
| `/api/docking_prepare` | Docking | Prepare PDBQT files |
| `/api/docking_run` | Docking | Run Vina + GNINA |
| `/api/docking_analysis` | Docking Analysis | 10 actions: deep_analysis, plif, rmsd_cluster, etc. |
| `/api/docking_download` | Docking | Download result files |
| `/api/docking_gnina` | Docking | GNINA CNN scoring |
| `/api/admet_swiss_endpoint` | ADMET | SwissADME 6-section analysis |
| `/api/qsar` | QSAR | train, predict, predict_batch, read_across, williams_plot, feature_selection |
| `/api/pharmacophore` | Pharmacophore | 13 actions: generate, protein_model, screen, batch_screen, etc. |
| `/api/journal_finder` | Journal Finder | verify, search, suggest, profile, history, check_fake, deep_research |
| `/api/mol_optimizer` | Molecule Editor | mutate — bioisostere replacement |
| `/api/slides/generate` | Slides | Generate slide content |
| `/api/lecture_generate` | Lecture Builder | Generate lecture content |
| `/api/system_health` | System Health | Full system diagnosis |

## Request Format
```json
{
  "action": "analyze",
  "smiles": "CC(=O)Oc1ccccc1C(=O)O"
}
```

## Response Format
```json
{
  "success": true,
  "molecular_weight": 180.16,
  "logp": 1.2,
  ...
}
```

## Error Response
```json
{
  "success": false,
  "error": "Invalid SMILES string"
}
```

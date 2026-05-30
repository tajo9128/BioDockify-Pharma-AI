# Chapter 25: Complete API Endpoint Table

## 25.1 Drug Properties & Analysis

| Endpoint | Action | Input | Output |
|----------|--------|-------|--------|
| `/api/drug_properties` | `analyze` | `{smiles}` | MW, LogP, TPSA, HBA, HBD, Lipinski, hERG, AMES, pKa, BBB, MP, druglikeness score |
| `/api/drug_analysis` | `check` | `{smiles}` | PAINS, Brenk, NIH alerts |

## 25.2 Molecular Structure

| Endpoint | Action | Input | Output |
|----------|--------|-------|--------|
| `/api/structure_3d` | — | `{smiles}` | 3D SDF, atom/bond count |
| `/api/structure_export` | — | `{smiles, format}` | PNG/SVG/MOL/SDF file |
| `/api/molecular_similarity` | — | `{query, reference}` | Tanimoto similarity |
| `/api/chemical_space_map` | — | `{smiles_list}` | PCA coordinates |

## 25.3 Docking

| Endpoint | Action | Input | Output |
|----------|--------|-------|--------|
| `/api/docking_prepare` | — | `{protein, ligand, format}` | PDBQT files, job_id |
| `/api/docking_run` | — | `{job_id, params}` | Poses, energies, consensus |
| `/api/docking_analysis` | `deep_analysis` | `{job_id}` | Interactions, energy, clusters, SVG |
| `/api/docking_analysis` | `plif` | `{job_id, pose_index}` | Interaction fingerprints |
| `/api/docking_analysis` | `rmsd_cluster` | `{job_id}` | RMSD clusters |
| `/api/docking_download` | — | `{job_id, filename}` | File download |

## 25.4 ADMET

| Endpoint | Action | Input | Output |
|----------|--------|-------|--------|
| `/api/admet_swiss_endpoint` | — | `{smiles}` | SwissADME 6-section results |

## 25.5 QSAR

| Endpoint | Action | Input | Output |
|----------|--------|-------|--------|
| `/api/qsar` | `descriptors` | — | Descriptor groups list |
| `/api/qsar` | `process_dataset` | `{content, smiles_col, activity_col}` | X, y, features |
| `/api/qsar` | `train` | `{X, y, features, model_type}` | job_id |
| `/api/qsar` | `predict` | `{model_id, smiles}` | Prediction + AD |
| `/api/qsar` | `predict_batch` | `{model_id, smiles_list}` | Batch predictions |
| `/api/qsar` | `read_across` | `{model_id, smiles}` | Analogues list |
| `/api/qsar` | `williams_plot` | `{model_id}` | SVG plot |
| `/api/qsar` | `feature_selection` | `{X, y, features, k}` | Top features |
| `/api/qsar` | `models` | — | Saved models list |

## 25.6 Pharmacophore

| Endpoint | Action | Input | Output |
|----------|--------|-------|--------|
| `/api/pharmacophore` | `generate` | `{smiles}` | Features list |
| `/api/pharmacophore` | `protein_model` | `{protein_pdb, center, cutoff}` | Protein features |
| `/api/pharmacophore` | `screen` | `{query, library}` | Screened hits |
| `/api/pharmacophore` | `batch_screen` | `{query, library, filters}` | Pre-filtered hits |
| `/api/pharmacophore` | `shared_model` | `{smiles_list}` | Shared features |
| `/api/pharmacophore` | `merged_model` | `{smiles_list}` | Merged features |
| `/api/pharmacophore` | `overlay` | `{smiles_list}` | Pairwise overlap |
| `/api/pharmacophore` | `hypothesis` | `{active_smiles}` | Common features |
| `/api/pharmacophore` | `identify_targets` | `{smiles, conformers}` | Target profile |
| `/api/pharmacophore` | `nci_types` | — | NCI type reference |

## 25.7 Journal Finder

| Endpoint | Action | Input | Output |
|----------|--------|-------|--------|
| `/api/journal_finder` | `verify` | `{title, issn}` | Verdict + indexing |
| `/api/journal_finder` | `search` | `{query, filters}` | Journal list |
| `/api/journal_finder` | `suggest` | `{title, abstract}` | Ranked suggestions |
| `/api/journal_finder` | `profile` | `{issn, title}` | Full dossier |
| `/api/journal_finder` | `check_fake` | `{title, website, issn}` | Fake detection |
| `/api/journal_finder` | `stats` | — | Database counts |

## 25.8 System

| Endpoint | Action | Input | Output |
|----------|--------|-------|--------|
| `/api/health` | — | — | System health status |
| `/api/system_health` | `status` | — | Full system check |
| `/api/system_health` | `diagnose` | — | Detailed diagnosis |

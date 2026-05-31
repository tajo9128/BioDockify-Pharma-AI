### docking_analysis
deep analysis of docking results: 3D view, 2D interaction diagram, residue energy, RMSD clusters, torsion analysis
args:
- `action` (one of: deep_analysis, interaction_svg, rmsd_cluster, torsion, residue_energy, pocket_surface, pose_overlay, binding_site, plif)
- `job_id` (docking job ID from molecular_docking)
- `pose_index` (optional, default 0)
- `smiles` (optional, for 2D diagram generation)
- `rmsd_cutoff` (optional, for clustering, default 2.0)
returns interaction data, clusters, residue energies, 3D overlay PDB
example:
~~~json
{
  "thoughts": ["I need to analyze the docking results in detail."],
  "headline": "Running deep docking analysis",
  "tool_name": "docking_analysis",
  "tool_args": {
    "action": "deep_analysis",
    "job_id": "abc123"
  }
}
~~~

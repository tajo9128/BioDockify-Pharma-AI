### docking_analysis
deep analysis of docking results: 3D view, interactions, clusters, energy
args: `action` (deep_analysis, interaction_svg, rmsd_cluster, torsion, residue_energy, pose_overlay, binding_site, plif), `job_id`
optional: `pose_index`, `smiles`, `rmsd_cutoff`
example:
~~~json
{
  "thoughts": ["I need to analyze the docking results."],
  "headline": "Running deep analysis",
  "tool_name": "docking_analysis",
  "tool_args": {
    "action": "deep_analysis",
    "job_id": "abc123"
  }
}
~~~

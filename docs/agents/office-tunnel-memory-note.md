# Office Tunnel Memory Footprint Note

During the ARM Desktop audit on 2026-05-03, `run_tunnel.py` was the clearest near-future memory optimization candidate. The process held roughly 573 MiB PSS while the main UI process held roughly 706 MiB PSS, even though the tunnel should mostly be a lightweight network edge.

## Observed Shape

- `run_tunnel.py` imports enough of the framework stack to pull in heavy provider and API dependencies.
- The tunnel stays resident for the life of the container, so every eagerly imported module becomes steady-state memory.
- The Desktop/Xpra service itself was not the largest outlier; the always-on tunnel process was.

## Future Work

- Split tunnel startup into a small import surface that only loads routing, auth, and socket plumbing required for health and proxy operation.
- Lazy-import provider/framework modules only when a tunnel request truly needs them.
- Review any `ApiHandler` or helper imports used by the tunnel path and replace broad framework imports with narrower functions.
- Measure with `smem -P run_tunnel.py`, `/proc/<pid>/smaps_rollup`, and before/after cold-start RSS/PSS on ARM64.

## Success Signal

The tunnel process should remain useful as an always-on edge while dropping its idle PSS substantially below the main UI process. A good first target is under 250 MiB PSS on ARM64 without changing tunnel behavior.

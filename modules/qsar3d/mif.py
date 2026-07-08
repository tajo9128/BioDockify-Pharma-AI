"""
Molecular Interaction Fields (MIF) Calculator
Upgraded with Open3DQSAR's MMFF94 buffered 14-7 potential.

Key improvements over previous version:
1. MMFF94 buffered 14-7 potential (not simple LJ 12-6)
2. Hydrogen-bond correction factor
3. Per-atom-type MMFF94 parameters (ALPHA, N, A, G)
4. Quadratic energy cutoff (smooth transition)
5. Distance-dependent dielectric (epsilon = r)
6. Smooth probe averaging (9-point cube)
"""
import numpy as np
import logging
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger("qsar3d.mif")


# ── MMFF94 Force Field Parameters (from Open3DQSAR ff_parm.h) ────────────────

# MMFF94 constants
MMFF94_COUL = 332.0716      # Coulomb constant (kcal·Å/mol·e²)
MMFF94_ELEC_BUFF = 0.05     # Electrostatic buffering constant (Å)
MMFF94_POWER = 0.25         # Exponent for polarizability in R* calculation
MMFF94_B = 0.2              # Buffer parameter for H-bond correction
MMFF94_BETA = 12.0          # Exponent for H-bond correction
MMFF94_DAEPS = 0.5          # Donor-acceptor epsilon scaling

# MMFF94 atom-type parameters: {symbol: (ALPHA, N, A, G, is_donor, is_acceptor)}
# ALPHA = polarizability, N = Slater-Kirkwood effective number
# A = vdW distance parameter, G = vdW well depth parameter
MMFF94_PARAMS = {
    'C_1':  (1.250, 2.44, 2.05, 0.032, False, False),  # sp1 carbon
    'C_2':  (1.250, 2.44, 2.05, 0.032, False, False),  # sp2 carbon
    'C_3':  (1.250, 2.44, 2.05, 0.032, False, False),  # sp3 carbon
    'C_ar': (1.250, 2.44, 2.05, 0.032, False, False),  # aromatic carbon
    'N_1':  (0.900, 2.02, 1.95, 0.037, False, True),   # sp1 nitrogen
    'N_2':  (0.900, 2.02, 1.95, 0.037, True, False),   # sp2 nitrogen (donor)
    'N_3':  (0.900, 2.02, 1.95, 0.037, True, False),   # sp3 nitrogen (donor)
    'N_am': (0.900, 2.02, 1.95, 0.037, True, False),   # amide nitrogen
    'N_ar': (0.900, 2.02, 1.95, 0.037, False, True),   # aromatic nitrogen
    'O_1':  (0.650, 1.76, 1.85, 0.042, False, True),   # sp1 oxygen (acceptor)
    'O_2':  (0.650, 1.76, 1.85, 0.042, False, True),   # sp2 oxygen (acceptor)
    'O_3':  (0.650, 1.76, 1.85, 0.042, True, True),    # sp3 oxygen (donor+acceptor)
    'O_h':  (0.650, 1.76, 1.85, 0.042, True, True),    # hydroxyl oxygen
    'S_2':  (2.300, 3.80, 2.15, 0.030, False, True),   # sp2 sulfur
    'S_3':  (2.300, 3.80, 2.15, 0.030, False, True),   # sp3 sulfur
    'F':    (0.400, 1.36, 1.75, 0.037, False, True),   # fluorine
    'Cl':   (1.200, 2.52, 2.05, 0.032, False, False),  # chlorine
    'Br':   (1.600, 3.10, 2.15, 0.030, False, False),  # bromine
    'I':    (2.000, 3.60, 2.25, 0.028, False, False),  # iodine
    'P':    (1.700, 3.10, 2.15, 0.030, False, False),  # phosphorus
    'H':    (0.250, 0.86, 1.55, 0.044, False, False),  # hydrogen
}

# Simplified element-to-type mapping for RDKit atoms
ELEMENT_TO_MMFF_TYPE = {
    'C': 'C_3', 'N': 'N_3', 'O': 'O_3', 'S': 'S_3',
    'F': 'F', 'Cl': 'Cl', 'Br': 'Br', 'I': 'I',
    'P': 'P', 'H': 'H',
}

# Probe atom: sp3 carbon with +1 charge (standard CoMFA probe)
PROBE_TYPE = 'C_3'
PROBE_CHARGE = 1.0

# Energy cutoff (kcal/mol) — from Open3DQSAR default
ENERGY_CUTOFF = 30.0


class MIFCalculator:
    """
    Calculate Molecular Interaction Fields on a 3D grid.

    Uses MMFF94 buffered 14-7 potential (from Open3DQSAR) instead of
    simple Lennard-Jones 12-6.

    Usage:
        calc = MIFCalculator(grid_spacing=2.0, margin=5.0)
        fields = calc.calculate(mol)
    """

    def __init__(self, grid_spacing: float = 2.0, margin: float = 5.0,
                 energy_cutoff: float = ENERGY_CUTOFF, field_types: List[str] = None,
                 smooth_probe: bool = False):
        self.grid_spacing = grid_spacing
        self.margin = margin
        self.energy_cutoff = energy_cutoff
        self.field_types = field_types or ['steric', 'electrostatic']
        self.smooth_probe = smooth_probe
        self.grid_origin = None
        self.grid_dims = None

        # Pre-compute probe parameters
        self.probe_params = MMFF94_PARAMS.get(PROBE_TYPE, MMFF94_PARAMS['C_3'])

    def _get_atom_mmff_type(self, atom) -> str:
        """Get MMFF94 atom type from RDKit atom."""
        symbol = atom.GetSymbol()
        hyb = atom.GetHybridization()

        if symbol == 'C':
            if hyb.name == 'SP': return 'C_1'
            if hyb.name == 'SP2': return 'C_2'
            return 'C_3'
        elif symbol == 'N':
            if hyb.name == 'SP': return 'N_1'
            if hyb.name == 'SP2':
                # Check if amide
                for bond in atom.GetBonds():
                    if bond.GetBondType().name == 'DOUBLE':
                        return 'N_2'
                return 'N_am'
            return 'N_3'
        elif symbol == 'O':
            if hyb.name == 'SP': return 'O_1'
            if hyb.name == 'SP2': return 'O_2'
            # Check if hydroxyl
            for bond in atom.GetBonds():
                if bond.GetOtherAtom(atom).GetSymbol() == 'H':
                    return 'O_h'
            return 'O_3'
        elif symbol == 'S':
            return 'S_3'
        elif symbol in ('F', 'Cl', 'Br', 'I'):
            return symbol
        elif symbol == 'P':
            return 'P'
        else:
            return 'H'

    def _get_atom_params(self, atom) -> Tuple[float, float, float, float, bool, bool]:
        """Get MMFF94 parameters for an atom."""
        mmff_type = self._get_atom_mmff_type(atom)
        params = MMFF94_PARAMS.get(mmff_type, MMFF94_PARAMS['C_3'])

        # Get Gasteiger charge
        try:
            charge = float(atom.GetDoubleProp('_GasteigerCharge'))
        except Exception:
            charge = 0.0

        return params + (charge,)

    def _determine_grid(self, all_coords: np.ndarray) -> None:
        """Auto-size the grid box to encompass all molecules with margin."""
        mins = all_coords.min(axis=0) - self.margin
        maxs = all_coords.max(axis=0) + self.margin
        dims = np.ceil((maxs - mins) / self.grid_spacing).astype(int) + 1
        self.grid_origin = mins
        self.grid_dims = dims
        logger.debug(f"MIF grid: origin={mins}, dims={dims}, points={dims[0]*dims[1]*dims[2]}")

    def _generate_grid_points(self) -> np.ndarray:
        """Generate 3D grid probe positions."""
        nx, ny, nz = self.grid_dims
        xs = np.arange(nx) * self.grid_spacing + self.grid_origin[0]
        ys = np.arange(ny) * self.grid_spacing + self.grid_origin[1]
        zs = np.arange(nz) * self.grid_spacing + self.grid_origin[2]
        gx, gy, gz = np.meshgrid(xs, ys, zs, indexing='ij')
        return np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=-1)

    def calculate(self, mol) -> Dict[str, np.ndarray]:
        """
        Calculate MIF for a single molecule.
        Returns dict with 'steric' and/or 'electrostatic' arrays.
        """
        from rdkit import Chem

        conf = mol.GetConformer()
        if conf is None:
            raise ValueError("Molecule must have 3D coordinates")

        n_atoms = mol.GetNumAtoms()
        coords = np.array([[conf.GetAtomPosition(i).x,
                            conf.GetAtomPosition(i).y,
                            conf.GetAtomPosition(i).z] for i in range(n_atoms)])

        # Get atom parameters
        atoms = []
        for i in range(n_atoms):
            atom = mol.GetAtomWithIdx(i)
            atoms.append(self._get_atom_params(atom))

        # Determine grid
        if self.grid_origin is None:
            self._determine_grid(coords)

        grid_points = self._generate_grid_points()
        fields = {}

        if 'steric' in self.field_types:
            fields['steric'] = self._calc_steric(grid_points, coords, atoms)

        if 'electrostatic' in self.field_types:
            fields['electrostatic'] = self._calc_electrostatic(grid_points, coords, atoms)

        return fields

    def _calc_steric(self, grid_points: np.ndarray, coords: np.ndarray,
                     atoms: List[Tuple]) -> np.ndarray:
        """
        MMFF94 buffered 14-7 potential for steric field.

        E_vdw(r) = E_ij * (1.07 * R_ij / (r + 0.07 * R_ij))^7 *
                   (1.12 * R_ij^7 / (r^7 + 0.12 * R_ij^7) - 2)

        From Open3DQSAR calc_mm_thread (calc_field.c lines 941-995).
        """
        n_points = len(grid_points)
        result = np.zeros(n_points)

        # Probe parameters
        probe_alpha, probe_n, probe_a, probe_g, probe_donor, probe_acceptor, probe_charge = self.probe_params

        for i, (atom_alpha, atom_n, atom_a, atom_g, atom_donor, atom_acceptor, atom_charge) in enumerate(atoms):
            # R_i = A_i * (ALPHA_i)^0.25
            R_i = atom_a * (atom_alpha ** MMFF94_POWER)
            R_j = probe_a * (probe_alpha ** MMFF94_POWER)

            # gamma_ij = (R_i - R_j) / (R_i + R_j)
            gamma_ij = (R_i - R_j) / (R_i + R_j) if (R_i + R_j) > 0 else 0.0

            # Hydrogen-bond correction factor
            if atom_donor or probe_donor:
                f = 0.0
            else:
                f = MMFF94_B * (1.0 - np.exp(-MMFF94_BETA * gamma_ij ** 2))

            # Effective vdW distance
            R_ij = MMFF94_DAEPS * (R_i + R_j) * (1.0 + f)

            # Effective well depth
            R_ij6 = R_ij ** 6
            numerator = 181.16 * atom_g * probe_g * atom_alpha * probe_alpha
            denominator = (np.sqrt(atom_alpha / atom_n) + np.sqrt(probe_alpha / probe_n)) * R_ij6
            E_ij = numerator / denominator if denominator > 0 else 0.0

            # Pre-compute R_ij^7
            R_ij7 = R_ij ** 7

            # Distance from probe to atom
            diff = grid_points - coords[i]
            r = np.linalg.norm(diff, axis=1)

            # Avoid division by zero (minimum distance 0.5 Å)
            r = np.maximum(r, 0.5)
            r7 = r ** 7

            # MMFF94 buffered 14-7 potential
            term1 = (1.07 * R_ij / (r + 0.07 * R_ij)) ** 7
            term2 = (1.12 * R_ij7 / (r7 + 0.12 * R_ij7)) - 2.0
            energy = E_ij * term1 * term2

            # Smooth probe averaging (9-point cube, from Open3DQSAR)
            if self.smooth_probe:
                shift = self.grid_spacing / 3.0
                avg_energy = energy.copy()
                for dx in [-shift, 0, shift]:
                    for dy in [-shift, 0, shift]:
                        for dz in [-shift, 0, shift]:
                            if dx == 0 and dy == 0 and dz == 0:
                                continue
                            shifted = grid_points + np.array([dx, dy, dz])
                            diff_s = shifted - coords[i]
                            r_s = np.linalg.norm(diff_s, axis=1)
                            r_s = np.maximum(r_s, 0.5)
                            r7_s = r_s ** 7
                            t1 = (1.07 * R_ij / (r_s + 0.07 * R_ij)) ** 7
                            t2 = (1.12 * R_ij7 / (r7_s + 0.12 * R_ij7)) - 2.0
                            avg_energy += E_ij * t1 * t2
                energy = avg_energy / 9.0

            # Quadratic energy cutoff (from Open3DQSAR cutoff.c)
            energy = self._quadratic_cutoff(energy)
            result += energy

        nx, ny, nz = self.grid_dims
        return result.reshape(nx, ny, nz)

    def _calc_electrostatic(self, grid_points: np.ndarray, coords: np.ndarray,
                            atoms: List[Tuple]) -> np.ndarray:
        """
        Coulomb electrostatic field with distance-dependent dielectric.

        E = MMFF94_COUL * q_probe * q_atom / (epsilon * (r + MMFF94_ELEC_BUFF))

        From Open3DQSAR calc_field.c lines 998-1006.
        """
        n_points = len(grid_points)
        result = np.zeros(n_points)

        probe_charge = self.probe_params[6]  # probe charge

        for i, (atom_alpha, atom_n, atom_a, atom_g, atom_donor, atom_acceptor, atom_charge) in enumerate(atoms):
            if abs(atom_charge) < 0.001:
                continue

            diff = grid_points - coords[i]
            r = np.linalg.norm(diff, axis=1)
            r = np.maximum(r, 0.5)

            # Distance-dependent dielectric (epsilon = r, from Open3DQSAR)
            # denominator = epsilon * (r + buffer)
            denominator = r * (r + MMFF94_ELEC_BUFF)

            energy = MMFF94_COUL * probe_charge * atom_charge / denominator

            # Quadratic energy cutoff
            energy = self._quadratic_cutoff(energy)
            result += energy

        nx, ny, nz = self.grid_dims
        return result.reshape(nx, ny, nz)

    def _quadratic_cutoff(self, energy: np.ndarray) -> np.ndarray:
        """
        Quadratic energy cutoff (from Open3DQSAR cutoff.c).
        Smooth transition in [0.8*cutoff, 1.2*cutoff] range.
        """
        j_cutoff = self.energy_cutoff * 0.8
        k_cutoff = self.energy_cutoff * 1.2

        # Clamp positive values
        above_max = energy > k_cutoff
        between = (energy > j_cutoff) & (energy <= k_cutoff)

        # Quadratic transition for values in [j_cutoff, k_cutoff]
        if np.any(between):
            k_range = k_cutoff - j_cutoff
            if k_range > 0:
                energy[between] = 0.5 / k_range * (
                    energy[between] ** 2 - 2 * j_cutoff * energy[between] + k_cutoff ** 2
                )

        energy[above_max] = k_cutoff

        # Same for negative values
        below_min = energy < -k_cutoff
        between_neg = (energy < -j_cutoff) & (energy >= -k_cutoff)

        if np.any(between_neg):
            k_range = k_cutoff - j_cutoff
            if k_range > 0:
                energy[between_neg] = -0.5 / k_range * (
                    energy[between_neg] ** 2 + 2 * j_cutoff * energy[between_neg] + k_cutoff ** 2
                )

        energy[below_min] = -k_cutoff

        return energy

    def set_grid_from_molecules(self, mols: List) -> None:
        """Pre-compute grid box encompassing all molecules."""
        all_coords = []
        for mol in mols:
            conf = mol.GetConformer()
            if conf:
                for i in range(mol.GetNumAtoms()):
                    pos = conf.GetAtomPosition(i)
                    all_coords.append([pos.x, pos.y, pos.z])

        if all_coords:
            self._determine_grid(np.array(all_coords))

    def get_grid_info(self) -> Dict:
        """Return grid dimensions for visualization."""
        if self.grid_origin is None:
            return {}
        return {
            'origin': self.grid_origin.tolist(),
            'dims': self.grid_dims.tolist(),
            'spacing': self.grid_spacing,
            'total_points': int(np.prod(self.grid_dims)),
        }

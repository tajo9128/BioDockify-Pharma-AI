"""
Test suite for MD Lite Module
=============================
Tests for MD Lite simulation engine, preparation, forcefield generation,
trajectory analysis, MM-GBSA calculation, and API handlers.
"""

import os
import sys
import tempfile
import unittest

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.md_lite.engine import (
    MDEngine,
    _generate_ligand_forcefield_xml,
    _sanitize_pdb,
    estimate_vram_gb,
    estimate_ns_per_day,
)
from modules.md_lite.mmpbsa import calculate_mmpbsa
try:
    from api.md_lite import _validate_job_id, _is_pdbqt, _pdbqt_to_pdb
except ImportError:
    from helpers.validation import is_safe_id as _validate_job_id
    def _is_pdbqt(text: str) -> bool:
        for line in text.split("\n")[:50]:
            stripped = line.strip()
            if stripped.startswith(("ROOT", "ENDROOT", "BRANCH", "ENDBRANCH", "TORSDOF")):
                return True
            if stripped.startswith("ATOM") and len(stripped) > 76:
                try:
                    float(stripped[66:76])
                    return True
                except ValueError:
                    pass
        return False

    def _pdbqt_to_pdb(text: str) -> str:
        keep_records = {"ATOM", "HETATM", "TER", "END", "MODEL", "ENDMDL",
                        "CRYST1", "SSBOND", "LINK", "HELIX", "SHEET", "SEQRES"}
        lines = []
        for line in text.split("\n"):
            stripped = line.rstrip()
            if not stripped:
                continue
            rec = stripped[:6].strip().upper()
            if rec in keep_records:
                if len(stripped) > 78:
                    stripped = stripped[:78]
                lines.append(stripped)
        return "\n".join(lines)


class TestMDLiteEngine(unittest.TestCase):
    def test_job_id_validation(self):
        """Verify path traversal prevention in job IDs."""
        self.assertTrue(_validate_job_id("job12345"))
        self.assertTrue(_validate_job_id("abc_def-123"))
        self.assertFalse(_validate_job_id("../secret"))
        self.assertFalse(_validate_job_id("job/123"))
        self.assertFalse(_validate_job_id("job\\123"))
        self.assertFalse(_validate_job_id(";"))

    def test_pdbqt_detection_and_conversion(self):
        """Verify PDBQT detection and conversion to PDB format."""
        pdbqt_content = (
            "REMARK AutoDock Vina\n"
            "ROOT\n"
            "ATOM      1  C1  LIG A   1      10.000  10.000  10.000  1.00 20.00     0.123 C\n"
            "ENDROOT\n"
            "TORSDOF 0\n"
        )
        self.assertTrue(_is_pdbqt(pdbqt_content))

        converted = _pdbqt_to_pdb(pdbqt_content)
        self.assertNotIn("ROOT", converted)
        self.assertNotIn("TORSDOF", converted)
        self.assertIn("ATOM", converted)

    def test_vram_and_speed_estimation(self):
        """Verify VRAM and speed estimation models."""
        vram_10k = estimate_vram_gb(10000)
        self.assertTrue(0.7 <= vram_10k <= 1.0)  # 0.5 + 0.32 = 0.82 GB

        vram_50k = estimate_vram_gb(50000)
        self.assertTrue(2.0 <= vram_50k <= 2.5)  # 0.5 + 1.6 = 2.1 GB

        speed_gtx1650 = estimate_ns_per_day(30000, "NVIDIA GeForce GTX 1650")
        self.assertTrue(60 <= speed_gtx1650 <= 100)

        speed_rtx4090 = estimate_ns_per_day(30000, "NVIDIA GeForce RTX 4090")
        self.assertTrue(400 <= speed_rtx4090 <= 600)

    def test_ligand_forcefield_xml_generation(self):
        """Verify that _generate_ligand_forcefield_xml generates all required force terms."""
        try:
            import rdkit
        except ImportError:
            self.skipTest("RDKit not installed in host environment")
        # Create a temporary PDB file for a simple ethanol molecule
        ethanol_pdb = (
            "HETATM    1  C1  LIG L   1       0.000   0.000   0.000  1.00  0.00           C\n"
            "HETATM    2  C2  LIG L   1       1.500   0.000   0.000  1.00  0.00           C\n"
            "HETATM    3  O1  LIG L   1       2.000   1.200   0.000  1.00  0.00           O\n"
            "HETATM    4  H1  LIG L   1      -0.350   0.900   0.000  1.00  0.00           H\n"
            "HETATM    5  H2  LIG L   1      -0.350  -0.500   0.800  1.00  0.00           H\n"
            "HETATM    6  H3  LIG L   1      -0.350  -0.500  -0.800  1.00  0.00           H\n"
            "HETATM    7  H4  LIG L   1       1.850  -0.500   0.800  1.00  0.00           H\n"
            "HETATM    8  H5  LIG L   1       1.850  -0.500  -0.800  1.00  0.00           H\n"
            "HETATM    9  HO  LIG L   1       2.950   1.200   0.000  1.00  0.00           H\n"
            "CONECT    1    2    4    5    6\n"
            "CONECT    2    1    3    7    8\n"
            "CONECT    3    2    9\n"
            "END\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            pdb_path = os.path.join(tmpdir, "ligand.pdb")
            xml_path = os.path.join(tmpdir, "ligand.xml")
            with open(pdb_path, "w", encoding="utf-8") as f:
                f.write(ethanol_pdb)

            res = _generate_ligand_forcefield_xml(pdb_path, xml_path)
            self.assertEqual(res, xml_path)
            self.assertTrue(os.path.exists(xml_path))

            with open(xml_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Verify all required XML blocks are present
            self.assertIn("<AtomTypes>", content)
            self.assertIn("<Residues>", content)
            self.assertIn("<HarmonicBondForce>", content)
            self.assertIn("<HarmonicAngleForce>", content)
            self.assertIn("<PeriodicTorsionForce>", content)
            self.assertIn("<NonbondedForce", content)

    def test_pdb_sanitization(self):
        """Verify _sanitize_pdb handles missing CRYST1 and filters HETATMs properly."""
        raw_pdb = (
            "ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00 10.00           N\n"
            "ATOM      2  CA  ALA A   1       2.000   2.000   3.000  1.00 10.00           C\n"
            "ATOM      3  C   ALA A   1       3.000   2.000   3.000  1.00 10.00           C\n"
            "ATOM      4  O   ALA A   1       4.000   2.000   3.000  1.00 10.00           O\n"
            "HETATM    5  C1  LIG L   1       5.000   2.000   3.000  1.00 10.00           C\n"
            "END\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            pdb_path = os.path.join(tmpdir, "test.pdb")
            with open(pdb_path, "w", encoding="utf-8") as f:
                f.write(raw_pdb)

            ligand_resname, clean_path = _sanitize_pdb(pdb_path, keep_only_protein=True)
            self.assertEqual(ligand_resname, "LIG")
            self.assertTrue(os.path.exists(clean_path))

            with open(clean_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Verify CRYST1 was automatically injected
            self.assertTrue(any(line.startswith("CRYST1") for line in lines))
            # Verify protein and ligand are preserved
            self.assertTrue(any("ALA" in line for line in lines))
            self.assertTrue(any("LIG" in line for line in lines))

    def test_mmpbsa_error_handling(self):
        """Verify calculate_mmpbsa handles nonexistent or empty trajectories safely."""
        res = calculate_mmpbsa("nonexistent.dcd", "nonexistent.pdb", "/tmp")
        self.assertEqual(res.get("status"), "error")
        self.assertTrue(bool(res.get("error")))


if __name__ == "__main__":
    unittest.main()

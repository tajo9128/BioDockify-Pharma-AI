"""
Test suite for PKPD Analysis Module
====================================

Comprehensive tests for pharmacokinetic/pharmacodynamic analysis.

Author: BioDockify AI
Version: 1.0.0
"""

import numpy as np
import pandas as pd
import sys
import os

# Add project path
sys.path.insert(0, "/a0/usr/projects/biodockify_ai")

from modules.statistics.pkpd_analysis import PKPDAnalysis


def test_basic_functionality():
    """Test basic PKPD analysis functionality."""
    print("\n" + "=" * 60)
    print("TEST 1: Basic PKPD Analysis Functionality")
    print("=" * 60)

    # Create sample PK data (IV bolus)
    time = np.array([0, 0.5, 1, 2, 4, 8, 12, 24])
    concentration = np.array([100, 70, 50, 30, 15, 6, 2.5, 0.5])

    data = pd.DataFrame({"time": time, "concentration": concentration})

    try:
        # Initialize PKPDAnalysis
        pkpd = PKPDAnalysis(data, dose=100, route="IV")
        print("✓ PKPDAnalysis initialized successfully")

        # Test NCA
        nca_result = pkpd.non_compartmental_analysis()
        print("✓ Non-compartmental analysis completed")
        print(f"  - AUC0-inf: {nca_result.parameters['AUC0-inf']:.2f}")
        print(f"  - Cmax: {nca_result.parameters['Cmax']:.2f}")
        print(f"  - t1/2: {nca_result.parameters['t1/2']:.2f}")

        # Test AUC calculation
        auc_result = pkpd.calculate_auc()
        print("✓ AUC calculation completed")
        print(f"  - AUC0-t: {auc_result.parameters['AUC0-t']:.2f}")

        # Test Cmax/Tmax
        ct_result = pkpd.calculate_cmax_tmax()
        print("✓ Cmax/Tmax calculation completed")
        print(f"  - Cmax: {ct_result.parameters['Cmax']:.2f}")
        print(f"  - Tmax: {ct_result.parameters['Tmax']:.2f}")

        # Test half-life
        hl_result = pkpd.estimate_half_life()
        print("✓ Half-life estimation completed")
        print(f"  - t1/2: {hl_result.parameters['t1/2']:.2f}")
        print(f"  - lambda_z: {hl_result.parameters['lambda_z']:.4f}")

        # Test clearance
        cl_result = pkpd.calculate_clearance()
        print("✓ Clearance calculation completed")
        print(f"  - CL: {cl_result.parameters['CL']:.2f}")
        print(f"  - Vd: {cl_result.parameters['Vd']:.2f}")

        # Test comprehensive PK parameters
        pk_result = pkpd.pk_parameter_estimation()
        print("✓ Comprehensive PK parameter estimation completed")
        print(f"  - AUC0-inf: {pk_result.parameters['AUC0-inf']:.2f}")
        print(f"  - Cmax: {pk_result.parameters['Cmax']:.2f}")
        print(f"  - t1/2: {pk_result.parameters['t1/2']:.2f}")
        print(f"  - CL: {pk_result.parameters['CL']:.2f}")
        print(f"  - Vd: {pk_result.parameters['Vd']:.2f}")

        # Test summary statistics
        summary_result = pkpd.pk_summary_statistics()
        print("✓ PK summary statistics generated")

        print("\n" + "=" * 60)
        print("TEST PASSED ✓")
        print("=" * 60)

    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        assert False, f"Basic test failed: {str(e)}"


def test_pd_modeling():
    """Test pharmacodynamic response modeling."""
    print("\n" + "=" * 60)
    print("TEST 2: Pharmacodynamic Response Modeling")
    print("=" * 60)

    # Create sample PK data
    time = np.array([0, 0.5, 1, 2, 4, 8, 12, 24])
    concentration = np.array([0, 5, 10, 20, 15, 8, 3, 1])

    data = pd.DataFrame({"time": time, "concentration": concentration})

    # Create sample effect data (Emax model)
    effect_conc = np.array([0, 1, 10, 100, 1000])
    effect = np.array([0, 10, 50, 80, 90])

    try:
        pkpd = PKPDAnalysis(data, dose=100, route="EV")

        # Test Emax model
        pd_result = pkpd.pd_response_modeling(
            effect_data=effect, concentration_data=effect_conc, model="Emax"
        )
        print("✓ Emax PD model fitted successfully")
        print(f"  - Emax: {pd_result.parameters['Emax']:.2f}%")
        print(f"  - EC50: {pd_result.parameters['EC50']:.2f}")
        print(f"  - R²: {pd_result.parameters.get('R_squared', 0):.3f}")

        # Test sigmoid Emax model
        pd_result_sig = pkpd.pd_response_modeling(
            effect_data=effect, concentration_data=effect_conc, model="Sigmoid_Emax"
        )
        print("✓ Sigmoid Emax PD model fitted successfully")
        print(f"  - Emax: {pd_result_sig.parameters['Emax']:.2f}%")
        print(f"  - EC50: {pd_result_sig.parameters['EC50']:.2f}")
        print(f"  - Hill: {pd_result_sig.parameters['Hill']:.2f}")
        print(f"  - R²: {pd_result_sig.parameters.get('R_squared', 0):.3f}")

        print("\n" + "=" * 60)
        print("PD MODELING TESTS PASSED ✓")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        assert False, f"PD modeling test failed: {str(e)}"


def test_bioavailability():
    """Test bioavailability calculation."""
    print("\n" + "=" * 60)
    print("TEST 3: Bioavailability Calculation")
    print("=" * 60)

    # Reference IV data
    time_iv = np.array([0, 0.5, 1, 2, 4, 8, 12, 24])
    conc_iv = np.array([100, 80, 60, 40, 20, 8, 3, 0.5])

    # Test EV data
    time_ev = np.array([0, 0.5, 1, 2, 4, 8, 12, 24])
    conc_ev = np.array([0, 30, 50, 40, 25, 10, 4, 1])

    reference_data = pd.DataFrame({"time": time_iv, "concentration": conc_iv})

    test_data = pd.DataFrame({"time": time_ev, "concentration": conc_ev})

    try:
        pkpd = PKPDAnalysis(test_data, dose=100, route="EV")

        # Test absolute bioavailability
        f_result = pkpd.bioavailability_calculation(
            reference_data=reference_data, reference_dose=100, reference_route="IV"
        )
        print("✓ Bioavailability calculation completed")
        print(f"  - Absolute F: {f_result.parameters['F_abs']:.1f}%")
        print(f"  - AUC Ratio: {f_result.parameters['Ratio_AUC']:.1f}%")
        print(f"  - Cmax Ratio: {f_result.parameters['Ratio_Cmax']:.1f}%")
        print(f"  - Bioequivalent: {f_result.parameters['Bioequivalent']}")

        print("\n" + "=" * 60)
        print("BIOAVAILABILITY TEST PASSED ✓")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        assert False, f"PD modeling test failed: {str(e)}"


def test_dose_proportionality():
    """Test dose proportionality assessment."""
    print("\n" + "=" * 60)
    print("TEST 4: Dose Proportionality Assessment")
    print("=" * 60)

    # Create dose-dependent data
    dose_levels = [50, 100, 200]
    dose_data = {}

    for dose in dose_levels:
        time = np.array([0, 0.5, 1, 2, 4, 8, 12, 24])
        # Simulate dose-proportional PK
        base_conc = np.array([0, 40, 60, 40, 20, 8, 3, 0.5])
        conc = base_conc * (dose / 100)

        dose_data[dose] = pd.DataFrame({"time": time, "concentration": conc})

    try:
        # Use middle dose as reference
        pkpd = PKPDAnalysis(dose_data[100], dose=100, route="IV")

        # Test dose proportionality
        dp_result = pkpd.dose_proportionality_pk(
            dose_data=dose_data, parameter="AUC0-inf"
        )
        print("✓ Dose proportionality assessment completed")
        print(f"  - Beta (slope): {dp_result.parameters['beta']:.3f}")
        print(
            f"  - 90% CI: [{dp_result.parameters['CI_beta_lower']:.3f}, {dp_result.parameters['CI_beta_upper']:.3f}]"
        )
        print(f"  - R²: {dp_result.parameters['R_squared']:.4f}")
        print(f"  - Proportional: {dp_result.parameters['Proportional']}")

        print("\n" + "=" * 60)
        print("DOSE PROPORTIONALITY TEST PASSED ✓")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        assert False, f"PD modeling test failed: {str(e)}"


def test_interpretations():
    """Test interpretation generation."""
    print("\n" + "=" * 60)
    print("TEST 5: Interpretation Generation")
    print("=" * 60)

    # Create sample data
    time = np.array([0, 0.5, 1, 2, 4, 8, 12, 24])
    concentration = np.array([0, 50, 80, 60, 30, 12, 5, 1])

    data = pd.DataFrame({"time": time, "concentration": concentration})

    try:
        pkpd = PKPDAnalysis(data, dose=100, route="EV")

        # Test NCA interpretation
        nca_result = pkpd.non_compartmental_analysis()
        print("✓ NCA interpretation generated")
        print(f"\n{nca_result.interpretation[:500]}...")

        # Test summary statistics interpretation
        summary_result = pkpd.pk_summary_statistics()
        print("✓ Summary statistics interpretation generated")

        print("\n" + "=" * 60)
        print("INTERPRETATION TEST PASSED ✓")
        print("=" * 60)

    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        assert False, f"Interpretation test failed: {str(e)}"


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PKPD ANALYSIS MODULE TEST SUITE")
    print("=" * 60)

    results = []

    # Run all tests
    results.append(("Basic Functionality", test_basic_functionality()))
    results.append(("PD Modeling", test_pd_modeling()))
    results.append(("Bioavailability", test_bioavailability()))
    results.append(("Dose Proportionality", test_dose_proportionality()))
    results.append(("Interpretations", test_interpretations()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")

    total = len(results)
    passed = sum(1 for _, r in results if r)

    print("\n" + "=" * 60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n✓ ALL TESTS PASSED - PKPD module is fully functional!")
    else:
        print(f"\n✗ {total - passed} test(s) failed")

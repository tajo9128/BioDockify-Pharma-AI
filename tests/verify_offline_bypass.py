
import asyncio
from unittest.mock import MagicMock, patch
from modules.system.connection_doctor import ConnectionDoctor, CheckStatus, CheckResult

async def test_offline_bypass():
    """
    Test that connection doctor allows proceeding even if totally offline.
    """
    doctor = ConnectionDoctor()
    
    # Mock checks to fail
    with patch.object(doctor, 'check_internet') as mock_net, \
         patch.object(doctor, 'check_lm_studio') as mock_lm, \
         patch.object(doctor, 'validate_api_keys') as mock_api, \
         patch.object(doctor, 'check_backend') as mock_backend:
         
        mock_net.return_value = CheckResult("Internet", CheckStatus.ERROR, "Fail")
        mock_lm.return_value = CheckResult("LM Studio", CheckStatus.ERROR, "Fail")
        mock_api.return_value = CheckResult("API", CheckStatus.WARNING, "Warning")
        mock_backend.return_value = CheckResult("Backend", CheckStatus.SUCCESS, "OK")
        
        print("Running diagnosis simulation (All Fail)...")
        report = await doctor.full_diagnosis(auto_repair=False)
        
        print(f"Overall Status: {report.overall_status}")
        print(f"Can Proceed: {report.can_proceed_with_degraded}")
        
        if report.overall_status == "offline" and report.can_proceed_with_degraded:
            print("SUCCESS: System allows proceeding despite offline status.")
        else:
            print("FAILURE: System blocking progress.")

if __name__ == "__main__":
    asyncio.run(test_offline_bypass())

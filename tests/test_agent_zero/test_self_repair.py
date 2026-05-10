import pytest
from agent_zero.skills.self_repair import SelfRepairSkill

@pytest.mark.asyncio
async def test_self_diagnosis():
    """Test Agent Zero self-diagnosis capability."""
    repair_skill = SelfRepairSkill()
    
    # Simulate an error
    error = ValueError("Test error")
    
    # Test self-diagnosis
    diagnosis = await repair_skill.diagnose_error(error)
    
    assert diagnosis is not None
    assert 'error_type' in diagnosis
    assert 'severity' in diagnosis

@pytest.mark.asyncio
async def test_self_repair():
    """Test Agent Zero self-repair capability."""
    repair_skill = SelfRepairSkill()
    
    # Simulate a fixable error
    diagnosis = {
        'error_type': 'syntax_error',
        'severity': 'medium',
        'repairable': True,
        'suggested_fix': 'Fix syntax'
    }
    
    # Test self-repair
    repaired = await repair_skill.attempt_repair(diagnosis)
    
    assert repaired is not None

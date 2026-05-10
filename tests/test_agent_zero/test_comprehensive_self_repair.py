"""
Comprehensive Self-Repair Integration Test for BioDockify AI
Tests all self-diagnosis and self-repair capabilities together.
"""
import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent_zero.skills.self_repair import SelfRepairSkill
from agent_zero.hybrid.diagnosis import SystemDiagnosis


class TestComprehensiveSelfRepair:
    """Test comprehensive self-repair capabilities."""
    
    @pytest.mark.asyncio
    async def test_self_diagnosis_integration(self):
        """Test SystemDiagnosis integration with self-repair."""
        diagnosis = SystemDiagnosis()
        
        # Run health check
        health = await diagnosis.check_health()
        
        assert health is not None
        assert 'disk' in health
        assert 'memory' in health
        assert 'network' in health
        
        # Get diagnosis report
        report = await diagnosis.get_diagnosis_report()
        assert report is not None
        assert 'System Diagnosis Report' in report
        assert 'Memory Usage' in report
        assert 'Disk Usage' in report
    
    @pytest.mark.asyncio
    async def test_self_repair_all_strategies(self):
        """Test self-repair with all error strategies."""
        repair_skill = SelfRepairSkill()
        
        # Test 12 error types
        test_cases = [
            (ImportError("No module named 'test'"), "ImportError", "high"),
            (ModuleNotFoundError("test"), "ModuleNotFoundError", "high"),
            (SyntaxError("invalid"), "SyntaxError", "high"),
            (IndentationError("indent"), "IndentationError", "high"),
            (KeyError("key"), "KeyError", "medium"),
            (AttributeError("attr"), "AttributeError", "medium"),
            (TypeError("type"), "TypeError", "medium"),
            (ValueError("value"), "ValueError", "low"),
            (FileNotFoundError("file.txt"), "FileNotFoundError", "high"),
            (PermissionError("perm"), "PermissionError", "high"),
            (ConnectionError("conn"), "ConnectionError", "high"),
            (TimeoutError("timeout"), "TimeoutError", "high"),
        ]
        
        for error, expected_type, expected_severity in test_cases:
            try:
                raise error
            except Exception as e:
                diagnosis = await repair_skill.diagnose_error(e)
                
                assert diagnosis['error_type'] == expected_type
                assert diagnosis['severity'] == expected_severity
                assert diagnosis['repairable'] is True
                assert diagnosis['repair_strategy'] == expected_type
                assert diagnosis['suggested_fix'] is not None
                
                # Test repair attempt
                result = await repair_skill.attempt_repair(diagnosis)
                assert 'success' in result
                assert 'strategy_used' in result
                assert 'actions_taken' in result
        
        # Check repair history
        history = repair_skill.get_repair_history()
        assert len(history) == len(test_cases)
    
    @pytest.mark.asyncio
    async def test_repairable_import_error(self):
        """Test repair of import errors."""
        repair_skill = SelfRepairSkill()
        
        try:
            raise ImportError("No module named 'nonexistent_module'")
        except Exception as e:
            diagnosis = await repair_skill.diagnose_error(e)
            
            assert 'missing_module' in diagnosis
            assert diagnosis['missing_module'] == 'nonexistent_module'
            assert 'install_command' in diagnosis
            assert 'pip install nonexistent_module' in diagnosis['install_command']
            
            # Attempt repair
            result = await repair_skill.attempt_repair(diagnosis)
            # Repair will fail because module doesn't exist
            assert result['strategy_used'] == 'ImportError'
    
    @pytest.mark.asyncio
    async def test_file_not_found_repair(self):
        """Test repair of file not found errors."""
        repair_skill = SelfRepairSkill(project_root='/tmp/test_self_repair')
        
        try:
            raise FileNotFoundError('/tmp/test_self_repair/deep/nested/file.txt')
        except Exception as e:
            diagnosis = await repair_skill.diagnose_error(e)
            
            assert diagnosis['error_type'] == 'FileNotFoundError'
            assert diagnosis['severity'] == 'high'
            
            # Attempt repair
            result = await repair_skill.attempt_repair(diagnosis)
            
            # Should create parent directory
            assert result['success'] is True or 'Created directory' in str(result.get('actions_taken', []))
    
    def test_repair_strategies_initialized(self):
        """Test all repair strategies are initialized."""
        repair_skill = SelfRepairSkill()
        
        expected_strategies = [
            'ImportError', 'ModuleNotFoundError', 'SyntaxError', 'IndentationError',
            'KeyError', 'AttributeError', 'TypeError', 'ValueError',
            'FileNotFoundError', 'PermissionError', 'ConnectionError', 'TimeoutError', 'RuntimeError'
        ]
        
        for strategy in expected_strategies:
            assert strategy in repair_skill.repair_strategies
    
    def test_repair_history_management(self):
        """Test repair history tracking."""
        repair_skill = SelfRepairSkill()
        
        # Initially empty
        assert len(repair_skill.get_repair_history()) == 0
        
        # Add dummy history
        repair_skill.repair_history.append({"test": "entry"})
        assert len(repair_skill.get_repair_history()) == 1
        
        # Clear history
        repair_skill.clear_repair_history()
        assert len(repair_skill.get_repair_history()) == 0
    
    @pytest.mark.asyncio
    async def test_error_context_handling(self):
        """Test error handling with context information."""
        repair_skill = SelfRepairSkill()
        
        context = {
            'file': 'test.py',
            'line': 42,
            'function': 'test_function',
            'user_input': 'test input'
        }
        
        try:
            raise ValueError("Invalid input")
        except Exception as e:
            diagnosis = await repair_skill.diagnose_error(e, context)
            
            assert diagnosis['affected_file'] == 'test.py'
            assert diagnosis['affected_line'] == 42
            assert diagnosis['context'] == context
            assert 'traceback' in diagnosis


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

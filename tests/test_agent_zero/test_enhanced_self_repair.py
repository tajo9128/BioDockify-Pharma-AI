"""
Comprehensive test for Enhanced Self-Repair System
Tests code awareness, system awareness, and automated repair capabilities.
"""
import pytest
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent_zero.skills.enhanced_self_repair import (
    EnhancedSelfRepairSystem,
    CodeAwarenessEngine,
    SystemAwarenessEngine,
    AutomatedCodeFixer,
    DependencyHealer,
)


class TestCodeAwarenessEngine:
    """Test code awareness and analysis capabilities."""
    
    @pytest.fixture
    def engine(self):
        return CodeAwarenessEngine(Path.cwd())
    
    def test_analyze_file(self, engine):
        """Test comprehensive code file analysis."""
        # Test with a simple Python file
        test_file = Path("test_sample.py")
        try:
            test_file.write_text('''
import os
import sys

def hello_world():
    print("Hello")

class MyClass:
    def method(self):
        pass
''')
            
            analysis = engine.analyze_file(test_file)
            
            assert analysis["file"] == str(test_file)
            assert analysis["functions"] == 1
            assert analysis["classes"] == 1
            assert len(analysis["imports"]) >= 2
            assert "os" in analysis["imports"]
            assert "complexity" in analysis
            assert "type_hints" in analysis
            assert "docstrings" in analysis
            assert analysis["line_count"] > 0
            
        finally:
            test_file.unlink(missing_ok=True)
    
    def test_security_detection(self, engine):
        """Test security issue detection."""
        test_code = '''
import hashlib
hash = hashlib.md5()
eval("dangerous")
exec("unsafe")
'''
        test_file = Path("test_security.py")
        try:
            test_file.write_text(test_code)
            analysis = engine.analyze_file(test_file)
            
            assert "security_issues" in analysis
            assert len(analysis["security_issues"]) >= 1
            assert any("md5" in issue for issue in analysis["security_issues"])
            
        finally:
            test_file.unlink(missing_ok=True)


class TestSystemAwarenessEngine:
    """Test system awareness and monitoring."""
    
    @pytest.fixture
    def engine(self):
        return SystemAwarenessEngine(Path.cwd())
    
    @pytest.mark.asyncio
    async def test_system_health(self, engine):
        """Test comprehensive system health check."""
        health = await engine.check_system_health()
        
        assert health is not None
        assert "cpu_percent" in health
        assert "memory_percent" in health
        assert "disk_percent" in health
        assert "network_io" in health
        assert "process_memory_mb" in health
        assert "python_version" in health
        assert "platform" in health
        
        # Check reasonable ranges
        assert 0 <= health["cpu_percent"] <= 100
        assert 0 <= health["memory_percent"] <= 100
        assert 0 <= health["disk_percent"] <= 100
        
    @pytest.mark.asyncio
    async def test_dependencies_check(self, engine):
        """Test dependency status checking."""
        deps = await engine._check_dependencies()
        
        assert deps is not None
        assert "total_packages" in deps or "error" in deps


class TestAutomatedCodeFixer:
    """Test automated code fixing capabilities."""
    
    @pytest.fixture
    def fixer(self):
        return AutomatedCodeFixer()
    
    def test_fix_syntax(self, fixer):
        """Test syntax error fixing."""
        # Code with style issues
        bad_code = '''
x=1+2
y  =  3
'''
        fixed, changed = fixer.fix_syntax(bad_code)
        
        assert isinstance(fixed, str)
        assert isinstance(changed, bool)
        
    def test_apply_fix(self, fixer):
        """Test applying fixes to files."""
        test_file = Path("test_fix.py")
        try:
            test_file.write_text("x=1+2")
            result = fixer.apply_fix(test_file, "syntax")
            
            assert result["success"] is True
            assert "backup" in result
            
            # Verify backup exists
            backup_file = Path(result["backup"])
            assert backup_file.exists()
            backup_file.unlink(missing_ok=True)
            
        finally:
            test_file.unlink(missing_ok=True)


class TestDependencyHealer:
    """Test dependency healing capabilities."""
    
    @pytest.fixture
    def healer(self):
        return DependencyHealer(Path.cwd())
    
    @pytest.mark.asyncio
    async def test_install_missing_package(self, healer):
        """Test installing a missing package."""
        # Test with a package that likely exists
        result = await healer.install_missing("requests")
        
        assert result is not None
        assert "success" in result
        assert "package" in result


class TestEnhancedSelfRepairSystem:
    """Test comprehensive self-repair system integration."""
    
    @pytest.fixture
    def repair_system(self):
        return EnhancedSelfRepairSystem(Path.cwd())
    
    def test_initialization(self, repair_system):
        """Test system initialization."""
        assert repair_system.project_root is not None
        assert repair_system.code_awareness is not None
        assert repair_system.system_awareness is not None
        assert repair_system.code_fixer is not None
        assert repair_system.dependency_healer is not None
        assert len(repair_system.repair_strategies) >= 15
    
    @pytest.mark.asyncio
    async def test_error_diagnosis(self, repair_system):
        """Test comprehensive error diagnosis."""
        # Test with ImportError
        try:
            raise ImportError("No module named 'nonexistent'")
        except Exception as e:
            diagnosis = await repair_system.diagnose_error(e)
            
            assert diagnosis["error_type"] == "ImportError"
            assert diagnosis["repairable"] is True
            assert diagnosis["repair_strategy"] == "ImportError"
            assert diagnosis["suggested_fix"] is not None
            assert diagnosis["severity"] == "high"
            assert "timestamp" in diagnosis
    
    @pytest.mark.asyncio
    async def test_repair_attempt(self, repair_system):
        """Test repair attempt execution."""
        # Create diagnosis
        diagnosis = {
            "error_type": "ImportError",
            "error_message": "No module named 'test'",
            "repairable": True,
            "context": {},
        }
        
        result = await repair_system.attempt_repair(diagnosis)
        
        assert result is not None
        assert "success" in result
        assert "strategy_used" in result
        assert "actions_taken" in result
    
    @pytest.mark.asyncio
    async def test_full_diagnosis(self, repair_system):
        """Test comprehensive system diagnosis."""
        diagnosis = await repair_system.run_full_diagnosis()
        
        assert "system_health" in diagnosis
        assert "repair_history" in diagnosis
        assert "timestamp" in diagnosis
        
        # Check system health details
        health = diagnosis["system_health"]
        assert "cpu_percent" in health
        assert "memory_percent" in health
    
    @pytest.mark.asyncio
    async def test_multiple_error_types(self, repair_system):
        """Test repair for multiple error types."""
        error_types = [
            ImportError("test"),
            ModuleNotFoundError("test"),
            SyntaxError("invalid"),
            FileNotFoundError("/nonexistent"),
            MemoryError(),
        ]
        
        for error in error_types:
            try:
                raise error
            except Exception as e:
                diagnosis = await repair_system.diagnose_error(e)
                
                assert diagnosis["error_type"] == type(e).__name__
                assert "severity" in diagnosis
                assert "repairable" in diagnosis


class TestCodeAwareness:
    """Test advanced code awareness features."""
    
    @pytest.fixture
    def system(self):
        return EnhancedSelfRepairSystem(Path.cwd())
    
    def test_analyze_project_files(self, system):
        """Test analyzing multiple project files."""
        # Find Python files to analyze
        py_files = list(Path("agent_zero").glob("**/*.py"))[:3]
        
        if py_files:
            for file_path in py_files:
                analysis = system.code_awareness.analyze_file(file_path)
                
                if "error" not in analysis:
                    assert "functions" in analysis
                    assert "classes" in analysis
                    assert "imports" in analysis


class TestIntegration:
    """Test integration with existing Agent Zero system."""
    
    @pytest.mark.asyncio
    async def test_repair_history_tracking(self):
        """Test that repair history is tracked."""
        system = EnhancedSelfRepairSystem(Path.cwd())
        
        # Attempt a repair
        diagnosis = {
            "error_type": "ImportError",
            "error_message": "No module named 'test'",
            "repairable": True,
            "context": {},
        }
        
        await system.attempt_repair(diagnosis)
        
        # Check history
        history = system.get_repair_history()
        
        assert len(history) > 0
        assert "timestamp" in history[-1]
        assert "success" in history[-1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

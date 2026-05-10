"""
Test suite for Self-Consciousness and System Control modules.

Last Updated: 2026-02-14
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime, UTC

from agent_zero.skills.agent_consciousness import (
    SelfConsciousnessEngine,
    ConsciousnessLevel,
    DecisionRecord,
    CapabilityScore,
)
from agent_zero.skills.system_control import (
    SystemController,
    ServiceStatus,
    ServiceInfo,
)


class TestSelfConsciousnessEngine:
    """Test self-consciousness capabilities."""
    
    @pytest.fixture
    def consciousness(self):
        return SelfConsciousnessEngine(Path.cwd())
    
    def test_initialization(self, consciousness):
        """Test consciousness engine initialization."""
        assert consciousness.consciousness_level == ConsciousnessLevel.REFLECTIVE
        assert isinstance(consciousness.decision_history, list)
        assert isinstance(consciousness.patterns, dict)
    
    def test_record_decision(self, consciousness):
        """Test decision recording."""
        record = consciousness.record_decision(
            task_id="test_task_1",
            decision_type="code_repair",
            reasoning="Fixed syntax error using autopep8",
            outcome="Code fixed successfully",
            success=True,
            confidence=0.85,
        )
        
        assert record.task_id == "test_task_1"
        assert record.decision_type == "code_repair"
        assert record.success is True
        assert len(consciousness.decision_history) == 1
    
    def test_assess_capabilities(self, consciousness):
        """Test capability assessment."""
        capabilities = consciousness.assess_capabilities()
        
        assert 'code_repair' in capabilities
        assert 'error_diagnosis' in capabilities
        assert 'system_monitoring' in capabilities
        assert 'decision_making' in capabilities
        assert 'adaptation' in capabilities
        
        for name, cap in capabilities.items():
            assert isinstance(cap, CapabilityScore)
            assert 0.0 <= cap.score <= 1.0
            assert cap.trend in ['improving', 'stable', 'declining']
    
    def test_reflect_on_recent_actions(self, consciousness):
        """Test reflection on recent actions."""
        # Record some decisions
        for i in range(5):
            consciousness.record_decision(
                task_id=f"task_{i}",
                decision_type="code_repair",
                reasoning=f"Fixed error {i}",
                outcome="Success",
                success=True,
                confidence=0.8,
            )
        
        reflection = consciousness.reflect_on_recent_actions()
        
        assert 'actions_analyzed' in reflection
        assert 'success_rate' in reflection
        assert 'recommendations' in reflection
        assert reflection['actions_analyzed'] == 5
    
    def test_get_self_assessment(self, consciousness):
        """Test self-assessment."""
        assessment = consciousness.get_self_assessment()
        
        assert 'consciousness_level' in assessment
        assert 'total_decisions' in assessment
        assert 'capabilities' in assessment
        assert 'patterns_learned' in assessment



class TestSystemController:
    """Test system control capabilities."""
    
    @pytest.fixture
    def controller(self):
        return SystemController(Path.cwd())
    
    def test_initialization(self, controller):
        """Test controller initialization."""
        assert controller.project_root == Path.cwd()
        assert isinstance(controller.managed_processes, dict)
        assert isinstance(controller.docker_available, bool)
        assert isinstance(controller.service_configs, dict)
    
    def test_get_system_resources(self, controller):
        """Test system resource monitoring."""
        resources = controller.get_system_resources()
        
        assert 'cpu' in resources
        assert 'memory' in resources
        assert 'disk' in resources
        assert 'network' in resources
        
        assert 'percent' in resources['cpu']
        assert 'percent' in resources['memory']
        assert 'percent' in resources['disk']
    
    @pytest.mark.asyncio
    async def test_start_stop_process(self, controller):
        """Test process start and stop."""
        # Start a simple process
        result = await controller.start_process(
            name="test_process",
            command=["python3", "-c", "import time; time.sleep(10)"],
        )
        
        assert result['success'] is True
        assert result['status'] == 'started'
        assert 'pid' in result
        
        # Check process status
        status = controller.get_process_status("test_process")
        assert status is not None
        assert status.status == ServiceStatus.RUNNING
        
        # Stop the process
        stop_result = await controller.stop_process("test_process")
        assert stop_result['success'] is True
        
        # Verify stopped
        status = controller.get_process_status("test_process")
        assert status.status == ServiceStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_restart_process(self, controller):
        """Test process restart."""
        # Start process
        await controller.start_process(
            name="restart_test",
            command=["python3", "-c", "import time; time.sleep(10)"],
        )
        
        original_pid = controller.get_process_status("restart_test").pid
        
        # Restart
        result = await controller.restart_process("restart_test")
        assert result['success'] is True
        
        # Verify new PID
        new_pid = controller.get_process_status("restart_test").pid
        assert new_pid != original_pid
    
    def test_list_all_processes(self, controller):
        """Test listing all managed processes."""
        processes = controller.list_all_processes()
        assert isinstance(processes, list)
        for proc in processes:
            assert isinstance(proc, ServiceInfo)


class TestIntegration:
    """Integration tests for self-consciousness and system control."""
    
    @pytest.fixture
    def system(self):
        return {
            'consciousness': SelfConsciousnessEngine(Path.cwd()),
            'controller': SystemController(Path.cwd()),
        }
    
    def test_full_system_assessment(self, system):
        """Test complete system assessment."""
        consciousness = system['consciousness']
        controller = system['controller']
        
        # Get consciousness assessment
        consciousness_assessment = consciousness.get_self_assessment()
        
        # Get system resources
        resources = controller.get_system_resources()
        
        # Verify integration
        assert consciousness_assessment['consciousness_level'] in [
            level.value for level in ConsciousnessLevel
        ]
        assert resources['cpu']['percent'] >= 0
        assert resources['memory']['percent'] >= 0
    
    def test_conscious_resource_monitoring(self, system):
        """Test that consciousness can monitor resources."""
        controller = system['controller']
        
        # Get resources
        resources = controller.get_system_resources()
        
        # Record a decision about resource usage
        consciousness = system['consciousness']
        consciousness.record_decision(
            task_id="resource_check",
            decision_type="resource_monitoring",
            reasoning=f"CPU at {resources['cpu']['percent']}%, Memory at {resources['memory']['percent']}%",
            outcome="System healthy",
            success=True,
            confidence=0.9,
        )
        
        assert len(consciousness.decision_history) == 1

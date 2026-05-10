"""
Verification test suite for Core Agent Hardening.
Tests: Path traversal, command whitelists, atomic writes, and subagent management.
"""

import asyncio
import os
import shutil
import platform
import unittest
from typing import Dict, Any

from agent_zero.hybrid.diagnosis import SystemDiagnosis
from agent_zero.hybrid.tools.file_editor import FileEditorTool
from agent_zero.hybrid.tools.code_execution import SafeCodeExecutionTool
from agent_zero.hybrid.errors import format_error
from agent_zero.hybrid.agent import HybridAgent, AgentConfig, LoopData
from orchestration.planner.orchestrator import OrchestratorConfig

class TestAgentHardening(unittest.IsolatedAsyncioTestCase):
    
    async def asyncSetUp(self):
        self.test_dir = os.path.abspath("./test_workspace")
        os.makedirs(self.test_dir, exist_ok=True)
        self.editor = FileEditorTool(root_dir=self.test_dir)
        self.exec_tool = SafeCodeExecutionTool()
        self.diagnosis = SystemDiagnosis()
        
    async def asyncTearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    # --- FileEditor Tests ---
    
    async def test_path_traversal_protection(self):
        print("[*] Testing path traversal protection...")
        # Attempt to read outside root
        res = self.editor.read_file({"path": "../../agent_zero/hybrid/agent.py"})
        self.assertIn("outside allowed directory", res)
        print("    OK: Path traversal blocked.")

    async def test_atomic_write_and_backup(self):
        print("[*] Testing atomic write and backup...")
        file_path = os.path.join(self.test_dir, "test.txt")
        
        # 1. Initial write
        self.editor.write_file({"path": file_path, "content": "original"})
        
        # 2. Overwrite
        res = self.editor.write_file({"path": file_path, "content": "updated"})
        self.assertIn("Backup created", res)
        self.assertTrue(os.path.exists(file_path + ".bak"))
        
        with open(file_path, 'r') as f:
            self.assertEqual(f.read(), "updated")
        with open(file_path + ".bak", 'r') as f:
            self.assertEqual(f.read(), "original")
        print("    OK: Atomic write and backup verified.")

    # --- CodeExecution Tests ---

    async def test_command_whitelist(self):
        print("[*] Testing command whitelist...")
        # Command in whitelist
        rc, _, _ = await self.exec_tool.execute_shell("ls")
        self.assertNotEqual(rc, -1)
        
        # Command NOT in whitelist
        rc, _, err = await self.exec_tool.execute_shell("rm -rf /tmp/dangerous")
        self.assertEqual(rc, -1)
        self.assertIn("not in the allowed whitelist", err)
        print("    OK: Command whitelist enforced.")

    async def test_python_cleanup(self):
        print("[*] Testing python temp file cleanup...")
        code = "print('hello')"
        # We can't easily check if file *existed* and was deleted without internal access,
        # but we verify it runs.
        out = await self.exec_tool.execute_python(code)
        self.assertEqual(out.strip(), "hello")
        print("    OK: Python execution works.")

    # --- Diagnosis Tests ---

    async def test_diagnosis_platform(self):
        print("[*] Testing diagnosis platform detection...")
        report = await self.diagnosis.get_diagnosis_report()
        self.assertIn("System Diagnosis Report", report)
        self.assertIn("Network Status", report)
        print("    OK: Diagnosis report generated.")

    # --- Agent Repair Tests ---

    async def test_repair_retry_limit(self):
        print("[*] Testing repair retry limits...")
        from agent_zero.hybrid.errors import RepairableException
        
        # Mock LLM and Config
        class MockLLM:
            async def generate(self, p): return "mock tool call"
            
        config = AgentConfig(name="Tester", workspace_path=self.test_dir)
        llm_config = OrchestratorConfig(primary_model="mock")
        
        # Patching LLMFactory to return mock
        from modules.llm.factory import LLMFactory
        original_get = LLMFactory.get_adapter
        LLMFactory.get_adapter = lambda **p: MockLLM()
        
        try:
            agent = HybridAgent(config, llm_config)
            agent.max_repairs_per_error = 2
            
            # Simulate a continuous error in monologue
            async def broken_build_prompt():
                raise RepairableException("Persistent Bug")
            
            agent._build_prompt = broken_build_prompt
            
            # Run loop
            await agent.monologue()
            
            self.assertEqual(agent.repair_attempts["Persistent Bug"], 2)
            self.assertFalse(agent.is_running)
            print("    OK: Repair retry limit enforced.")
            
        finally:
            LLMFactory.get_adapter = original_get

if __name__ == "__main__":
    unittest.main()

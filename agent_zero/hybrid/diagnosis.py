"""
System Diagnosis - Tools for Agent Self-Awareness of Infrastructure.
"""
import logging
import asyncio
import platform
from typing import Dict, Any
from agent_zero.hybrid.tools.code_execution import SafeCodeExecutionTool

logger = logging.getLogger(__name__)

class SystemDiagnosis:
    """
    Provides health checks for the internal agent system.
    """
    
    def __init__(self):
        self.exec_tool = SafeCodeExecutionTool()
        
    async def check_health(self) -> Dict[str, Any]:
        """Run full system health check."""
        results = {}
        system = platform.system()
        
        # 1. Disk Space (Cross-platform)
        if system == "Windows":
            rc, out, err = await self.exec_tool.execute_shell("wmic logicaldisk get size,freespace")
        else:
            rc, out, err = await self.exec_tool.execute_shell("df -h /")
        results["disk"] = out if rc == 0 else f"Error: {err}"
        
        # 2. Memory (Cross-platform)
        if system == "Windows":
            rc, out, err = await self.exec_tool.execute_shell("wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value")
        else:
            rc, out, err = await self.exec_tool.execute_shell("free -m")
        results["memory"] = out if rc == 0 else f"Error: {err}"
        
        # 3. Network (Connectivity - Multi-target)
        endpoints = ["https://www.google.com", "https://api.github.com"]
        online = False
        for url in endpoints:
            rc, _, _ = await self.exec_tool.execute_shell(f"curl -I {url} --max-time 2")
            if rc == 0:
                online = True
                break
        results["network"] = "Online" if online else "Offline/Unreachable"
        
        return results
        
    async def get_diagnosis_report(self) -> str:
        """Format health check as a readable report for the Agent."""
        data = await self.check_health()
        
        report = [
            "# System Diagnosis Report",
            f"**Network Status**: {data.get('network')}",
            "",
            "## Memory Usage",
            f"```\n{data.get('memory')}\n```",
            "",
            "## Disk Usage",
            f"```\n{data.get('disk')}\n```"
        ]
        
        return "\n".join(report)

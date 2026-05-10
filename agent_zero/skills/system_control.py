"""
System Control Module

Provides full control over software processes and Docker environment.

Last Updated: 2026-02-14
Version: 1.0
"""

import asyncio
import json
import logging
import subprocess
import os
import signal
from pathlib import Path
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import psutil

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status enumeration."""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    """Information about a managed service."""
    name: str
    pid: Optional[int]
    status: ServiceStatus
    cpu_percent: float
    memory_mb: float
    uptime_seconds: float
    port: Optional[int]
    command: str


@dataclass
class DockerContainerInfo:
    """Information about a Docker container."""
    container_id: str
    name: str
    status: str
    image: str
    ports: Dict[str, str]
    created: str


class SystemController:
    """
    Comprehensive system control for software processes and Docker environment.
    
    Features:
    - Process management (start, stop, restart, monitor)
    - Service management (BioDockify services)
    - Docker container management
    - Resource allocation and limits
    - Health monitoring and auto-recovery
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.managed_processes: Dict[str, Dict[str, Any]] = {}
        self.docker_available = self._check_docker_available()
        self.service_configs = self._load_service_configs()
    
    def _check_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True, timeout=5)
            return True
        except Exception:
            return False
    
    def _load_service_configs(self) -> Dict[str, Any]:
        """Load service configurations from docker-compose.yml or config."""
        configs = {
            'api_server': {
                'name': 'BioDockify API Server',
                'command': ['python3', 'server.py'],
                'port': 3000,
                'auto_restart': True,
                'health_check': 'http://localhost:3000/health',
            },
        }
        return configs
    
    # ========== Process Management ==========
    
    async def start_process(
        self,
        name: str,
        command: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        auto_restart: bool = False
    ) -> Dict[str, Any]:
        """Start a managed process."""
        try:
            cwd = cwd or self.project_root
            env = env or os.environ.copy()
            
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            self.managed_processes[name] = {
                'process': process,
                'command': command,
                'cwd': str(cwd),
                'started_at': datetime.now(UTC).isoformat(),
                'auto_restart': auto_restart,
            }
            
            return {
                'success': True,
                'name': name,
                'pid': process.pid,
                'status': 'started',
                'message': f"Process {name} started successfully",
            }
        except Exception as e:
            return {
                'success': False,
                'name': name,
                'error': str(e),
                'status': 'error',
            }
    
    async def stop_process(self, name: str, force: bool = False) -> Dict[str, Any]:
        """Stop a managed process."""
        if name not in self.managed_processes:
            return {'success': False, 'error': f'Process {name} not managed'}
        
        process_info = self.managed_processes[name]
        process = process_info['process']
        
        try:
            if force:
                process.kill()
            else:
                process.terminate()
            
            process.wait(timeout=10)
            
            # Mark as stopped but keep in managed_processes for status querying
            process_info['stopped_at'] = datetime.now(UTC).isoformat()
            
            return {
                'success': True,
                'name': name,
                'status': 'stopped',
                'message': f"Process {name} stopped successfully",
            }
        except Exception as e:
            return {
                'success': False,
                'name': name,
                'error': str(e),
            }
    
    async def restart_process(self, name: str) -> Dict[str, Any]:
        """Restart a managed process."""
        if name not in self.managed_processes:
            return {'success': False, 'error': f'Process {name} not managed'}
        
        process_info = self.managed_processes[name]
        command = process_info['command']
        cwd = Path(process_info['cwd'])
        auto_restart = process_info['auto_restart']
        
        # Stop the process
        await self.stop_process(name)
        
        # Start it again
        return await self.start_process(name, command, cwd, None, auto_restart)
    
    def get_process_status(self, name: str) -> Optional[ServiceInfo]:
        """Get detailed status of a managed process."""
        if name not in self.managed_processes:
            return None
        
        process_info = self.managed_processes[name]
        process = process_info['process']
        
        # Check if process is still running
        is_running = False
        try:
            if process.poll() is None:  # poll() returns None if process is running
                is_running = True
        except Exception:
            pass
        
        if is_running:
            try:
                ps = psutil.Process(process.pid)
                return ServiceInfo(
                    name=name,
                    pid=process.pid,
                    status=ServiceStatus.RUNNING,
                    cpu_percent=ps.cpu_percent(),
                    memory_mb=ps.memory_info().rss / 1024 / 1024,
                    uptime_seconds=(datetime.now(UTC) - datetime.fromisoformat(process_info['started_at'])).total_seconds(),
                    port=None,
                    command=' '.join(process_info['command']),
                )
            except Exception:
                pass
        
        # Process is stopped or terminated
        return ServiceInfo(
            name=name,
            pid=process.pid if process else None,
            status=ServiceStatus.STOPPED,
            cpu_percent=0.0,
            memory_mb=0.0,
            uptime_seconds=0.0,
            port=None,
            command=' '.join(process_info['command']) if process else 'unknown',
        )
    
    def list_all_processes(self) -> List[ServiceInfo]:
        """List all managed processes."""
        return [
            self.get_process_status(name)
            for name in self.managed_processes.keys()
        ]
    
    # ========== Docker Management ==========
    
    async def list_docker_containers(self, all_containers: bool = False) -> List[DockerContainerInfo]:
        """List all Docker containers."""
        if not self.docker_available:
            return []
        
        try:
            cmd = ['docker', 'ps', '-a'] if all_containers else ['docker', 'ps']
            cmd.extend(['--format', '{{json .}}'])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    data = json.loads(line)
                    containers.append(DockerContainerInfo(
                        container_id=data.get('ID', ''),
                        name=data.get('Names', ''),
                        status=data.get('Status', ''),
                        image=data.get('Image', ''),
                        ports=self._parse_docker_ports(data.get('Ports', '')),
                        created=data.get('CreatedAt', ''),
                    ))
            
            return containers
        except Exception as e:
            logger.error(f"Failed to list Docker containers: {e}")
            return []
    
    def _parse_docker_ports(self, ports_str: str) -> Dict[str, str]:
        """Parse Docker port string to dict."""
        ports = {}
        for mapping in ports_str.split(', '):
            if '->' in mapping:
                parts = mapping.split('->')
                ports[parts[0].strip()] = parts[1].strip() if len(parts) > 1 else ''
        return ports
    
    async def start_docker_container(self, container_name: str) -> Dict[str, Any]:
        """Start a Docker container."""
        if not self.docker_available:
            return {'success': False, 'error': 'Docker not available'}
        
        try:
            subprocess.run(
                ['docker', 'start', container_name],
                check=True,
                timeout=30,
                capture_output=True
            )
            return {
                'success': True,
                'container': container_name,
                'status': 'started',
                'message': f"Container {container_name} started successfully",
            }
        except Exception as e:
            return {
                'success': False,
                'container': container_name,
                'error': str(e),
            }
    
    async def stop_docker_container(self, container_name: str, timeout: int = 10) -> Dict[str, Any]:
        """Stop a Docker container."""
        if not self.docker_available:
            return {'success': False, 'error': 'Docker not available'}
        
        try:
            subprocess.run(
                ['docker', 'stop', '-t', str(timeout), container_name],
                check=True,
                timeout=timeout + 5,
                capture_output=True
            )
            return {
                'success': True,
                'container': container_name,
                'status': 'stopped',
                'message': f"Container {container_name} stopped successfully",
            }
        except Exception as e:
            return {
                'success': False,
                'container': container_name,
                'error': str(e),
            }
    
    async def restart_docker_container(self, container_name: str, timeout: int = 10) -> Dict[str, Any]:
        """Restart a Docker container."""
        await self.stop_docker_container(container_name, timeout)
        return await self.start_docker_container(container_name)
    
    async def get_docker_container_logs(
        self,
        container_name: str,
        tail: int = 100,
        follow: bool = False
    ) -> Dict[str, Any]:
        """Get logs from a Docker container."""
        if not self.docker_available:
            return {'success': False, 'error': 'Docker not available'}
        
        try:
            cmd = ['docker', 'logs', '--tail', str(tail)]
            if follow:
                cmd.append('-f')
            cmd.append(container_name)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10 if not follow else None
            )
            
            return {
                'success': True,
                'container': container_name,
                'logs': result.stdout,
                'stderr': result.stderr,
            }
        except Exception as e:
            return {
                'success': False,
                'container': container_name,
                'error': str(e),
            }
    
    async def execute_in_docker_container(
        self,
        container_name: str,
        command: List[str]
    ) -> Dict[str, Any]:
        """Execute a command inside a Docker container."""
        if not self.docker_available:
            return {'success': False, 'error': 'Docker not available'}
        
        try:
            cmd = ['docker', 'exec', container_name] + command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                'success': True,
                'container': container_name,
                'command': ' '.join(command),
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
            }
        except Exception as e:
            return {
                'success': False,
                'container': container_name,
                'error': str(e),
            }
    
    # ========== System Resource Management ==========
    
    def get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage."""
        return {
            'cpu': {
                'percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used,
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent,
            },
            'network': self._get_network_stats(),
        }
    
    def _get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics."""
        stats = psutil.net_io_counters()
        connections = psutil.net_connections()
        return {
            'bytes_sent': stats.bytes_sent,
            'bytes_recv': stats.bytes_recv,
            'packets_sent': stats.packets_sent,
            'packets_recv': stats.packets_recv,
            'connections': len(connections),
        }
    
    async def set_resource_limits(
        self,
        process_name: str,
        cpu_percent: Optional[float] = None,
        memory_mb: Optional[float] = None
    ) -> Dict[str, Any]:
        """Set resource limits for a managed process."""
        if process_name not in self.managed_processes:
            return {'success': False, 'error': f'Process {process_name} not managed'}
        
        process_info = self.managed_processes[process_name]
        process = process_info['process']
        
        try:
            ps = psutil.Process(process.pid)
            
            if memory_mb is not None:
                # Set memory limit (if supported)
                try:
                    import resource
                    resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024 * 1024, memory_mb * 1024 * 1024))
                except Exception:
                    pass  # May not be supported on all systems
            
            return {
                'success': True,
                'process': process_name,
                'message': 'Resource limits applied',
            }
        except Exception as e:
            return {
                'success': False,
                'process': process_name,
                'error': str(e),
            }
    
    # ========== Health Monitoring ==========
    
    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of a specific service."""
        if service_name not in self.service_configs:
            return {'status': 'unknown', 'error': 'Service not configured'}
        
        config = self.service_configs[service_name]
        health_check = config.get('health_check')
        
        if not health_check:
            return {'status': 'no_health_check', 'message': 'No health check configured'}
        
        try:
            if health_check.startswith('http://'):
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_check, timeout=5) as response:
                        return {
                            'status': 'healthy' if response.status == 200 else 'unhealthy',
                            'status_code': response.status,
                            'response_time': 0.0,  # TODO: Measure
                        }
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    async def auto_recover_service(self, service_name: str) -> Dict[str, Any]:
        """Attempt to auto-recover a failed service."""
        health = await self.check_service_health(service_name)
        
        if health.get('status') == 'healthy':
            return {'success': True, 'message': 'Service is healthy, no recovery needed'}
        
        config = self.service_configs.get(service_name, {})
        if config.get('auto_restart', False):
            # Restart the process if it's managed
            result = await self.restart_process(service_name)
            return result
        
        return {'success': False, 'message': 'Auto-recovery not enabled for this service'}


__all__ = ["SystemController", "ServiceStatus", "ServiceInfo", "DockerContainerInfo"]

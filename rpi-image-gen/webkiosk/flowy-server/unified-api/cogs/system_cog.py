"""
System Cog for Flowy Unified API

Provides system-level endpoints for monitoring, health checks, and cog management.
This cog provides information about the overall system status and individual cog health.
"""

import os
import sys
import platform
import subprocess

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    print("Warning: psutil not available, system monitoring will be limited")
    PSUTIL_AVAILABLE = False
    
    # Mock psutil for basic functionality
    class MockPsutil:
        @staticmethod
        def cpu_percent(interval=None):
            return 0.0
        
        @staticmethod
        def boot_time():
            return 0
            
        @staticmethod
        def virtual_memory():
            class MockMemory:
                percent = 0.0
                available = 0
                total = 1024 * 1024 * 1024  # 1GB
            return MockMemory()
        
        @staticmethod
        def disk_usage(path):
            class MockDisk:
                percent = 0.0
                free = 1024 * 1024 * 1024  # 1GB
                total = 2 * 1024 * 1024 * 1024  # 2GB
                used = 1024 * 1024 * 1024  # 1GB
            return MockDisk()
        
        @staticmethod
        def process_iter(*args, **kwargs):
            return []
        
        @staticmethod
        def net_io_counters(pernic=False):
            if pernic:
                return {}
            return None
        
        @staticmethod
        def disk_partitions():
            return []
    
    psutil = MockPsutil()
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from pydantic import BaseModel

from .base_cog import BaseCog

# System information models
class SystemInfo(BaseModel):
    hostname: str
    platform: str
    architecture: str
    python_version: str
    uptime_seconds: float
    boot_time: str

class ResourceUsage(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    memory_total_gb: float
    disk_usage_percent: float
    disk_available_gb: float
    disk_total_gb: float
    temperature_celsius: Optional[float] = None

class ProcessInfo(BaseModel):
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    create_time: str

class ServiceStatus(BaseModel):
    name: str
    active: bool
    enabled: bool
    status: str

class SystemCog(BaseCog):
    """System monitoring and management cog"""
    
    def __init__(self, name: str = "system"):
        super().__init__(name)
        self.supports_websocket = True  # Enable WebSocket for real-time system monitoring
        
        # Cache for expensive operations
        self._last_cpu_check = None
        self._cached_cpu_percent = 0.0
        self._cache_duration = timedelta(seconds=2)
        
        # Register system endpoints
        self._register_system_endpoints()
    
    async def initialize(self) -> bool:
        """Initialize system monitoring"""
        try:
            # Test system information access
            psutil.cpu_percent()  # Initialize CPU monitoring
            if PSUTIL_AVAILABLE:
                self.logger.info("System monitoring initialized successfully with full psutil support")
            else:
                self.logger.info("System monitoring initialized with limited functionality (no psutil)")
            self.status = "running"
            return True
        except Exception as e:
            self.log_error(e, "System monitoring initialization failed")
            self.status = "failed"
            return False
    
    async def shutdown(self):
        """Clean shutdown of system monitoring"""
        try:
            self.logger.info("System monitoring shutting down")
            # No specific cleanup needed
        except Exception as e:
            self.log_error(e, "System shutdown error")
    
    def get_capabilities(self) -> List[str]:
        """Return system monitoring capabilities"""
        capabilities = [
            "system_monitoring",
            "service_status",
            "log_management",
            "websocket_support"
        ]
        
        if PSUTIL_AVAILABLE:
            capabilities.extend([
                "resource_usage",
                "process_monitoring", 
                "real_time_metrics",
                "network_stats",
                "disk_monitoring"
            ])
        else:
            capabilities.extend([
                "basic_system_info",
                "limited_functionality"
            ])
        
        return capabilities
    
    def _get_system_info(self) -> SystemInfo:
        """Get basic system information"""
        if PSUTIL_AVAILABLE:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = (datetime.now() - boot_time).total_seconds()
        else:
            # Mock values when psutil not available
            boot_time = datetime.now() - timedelta(hours=1)  # Fake 1 hour uptime
            uptime = 3600.0
        
        return SystemInfo(
            hostname=platform.node(),
            platform=f"{platform.system()} {platform.release()}",
            architecture=platform.architecture()[0],
            python_version=platform.python_version(),
            uptime_seconds=uptime,
            boot_time=boot_time.isoformat()
        )
    
    def _get_resource_usage(self) -> ResourceUsage:
        """Get current resource usage"""
        # Use cached CPU if recent
        now = datetime.now()
        if (self._last_cpu_check is None or 
            now - self._last_cpu_check > self._cache_duration):
            self._cached_cpu_percent = psutil.cpu_percent(interval=1)
            self._last_cpu_check = now
        
        # Memory information
        memory = psutil.virtual_memory()
        
        # Disk information (root filesystem)
        disk = psutil.disk_usage('/')
        
        # Temperature (try to get CPU temperature on Raspberry Pi)
        temperature = None
        try:
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_raw = int(f.read().strip())
                    temperature = temp_raw / 1000.0  # Convert from millidegrees
        except Exception:
            pass
        
        return ResourceUsage(
            cpu_percent=self._cached_cpu_percent,
            memory_percent=memory.percent,
            memory_available_gb=round(memory.available / (1024**3), 2),
            memory_total_gb=round(memory.total / (1024**3), 2),
            disk_usage_percent=disk.percent,
            disk_available_gb=round(disk.free / (1024**3), 2),
            disk_total_gb=round(disk.total / (1024**3), 2),
            temperature_celsius=temperature
        )
    
    def _get_process_list(self, limit: int = 10) -> List[ProcessInfo]:
        """Get list of top processes by CPU usage"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 
                                       'memory_percent', 'create_time']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] is not None:
                    create_time = datetime.fromtimestamp(pinfo['create_time']).isoformat()
                    processes.append(ProcessInfo(
                        pid=pinfo['pid'],
                        name=pinfo['name'],
                        status=pinfo['status'],
                        cpu_percent=pinfo['cpu_percent'],
                        memory_percent=pinfo['memory_percent'],
                        create_time=create_time
                    ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage and return top N
        processes.sort(key=lambda x: x.cpu_percent, reverse=True)
        return processes[:limit]
    
    def _get_service_status(self, services: List[str]) -> List[ServiceStatus]:
        """Get status of specific systemd services"""
        service_statuses = []
        
        for service in services:
            try:
                # Check if service is active
                active_result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True, text=True, timeout=5
                )
                is_active = active_result.returncode == 0
                
                # Check if service is enabled
                enabled_result = subprocess.run(
                    ['systemctl', 'is-enabled', service],
                    capture_output=True, text=True, timeout=5
                )
                is_enabled = enabled_result.returncode == 0
                
                # Get detailed status
                status_result = subprocess.run(
                    ['systemctl', 'show', service, '--property=ActiveState,SubState'],
                    capture_output=True, text=True, timeout=5
                )
                
                status_info = "unknown"
                if status_result.returncode == 0:
                    for line in status_result.stdout.strip().split('\n'):
                        if line.startswith('ActiveState='):
                            status_info = line.split('=', 1)[1]
                            break
                
                service_statuses.append(ServiceStatus(
                    name=service,
                    active=is_active,
                    enabled=is_enabled,
                    status=status_info
                ))
                
            except subprocess.TimeoutExpired:
                service_statuses.append(ServiceStatus(
                    name=service,
                    active=False,
                    enabled=False,
                    status="timeout"
                ))
            except Exception as e:
                service_statuses.append(ServiceStatus(
                    name=service,
                    active=False,
                    enabled=False,
                    status=f"error: {str(e)}"
                ))
        
        return service_statuses
    
    def _register_system_endpoints(self):
        """Register all system-specific endpoints"""
        
        @self.router.get("/info", response_model=SystemInfo)
        async def get_system_info():
            """Get basic system information"""
            try:
                return self._get_system_info()
            except Exception as e:
                self.log_error(e, "Error getting system info")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/resources", response_model=ResourceUsage)
        async def get_resource_usage():
            """Get current system resource usage"""
            try:
                return self._get_resource_usage()
            except Exception as e:
                self.log_error(e, "Error getting resource usage")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/processes")
        async def get_processes(limit: int = 10):
            """Get list of top processes by CPU usage"""
            try:
                if limit > 50:
                    limit = 50  # Reasonable limit
                return self._get_process_list(limit)
            except Exception as e:
                self.log_error(e, "Error getting process list")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/services")
        async def get_services(services: str = ""):
            """Get status of systemd services (comma-separated list)"""
            try:
                if not services:
                    # Default services to check
                    service_list = [
                        "ssh", "NetworkManager", "systemd-timesyncd",
                        "flowy-unified-api"  # Our own service
                    ]
                else:
                    service_list = [s.strip() for s in services.split(',')]
                
                return self._get_service_status(service_list)
            except Exception as e:
                self.log_error(e, "Error getting service status")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/uptime")
        async def get_uptime():
            """Get system uptime information"""
            try:
                boot_time = datetime.fromtimestamp(psutil.boot_time())
                uptime_seconds = (datetime.now() - boot_time).total_seconds()
                
                # Format uptime
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                
                return {
                    "boot_time": boot_time.isoformat(),
                    "uptime_seconds": uptime_seconds,
                    "uptime_formatted": f"{days}d {hours}h {minutes}m",
                    "current_time": datetime.now().isoformat()
                }
            except Exception as e:
                self.log_error(e, "Error getting uptime")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/disk")
        async def get_disk_usage():
            """Get disk usage for all mounted filesystems"""
            try:
                disk_info = []
                
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disk_info.append({
                            "device": partition.device,
                            "mountpoint": partition.mountpoint,
                            "filesystem": partition.fstype,
                            "total_gb": round(usage.total / (1024**3), 2),
                            "used_gb": round(usage.used / (1024**3), 2),
                            "free_gb": round(usage.free / (1024**3), 2),
                            "percent_used": round(usage.used / usage.total * 100, 1)
                        })
                    except PermissionError:
                        continue
                
                return disk_info
            except Exception as e:
                self.log_error(e, "Error getting disk usage")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/network")
        async def get_network_stats():
            """Get network interface statistics"""
            try:
                network_info = []
                stats = psutil.net_io_counters(pernic=True)
                
                for interface, stat in stats.items():
                    # Skip loopback interface
                    if interface == 'lo':
                        continue
                    
                    network_info.append({
                        "interface": interface,
                        "bytes_sent": stat.bytes_sent,
                        "bytes_recv": stat.bytes_recv,
                        "packets_sent": stat.packets_sent,
                        "packets_recv": stat.packets_recv,
                        "errors_in": stat.errin,
                        "errors_out": stat.errout,
                        "dropped_in": stat.dropin,
                        "dropped_out": stat.dropout
                    })
                
                return network_info
            except Exception as e:
                self.log_error(e, "Error getting network stats")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/restart-service")
        async def restart_service(service_name: str):
            """Restart a systemd service (requires appropriate permissions)"""
            try:
                # Security: Only allow specific services
                allowed_services = [
                    "flowy-unified-api",
                    "NetworkManager",
                    "ssh"
                ]
                
                if service_name not in allowed_services:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Service '{service_name}' not allowed to be restarted"
                    )
                
                result = subprocess.run(
                    ['sudo', 'systemctl', 'restart', service_name],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    self.logger.info(f"Successfully restarted service: {service_name}")
                    return {
                        "success": True,
                        "message": f"Service '{service_name}' restarted successfully"
                    }
                else:
                    error_msg = result.stderr or "Unknown error"
                    self.logger.error(f"Failed to restart service {service_name}: {error_msg}")
                    return {
                        "success": False,
                        "message": f"Failed to restart service: {error_msg}"
                    }
                    
            except subprocess.TimeoutExpired:
                raise HTTPException(status_code=408, detail="Service restart timed out")
            except Exception as e:
                self.log_error(e, f"Error restarting service {service_name}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def websocket_handler(self, websocket):
        """Custom WebSocket handler for real-time system monitoring"""
        await self.websocket_manager.connect(websocket)
        
        try:
            # Send initial system status
            await websocket.send_json({
                "type": "system_status",
                "data": {
                    "system_info": self._get_system_info().dict(),
                    "resource_usage": self._get_resource_usage().dict()
                }
            })
            
            # Start monitoring loop
            import asyncio
            monitoring_task = asyncio.create_task(self._monitoring_loop(websocket))
            
            # Handle client messages
            while True:
                try:
                    data = await websocket.receive_text()
                    await self.handle_websocket_message(websocket, data)
                except Exception as e:
                    self.logger.warning(f"System WebSocket message error: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"System WebSocket handler error: {e}")
        finally:
            self.websocket_manager.disconnect(websocket)
            if 'monitoring_task' in locals():
                monitoring_task.cancel()
    
    async def _monitoring_loop(self, websocket):
        """Send periodic system updates via WebSocket"""
        try:
            while True:
                await asyncio.sleep(5)  # Update every 5 seconds
                
                # Send resource usage update
                try:
                    resource_usage = self._get_resource_usage()
                    await websocket.send_json({
                        "type": "resource_update",
                        "data": resource_usage.dict()
                    })
                except Exception as e:
                    self.logger.warning(f"Error sending resource update: {e}")
                    break
                    
        except asyncio.CancelledError:
            pass
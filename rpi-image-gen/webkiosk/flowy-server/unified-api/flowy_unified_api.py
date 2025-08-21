#!/usr/bin/env python3
"""
Flowy Unified API Server

A modular API system using a "cogs" architecture where each service (LED, NFC, WiFi, etc.)
is a separate module with isolated error handling. Individual cog failures don't crash
the main server.

Features:
- FastAPI with automatic Swagger documentation
- WebSocket support for real-time events
- Per-cog error isolation and health monitoring
- Structured logging with rotation
- Hot-reload support for development
"""

import os
import sys
import asyncio
import logging
import importlib
import inspect
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Add the current directory to Python path for cog imports
sys.path.insert(0, os.path.dirname(__file__))

from cogs.base_cog import BaseCog, CogHealth

# Configuration
DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"

class SystemHealth(BaseModel):
    status: str  # "healthy", "degraded", "failed"
    timestamp: str
    uptime_seconds: float
    total_cogs: int
    healthy_cogs: int
    failed_cogs: int
    cog_details: Dict[str, CogHealth]

class CogInfo(BaseModel):
    name: str
    status: str
    capabilities: List[str]
    supports_websocket: bool
    endpoints: List[str]

class FlowyUnifiedAPI:
    """Main API server that manages and loads all cogs"""
    
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.start_time = datetime.now()
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Flowy Unified API",
            description="""
            Unified API system for Flowy OS with modular cogs architecture.
            
            Each service (LED, NFC, WiFi, etc.) runs as an isolated cog with individual error handling.
            WebSocket support is available for real-time events and monitoring.
            
            ## Features
            - **Modular Design**: Services isolated in cogs for reliability
            - **WebSocket Support**: Real-time events and bidirectional communication
            - **Health Monitoring**: Per-cog and system-wide health checks
            - **Comprehensive Logging**: Structured logs with rotation
            - **Auto Documentation**: Complete Swagger UI for all endpoints
            """,
            version="1.0.0",
            docs_url="/",  # Serve Swagger UI at root
            redoc_url="/redoc"
        )
        
        # Enable CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Cog management
        self.cogs: Dict[str, BaseCog] = {}
        self.failed_cogs: Dict[str, str] = {}  # cog_name -> error_message
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Register system endpoints
        self._register_system_endpoints()
        
        self.logger.info("Flowy Unified API initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup main server logging"""
        # Create main log directory
        log_dir = '/flowy/logs/unified-api'
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup logger
        logger = logging.getLogger("unified_api")
        logger.setLevel(logging.INFO)
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        log_file = os.path.join(log_dir, 'unified_api.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10_000_000,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _register_system_endpoints(self):
        """Register system-wide endpoints"""
        
        @self.app.get("/health", response_model=SystemHealth, summary="System Health Check")
        async def system_health():
            """Get overall system health including all cogs"""
            cog_details = {}
            healthy_count = 0
            failed_count = 0
            
            # Check all loaded cogs
            for name, cog in self.cogs.items():
                health = cog.get_health()
                cog_details[name] = health
                
                if health.status == "healthy":
                    healthy_count += 1
                elif health.status == "failed":
                    failed_count += 1
            
            # Include failed cogs that couldn't load
            for name, error in self.failed_cogs.items():
                cog_details[name] = CogHealth(
                    name=name,
                    status="failed",
                    last_check=datetime.now().isoformat(),
                    error_count=1,
                    last_error=error,
                    uptime_seconds=0,
                    capabilities=[]
                )
                failed_count += 1
            
            # Determine overall system status
            total_cogs = len(cog_details)
            if failed_count == 0:
                system_status = "healthy"
            elif healthy_count > 0:
                system_status = "degraded"
            else:
                system_status = "failed"
            
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            return SystemHealth(
                status=system_status,
                timestamp=datetime.now().isoformat(),
                uptime_seconds=uptime,
                total_cogs=total_cogs,
                healthy_cogs=healthy_count,
                failed_cogs=failed_count,
                cog_details=cog_details
            )
        
        @self.app.get("/cogs", response_model=Dict[str, CogInfo], summary="List All Cogs")
        async def list_cogs():
            """List all loaded cogs and their information"""
            cog_info = {}
            
            for name, cog in self.cogs.items():
                cog_info[name] = CogInfo(
                    name=name,
                    status=cog.status,
                    capabilities=[],  # Simplified - no longer showing detailed capabilities
                    supports_websocket=cog.supports_websocket,
                    endpoints=[route.path for route in cog.router.routes]
                )
            
            # Include failed cogs
            for name, error in self.failed_cogs.items():
                cog_info[name] = CogInfo(
                    name=name,
                    status="failed",
                    capabilities=[],
                    supports_websocket=False,
                    endpoints=[]
                )
            
            return cog_info
        
        @self.app.websocket("/ws")
        async def main_websocket(websocket: WebSocket):
            """Main WebSocket endpoint for multiplexed events from all cogs"""
            await websocket.accept()
            self.logger.info("Main WebSocket client connected")
            
            try:
                # Send initial system status
                health = await system_health()
                await websocket.send_json({
                    "type": "system_status",
                    "data": health.dict(),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Keep connection alive
                while True:
                    try:
                        # Listen for client messages (can be used for commands)
                        data = await websocket.receive_text()
                        # Echo back for now
                        await websocket.send_json({
                            "type": "echo",
                            "message": data,
                            "timestamp": datetime.now().isoformat()
                        })
                    except WebSocketDisconnect:
                        break
                    except Exception as e:
                        self.logger.warning(f"Main WebSocket message error: {e}")
                        break
                        
            except Exception as e:
                self.logger.error(f"Main WebSocket error: {e}")
            finally:
                self.logger.info("Main WebSocket client disconnected")
        
        @self.app.websocket("/ws/{cog_name}")
        async def cog_websocket(websocket: WebSocket, cog_name: str):
            """Cog-specific WebSocket endpoint"""
            if cog_name not in self.cogs:
                await websocket.close(code=1000, reason=f"Cog '{cog_name}' not found")
                return
            
            cog = self.cogs[cog_name]
            if not cog.supports_websocket:
                await websocket.close(code=1000, reason=f"Cog '{cog_name}' doesn't support WebSocket")
                return
            
            await cog.websocket_handler(websocket)
        
        @self.app.get("/logs/{cog_name}")
        async def get_cog_logs(cog_name: str, lines: int = 100):
            """Get recent log entries for a specific cog"""
            log_file = f'/flowy/logs/{cog_name}/{cog_name}_cog.log'
            
            if not os.path.exists(log_file):
                raise HTTPException(status_code=404, detail=f"Log file for cog '{cog_name}' not found")
            
            try:
                # Read last N lines
                with open(log_file, 'r') as f:
                    lines_list = f.readlines()
                    recent_lines = lines_list[-lines:] if len(lines_list) > lines else lines_list
                
                return {
                    "cog": cog_name,
                    "lines": len(recent_lines),
                    "logs": [line.strip() for line in recent_lines]
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")
        
        @self.app.get("/wc", response_class=HTMLResponse)
        async def websocket_client():
            """WebSocket test client for NFC tags"""
            try:
                # Read the HTML file
                html_file = Path(__file__).parent / "nfc_websocket_test.html"
                if html_file.exists():
                    with open(html_file, 'r', encoding='utf-8') as f:
                        return HTMLResponse(content=f.read())
                else:
                    raise HTTPException(status_code=404, detail="WebSocket client file not found")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error loading WebSocket client: {str(e)}")
    
    async def discover_and_load_cogs(self):
        """Discover and load all available cogs"""
        cogs_dir = Path(__file__).parent / "cogs"
        
        self.logger.info(f"Discovering cogs in: {cogs_dir}")
        
        # Find all Python files in cogs directory (except __init__ and base_cog)
        cog_files = []
        for file_path in cogs_dir.glob("*.py"):
            if file_path.name not in ["__init__.py", "base_cog.py"]:
                cog_files.append(file_path.stem)
        
        self.logger.info(f"Found potential cogs: {cog_files}")
        
        # Load each cog
        for cog_name in cog_files:
            await self._load_cog(cog_name)
        
        self.logger.info(f"Successfully loaded {len(self.cogs)} cogs")
        if self.failed_cogs:
            self.logger.warning(f"Failed to load {len(self.failed_cogs)} cogs: {list(self.failed_cogs.keys())}")
    
    async def _load_cog(self, cog_name: str):
        """Load a specific cog by name"""
        try:
            self.logger.info(f"Loading cog: {cog_name}")
            
            # Import the cog module
            module = importlib.import_module(f"cogs.{cog_name}")
            
            # Find the cog class (should be subclass of BaseCog)
            cog_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (obj != BaseCog and 
                    issubclass(obj, BaseCog) and 
                    obj.__module__ == module.__name__):
                    cog_class = obj
                    break
            
            if not cog_class:
                raise Exception(f"No BaseCog subclass found in {cog_name}")
            
            # Create cog instance
            cog_instance = cog_class(cog_name.replace("_cog", ""))
            
            # Initialize the cog
            if await cog_instance.initialize():
                # Add cog router to main app
                self.app.include_router(cog_instance.router)
                
                # Store the cog
                self.cogs[cog_instance.name] = cog_instance
                cog_instance.status = "running"
                
                self.logger.info(f"Successfully loaded cog: {cog_instance.name}")
            else:
                raise Exception("Cog initialization failed")
                
        except Exception as e:
            error_msg = f"Failed to load cog {cog_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.failed_cogs[cog_name] = error_msg
    
    async def start_server(self):
        """Start the unified API server"""
        self.logger.info(f"Starting Flowy Unified API server on {self.host}:{self.port}")
        
        # Load all cogs
        await self.discover_and_load_cogs()
        
        # Start the server
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        await server.serve()
    
    async def shutdown(self):
        """Clean shutdown of all cogs"""
        self.logger.info("Shutting down unified API server...")
        
        for name, cog in self.cogs.items():
            try:
                await cog.shutdown()
                self.logger.info(f"Cog {name} shut down successfully")
            except Exception as e:
                self.logger.error(f"Error shutting down cog {name}: {e}")
        
        self.logger.info("Unified API server shutdown complete")

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Flowy Unified API Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    # Create and start the server
    server = FlowyUnifiedAPI(host=args.host, port=args.port)
    
    try:
        if args.reload:
            # Use uvicorn directly with reload for development
            uvicorn.run(
                "flowy_unified_api:app",
                host=args.host,
                port=args.port,
                reload=True,
                log_level="info"
            )
        else:
            await server.start_server()
    except KeyboardInterrupt:
        print("\nReceived interrupt signal")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        await server.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
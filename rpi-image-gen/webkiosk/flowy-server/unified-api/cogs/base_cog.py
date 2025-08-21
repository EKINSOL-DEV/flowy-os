"""
Base Cog Architecture for Flowy Unified API

This module provides the abstract base class and common functionality for all API cogs.
Each cog represents a modular component (LED, NFC, WiFi, etc.) with isolated error handling.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

class CogHealth(BaseModel):
    name: str
    status: str  # "healthy", "degraded", "failed"
    last_check: str
    error_count: int = 0
    last_error: Optional[str] = None
    uptime_seconds: float
    capabilities: List[str] = []

class WebSocketManager:
    """Manages WebSocket connections for a cog"""
    
    def __init__(self, cog_name: str):
        self.cog_name = cog_name
        self.active_connections: List[WebSocket] = []
        self.logger = logging.getLogger(f"websocket.{cog_name}")
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"WebSocket connected to {self.cog_name}. Active connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.logger.info(f"WebSocket disconnected from {self.cog_name}. Active connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected WebSocket clients"""
        if not self.active_connections:
            return
        
        # Add metadata
        message_with_meta = {
            **message,
            "cog": self.cog_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all clients, remove failed connections
        failed_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message_with_meta)
            except Exception as e:
                self.logger.warning(f"Failed to send message to WebSocket client: {e}")
                failed_connections.append(connection)
        
        # Clean up failed connections
        for connection in failed_connections:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

class BaseCog(ABC):
    """
    Abstract base class for all API cogs.
    
    Each cog should inherit from this class and implement the required methods.
    This provides standard functionality for health checks, logging, WebSocket support,
    and error isolation.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.router = APIRouter(prefix=f"/{name}", tags=[name.upper()])
        self.logger = logging.getLogger(f"cog.{name}")
        self.start_time = datetime.now()
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.status = "initializing"
        
        # WebSocket support
        self.websocket_manager = WebSocketManager(name)
        self.supports_websocket = False
        
        # Setup logging
        self._setup_logging()
        
        # Register common endpoints
        self._register_common_endpoints()
        
        self.logger.info(f"Cog {name} initialized")
    
    def _setup_logging(self):
        """Setup cog-specific logging with rotation"""
        import os
        from logging.handlers import RotatingFileHandler
        
        # Create log directory
        log_dir = f'/flowy/logs/{self.name}'
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup file handler
        log_file = os.path.join(log_dir, f'{self.name}_cog.log')
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10_000_000,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
    
    def _register_common_endpoints(self):
        """Register common endpoints that all cogs have"""
        
        @self.router.get("/health", response_model=CogHealth)
        async def get_cog_health():
            """Get health status of this cog"""
            return self.get_health()
        
        @self.router.get("/info")
        async def get_cog_info():
            """Get general information about this cog"""
            return {
                "name": self.name,
                "status": self.status,
                "capabilities": self.get_capabilities(),
                "supports_websocket": self.supports_websocket,
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "endpoints": [route.path for route in self.router.routes]
            }
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the cog. Called once at startup.
        Should return True if successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def shutdown(self):
        """
        Clean shutdown of the cog. Called when the server is stopping.
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Return a list of capabilities this cog provides.
        Used for service discovery and health monitoring.
        """
        pass
    
    def get_health(self) -> CogHealth:
        """Get current health status of this cog"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Determine status based on errors and functionality
        if self.status == "failed":
            status = "failed"
        elif self.error_count > 0:
            status = "degraded"
        else:
            status = "healthy"
        
        return CogHealth(
            name=self.name,
            status=status,
            last_check=datetime.now().isoformat(),
            error_count=self.error_count,
            last_error=self.last_error,
            uptime_seconds=uptime,
            capabilities=self.get_capabilities()
        )
    
    def log_error(self, error: Exception, context: str = ""):
        """Log an error and update error tracking"""
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(error_msg, exc_info=True)
        self.error_count += 1
        self.last_error = error_msg
    
    def safe_execute(self, func, *args, **kwargs):
        """
        Safely execute a function with error handling.
        Returns the result or raises HTTPException on error.
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.log_error(e, f"Error in {func.__name__}")
            raise HTTPException(
                status_code=503,
                detail=f"Cog {self.name} error: {str(e)}"
            )
    
    async def safe_execute_async(self, coro, context: str = ""):
        """
        Safely execute an async function with error handling.
        Returns the result or raises HTTPException on error.
        """
        try:
            return await coro
        except Exception as e:
            self.log_error(e, context)
            raise HTTPException(
                status_code=503,
                detail=f"Cog {self.name} error: {str(e)}"
            )
    
    async def websocket_handler(self, websocket: WebSocket):
        """
        Default WebSocket handler. Override in subclasses for custom behavior.
        """
        if not self.supports_websocket:
            await websocket.close(code=1000, reason="WebSocket not supported by this cog")
            return
        
        await self.websocket_manager.connect(websocket)
        
        try:
            # Send initial status
            await websocket.send_json({
                "type": "connection_established",
                "cog": self.name,
                "status": self.status,
                "capabilities": self.get_capabilities()
            })
            
            # Keep connection alive and handle client messages
            while True:
                try:
                    # Wait for client messages (can be used for commands)
                    data = await websocket.receive_text()
                    await self.handle_websocket_message(websocket, data)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    self.logger.warning(f"WebSocket message error: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"WebSocket handler error: {e}")
        finally:
            self.websocket_manager.disconnect(websocket)
    
    async def handle_websocket_message(self, websocket: WebSocket, message: str):
        """
        Handle incoming WebSocket messages. Override in subclasses.
        Default implementation echoes the message back.
        """
        await websocket.send_json({
            "type": "echo",
            "message": message,
            "cog": self.name
        })
    
    async def broadcast_websocket_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast an event to all WebSocket clients"""
        if self.supports_websocket:
            await self.websocket_manager.broadcast({
                "type": event_type,
                "data": data
            })
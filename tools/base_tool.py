"""
Base tool class for Smithery tool integrations
"""
import asyncio
import aiohttp
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from loguru import logger
from config import config


class BaseTool(ABC):
    """Base class for all Smithery tools"""
    
    def __init__(self, tool_url: str, name: str):
        self.tool_url = tool_url
        self.name = name
        self.timeout = config.TOOL_TIMEOUT
        self.max_retries = config.MAX_RETRIES
    
    # Legacy method - now using specialized Smithery clients
    async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Legacy method - tools now use specialized Smithery clients"""
        logger.warning(f"Legacy _make_request called for {self.name} tool - should use Smithery client instead")
        return None
    
    @abstractmethod
    async def execute(self, query: str, **kwargs) -> str:
        """Execute the tool with given query"""
        pass
    
    @abstractmethod
    def can_handle(self, query: str) -> bool:
        """Check if this tool can handle the given query"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get tool description for the agent"""
        pass

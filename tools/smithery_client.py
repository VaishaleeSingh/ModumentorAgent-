"""
Smithery MCP Client for direct HTTP calls to Smithery servers
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
from loguru import logger
from config import config


class SmitheryClient:
    """Client for making direct HTTP calls to Smithery MCP servers"""
    
    def __init__(self, server_url: str, timeout: int = 20):  # increased for slow networks
        self.server_url = server_url
        self.timeout = timeout
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Add Smithery API token if available
        if config.SMITHERY_API_TOKEN and config.SMITHERY_API_TOKEN != "your_smithery_api_token_here":
            headers['Authorization'] = f'Bearer {config.SMITHERY_API_TOKEN}'

        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers=headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call a tool on the Smithery server"""
        try:
            # Smithery MCP servers expect tool calls in this format
            payload = {
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            logger.info(f"Calling Smithery tool {tool_name} at {self.server_url}")
            logger.debug(f"Payload: {payload}")
            
            async with self.session.post(self.server_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Tool {tool_name} call successful")
                    return result
                else:
                    error_text = await response.text()
                    logger.warning(f"Tool {tool_name} returned status {response.status}: {error_text}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout calling tool {tool_name}")
            return None
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return None
    
    async def list_tools(self) -> Optional[List[Dict[str, Any]]]:
        """List available tools on the server"""
        try:
            payload = {
                "method": "tools/list",
                "params": {}
            }
            
            async with self.session.post(self.server_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("result", {}).get("tools", [])
                else:
                    logger.warning(f"List tools returned status {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return None


class SmitheryWeatherClient(SmitheryClient):
    """Specialized client for Smithery weather server"""
    
    def __init__(self):
        super().__init__("https://server.smithery.ai/@isdaniel/mcp_weather_server")
    
    async def get_current_weather(self, city: str) -> Optional[Dict[str, Any]]:
        """Get current weather for a city"""
        return await self.call_tool("get_current_weather", {"city": city})
    
    async def get_weather_by_datetime_range(self, city: str, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """Get weather for a date range"""
        return await self.call_tool("get_weather_by_datetime_range", {
            "city": city,
            "start_date": start_date,
            "end_date": end_date
        })


class SmitherySearchClient(SmitheryClient):
    """Specialized client for Smithery Tavily search server"""
    
    def __init__(self):
        super().__init__("https://server.smithery.ai/@tavily-ai/tavily-mcp")
    
    async def search(self, query: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
        """Perform web search"""
        return await self.call_tool("tavily-search", {
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": True,
            "include_raw_content": False
        })


class SmitheryDictionaryClient(SmitheryClient):
    """Specialized client for Smithery dictionary server"""
    
    def __init__(self):
        # Use a reasonable timeout for dictionary calls
        super().__init__("https://server.smithery.ai/@emro624/dictionary-mcp-main", timeout=12)  # increased for slow networks
    
    async def get_definitions(self, word: str) -> Optional[Dict[str, Any]]:
        """Get definitions for a word"""
        try:
            return await self.call_tool("get_definitions", {"word": word})
        except Exception as e:
            logger.error(f"Dictionary client error: {e}")
            return None

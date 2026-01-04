"""
MCP Dictionary Client using official MCP SDK
Connects to Smithery dictionary server via MCP protocol
"""
import asyncio
import json
from typing import Dict, Any, Optional
from loguru import logger
import mcp
from mcp.client.streamable_http import streamablehttp_client
from config import Config


class MCPDictionaryClient:
    """MCP-based dictionary client using official MCP SDK"""
    
    def __init__(self):
        self.smithery_api_key = Config.SMITHERY_API_TOKEN
        self.base_url = "https://server.smithery.ai/@emro624/dictionary-mcp-main/mcp"
        self.timeout = Config.TOOL_TIMEOUT
        
    async def get_definitions(self, word: str) -> Optional[Dict[str, Any]]:
        """Get definitions for a word using MCP protocol"""
        try:
            url = f"{self.base_url}?api_key={self.smithery_api_key}&profile=visual-sparrow-jYeLhy"
            
            logger.info(f"MCP Dictionary: Looking up word '{word}'")
            
            async with asyncio.timeout(self.timeout):
                async with streamablehttp_client(url) as (read_stream, write_stream, _):
                    async with mcp.ClientSession(read_stream, write_stream) as session:
                        # Initialize the connection
                        await session.initialize()
                        
                        # List available tools to verify connection
                        tools_result = await session.list_tools()
                        logger.debug(f"MCP Dictionary: Available tools: {[t.name for t in tools_result.tools]}")
                        
                        # Call the get_definitions tool
                        call_result = await session.call_tool(
                            "get_definitions",
                            {"word": word}
                        )
                        
                        if call_result.content:
                            # Parse the content
                            content_text = call_result.content[0].text
                            logger.info(f"MCP Dictionary: Received response for '{word}'")
                            
                            try:
                                # Try to parse as JSON
                                data = json.loads(content_text)
                                return self._format_mcp_response(data, word)
                            except json.JSONDecodeError:
                                # If not JSON, return as plain text
                                return self._format_plain_text_response(content_text, word)
                        else:
                            logger.warning(f"MCP Dictionary: No content received for '{word}'")
                            return None
                            
        except asyncio.TimeoutError:
            logger.warning(f"MCP Dictionary: Timeout after {self.timeout}s for word '{word}'")
            return None
        except Exception as e:
            logger.error(f"MCP Dictionary: Error getting definition for '{word}': {e}")
            return None
    
    def _format_mcp_response(self, data: Dict[str, Any], word: str) -> Dict[str, Any]:
        """Format MCP response data"""
        return {
            "word": word,
            "data": data,
            "source": "MCP Dictionary",
            "success": True
        }
    
    def _format_plain_text_response(self, text: str, word: str) -> Dict[str, Any]:
        """Format plain text response"""
        return {
            "word": word,
            "text": text,
            "source": "MCP Dictionary",
            "success": True
        }
    
    async def test_connection(self) -> bool:
        """Test MCP connection"""
        try:
            url = f"{self.base_url}?api_key={self.smithery_api_key}&profile=visual-sparrow-jYeLhy"
            
            async with asyncio.timeout(10):
                async with streamablehttp_client(url) as (read_stream, write_stream, _):
                    async with mcp.ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        tools_result = await session.list_tools()
                        logger.info(f"MCP Dictionary: Connection test successful. Tools: {[t.name for t in tools_result.tools]}")
                        return True
                        
        except Exception as e:
            logger.error(f"MCP Dictionary: Connection test failed: {e}")
            import traceback
            logger.error(f"MCP Dictionary: Full traceback: {traceback.format_exc()}")
            return False


# Global instance
mcp_dictionary_client = MCPDictionaryClient() 
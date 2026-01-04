"""
Local MCP Dictionary Client using Smithery CLI
Runs the dictionary server locally using the Smithery CLI
"""
import asyncio
import json
import subprocess
import sys
from typing import Dict, Any, Optional
from loguru import logger
from config import Config


class MCPLocalDictionaryClient:
    """Local MCP dictionary client using Smithery CLI"""
    
    def __init__(self):
        # Use the new API key for dictionary lookups
        self.smithery_api_key = "7658cf17592aa40c9ed0105ac6f1f47d"
        self.profile = "visual-sparrow-jYeLhy"
        self.timeout = Config.TOOL_TIMEOUT
        self._process = None
        
    async def connect(self) -> bool:
        """Start the local MCP server"""
        try:
            logger.info("Starting local MCP dictionary server...")
            
            # Command to start the Smithery CLI server
            cmd = [
                "cmd", "/c", "npx", "-y", "@smithery/cli@latest", "run",
                "@emro624/dictionary-mcp-main", "--key", self.smithery_api_key,
                "--profile", self.profile
            ]
            
            logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Start the process
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Wait a bit for the server to start
            await asyncio.sleep(3)
            
            # Check if process is still running
            if self._process.poll() is None:
                logger.info("Local MCP dictionary server started successfully")
                return True
            else:
                stdout, stderr = self._process.communicate()
                logger.error(f"Failed to start MCP server. stdout: {stdout}, stderr: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting local MCP server: {e}")
            return False
    
    async def get_definitions(self, word: str) -> Optional[Dict[str, Any]]:
        """Get definitions for a word using local MCP server"""
        try:
            if not self._process or self._process.poll() is not None:
                # Server not running, try to start it
                if not await self.connect():
                    return None
            
            logger.info(f"Local MCP Dictionary: Looking up word '{word}'")
            
            # Try to get real data from the local dictionary first
            from .local_dictionary import local_dictionary
            local_result = local_dictionary.get_definition(word)
            
            if local_result:
                logger.info(f"Found local definition for '{word}'")
                return {
                    "word": word,
                    "data": local_result,
                    "source": "Local MCP Dictionary (Local Cache)",
                    "success": True
                }
            
            # Try to communicate with the running MCP server via subprocess output
            try:
                # Check if the subprocess has any output we can read
                if self._process and self._process.poll() is None:
                    # Try to read any available output from the subprocess
                    import select
                    import time
                    
                    # Give the process a moment to potentially respond
                    await asyncio.sleep(0.5)
                    
                    # Check if there's any output available
                    if hasattr(self._process.stdout, 'readable'):
                        try:
                            # Try to read any available output
                            output = self._process.stdout.read(1024) if self._process.stdout.readable() else ""
                            if output:
                                logger.info(f"Got output from MCP server: {output[:100]}...")
                                # Parse the output for definition data
                                # This is a simplified approach - in a real implementation,
                                # you'd need to implement the full MCP protocol
                        except Exception as e:
                            logger.debug(f"Could not read from MCP server output: {e}")
                            
            except Exception as e:
                logger.debug(f"Failed to communicate with MCP server via subprocess: {e}")
            
            # If all else fails, return a placeholder with note
            return {
                "word": word,
                "data": {
                    "definitions": [
                        {
                            "partOfSpeech": "noun",
                            "definition": f"Definition for '{word}' not available in local cache. The MCP server is running but direct communication needs to be configured.",
                            "example": f"Please check the word spelling or try a different word."
                        }
                    ],
                    "note": "This is a fallback response. The local MCP server is running but direct communication needs to be configured."
                },
                "source": "Local MCP Dictionary (Fallback)",
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error getting definition from local MCP server: {e}")
            return None
    
    async def disconnect(self):
        """Stop the local MCP server"""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
                logger.info("Local MCP dictionary server stopped")
            except subprocess.TimeoutExpired:
                self._process.kill()
                logger.warning("Force killed local MCP dictionary server")
            except Exception as e:
                logger.error(f"Error stopping local MCP server: {e}")
    
    async def test_connection(self) -> bool:
        """Test local MCP connection"""
        try:
            success = await self.connect()
            if success:
                await self.disconnect()
            return success
        except Exception as e:
            logger.error(f"Local MCP connection test failed: {e}")
            return False


# Global instance
mcp_local_dictionary_client = MCPLocalDictionaryClient() 
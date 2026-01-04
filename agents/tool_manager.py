"""
Tool Manager for handling tool selection and execution
"""
from typing import List, Optional, Dict, Any
from loguru import logger
from tools import WeatherTool, WebSearchTool, DictionaryTool, GoogleSheetsTool, GmailTool, LyricsTool, AdvancedAITool, BaseTool


class ToolManager:
    """Manages available tools and handles tool selection"""
    
    def __init__(self):
        self.tools: List[BaseTool] = [
            WeatherTool(),
            GoogleSheetsTool(),
            GmailTool(),
            LyricsTool(),
            DictionaryTool(),
            AdvancedAITool(),
            WebSearchTool()  # WebSearch as fallback
        ]
        logger.info(f"Initialized ToolManager with {len(self.tools)} tools (including Lyrics and Advanced AI)")
    
    def get_available_tools(self) -> Dict[str, str]:
        """Get list of available tools and their descriptions"""
        return {tool.name: tool.get_description() for tool in self.tools}
    
    def select_tool(self, query: str) -> Optional[BaseTool]:
        """Select the most appropriate tool for the given query with intelligent fallback"""
        logger.info(f"ToolManager: Selecting tool for query: '{query}'")

        # Check each tool to see if it can handle the query
        suitable_tools = []
        for tool in self.tools:
            can_handle = tool.can_handle(query)
            logger.info(f"ToolManager: {tool.name} can_handle = {can_handle}")
            if can_handle:
                suitable_tools.append(tool)
                logger.info(f"ToolManager: Tool {tool.name} can handle the query")

        # If specific tools can handle it, prioritize them
        if suitable_tools:
            # Priority order: GoogleSheets first (for data queries), then Gmail, then Dictionary, then others, WebSearch last
            priority_order = ["GoogleSheets", "Gmail", "Dictionary", "Lyrics", "AdvancedAI", "Weather", "WebSearch"]

            for tool_name in priority_order:
                for tool in suitable_tools:
                    if tool.name == tool_name:
                        logger.info(f"ToolManager: Selected tool: {tool.name}")
                        return tool

        # If no specific tool can handle it, default to WebSearch as fallback
        for tool in self.tools:
            if tool.name == "WebSearch":
                logger.info(f"ToolManager: No specific tool found, defaulting to WebSearch for: '{query}'")
                return tool

        logger.warning(f"ToolManager: No suitable tool found for the query: '{query}'")
        return None
    
    async def execute_tool(self, tool: BaseTool, query: str, **kwargs) -> str:
        """Execute the selected tool with the given query"""
        try:
            logger.info(f"ToolManager: Executing tool {tool.name} with query: '{query}'")
            result = await tool.execute(query, **kwargs)
            logger.info(f"ToolManager: Tool {tool.name} execution completed, result length: {len(str(result))}")
            return result
        except Exception as e:
            logger.error(f"ToolManager: Error executing tool {tool.name}: {e}")
            return f"Sorry, I encountered an error while using the {tool.name.lower()} tool. Please try again."
    
    def needs_tool(self, query: str) -> bool:
        """Check if the query needs any tool"""
        return any(tool.can_handle(query) for tool in self.tools)
    
    def get_tool_suggestions(self, query: str) -> List[str]:
        """Get suggestions for which tools might be relevant"""
        suggestions = []
        for tool in self.tools:
            if tool.can_handle(query):
                suggestions.append(f"{tool.name}: {tool.get_description()}")
        return suggestions

"""
Google Sheets tool for reading and writing spreadsheet data
"""
import re
from typing import Dict, Any, Optional, List
from loguru import logger
from .base_tool import BaseTool
from .smithery_client import SmitheryClient
from .direct_sheets_client import get_real_sheet_data, search_real_sheet_data, update_real_sheet_data
from .google_sheets_api_client import update_real_sheet_data_enhanced
from .alternative_sheets_updater import update_with_alternative_method, apply_session_updates
from config import config


class GoogleSheetsClient(SmitheryClient):
    """Client for Google Sheets MCP server via Smithery"""

    def __init__(self):
        super().__init__("https://server.smithery.ai/@modelcontextprotocol/google-sheets")
    
    async def read_sheet(self, spreadsheet_id: str, range_name: str = "A:Z") -> Optional[Dict[str, Any]]:
        """Read data from Google Sheets"""
        return await self.call_tool("read_sheet", {
            "spreadsheet_id": spreadsheet_id,
            "range": range_name
        })
    
    async def write_sheet(self, spreadsheet_id: str, range_name: str, values: List[List[str]]) -> Optional[Dict[str, Any]]:
        """Write data to Google Sheets"""
        return await self.call_tool("write_sheet", {
            "spreadsheet_id": spreadsheet_id,
            "range": range_name,
            "values": values
        })
    
    async def append_sheet(self, spreadsheet_id: str, range_name: str, values: List[List[str]]) -> Optional[Dict[str, Any]]:
        """Append data to Google Sheets"""
        return await self.call_tool("append_sheet", {
            "spreadsheet_id": spreadsheet_id,
            "range": range_name,
            "values": values
        })
    
    async def search_sheet(self, spreadsheet_id: str, search_term: str, range_name: str = "A:Z") -> Optional[Dict[str, Any]]:
        """Search for data in Google Sheets"""
        return await self.call_tool("search_sheet", {
            "spreadsheet_id": spreadsheet_id,
            "search_term": search_term,
            "range": range_name
        })


class GoogleSheetsTool(BaseTool):
    """Tool for Google Sheets operations"""
    
    def __init__(self):
        super().__init__(
            tool_url="https://server.smithery.ai/@modelcontextprotocol/google-sheets",
            name="GoogleSheets"
        )
        self.description = "Read, write, and search Google Sheets data"
        
        # Keywords that indicate Google Sheets queries
        self.sheets_keywords = [
            "sheet", "spreadsheet", "google sheet", "sheet data", "spreadsheet data",
            "my sheet", "my google sheet", "my spreadsheet", "my data",
            "employee", "customer", "contact", "list", "database", "record",
            "find in sheet", "search sheet", "give me", "show me", "get my",
            "update", "change", "modify", "edit"  # Add update keywords
        ]
        
        # Common sheet operations
        self.operation_patterns = [
            r"show.*sheet",
            r"give.*me.*sheet",
            r"give.*me.*data",
            r"get.*my.*sheet",
            r"get.*my.*data",
            r"my.*sheet.*data",
            r"my.*google.*sheet",
            r"read.*sheet",
            r"find.*in.*sheet",
            r"search.*sheet",
            r"get.*from.*sheet",
            r"sheet.*data",
            r"spreadsheet.*data",
            r"employee.*data",
            r"customer.*data",
            r"update.*sheet",
            r"update.*my.*sheet",
            r"change.*sheet",
            r"modify.*sheet",
            r"edit.*sheet",
            r"update.*data",
            r"change.*data",
            r"modify.*data",
            r"edit.*data"
        ]
    
    def can_handle(self, query: str) -> bool:
        """Check if this tool can handle the query"""
        query_lower = query.lower()

        # Check for sheets keywords
        if any(keyword in query_lower for keyword in self.sheets_keywords):
            return True

        # Check for operation patterns
        for pattern in self.operation_patterns:
            if re.search(pattern, query_lower):
                return True

        # Special check for update operations with names (likely sheet updates)
        update_with_name_patterns = [
            r"update\s+\w+.*email",
            r"change\s+\w+.*email",
            r"modify\s+\w+.*email",
            r"edit\s+\w+.*email"
        ]
        for pattern in update_with_name_patterns:
            if re.search(pattern, query_lower):
                return True

        return False

    def get_description(self) -> str:
        """Get tool description"""
        return "Google Sheets: Read, write, and search spreadsheet data including employee records, customer information, and other tabular data"
    
    async def execute(self, query: str, **kwargs) -> str:
        """Execute Google Sheets operations"""
        try:
            operation, params = self._parse_sheets_query(query)
            logger.info(f"Executing Google Sheets operation: {operation}")
            
            # Try direct Google Sheets API first (if Sheet ID is configured)
            if config.GOOGLE_SHEETS_ID and config.GOOGLE_SHEETS_ID != "your_sheet_id_here":
                try:
                    logger.info("Using direct Google Sheets API")
                    if operation == "update":
                        result = await self._handle_update_operation(params)
                        if result:
                            return result
                    elif operation == "search" and params.get("search_term"):
                        result = await search_real_sheet_data(
                            params["spreadsheet_id"],
                            params["search_term"],
                            params["range"]
                        )
                    else:
                        result = await get_real_sheet_data(
                            params["spreadsheet_id"],
                            params["range"]
                        )

                        # Apply any session updates
                        result = apply_session_updates(result, params["spreadsheet_id"])

                    if result:
                        if "error" in result:
                            # Sheet is not accessible
                            error_msg = result.get('message', 'The sheet is not publicly accessible.')
                            logger.error(f"Google Sheets access error: {error_msg}")
                            return f"❌ **Google Sheets Access Error**\n\n{error_msg}\n\n💡 **To fix this:**\n1. Open your Google Sheet\n2. Click the 'Share' button (top right)\n3. Click 'Change to anyone with the link'\n4. Set permission to 'Viewer'\n5. Click 'Done'\n\nAfter making it public, try again!"
                        elif "values" in result:
                            formatted = self._format_sheets_response(result, operation, params)
                            logger.info(f"Formatted Google Sheets response: {len(formatted)} characters, {len(result.get('values', []))} rows")
                            return formatted
                        else:
                            logger.warning(f"Unexpected result format: {list(result.keys())}")
                            return f"⚠️ **Unexpected Response**\n\nReceived data but in unexpected format. Keys: {list(result.keys())}"
                except Exception as e:
                    logger.warning(f"Direct Google Sheets API failed: {e}")

            # Try Smithery Google Sheets MCP as backup
            if (config.SMITHERY_API_TOKEN and
                config.SMITHERY_API_TOKEN != "your_smithery_api_token_here"):
                try:
                    async with GoogleSheetsClient() as client:
                        result = await self._execute_sheets_operation(client, operation, params)
                        if result and "values" in result:
                            return self._format_sheets_response(result, operation, params)
                except Exception as e:
                    logger.warning(f"Smithery Google Sheets API failed: {e}")

            # All methods failed - return error
            logger.error("All Google Sheets access methods failed")
            if operation == "update":
                return "❌ **Google Sheets Update Failed**\n\nCould not access the Google Sheet to perform update. Please ensure:\n1. The sheet is publicly accessible (Share > Anyone with link > Viewer), or\n2. GOOGLE_SHEETS_API_KEY is set in .env file with proper permissions"
            else:
                return f"❌ **Google Sheets Access Error**\n\nCould not access the Google Sheet for: {query}\n\n**To fix this:**\n1. Make the sheet public: Share > 'Anyone with the link' > Viewer\n2. Or set GOOGLE_SHEETS_API_KEY in .env file\n3. Ensure GOOGLE_SHEETS_ID is set correctly in .env"
                
        except Exception as e:
            logger.error(f"Error in Google Sheets tool: {e}")
            return "Sorry, I encountered an error while accessing Google Sheets. Please try again."
    
    def _parse_sheets_query(self, query: str) -> tuple:
        """Parse the query to determine operation and parameters"""
        query_lower = query.lower()

        # Default parameters
        operation = "read"
        params = {
            "spreadsheet_id": config.GOOGLE_SHEETS_ID or "",  # Use configured sheet ID from environment
            "range": "A:Z",
            "search_term": None,
            "update_data": None
        }

        # Determine operation type
        if any(word in query_lower for word in ["update", "change", "modify", "edit"]):
            operation = "update"
            # Parse update request - looking for patterns like "update X to Y" or "change X email to Y"
            update_patterns = [
                r"update\s+(?:email\s+of\s+)?(\w+)(?:\s+in\s+sheet)?\s+to\s+(.+?)(?:\s|$)",  # "update email of vaishalee in sheet to X"
                r"update\s+(\w+)\s+email(?:\s+in\s+sheet)?\s+to\s+(.+?)(?:\s|$)",  # "update vaishalee email in sheet to X"
                r"update\s+(\w+)(?:\s+in\s+sheet)?\s+to\s+(.+?)(?:\s|$)",  # "update vaishalee in sheet to X"
                r"change\s+(?:email\s+of\s+)?(\w+)(?:\s+in\s+sheet)?\s+to\s+(.+?)(?:\s|$)",
                r"change\s+(\w+)\s+email(?:\s+in\s+sheet)?\s+to\s+(.+?)(?:\s|$)",
                r"modify\s+(?:email\s+of\s+)?(\w+)(?:\s+in\s+sheet)?\s+to\s+(.+?)(?:\s|$)",
                r"edit\s+(?:email\s+of\s+)?(\w+)(?:\s+in\s+sheet)?\s+to\s+(.+?)(?:\s|$)"
            ]
            for pattern in update_patterns:
                match = re.search(pattern, query_lower)
                if match:
                    search_term = match.group(1).strip()
                    new_value = match.group(2).strip()
                    params["search_term"] = search_term
                    params["update_data"] = {
                        "field": "email" if "email" in query_lower else "auto_detect",
                        "new_value": new_value
                    }
                    break
        elif any(word in query_lower for word in ["search", "find", "look for"]):
            operation = "search"
            # Extract search term
            search_patterns = [
                r"search.*?for\s+([^.?!]+)",
                r"find\s+([^.?!]+)",
                r"look.*?for\s+([^.?!]+)"
            ]
            for pattern in search_patterns:
                match = re.search(pattern, query_lower)
                if match:
                    params["search_term"] = match.group(1).strip()
                    break

        # Use configured sheet ID if available, otherwise keep default
        if not params["spreadsheet_id"] and config.GOOGLE_SHEETS_ID:
            params["spreadsheet_id"] = config.GOOGLE_SHEETS_ID

        return operation, params
    
    async def _execute_sheets_operation(self, client, operation: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute the sheets operation"""
        if operation == "search" and params.get("search_term"):
            return await client.search_sheet(
                params["spreadsheet_id"],
                params["search_term"],
                params["range"]
            )
        else:
            return await client.read_sheet(
                params["spreadsheet_id"],
                params["range"]
            )
    
    def _format_sheets_response(self, data: Dict[str, Any], operation: str, params: Dict[str, Any]) -> str:
        """Format the sheets response"""
        try:
            values = data.get("values", [])
            if not values:
                logger.warning("No values in sheet data")
                return "No data found in the Google Sheet."
            
            logger.info(f"Formatting {len(values)} rows from Google Sheet")
            
            # Format as table
            response = f"📊 **Google Sheets Data**\n\n"
            
            if operation == "search":
                response += f"🔍 **Search Results for: '{params.get('search_term', '')}'**\n\n"
            
            # Add table headers and data
            if len(values) > 0:
                headers = values[0]
                logger.info(f"Headers: {headers}")
                response += "| " + " | ".join(str(h) for h in headers) + " |\n"
                response += "|" + "|".join(["---"] * len(headers)) + "|\n"
                
                # Add data rows (limit to 10 for readability)
                data_rows = values[1:11]  # Skip header, show max 10 rows
                logger.info(f"Adding {len(data_rows)} data rows to response")
                for row in data_rows:
                    # Pad row to match header length
                    padded_row = row + [""] * (len(headers) - len(row))
                    # Convert all cells to strings and handle None values
                    formatted_row = [str(cell) if cell is not None else "" for cell in padded_row]
                    response += "| " + " | ".join(formatted_row) + " |\n"
                
                if len(values) > 11:
                    response += f"\n*... and {len(values) - 11} more rows*\n"
            
            logger.info(f"Formatted response: {len(response)} characters")
            return response
            
        except Exception as e:
            logger.error(f"Error formatting sheets response: {e}")
            return "Retrieved Google Sheets data, but there was an error formatting the response."

    async def _handle_update_operation(self, params: Dict[str, Any]) -> Optional[str]:
        """Handle update operations for real Google Sheets"""
        try:
            search_term = params.get("search_term", "")
            update_data = params.get("update_data", {})
            new_value = update_data.get("new_value", "")
            field = update_data.get("field", "email")
            spreadsheet_id = params.get("spreadsheet_id", config.GOOGLE_SHEETS_ID)

            logger.info(f"Processing update: {search_term} -> {field}: {new_value}")

            # Try enhanced update function first (with API key)
            result = await update_real_sheet_data_enhanced(spreadsheet_id, search_term, field, new_value)

            # If it's still simulated, try alternative method
            if "simulated" in result.lower():
                logger.info("API update was simulated, trying alternative method")
                result = await update_with_alternative_method(spreadsheet_id, search_term, field, new_value)

            return result

        except Exception as e:
            logger.error(f"Error in update operation: {e}")
            return None


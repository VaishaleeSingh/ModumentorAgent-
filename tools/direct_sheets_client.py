"""
Direct Google Sheets API client using Google Sheets API v4
"""
import aiohttp
import json
from typing import Dict, Any, Optional, List
from loguru import logger
from config import config


class DirectSheetsClient:
    """Direct Google Sheets API client"""
    
    def __init__(self):
        self.base_url = "https://sheets.googleapis.com/v4/spreadsheets"
    
    async def read_sheet(self, spreadsheet_id: str, range_name: str = "A:Z") -> Optional[Dict[str, Any]]:
        """Read data from Google Sheets using API key first, then CSV export"""
        try:
            if not spreadsheet_id or not spreadsheet_id.strip():
                logger.error("No spreadsheet ID provided")
                return {
                    "error": "No spreadsheet ID",
                    "message": "Google Sheet ID is required. Set GOOGLE_SHEETS_ID in .env file.",
                    "values": None
                }
            
            # Try Google Sheets API first if API key is available
            if config.GOOGLE_SHEETS_API_KEY and config.GOOGLE_SHEETS_API_KEY.strip():
                try:
                    logger.info(f"Trying Google Sheets API for sheet: {spreadsheet_id}")
                    api_url = f"{self.base_url}/{spreadsheet_id}/values/{range_name}"
                    params = {"key": config.GOOGLE_SHEETS_API_KEY}
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(api_url, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                if data.get("values"):
                                    logger.info(f"Successfully fetched {len(data['values'])} rows via Google Sheets API")
                                    return data
                                else:
                                    logger.warning("API returned no values")
                            else:
                                error_text = await response.text()
                                logger.warning(f"Google Sheets API failed: HTTP {response.status}")
                except Exception as e:
                    logger.warning(f"Google Sheets API error: {e}, trying CSV export")
            
            # Fallback to CSV export method - try multiple gid values
            logger.info(f"Trying CSV export for sheet: {spreadsheet_id}")
            # Try gid=0 first (first sheet), then try without gid parameter
            csv_urls = [
                f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid=0",
                f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
            ]
            
            for csv_url in csv_urls:
            
                async with aiohttp.ClientSession() as session:
                    async with session.get(csv_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            
                            # Check if we got HTML instead of CSV (means sheet is private)
                            if content.strip().startswith('<!DOCTYPE') or content.strip().startswith('<html'):
                                logger.warning(f"Received HTML instead of CSV (sheet is private): {csv_url}")
                                continue  # Try next URL
                            
                            if not content or not content.strip():
                                logger.warning("Sheet data is empty")
                                continue  # Try next URL

                            # Parse CSV content into values array with proper CSV handling
                            values = self._parse_csv_content(content)

                            if values:
                                logger.info(f"Successfully fetched {len(values)} rows from Google Sheet via CSV: {spreadsheet_id}")
                                return {
                                    "values": values,
                                    "range": range_name,
                                    "majorDimension": "ROWS"
                                }
                            else:
                                logger.warning("No data parsed from CSV")
                                continue  # Try next URL
                        elif response.status == 400 or response.status == 403:
                            # Sheet is not publicly accessible
                            logger.warning(f"Sheet access denied: HTTP {response.status} for {csv_url}")
                            continue  # Try next URL
                        else:
                            logger.warning(f"Failed to fetch sheet data: HTTP {response.status} for {csv_url}")
                            continue  # Try next URL
            
            # If all URLs failed, return error
            logger.error("All CSV export attempts failed - sheet is not publicly accessible")
            return {
                "error": "Sheet not publicly accessible",
                "message": f"Google Sheet (ID: {spreadsheet_id[:20]}...) is not accessible. Make it public: Share > 'Anyone with the link' > Viewer, or set GOOGLE_SHEETS_API_KEY in .env",
                "values": None
            }

        except Exception as e:
            logger.error(f"Error reading sheet: {e}", exc_info=True)
            return {
                "error": "Sheet read error",
                "message": f"Failed to read Google Sheet: {str(e)}",
                "values": None
            }
    
    def _parse_csv_content(self, content: str) -> List[List[str]]:
        """Parse CSV content properly handling quoted fields and commas"""
        import csv
        import io
        
        values = []
        try:
            # Use Python's csv module for proper parsing
            csv_reader = csv.reader(io.StringIO(content))
            for row in csv_reader:
                if row:  # Skip completely empty rows
                    # Clean up cells (remove extra whitespace, handle None values)
                    cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                    values.append(cleaned_row)
        except Exception as e:
            logger.error(f"Error parsing CSV with csv module: {e}, trying simple parsing")
            # Fallback to simple parsing if csv module fails
            lines = content.strip().split('\n')
            for line in lines:
                if line.strip():
                    # Simple CSV parsing (handles basic cases)
                    row = [cell.strip('"').strip().replace('\r', '') for cell in line.split(',')]
                    if row:
                        values.append(row)
        
        return values

    async def search_sheet(self, spreadsheet_id: str, search_term: str, range_name: str = "A:Z") -> Optional[Dict[str, Any]]:
        """Search for data in Google Sheets"""
        try:
            # Get all data first
            data = await self.read_sheet(spreadsheet_id, range_name)
            if not data or "values" not in data:
                return None
            
            # Filter results based on search term
            values = data["values"]
            if not values:
                return data
            
            headers = values[0]
            filtered_results = [headers]  # Keep headers
            
            # Search through all rows
            for row in values[1:]:
                if any(search_term.lower() in str(cell).lower() for cell in row):
                    filtered_results.append(row)
            
            return {
                "values": filtered_results,
                "range": range_name,
                "majorDimension": "ROWS",
                "search_term": search_term
            }
            
        except Exception as e:
            logger.error(f"Error searching sheet: {e}")
            return None


class GoogleSheetsAPISetup:
    """Helper for setting up Google Sheets API access"""
    
    @staticmethod
    def get_setup_instructions():
        """Get instructions for setting up Google Sheets API"""
        return """
🔧 To Access Your Real Google Sheets Data:

📋 Option 1: Make Sheet Public (Quick Setup)
1. Open your Google Sheet
2. Click "Share" button (top right)
3. Click "Change to anyone with the link"
4. Set permission to "Viewer"
5. Copy the link - your bot can now read it!

📋 Option 2: Google Sheets API (Full Access)
1. Go to Google Cloud Console (console.cloud.google.com)
2. Create a new project or select existing
3. Enable Google Sheets API
4. Create credentials (Service Account)
5. Download JSON key file
6. Share your sheet with the service account email
7. Add the JSON key to your bot configuration

🎯 Make sure your sheet is accessible and GOOGLE_SHEETS_ID is set correctly!
"""


# Integration with existing Google Sheets tool
async def get_real_sheet_data(spreadsheet_id: str, range_name: str = "A:Z") -> Optional[Dict[str, Any]]:
    """Get real sheet data using direct API"""
    client = DirectSheetsClient()
    return await client.read_sheet(spreadsheet_id, range_name)


async def search_real_sheet_data(spreadsheet_id: str, search_term: str, range_name: str = "A:Z") -> Optional[Dict[str, Any]]:
    """Search real sheet data using direct API"""
    client = DirectSheetsClient()
    return await client.search_sheet(spreadsheet_id, search_term, range_name)


async def update_real_sheet_data(spreadsheet_id: str, search_term: str, field: str, new_value: str) -> Optional[str]:
    """Update real sheet data (simulated for now)"""
    try:
        # For now, we'll simulate the update since we need proper Google Sheets API credentials
        # In a real implementation, you'd use the Google Sheets API with OAuth2 to update the actual sheet

        # First, search for the record
        client = DirectSheetsClient()
        data = await client.search_sheet(spreadsheet_id, search_term)

        if data and "values" in data and len(data["values"]) > 1:
            # Found matching records
            headers = data["values"][0] if data["values"] else []
            matching_rows = data["values"][1:] if len(data["values"]) > 1 else []

            if matching_rows:
                return f"""✅ **Update Successful!**

📊 **Found and updated record for: {search_term}**
• **Field:** {field}
• **New value:** {new_value}
• **Rows affected:** {len(matching_rows)}

🔄 **Updated data:**
{_format_updated_rows(headers, matching_rows, field, new_value)}

💡 **Note:** This is a simulated update. To enable real updates, configure Google Sheets API with write permissions and OAuth2 authentication."""
            else:
                return f"❌ No records found matching '{search_term}' in the sheet."
        else:
            return f"❌ Could not access sheet data for update operation."

    except Exception as e:
        logger.error(f"Error in update operation: {e}")
        return f"❌ Error updating sheet: {e}"


def _format_updated_rows(headers: List[str], rows: List[List[str]], field: str, new_value: str) -> str:
    """Format updated rows for display"""
    try:
        # Find the field index
        field_index = -1
        for i, header in enumerate(headers):
            if header.lower() == field.lower():
                field_index = i
                break

        if field_index == -1:
            return f"Field '{field}' not found in sheet headers: {', '.join(headers)}"

        result = []
        for row in rows[:3]:  # Show first 3 matching rows
            if len(row) > field_index:
                old_value = row[field_index]
                result.append(f"  • {headers[0] if headers else 'Row'}: {row[0] if row else 'N/A'} | {field}: {old_value} → {new_value}")

        return "\n".join(result)

    except Exception as e:
        return f"Error formatting update results: {e}"

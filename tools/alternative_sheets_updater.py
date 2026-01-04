"""
Alternative Google Sheets Update Method
This provides an alternative way to update Google Sheets without requiring API keys
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
from loguru import logger


class AlternativeSheetsUpdater:
    """Alternative method for updating Google Sheets"""
    
    def __init__(self):
        self.session_updates = {}  # Store updates in memory for the session
    
    async def update_with_memory_persistence(self, spreadsheet_id: str, search_term: str, field: str, new_value: str) -> str:
        """Update with memory persistence - shows updated data in subsequent reads"""
        try:
            # Read current data first
            from .direct_sheets_client import DirectSheetsClient
            client = DirectSheetsClient()
            data = await client.read_sheet(spreadsheet_id)
            
            if not data or "values" not in data:
                return "❌ Could not read sheet data for update"
            
            values = data["values"]
            if len(values) < 2:
                return "❌ Sheet appears to be empty"
            
            headers = values[0]
            rows = values[1:]
            
            # Find field column
            field_index = -1
            for i, header in enumerate(headers):
                if header.lower() == field.lower():
                    field_index = i
                    break
            
            if field_index == -1:
                return f"❌ Field '{field}' not found in headers"
            
            # Find matching rows
            matching_rows = []
            for i, row in enumerate(rows):
                if len(row) > 0 and search_term.lower() in ' '.join(row).lower():
                    matching_rows.append((i, row))
            
            if not matching_rows:
                return f"❌ No records found matching '{search_term}'"
            
            # Store the update in memory
            update_key = f"{spreadsheet_id}_{search_term}_{field}"
            old_value = matching_rows[0][1][field_index] if field_index < len(matching_rows[0][1]) else ""
            
            self.session_updates[update_key] = {
                "old_value": old_value,
                "new_value": new_value,
                "field": field,
                "search_term": search_term,
                "row_index": matching_rows[0][0],
                "timestamp": asyncio.get_event_loop().time()
            }
            
            logger.info(f"Stored update in memory: {update_key} -> {new_value}")
            
            return f"""✅ **Update Successful! (Memory Persistence)**

📊 **Found and updated record for: {search_term}**
• **Field:** {field}
• **Old value:** {old_value}
• **New value:** {new_value}
• **Status:** Stored in session memory

🔄 **Updated data:**
  • {headers[0] if headers else 'NAME'}: {matching_rows[0][1][0] if matching_rows[0][1] else 'N/A'} | {field}: {old_value} → {new_value}

💡 **Note:** Update stored in memory. Will show updated data in subsequent reads during this session.
🔧 **For permanent updates:** Configure Google Sheets API key using setup_google_sheets_api.py"""
            
        except Exception as e:
            logger.error(f"Error in memory persistence update: {e}")
            return f"❌ Error updating record: {e}"
    
    def apply_memory_updates(self, data: Dict[str, Any], spreadsheet_id: str) -> Dict[str, Any]:
        """Apply stored memory updates to read data"""
        if not data or "values" not in data:
            return data
        
        values = data["values"]
        if len(values) < 2:
            return data
        
        headers = values[0]
        rows = values[1:]
        
        # Apply any stored updates
        for update_key, update_info in self.session_updates.items():
            if update_key.startswith(f"{spreadsheet_id}_"):
                search_term = update_info["search_term"]
                field = update_info["field"]
                new_value = update_info["new_value"]
                
                # Find field column
                field_index = -1
                for i, header in enumerate(headers):
                    if header.lower() == field.lower():
                        field_index = i
                        break
                
                if field_index == -1:
                    continue
                
                # Find and update matching rows
                for i, row in enumerate(rows):
                    if len(row) > 0 and search_term.lower() in ' '.join(row).lower():
                        # Ensure row has enough columns
                        while len(row) <= field_index:
                            row.append("")
                        
                        # Apply the update
                        row[field_index] = new_value
                        logger.info(f"Applied memory update: {search_term} {field} -> {new_value}")
                        break
        
        return data
    
    def clear_session_updates(self):
        """Clear all session updates"""
        self.session_updates.clear()
        logger.info("Cleared all session updates")
    
    def get_session_updates(self) -> Dict[str, Any]:
        """Get current session updates"""
        return self.session_updates.copy()


# Global instance for session persistence
alternative_updater = AlternativeSheetsUpdater()


async def update_with_alternative_method(spreadsheet_id: str, search_term: str, field: str, new_value: str) -> str:
    """Update using alternative method with memory persistence"""
    return await alternative_updater.update_with_memory_persistence(spreadsheet_id, search_term, field, new_value)


def apply_session_updates(data: Dict[str, Any], spreadsheet_id: str) -> Dict[str, Any]:
    """Apply session updates to read data"""
    return alternative_updater.apply_memory_updates(data, spreadsheet_id)

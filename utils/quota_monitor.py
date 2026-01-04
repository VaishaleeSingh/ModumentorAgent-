"""
Quota monitoring utility for Gemini API
"""
import time
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any
from loguru import logger
from config import config


class QuotaMonitor:
    """Monitor Gemini API quota usage"""
    
    def __init__(self):
        self.quota_file = "quota_usage.json"
        self.usage_data = self._load_usage_data()
    
    def _load_usage_data(self) -> Dict[str, Any]:
        """Load usage data from file"""
        try:
            if os.path.exists(self.quota_file):
                with open(self.quota_file, 'r') as f:
                    data = json.load(f)
                    # Check if we need to reset for a new day
                    if self._should_reset_quota(data):
                        logger.info("Resetting quota for new day")
                        return self._get_default_usage_data()
                    return data
            else:
                return self._get_default_usage_data()
        except Exception as e:
            logger.error(f"Error loading quota data: {e}")
            return self._get_default_usage_data()
    
    def _get_default_usage_data(self) -> Dict[str, Any]:
        """Get default usage data structure"""
        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "requests_made": 0,
            "quota_limit": config.GEMINI_QUOTA_LIMIT,
            "last_request_time": None,
            "quota_exceeded": False
        }
    
    def _should_reset_quota(self, data: Dict[str, Any]) -> bool:
        """Check if quota should be reset for a new day"""
        try:
            stored_date = data.get("date")
            current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            return stored_date != current_date
        except Exception:
            return True
    
    def _save_usage_data(self):
        """Save usage data to file"""
        try:
            with open(self.quota_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving quota data: {e}")
    
    def increment_request(self):
        """Increment request count"""
        self.usage_data["requests_made"] += 1
        self.usage_data["last_request_time"] = datetime.now(timezone.utc).isoformat()
        
        # Check if quota exceeded
        if self.usage_data["requests_made"] >= self.usage_data["quota_limit"]:
            self.usage_data["quota_exceeded"] = True
            logger.warning(f"Gemini API quota exceeded! Used: {self.usage_data['requests_made']}/{self.usage_data['quota_limit']}")
        
        self._save_usage_data()
    
    def can_make_request(self) -> bool:
        """Check if we can make a request without exceeding quota"""
        return not self.usage_data["quota_exceeded"]
    
    def get_usage_info(self) -> Dict[str, Any]:
        """Get current usage information"""
        return {
            "requests_made": self.usage_data["requests_made"],
            "quota_limit": self.usage_data["quota_limit"],
            "remaining": max(0, self.usage_data["quota_limit"] - self.usage_data["requests_made"]),
            "quota_exceeded": self.usage_data["quota_exceeded"],
            "last_request": self.usage_data.get("last_request_time"),
            "date": self.usage_data["date"]
        }
    
    def get_usage_message(self) -> str:
        """Get a user-friendly usage message"""
        info = self.get_usage_info()
        
        if info["quota_exceeded"]:
            return f"⚠️ **API Quota Exceeded**\n\n" \
                   f"📊 **Usage:** {info['requests_made']}/{info['quota_limit']} requests\n" \
                   f"🕐 **Date:** {info['date']}\n" \
                   f"🔄 **Reset:** Tomorrow at midnight UTC\n\n" \
                   f"💡 **Note:** Tool-based queries (weather, dictionary, search) still work!"
        else:
            remaining = info["remaining"]
            if remaining <= 5:
                status = "🔴 Critical"
            elif remaining <= 15:
                status = "🟡 Warning"
            else:
                status = "🟢 Good"
            
            return f"📊 **API Usage Status: {status}**\n\n" \
                   f"📈 **Used:** {info['requests_made']}/{info['quota_limit']} requests\n" \
                   f"📉 **Remaining:** {remaining} requests\n" \
                   f"🕐 **Date:** {info['date']}"
    
    def reset_quota(self):
        """Manually reset quota (for testing)"""
        self.usage_data = self._get_default_usage_data()
        self._save_usage_data()
        logger.info("Quota manually reset")


# Global quota monitor instance
quota_monitor = QuotaMonitor() 
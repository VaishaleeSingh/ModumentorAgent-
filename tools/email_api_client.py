"""
Email API client using Resend API (no password required - just API key)
"""
import aiohttp
import json
from typing import Dict, Any, Optional
from loguru import logger
from config import config


class EmailAPIClient:
    """Email API client using Resend (no password required)"""
    
    def __init__(self):
        self.api_key = config.RESEND_API_KEY
        self.from_email = config.EMAIL_FROM
        self.base_url = "https://api.resend.com/emails"
    
    async def send_email(self, to: str, subject: str, body: str, from_email: str = None) -> Optional[Dict[str, Any]]:
        """Send email via Resend API (no password required)"""
        try:
            if not self.api_key:
                logger.warning("RESEND_API_KEY not configured")
                return None
            
            if not to or not subject or not body:
                logger.error("Missing required email parameters")
                return None
            
            logger.info(f"Sending email via Resend API to {to}")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "from": from_email or self.from_email,
                "to": to,
                "subject": subject,
                "text": body
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Email sent successfully via Resend API: {result.get('id')}")
                        return {
                            'status': 'sent',
                            'to': to,
                            'subject': subject,
                            'message_id': result.get('id'),
                            'method': 'Resend API',
                            'demo': False
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Resend API error: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error sending email via Resend API: {e}", exc_info=True)
            return None


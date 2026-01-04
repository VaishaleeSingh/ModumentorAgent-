"""
Real Gmail API client using Google Gmail API v1
"""
import json
import base64
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from loguru import logger
import aiohttp
import asyncio
from config import config


class GmailAPIClient:
    """Real Gmail API client using service account"""
    
    def __init__(self):
        self.base_url = "https://gmail.googleapis.com/gmail/v1"
        self.credentials_file = "gmail_credentials.json"
        self.access_token = None
        self.token_expires = 0
    
    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token using service account"""
        try:
            if not os.path.exists(self.credentials_file):
                logger.warning(f"Gmail credentials file not found: {self.credentials_file}")
                return None
            
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)
            
            # For service accounts, we need to create a JWT and exchange it for an access token
            # This is a simplified version - in production, use google-auth library
            
            import time
            import jwt
            
            # Create JWT payload
            now = int(time.time())
            payload = {
                'iss': credentials['client_email'],
                'scope': 'https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly',
                'aud': 'https://oauth2.googleapis.com/token',
                'exp': now + 3600,
                'iat': now
            }
            
            # Sign JWT with private key
            private_key = credentials['private_key']
            token = jwt.encode(payload, private_key, algorithm='RS256')
            
            # Exchange JWT for access token
            async with aiohttp.ClientSession() as session:
                data = {
                    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                    'assertion': token
                }
                
                async with session.post('https://oauth2.googleapis.com/token', data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.access_token = result.get('access_token')
                        self.token_expires = now + result.get('expires_in', 3600)
                        logger.info("Successfully obtained Gmail API access token")
                        return self.access_token
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get access token: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting Gmail access token: {e}")
            return None
    
    async def send_email(self, to: str, subject: str, body: str, from_email: str = None) -> Optional[Dict[str, Any]]:
        """Send email via Gmail API"""
        try:
            # Get access token
            token = await self._get_access_token()
            if not token:
                return None

            # Get service account email
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)
            service_email = credentials.get('client_email', config.GMAIL_ADDRESS)

            # Create email message
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message['from'] = service_email

            # Add body
            message.attach(MIMEText(body, 'plain'))

            # Add signature
            signature = f"\n\n--\nSent via ModuMentor Bot\nService Account: {service_email}"
            message.attach(MIMEText(signature, 'plain'))

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Send via Gmail API
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }

                payload = {
                    'raw': raw_message
                }

                # Use service account email as "me"
                url = f"{self.base_url}/users/{service_email}/messages/send"
                
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Email sent successfully via Gmail API: {result.get('id')}")
                        return {
                            'status': 'sent',
                            'message_id': result.get('id'),
                            'to': to,
                            'subject': subject
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send email: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error sending email via Gmail API: {e}")
            return None
    
    async def read_emails(self, query: str = "", max_results: int = 10) -> Optional[Dict[str, Any]]:
        """Read emails from Gmail"""
        try:
            token = await self._get_access_token()
            if not token:
                return None
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {token}'
                }
                
                params = {
                    'maxResults': max_results
                }
                if query:
                    params['q'] = query
                
                url = f"{self.base_url}/users/me/messages"
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        messages = result.get('messages', [])
                        
                        # Get details for each message
                        detailed_messages = []
                        for msg in messages[:max_results]:
                            msg_detail = await self._get_message_details(session, headers, msg['id'])
                            if msg_detail:
                                detailed_messages.append(msg_detail)
                        
                        return {
                            'emails': detailed_messages,
                            'total': len(detailed_messages)
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to read emails: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error reading emails: {e}")
            return None
    
    async def _get_message_details(self, session, headers, message_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific message"""
        try:
            url = f"{self.base_url}/users/me/messages/{message_id}"
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Extract relevant information
                    payload = result.get('payload', {})
                    headers_list = payload.get('headers', [])
                    
                    # Extract headers
                    subject = ""
                    from_email = ""
                    date = ""
                    
                    for header in headers_list:
                        name = header.get('name', '').lower()
                        value = header.get('value', '')
                        
                        if name == 'subject':
                            subject = value
                        elif name == 'from':
                            from_email = value
                        elif name == 'date':
                            date = value
                    
                    # Extract body (simplified)
                    body = self._extract_body(payload)
                    
                    return {
                        'id': message_id,
                        'subject': subject,
                        'from': from_email,
                        'date': date,
                        'body': body[:200] + "..." if len(body) > 200 else body,
                        'read': 'UNREAD' not in result.get('labelIds', [])
                    }
                        
        except Exception as e:
            logger.error(f"Error getting message details: {e}")
            return None
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload"""
        try:
            # Handle multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')
            
            # Handle single part messages
            elif payload.get('mimeType') == 'text/plain':
                data = payload.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')
            
            return "Email body could not be extracted"
            
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            return "Error extracting email body"

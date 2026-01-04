"""
SMTP Gmail client for sending emails via Gmail SMTP
This is a simpler alternative to Gmail API that works immediately
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from loguru import logger
from config import config


class SMTPGmailClient:
    """SMTP Gmail client for sending emails"""
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.gmail_address = config.GMAIL_ADDRESS
        self.gmail_app_password = config.GMAIL_APP_PASSWORD
        self.last_error = None
    
    async def send_email(self, to: str, subject: str, body: str, from_email: str = None) -> Optional[Dict[str, Any]]:
        """Send email via Gmail SMTP with custom content"""
        try:
            if not to or not subject or not body:
                logger.error(f"Missing required email parameters: to={bool(to)}, subject={bool(subject)}, body={bool(body)}")
                return None
            
            if not self.gmail_address or not self.gmail_app_password:
                logger.error(f"SMTP credentials not configured: address={'SET' if self.gmail_address else 'NOT SET'}, password={'SET' if self.gmail_app_password else 'NOT SET'}")
                return None
            
            logger.info(f"Creating email message: to={to}, subject={subject[:50]}")
            
            # Create message
            message = MIMEMultipart()
            message["From"] = from_email or self.gmail_address
            message["To"] = to
            message["Subject"] = subject
            
            # Combine body and signature
            full_body = body + f"\n\n--\nSent via ModuMentor Bot\nFrom: {self.gmail_address}"
            message.attach(MIMEText(full_body, "plain"))
            
            # Create secure connection and send email
            logger.info(f"Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}")
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                logger.info("Starting TLS...")
                server.starttls(context=context)
                logger.info(f"Logging in with: {self.gmail_address}")
                server.login(self.gmail_address, self.gmail_app_password)
                logger.info("Login successful, sending email...")
                
                text = message.as_string()
                server.sendmail(self.gmail_address, to, text)
                logger.info(f"Email sent successfully via SMTP to {to}")
            
            return {
                'status': 'sent',
                'to': to,
                'subject': subject,
                'message_id': f'smtp_{hash(text)}',
                'method': 'SMTP',
                'demo': False
            }
        
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"Authentication failed: {str(e)}. Check if GMAIL_APP_PASSWORD is correct and 2FA is enabled."
            logger.error(f"SMTP Authentication Error: {e}")
            logger.error("Check if GMAIL_APP_PASSWORD is correct and 2FA is enabled")
            self.last_error = error_msg
            # Raise to get better error reporting
            raise Exception(error_msg) from e
        except smtplib.SMTPException as e:
            error_msg = f"SMTP protocol error: {str(e)}"
            logger.error(f"SMTP Error: {e}")
            self.last_error = error_msg
            raise Exception(error_msg) from e
        except (ConnectionError, OSError) as e:
            error_msg = f"Connection error: {str(e)}. Check network connection and firewall."
            logger.error(f"SMTP Connection Error: {e}")
            self.last_error = error_msg
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Error sending email via SMTP: {e}", exc_info=True)
            self.last_error = error_msg
            raise
    
    async def read_emails(self, query: str = "", max_results: int = 10) -> Optional[Dict[str, Any]]:
        """SMTP doesn't support reading emails - return demo data"""
        return {
            'emails': [
                {
                    'subject': 'SMTP Demo - Reading not supported',
                    'from': 'system@modumentor.bot',
                    'body': 'SMTP only supports sending emails. Use Gmail API for reading.',
                    'date': '2024-01-21',
                    'read': True
                }
            ],
            'total': 1,
            'note': 'SMTP only supports sending emails'
        }


def get_smtp_setup_instructions():
    """Get instructions for setting up Gmail SMTP"""
    return """
🔧 Gmail SMTP Setup (Alternative to Gmail API)

📧 This is simpler than Gmail API and works immediately!

📋 Steps:
1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to: https://myaccount.google.com/security
   - Click "2-Step Verification"
   - Scroll down to "App passwords"
   - Generate password for "Mail"
   - Copy the 16-character password

3. Update your .env file:
   GMAIL_ADDRESS=your_email@gmail.com
   GMAIL_APP_PASSWORD=your_16_char_app_password

4. Restart your bot

✅ Pros:
- Simple setup (5 minutes)
- Works immediately
- No Google Cloud Console needed
- Sends from your actual Gmail

❌ Cons:
- Can't read emails (only send)
- Requires app password
- Less secure than OAuth2

💡 Perfect for: Testing and personal use
🏢 For production: Use Gmail API with proper OAuth2
"""



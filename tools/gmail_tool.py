"""
Gmail tool for sending and reading emails
"""
import re
from typing import Dict, Any, Optional, List
from loguru import logger
from .base_tool import BaseTool
from .smithery_client import SmitheryClient
from .direct_sheets_client import get_real_sheet_data
from config import config
import os


class GmailClient(SmitheryClient):
    """Client for Gmail MCP server via Smithery"""

    def __init__(self):
        super().__init__("https://server.smithery.ai/@modelcontextprotocol/gmail")
    
    async def send_email(self, to: str, subject: str, body: str, cc: str = None, bcc: str = None) -> Optional[Dict[str, Any]]:
        """Send an email via Gmail"""
        params = {
            "to": to,
            "subject": subject,
            "body": body
        }
        if cc:
            params["cc"] = cc
        if bcc:
            params["bcc"] = bcc
            
        return await self.call_tool("send_email", params)
    
    async def read_emails(self, query: str = "", max_results: int = 10) -> Optional[Dict[str, Any]]:
        """Read emails from Gmail"""
        return await self.call_tool("read_emails", {
            "query": query,
            "max_results": max_results
        })
    
    async def search_emails(self, search_term: str, max_results: int = 10) -> Optional[Dict[str, Any]]:
        """Search emails in Gmail"""
        return await self.call_tool("search_emails", {
            "search_term": search_term,
            "max_results": max_results
        })


class GmailToolFallback:
    """Fallback for Gmail when MCP is not available"""
    
    def __init__(self):
        self.demo_emails = [
            {
                "from": "john.doe@company.com",
                "subject": "Project Update",
                "body": "Hi, here's the latest update on our project...",
                "date": "2024-01-20",
                "read": True
            },
            {
                "from": "jane.smith@company.com", 
                "subject": "Meeting Tomorrow",
                "body": "Don't forget about our meeting tomorrow at 2 PM...",
                "date": "2024-01-19",
                "read": False
            }
        ]
    
    async def send_email(self, to: str, subject: str, body: str, cc: str = None, bcc: str = None) -> Dict[str, Any]:
        """Demo send email"""
        return {
            "status": "sent",
            "to": to,
            "subject": subject,
            "message_id": "demo_message_123",
            "note": "Demo email sent - Configure Gmail API for real email sending"
        }
    
    async def read_emails(self, query: str = "", max_results: int = 10) -> Dict[str, Any]:
        """Demo read emails"""
        return {
            "emails": self.demo_emails[:max_results],
            "total": len(self.demo_emails),
            "note": "Demo emails - Configure Gmail API for real email access"
        }
    
    async def search_emails(self, search_term: str, max_results: int = 10) -> Dict[str, Any]:
        """Demo search emails"""
        # Simple search simulation
        results = []
        for email in self.demo_emails:
            if (search_term.lower() in email["subject"].lower() or 
                search_term.lower() in email["body"].lower() or
                search_term.lower() in email["from"].lower()):
                results.append(email)
        
        return {
            "emails": results[:max_results],
            "search_term": search_term,
            "total": len(results),
            "note": "Demo search results - Configure Gmail API for real email search"
        }


class GmailTool(BaseTool):
    """Tool for Gmail operations"""
    
    def __init__(self):
        super().__init__(
            tool_url="https://server.smithery.ai/@modelcontextprotocol/gmail",
            name="Gmail"
        )
        self.description = "Send and read emails via Gmail"
        
        # Keywords that indicate Gmail queries
        self.gmail_keywords = [
            "email", "mail", "send email", "gmail", "inbox", "message",
            "send mail", "compose", "reply", "forward", "read email",
            "check email", "email someone", "mail to", "sick leave",
            "seeking leave", "leave request", "send message", "attached mail",
            "mail id", "email id"
        ]
        
        # Email operation patterns
        self.operation_patterns = [
            r"send.*email",
            r"send.*mail",
            r"email.*to",
            r"mail.*to",
            r"compose.*email",
            r"read.*email",
            r"check.*email",
            r"inbox",
            r"recent.*email",
            r"send.*message",
            r"mail.*as",
            r"mail.*id",
            r"attached.*mail"
        ]
    
    def can_handle(self, query: str) -> bool:
        """Check if this tool can handle the query"""
        query_lower = query.lower()

        # Check for Gmail keywords
        if any(keyword in query_lower for keyword in self.gmail_keywords):
            return True

        # Check for operation patterns
        for pattern in self.operation_patterns:
            if re.search(pattern, query_lower):
                return True

        return False

    def get_description(self) -> str:
        """Get tool description"""
        return "Gmail: Send and read emails, search inbox, compose messages, and manage email communications"
    
    async def execute(self, query: str, **kwargs) -> str:
        """Execute Gmail operations with LLM-generated content"""
        try:
            operation, params = self._parse_gmail_query(query)
            logger.info(f"Executing Gmail operation: {operation}")

            # Generate email content using LLM first
            if operation == "send":
                # Generate professional email content
                email_content = await self._generate_email_content(query, params)
                if email_content:
                    params["subject"] = email_content["subject"]
                    params["body"] = email_content["body"]
                else:
                    # Enhanced fallback with business templates
                    template_content = self._get_enhanced_business_email_template(query, params)
                    params["subject"] = template_content["subject"]
                    params["body"] = template_content["body"]

            # Lookup recipient email if needed
            if operation == "send":
                # Check if query mentions "sheet" or "attached mail" - get first email from sheet
                query_lower = query.lower()
                if ("sheet" in query_lower or "attached mail" in query_lower or "mail id" in query_lower) and not params.get("to"):
                    logger.info("Query mentions sheet - looking up email from Google Sheet")
                    email = await self._get_email_from_sheets()
                    if email:
                        params["to"] = email
                        logger.info(f"Found email from sheet: {email}")
                    else:
                        return "❌ **Could not find email in Google Sheet**\n\nPlease ensure:\n1. Your Google Sheet has an 'Email' or 'Company Email' column\n2. There is at least one row with an email address\n3. GOOGLE_SHEETS_ID is set correctly in .env"
                
                # Check if we have a recipient name but no email
                if "recipient_name" in params and not params.get("to"):
                    logger.info(f"Looking up email for recipient: {params['recipient_name']}")
                    email = await self._lookup_email_from_sheets(params["recipient_name"])
                    if email:
                        params["to"] = email
                        logger.info(f"Found email for {params['recipient_name']}: {email}")
                    else:
                        return f"❌ **Email Lookup Failed**\n\nCould not find email address for '{params['recipient_name']}' in your Google Sheet.\n\n**Please check:**\n1. The name is spelled correctly\n2. The person exists in your Google Sheet\n3. The sheet has 'Name' and 'Email' (or 'Company Email') columns\n4. GOOGLE_SHEETS_ID is set correctly in .env"
                
                # Validate that we have an email address
                if not params.get("to"):
                    return "❌ **Missing Email Address**\n\nPlease provide an email address or a name that exists in your Google Sheet.\n\n**Examples:**\n- \"send email to vaishalee about project update\"\n- \"send email to vaishalisinghsln5@gmail.com about meeting\"\n- \"send mail to attached mail id in sheet\""

            # Execute the email sending with LLM-generated content
            result = await self._execute_gmail_operation_with_content(operation, params)
            
            if result:
                return self._format_gmail_response(result, operation, params)
            else:
                # Provide more detailed error message
                error_msg = f"❌ **Email Sending Failed**\n\n"
                if not params.get("to"):
                    error_msg += "No recipient email address found.\n"
                if not params.get("subject"):
                    error_msg += "No email subject generated.\n"
                if not params.get("body"):
                    error_msg += "No email body generated.\n"
                error_msg += f"\n**Query:** {query}\n"
                error_msg += "\n**Please check:**\n"
                error_msg += "1. GMAIL_ADDRESS and GMAIL_APP_PASSWORD are set in .env\n"
                error_msg += "2. The recipient email was found in your Google Sheet\n"
                error_msg += "3. Email content was generated properly"
                logger.error(f"Gmail operation failed: operation={operation}, params={params}")
                return error_msg
                
        except Exception as e:
            logger.error(f"Error in Gmail tool: {e}")
            return "Sorry, I encountered an error while processing your email request."

    async def _execute_gmail_operation_with_content(self, operation: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute Gmail operation with LLM-generated content"""
        if operation == "send":
            to_email = params.get("to", "")
            subject = params.get("subject", "Message from AI Assistant")
            body = params.get("body", "This email was sent via your AI assistant.")
            
            if not to_email:
                logger.error("No recipient email address provided")
                return None
            
            logger.info(f"Attempting to send email to: {to_email}, subject: {subject[:50] if subject else 'None'}")
            
            # Try Email API first (Resend - no password required, just API key)
            if config.RESEND_API_KEY:
                try:
                    from .email_api_client import EmailAPIClient
                    logger.info(f"Using Resend API to send email to {to_email} (no password required)")
                    client = EmailAPIClient()
                    result = await client.send_email(to_email, subject, body)
                    if result:
                        logger.info(f"✅ Email sent successfully via Resend API to {to_email}")
                        result["method"] = "Resend API"
                        result["demo"] = False
                        result["status"] = "sent"
                        return result
                    else:
                        logger.warning("Resend API returned None, trying SMTP fallback")
                except Exception as e:
                    logger.warning(f"Resend API failed: {e}, trying SMTP fallback")
            
            # Try SMTP Gmail (if configured)
            has_smtp_config = config.GMAIL_ADDRESS and config.GMAIL_APP_PASSWORD
            logger.info(f"SMTP Configuration check: GMAIL_ADDRESS={'SET' if config.GMAIL_ADDRESS else 'NOT SET'}, GMAIL_APP_PASSWORD={'SET' if config.GMAIL_APP_PASSWORD else 'NOT SET'}")
            
            if has_smtp_config:
                try:
                    from .smtp_gmail_client import SMTPGmailClient
                    logger.info(f"Attempting to send email via SMTP to {to_email}")
                    client = SMTPGmailClient()
                    result = await client.send_email(to_email, subject, body)
                    if result:
                        logger.info(f"✅ Email sent successfully via SMTP to {to_email}")
                        result["method"] = "SMTP"
                        result["demo"] = False
                        result["status"] = "sent"
                        return result
                    else:
                        logger.error("SMTP Gmail returned None - email sending failed")
                        # Get more detailed error from SMTP client if available
                        smtp_error = getattr(client, 'last_error', None) or "SMTP connection or authentication failed"
                        # Don't fallback to demo, return error instead
                        return {
                            "status": "error",
                            "to": to_email,
                            "subject": subject,
                            "demo": False,
                            "error": f"SMTP email sending failed: {smtp_error}. Check Gmail credentials, App Password, and network connection."
                        }
                except Exception as e:
                    logger.error(f"SMTP Gmail failed with exception: {e}", exc_info=True)
                    # Return error instead of falling back to demo
                    return {
                        "status": "error",
                        "to": to_email,
                        "subject": subject,
                        "demo": False,
                        "error": f"SMTP error: {str(e)}"
                    }

            # Fallback to demo (simulation only - doesn't actually send)
            logger.warning("SMTP not configured - using demo mode (email not actually sent)")
            try:
                fallback_client = GmailToolFallback()
                result = await fallback_client.send_email(to_email, subject, body)
                if result:
                    # Mark as demo/simulation
                    result["demo"] = True
                    result["note"] = "⚠️ DEMO MODE: Email was NOT actually sent. Configure GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env to send real emails."
                    logger.warning(f"Demo email created (not sent) to {to_email}")
                    return result
                else:
                    logger.error("Fallback Gmail returned None, creating default result")
                    # Create a default result if fallback fails
                    return {
                        "status": "simulated",
                        "to": to_email,
                        "subject": subject,
                        "message_id": f"fallback_{hash(to_email + subject)}",
                        "demo": True,
                        "note": "⚠️ DEMO MODE: Email was NOT actually sent. Configure GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env to send real emails."
                    }
            except Exception as e:
                logger.error(f"Fallback Gmail failed: {e}", exc_info=True)
                # Return a result even if fallback fails
                return {
                    "status": "error",
                    "to": to_email,
                    "subject": subject,
                    "message_id": f"error_{hash(to_email + subject)}",
                    "demo": True,
                    "note": f"⚠️ Error: {str(e)}. Configure GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env to send real emails."
                }
        
        return None

    def _parse_gmail_query(self, query: str) -> tuple:
        """Parse Gmail query and extract parameters"""
        operation = "send"  # Default operation
        params = {}

        # Extract recipient email or name
        email_patterns = [
            r'to\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'mail\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'email\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        ]
        
        name_patterns = [
            r'send\s+(?:an?\s+)?(?:email|mail)\s+to\s+([A-Za-z\s]+?)(?:\s+(?:as|about|regarding|for|asking|saying)|$)',
            r'email\s+to\s+([A-Za-z\s]+?)(?:\s+(?:as|about|regarding|for|asking|saying)|$)',
            r'mail\s+to\s+([A-Za-z\s]+?)(?:\s+(?:as|about|regarding|for|asking|saying)|$)',
            r'send\s+(?:an?\s+)?(?:email|mail)\s+(?:to\s+)?([A-Za-z\s]+?)(?:\s+(?:as|about|regarding|for|asking|saying)|$)',
            r'to\s+([A-Za-z\s]+?)(?:\s+(?:as|about|regarding|for|asking|saying))',
            r'(?:send|email|mail)\s+([A-Za-z\s]+?)(?:\s+(?:as|about|regarding|for|asking|saying))',
            r'send\s+(?:an?\s+)?(?:email|mail)\s+to\s+([A-Za-z]+)',
            r'email\s+to\s+([A-Za-z]+)',
            r'mail\s+to\s+([A-Za-z]+)'
        ]

        # Try to find email first
        for pattern in email_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                params["to"] = match.group(1).strip()
                break

        # If no email found, try to find name
        if "to" not in params:
            for pattern in name_patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    # Filter out common words and clean up
                    name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
                    if name.lower() not in ['about', 'regarding', 'saying', 'for', 'asking', 'an', 'a', 'the']:
                        params["recipient_name"] = name
                        logger.info(f"Extracted recipient name from query: {name}")
                        break

        # Extract subject
        subject_patterns = [
            r'about\s+([^"\']+?)(?:\s+saying|\s+message|\s*$)',
            r'regarding\s+([^"\']+?)(?:\s+saying|\s+message|\s*$)',
            r'subject[:\s]+["\']([^"\']+)["\']'
        ]
        for pattern in subject_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                params["subject"] = match.group(1).strip()
                break

        # Store the full query for LLM processing
        params["full_query"] = query

        # Remove hardcoded body - let LLM generate it
        # Don't set a default body here

        return operation, params
    
    def _extract_email_details(self, query: str) -> Dict[str, str]:
        """Extract email details from query"""
        params = {
            "to": "",
            "subject": "",
            "body": ""
        }

        # Extract email address
        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        email_match = re.search(email_pattern, query)
        if email_match:
            params["to"] = email_match.group(1)

        # Check if query mentions a person name (for sheet lookup)
        name_patterns = [
            r'send.*?mail.*?to\s+([A-Za-z]+)',
            r'email\s+([A-Za-z]+)',
            r'mail.*?([A-Za-z]+)\s+regarding',
            r'send.*?to\s+([A-Za-z]+)'
        ]

        extracted_name = None
        for pattern in name_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                extracted_name = match.group(1).strip()
                break

        # If we found a name but no email, we'll need to look it up from sheets
        if extracted_name and not params["to"]:
            params["recipient_name"] = extracted_name

        # Extract subject - handle sick leave, meeting, etc.
        if "sick leave" in query.lower() or "seek leave" in query.lower() or "seeking leave" in query.lower() or ("sick" in query.lower() and "leave" in query.lower()):
            params["subject"] = "Sick Leave Request"
        elif "meeting" in query.lower():
            params["subject"] = "Meeting Request"
        elif "project" in query.lower():
            params["subject"] = "Project Update"
        else:
            # Try to extract subject from patterns
            subject_patterns = [
                r'subject[:\s]+["\']([^"\']+)["\']',
                r'subject[:\s]+([^.?!,]+)',
                r'about\s+([^.?!,]+)',
                r'regarding\s+([^.?!,]+)'
            ]
            for pattern in subject_patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    params["subject"] = match.group(1).strip()
                    break

        # Extract body/message - handle sick leave specifically
        if "sick leave" in query.lower() or "seek leave" in query.lower() or "seeking leave" in query.lower() or ("sick" in query.lower() and "leave" in query.lower()):
            params["body"] = """Dear Manager,

I am writing to request sick leave due to health reasons. I will keep you updated on my recovery and expected return date.

Thank you for your understanding.

Best regards"""
        else:
            body_patterns = [
                r'message[:\s]+["\']([^"\']+)["\']',
                r'body[:\s]+["\']([^"\']+)["\']',
                r'saying[:\s]+["\']([^"\']+)["\']',
                r'tell.*?["\']([^"\']+)["\']'
            ]
            for pattern in body_patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    params["body"] = match.group(1).strip()
                    break

        # If no specific body found, use a generic message
        if not params["body"]:
            params["body"] = "This email was sent via your AI assistant."

        return params

    async def _generate_email_content(self, query: str, params: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Generate email content using AI or fallback to templates"""
        try:
            # Try to use AI for content generation first
            if hasattr(self, 'llm') and self.llm:
                prompt = self._create_email_prompt(query, params)
                response = await self.llm.generate_content(prompt)
                content = response.text
                
                # Parse the AI response
                parsed_content = self._parse_ai_email_response(content)
                if parsed_content:
                    return parsed_content
            
            # Fallback to template-based content generation
            logger.warning("AI quota exceeded, using enhanced template-based content generation")
            return self._get_enhanced_business_email_template(query, params)
            
        except Exception as e:
            logger.error(f"Error generating email content: {e}")
            # Fallback to template-based content generation
            return self._get_enhanced_business_email_template(query, params)

    def _get_enhanced_business_email_template(self, query: str, params: Dict[str, Any]) -> Dict[str, str]:
        """Enhanced template-based email content generation with better context analysis"""
        query_lower = query.lower()
        recipient_name = params.get("recipient_name", "Manager")
        
        # Extract context from query
        context = self._extract_email_context(query)
        
        # Personal/Romantic message template
        if any(keyword in query_lower for keyword in ["love", "romantic", "personal", "feelings", "heart", "care about", "special", "dear"]):
            return {
                "subject": "Personal Message",
                "body": f"""Dear {recipient_name},

I hope this message finds you well.

I wanted to reach out and share something personal with you. This message comes from the heart, and I felt it was important to express my feelings directly.

Please know that this message is sent with genuine care and respect for you as a person.

I would appreciate the opportunity to speak with you in person when you have time, as some things are better shared face-to-face.

Thank you for taking the time to read this.

With warm regards,
[Your Name]

---
This personal message was sent via ModuMentor AI Assistant"""
            }

        # HR/Harassment complaint template (PRIORITY - most serious)
        elif any(keyword in query_lower for keyword in ["harass", "harassment", "hr", "complaint", "inappropriate", "misconduct", "discrimination", "hostile", "abuse", "bully"]):
            return {
                "subject": "Formal Complaint - Workplace Harassment",
                "body": f"""Dear {recipient_name},

I am writing to formally report a serious workplace issue that requires immediate HR attention and investigation.

**Nature of Complaint:** Workplace harassment and inappropriate conduct
**Date of Incident(s):** {context.get('dates', '[Please specify dates]')}
**Location:** {context.get('location', '[Please specify location]')}
**Type of Harassment:** {context.get('harassment_type', '[Please specify the nature of harassment]')}

**Detailed Description:**
I am experiencing ongoing harassment in the workplace that is creating a hostile work environment and significantly impacting my ability to perform my duties effectively. This behavior includes {context.get('description', '[describe specific incidents, behaviors, or actions that constitute harassment]')}.

**Impact on Work Environment:**
• Creates a hostile and uncomfortable work environment
• Affects my mental health and well-being
• Impacts my productivity and job performance
• Creates an atmosphere of fear and anxiety

**Previous Actions Taken:**
{context.get('previous_actions', '[If applicable, mention any previous attempts to resolve the issue informally]')}

**Requested Actions:**
• Immediate investigation of this matter by HR
• Formal documentation of this complaint
• Meeting to discuss the situation in detail
• Appropriate corrective measures to prevent further incidents
• Protection against retaliation
• Follow-up to ensure resolution

**Confidentiality:**
I understand the sensitive nature of this complaint and request that this matter be handled with the utmost confidentiality, sharing information only with those who need to know for investigation purposes.

I am available to meet at your earliest convenience to discuss this matter in detail and provide additional information, documentation, or witness statements as needed.

This is a serious matter that affects not only my well-being but also the overall workplace culture and safety for all employees.

Thank you for your immediate attention to this urgent matter.

Best regards,
[Your Name]

**CONFIDENTIAL - HR MATTER**
**PRIORITY: URGENT**

---
This email was sent via ModuMentor AI Assistant"""
            }

        # Sick leave template
        elif any(keyword in query_lower for keyword in ["sick", "leave", "ill", "unwell", "medical", "health"]):
            return {
                "subject": "Sick Leave Request",
                "body": f"""Dear {recipient_name},

I am writing to inform you that I am feeling unwell today and will not be able to come to work.

**Reason for Absence:** {context.get('reason', 'Medical/Health related')}
**Expected Duration:** {context.get('duration', '[Please specify if known]')}
**Return Date:** {context.get('return_date', '[Please specify if known]')}

**Current Status:**
I have been experiencing symptoms that require me to take a sick day to rest and recover. I am taking appropriate measures to address my health concerns.

**Work Coverage:**
• I will monitor my emails periodically for urgent matters
• I will be available for critical issues that require my immediate attention
• I have arranged for {context.get('backup_person', '[colleague name]')} to cover my urgent tasks
• All pending work has been documented and can be accessed by the team

**Updates:**
I will keep you updated on my condition and expected return date. If my condition changes or I need to extend my leave, I will notify you immediately.

**Documentation:**
I will provide any necessary medical documentation as required by company policy.

Thank you for your understanding and support during this time.

Best regards,
[Your Name]

---
This email was sent via ModuMentor AI Assistant"""
            }

        # Meeting request template
        elif any(keyword in query_lower for keyword in ["meeting", "schedule", "appointment", "discuss", "talk"]):
            return {
                "subject": f"Meeting Request - {context.get('purpose', 'Important Matters')}",
                "body": f"""Dear {recipient_name},

I hope this email finds you well.

I would like to schedule a meeting with you to discuss some important matters that require your attention and input.

**Meeting Purpose:** {context.get('purpose', '[Please specify the purpose]')}
**Estimated Duration:** {context.get('duration', '30-60 minutes')}
**Preferred Format:** {context.get('format', '[In-person/Virtual/Hybrid]')}
**Urgency Level:** {context.get('urgency', '[High/Medium/Low]')}

**Topics to Discuss:**
• {context.get('topic1', '[Topic 1]')}
• {context.get('topic2', '[Topic 2]')}
• {context.get('topic3', '[Topic 3]')}

**Preparation Required:**
{context.get('preparation', '[If any preparation is needed from either party]')}

**Suggested Time Slots:**
• {context.get('time1', '[Date and time option 1]')}
• {context.get('time2', '[Date and time option 2]')}
• {context.get('time3', '[Date and time option 3]')}

I am flexible with timing and can accommodate your schedule. Please let me know your availability, and I will arrange a suitable time that works for both of us.

If this meeting requires the presence of other team members or stakeholders, please let me know so I can coordinate accordingly.

Thank you for your time and consideration.

Best regards,
[Your Name]

---
This email was sent via ModuMentor AI Assistant"""
            }

        # Project update/Report template
        elif any(keyword in query_lower for keyword in ["update", "report", "status", "progress", "project"]):
            return {
                "subject": f"Project Status Update - {context.get('project_name', 'Current Projects')}",
                "body": f"""Dear {recipient_name},

I hope this email finds you well.

I am writing to provide you with a comprehensive update on the current status of my projects and ongoing work.

**Project Overview:**
{context.get('project_name', '[Project name or general work area]')}

**Current Status:**
• **Completed:** {context.get('completed', '[List completed tasks]')}
• **In Progress:** {context.get('in_progress', '[List ongoing tasks]')}
• **Pending:** {context.get('pending', '[List pending tasks]')}
• **Blocked:** {context.get('blocked', '[List any blockers or issues]')}

**Key Achievements:**
• {context.get('achievement1', '[Achievement 1]')}
• {context.get('achievement2', '[Achievement 2]')}
• {context.get('achievement3', '[Achievement 3]')}

**Challenges & Issues:**
• {context.get('challenge1', '[Challenge 1 and proposed solution]')}
• {context.get('challenge2', '[Challenge 2 and proposed solution]')}

**Next Steps:**
• {context.get('next_step1', '[Next step 1]')}
• {context.get('next_step2', '[Next step 2]')}
• {context.get('next_step3', '[Next step 3]')}

**Timeline:**
• **Current Phase:** {context.get('current_phase', '[Phase name]')}
• **Expected Completion:** {context.get('completion_date', '[Date]')}
• **Milestones:** {context.get('milestones', '[Key milestones]')}

**Resource Requirements:**
{context.get('resources', '[If any additional resources, support, or approvals are needed]')}

**Questions/Decisions Needed:**
• {context.get('question1', '[Question 1]')}
• {context.get('question2', '[Question 2]')}

I will continue to provide regular updates and am available for any questions or clarifications you may have.

Thank you for your attention and support.

Best regards,
[Your Name]

---
This email was sent via ModuMentor AI Assistant"""
            }

        # General business communication template
        else:
            return {
                "subject": f"Business Communication - {context.get('topic', 'Important Matter')}",
                "body": f"""Dear {recipient_name},

I hope this email finds you well.

I am writing regarding {context.get('matter', '[brief description of the matter]')}.

**Purpose:** {context.get('purpose', '[State the main purpose of this communication]')}
**Details:** {context.get('details', '[Provide relevant details and context]')}
**Action Required:** {context.get('action_required', '[Specify what action is needed, if any]')}

**Key Points:**
• {context.get('point1', '[Point 1]')}
• {context.get('point2', '[Point 2]')}
• {context.get('point3', '[Point 3]')}

**Next Steps:**
{context.get('next_steps', '[Outline the next steps or timeline]')}

**Questions:**
{context.get('questions', '[If you have any questions or need clarification]')}

I appreciate your time and attention to this matter. Please let me know if you need any additional information or have any questions.

Thank you for your consideration.

Best regards,
[Your Name]

---
This email was sent via ModuMentor AI Assistant"""
            }

    def _extract_email_context(self, query: str) -> Dict[str, str]:
        """Extract context from email query to provide more specific content"""
        context = {}
        query_lower = query.lower()
        
        # Extract dates
        import re
        date_patterns = [
            r'today', r'tomorrow', r'yesterday', r'next week', r'this week',
            r'\d{1,2}/\d{1,2}/\d{4}', r'\d{1,2}-\d{1,2}-\d{4}'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, query_lower)
            if match:
                context['dates'] = match.group()
                break
        
        # Extract location
        location_keywords = ['office', 'workplace', 'meeting room', 'conference room', 'cafeteria']
        for keyword in location_keywords:
            if keyword in query_lower:
                context['location'] = keyword.title()
                break
        
        # Extract harassment type
        harassment_types = {
            'verbal': ['verbal', 'words', 'comments', 'remarks'],
            'physical': ['physical', 'touch', 'gesture'],
            'psychological': ['psychological', 'mental', 'emotional'],
            'sexual': ['sexual', 'inappropriate', 'unwanted'],
            'bullying': ['bully', 'intimidation', 'threat']
        }
        
        for h_type, keywords in harassment_types.items():
            if any(keyword in query_lower for keyword in keywords):
                context['harassment_type'] = h_type.title()
                break
        
        # Extract project names
        project_keywords = ['project', 'task', 'assignment', 'work']
        for keyword in project_keywords:
            if keyword in query_lower:
                # Try to extract project name from context
                words = query.split()
                for i, word in enumerate(words):
                    if word.lower() == keyword and i + 1 < len(words):
                        context['project_name'] = words[i + 1]
                        break
        
        # Extract urgency
        urgency_keywords = {
            'high': ['urgent', 'immediate', 'asap', 'critical', 'emergency'],
            'medium': ['important', 'soon', 'priority'],
            'low': ['when convenient', 'no rush', 'low priority']
        }
        
        for urgency, keywords in urgency_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                context['urgency'] = urgency.title()
                break
        
        return context

    def _create_email_prompt(self, query: str, params: Dict[str, Any]) -> str:
        """Create a prompt for AI email generation"""
        recipient_name = params.get("recipient_name", "recipient")
        context = params.get("full_query", query)

        prompt = f"""
Generate a professional email based on this request: "{context}"

The email should be:
- Professional and polite
- Clear and concise
- Appropriate for workplace communication
- Include proper greeting and closing

Recipient: {recipient_name}

Please provide the response in this exact format:
SUBJECT: [email subject]
BODY: [email body]

Make sure the subject is clear and the body is well-formatted with proper paragraphs.
"""
        return prompt

    def _parse_ai_email_response(self, content: str) -> Optional[Dict[str, str]]:
        """Parse AI-generated email response"""
        try:
            import re
            text = content.strip()
            subject = ""
            body = ""

            # Look for **SUBJECT:** pattern
            subject_match = re.search(r'\*\*SUBJECT:\*\*\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).strip()

            # Look for **BODY:** pattern
            body_match = re.search(r'\*\*BODY:\*\*\s*\n(.*)', text, re.IGNORECASE | re.DOTALL)
            if body_match:
                body = body_match.group(1).strip()

            # Fallback: try simple SUBJECT: and BODY: patterns
            if not subject:
                subject_match = re.search(r'SUBJECT:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
                if subject_match:
                    subject = subject_match.group(1).strip()

            if not body:
                body_match = re.search(r'BODY:\s*\n(.*)', text, re.IGNORECASE | re.DOTALL)
                if body_match:
                    body = body_match.group(1).strip()

            if subject and body:
                return {
                    "subject": subject,
                    "body": body
                }

            return None

        except Exception as e:
            logger.error(f"Error parsing AI email response: {e}")
            return None

    async def _lookup_email_from_sheets(self, name: str) -> Optional[str]:
        """Look up email address from Google Sheets based on name"""
        try:
            if not config.GOOGLE_SHEETS_ID:
                logger.warning("No GOOGLE_SHEETS_ID configured for email lookup")
                return None

            logger.info(f"Looking up email for name: {name}")

            # Get sheet data
            sheet_data = await get_real_sheet_data(config.GOOGLE_SHEETS_ID)
            if not sheet_data:
                logger.warning("No sheet data returned")
                return None
            
            if "error" in sheet_data:
                logger.warning(f"Sheet access error: {sheet_data.get('message')}")
                return None
                
            if "values" not in sheet_data:
                logger.warning("Sheet data has no 'values' key")
                return None

            values = sheet_data["values"]
            if len(values) < 2:  # Need at least headers + 1 row
                logger.warning(f"Sheet has insufficient data: {len(values)} rows")
                return None

            headers = [str(h).strip() for h in values[0]]
            headers_lower = [h.lower() for h in headers]
            
            logger.info(f"Sheet headers: {headers}")

            # Find name and email column indices (check for various email column names)
            name_col = -1
            email_col = -1

            for i, header_lower in enumerate(headers_lower):
                if "name" in header_lower and name_col == -1:
                    name_col = i
                    logger.info(f"Found name column at index {i}: {headers[i]}")
                elif "email" in header_lower and email_col == -1:
                    email_col = i
                    logger.info(f"Found email column at index {i}: {headers[i]}")

            if name_col == -1:
                logger.warning("Could not find 'name' column in sheet")
                return None
                
            if email_col == -1:
                logger.warning("Could not find 'email' column in sheet")
                return None

            # Normalize the search name (remove extra spaces, lowercase)
            search_name = re.sub(r'\s+', ' ', name.strip().lower())
            logger.info(f"Searching for name: '{search_name}' in column {name_col}")

            # Search for the name (try exact match first, then partial match)
            for row_idx, row in enumerate(values[1:], start=2):
                if len(row) > max(name_col, email_col):
                    row_name = str(row[name_col]).strip() if name_col < len(row) else ""
                    row_name_lower = row_name.lower()
                    
                    # Try exact match first
                    if search_name == row_name_lower:
                        email = str(row[email_col]).strip() if email_col < len(row) else ""
                        if email and "@" in email:
                            logger.info(f"Found exact match: {row_name} -> {email}")
                            return email
                    
                    # Try partial match (name contains search term or vice versa)
                    elif search_name in row_name_lower or row_name_lower in search_name:
                        # Additional check: make sure it's not just a common word match
                        if len(search_name) >= 3 and len(row_name_lower) >= 3:
                            email = str(row[email_col]).strip() if email_col < len(row) else ""
                            if email and "@" in email:
                                logger.info(f"Found partial match: {row_name} -> {email}")
                                return email
                    
                    # Try matching first name only
                    elif search_name.split()[0] in row_name_lower or row_name_lower.split()[0] in search_name:
                        email = str(row[email_col]).strip() if email_col < len(row) else ""
                        if email and "@" in email:
                            logger.info(f"Found first name match: {row_name} -> {email}")
                            return email

            logger.warning(f"Could not find email for name: {name}")
            return None

        except Exception as e:
            logger.error(f"Error looking up email from sheets: {e}", exc_info=True)
            return None
    
    async def _get_email_from_sheets(self) -> Optional[str]:
        """Get the first email address from Google Sheets"""
        try:
            if not config.GOOGLE_SHEETS_ID:
                logger.warning("No GOOGLE_SHEETS_ID configured for email lookup")
                return None

            logger.info("Getting first email from Google Sheet")

            # Get sheet data
            sheet_data = await get_real_sheet_data(config.GOOGLE_SHEETS_ID)
            if not sheet_data:
                logger.warning("No sheet data returned")
                return None
            
            if "error" in sheet_data:
                logger.warning(f"Sheet access error: {sheet_data.get('message')}")
                return None
                
            if "values" not in sheet_data:
                logger.warning("Sheet data has no 'values' key")
                return None

            values = sheet_data["values"]
            if len(values) < 2:  # Need at least headers + 1 row
                logger.warning(f"Sheet has insufficient data: {len(values)} rows")
                return None

            headers = [str(h).strip() for h in values[0]]
            headers_lower = [h.lower() for h in headers]
            
            logger.info(f"Sheet headers: {headers}")

            # Find email column index
            email_col = -1
            for i, header_lower in enumerate(headers_lower):
                if "email" in header_lower:
                    email_col = i
                    logger.info(f"Found email column at index {i}: {headers[i]}")
                    break

            if email_col == -1:
                logger.warning("Could not find 'email' column in sheet")
                return None

            # Get first email from data rows
            for row_idx, row in enumerate(values[1:], start=2):
                if len(row) > email_col:
                    email = str(row[email_col]).strip() if email_col < len(row) else ""
                    if email and "@" in email:
                        logger.info(f"Found email from row {row_idx}: {email}")
                        return email

            logger.warning("Could not find any email address in sheet")
            return None

        except Exception as e:
            logger.error(f"Error getting email from sheets: {e}", exc_info=True)
            return None

    async def _execute_gmail_operation(self, client, operation: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute the Gmail operation"""
        if operation == "send":
            return await client.send_email(
                params.get("to", ""),
                params.get("subject", "Message from AI Assistant"),
                params.get("body", "This email was sent via your AI assistant.")
            )
        elif operation == "search":
            return await client.search_emails(
                params.get("search_term", ""),
                max_results=5
            )
        else:  # read
            return await client.read_emails(max_results=5)
    
    def _format_gmail_response(self, data: Dict[str, Any], operation: str, params: Dict[str, Any]) -> str:
        """Format Gmail operation response"""
        # Check for errors first (when SMTP is configured but fails)
        if data.get("status") == "error" and not data.get("demo"):
            error_msg = data.get("error", "Unknown error")
            return f"""❌ **Email Sending Failed**

📧 **Email Details:**
• **To:** {data.get('to', 'N/A')}
• **Subject:** {data.get('subject', 'N/A')}

❌ **Error:** {error_msg}

🔧 **Solutions:**

**Option 1: Use Resend API (Recommended - No Password Required)**
1. Sign up at: https://resend.com (free tier available)
2. Get your API key from dashboard
3. Add to `agent/.env`:
   ```
   RESEND_API_KEY=re_your_api_key_here
   EMAIL_FROM=ModuMentor Bot <bot@yourdomain.com>
   ```
4. Restart server
✅ No email/password needed - just API key!

**Option 2: Fix Gmail SMTP**
1. Verify GMAIL_ADDRESS and GMAIL_APP_PASSWORD in `agent/.env`
2. Check if 2-Factor Authentication is enabled
3. Generate new App Password (16 characters)
4. Restart the server
"""
        
        # Check if it's demo mode
        if data.get("demo") or data.get("note", "").startswith("Demo") or data.get("note", "").startswith("⚠️"):
            # Demo mode - email not actually sent
            return f"""⚠️ **DEMO MODE - Email NOT Actually Sent**

📧 **Email Prepared:**
• **To:** {data.get('to', 'N/A')}
• **Subject:** {data.get('subject', 'N/A')}
• **Body:** {params.get('body', 'N/A')[:200]}...

❌ **Email was NOT sent** because no email service is configured.

🔧 **To Send Real Emails (Choose One):**

**Option 1: Resend API (Recommended - No Password Required)**
1. Sign up at: https://resend.com (free tier: 3,000 emails/month)
2. Get API key from dashboard
3. Add to `agent/.env`:
   ```
   RESEND_API_KEY=re_your_api_key_here
   EMAIL_FROM=ModuMentor Bot <bot@yourdomain.com>
   ```
4. Restart server
✅ **No email/password needed - just API key!**

**Option 2: Gmail SMTP (Requires Password)**
1. Enable 2-Factor Authentication on Gmail
2. Generate App Password from: https://myaccount.google.com/security
3. Add to `agent/.env`:
   ```
   GMAIL_ADDRESS=your_email@gmail.com
   GMAIL_APP_PASSWORD=your_16_char_app_password
   ```
4. Restart server
"""
        
        try:
            if operation == "send":
                # Check if email was actually sent via SMTP
                if data.get("method") == "SMTP" or (not data.get("demo") and data.get("status") == "sent"):
                    response = f"✅ **Email Sent Successfully!**\n\n"
                    response += f"📧 **To:** {data.get('to', 'Unknown')}\n"
                    response += f"📌 **Subject:** {data.get('subject', 'No subject')}\n"
                    
                    if data.get("message_id"):
                        response += f"🆔 **Message ID:** {data['message_id']}\n"
                    
                    if data.get("method"):
                        response += f"📤 **Method:** {data['method']}\n"
                    
                    # Show email body preview
                    if params.get("body"):
                        body_preview = params["body"][:150] + "..." if len(params["body"]) > 150 else params["body"]
                        response += f"\n📝 **Email Content:**\n{body_preview}\n"
                    
                    response += f"\n✅ **Email has been sent successfully via Gmail SMTP!**"
                    return response
                else:
                    # Fallback response
                    response = f"📧 **Email Prepared**\n\n"
                    response += f"**To:** {data.get('to', 'Unknown')}\n"
                    response += f"**Subject:** {data.get('subject', 'No subject')}\n"
                    
                    if data.get("message_id"):
                        response += f"**Message ID:** {data['message_id']}\n"
                    
                    if data.get("note"):
                        response += f"\n💡 *{data['note']}*\n"
                    
                    return response
            
            elif operation in ["read", "search"]:
                emails = data.get("emails", [])
                if not emails:
                    return "📭 No emails found."
                
                response = f"📧 **{'Search Results' if operation == 'search' else 'Recent Emails'}**\n\n"
                
                if operation == "search":
                    response += f"🔍 **Search term:** {params.get('search_term', '')}\n\n"
                
                for i, email in enumerate(emails[:5], 1):  # Show max 5 emails
                    status = "📩" if email.get("read", True) else "📨"
                    response += f"{status} **{i}. {email.get('subject', 'No subject')}**\n"
                    response += f"   **From:** {email.get('from', 'Unknown')}\n"
                    response += f"   **Date:** {email.get('date', 'Unknown')}\n"
                    
                    body = email.get('body', '')
                    if body:
                        preview = body[:100] + "..." if len(body) > 100 else body
                        response += f"   **Preview:** {preview}\n"
                    
                    response += "\n"
                
                total = data.get("total", len(emails))
                if total > 5:
                    response += f"*... and {total - 5} more emails*\n"
                
                if data.get("note"):
                    response += f"\n💡 *{data['note']}*\n"
                
                return response
            
        except Exception as e:
            logger.error(f"Error formatting Gmail response: {e}")
            return "Gmail operation completed, but there was an error formatting the response."



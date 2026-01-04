"""
Advanced AI Tool for ModuMentor
Provides image analysis, document processing, and advanced AI capabilities
"""
import asyncio
import base64
import io
from typing import Dict, Any, Optional, List
from loguru import logger
import google.generativeai as genai
from PIL import Image
import requests
from .base_tool import BaseTool
from config import config


class AdvancedAITool(BaseTool):
    """Advanced AI capabilities including image analysis and document processing"""
    
    def __init__(self):
        super().__init__(tool_url="local://advanced_ai", name="AdvancedAI")
        
        # Configure Gemini for image analysis
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.vision_model = genai.GenerativeModel('gemini-1.5-flash')  # Use flash model for vision
        self.text_model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        logger.info("AdvancedAITool initialized with vision capabilities")
    
    def can_handle(self, query: str) -> bool:
        """Check if this tool can handle the query"""
        ai_indicators = [
            "analyze image", "describe image", "what's in this image",
            "read document", "extract text", "summarize document",
            "analyze photo", "describe picture", "what do you see",
            "ocr", "text recognition", "image to text",
            "analyze chart", "read graph", "interpret diagram",
            "business card", "receipt analysis", "invoice processing"
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in ai_indicators)
    
    def get_description(self) -> str:
        """Get tool description"""
        return "Advanced AI: Image analysis, document processing, OCR, visual understanding, and intelligent content extraction"
    
    async def execute(self, query: str, **kwargs) -> str:
        """Execute advanced AI operations"""
        try:
            # Check if image/document is provided
            image_data = kwargs.get('image_data')
            image_url = kwargs.get('image_url')
            file_path = kwargs.get('file_path')
            
            if image_data or image_url or file_path:
                return await self._process_visual_content(query, image_data, image_url, file_path)
            else:
                return await self._process_text_analysis(query)
                
        except Exception as e:
            logger.error(f"Error in AdvancedAI tool: {e}")
            return f"Sorry, I encountered an error while processing your request: {str(e)}"
    
    async def _process_visual_content(self, query: str, image_data: bytes = None, 
                                    image_url: str = None, file_path: str = None) -> str:
        """Process image or visual content"""
        try:
            # Load image
            image = None
            
            if image_data:
                image = Image.open(io.BytesIO(image_data))
            elif image_url:
                response = requests.get(image_url)
                image = Image.open(io.BytesIO(response.content))
            elif file_path:
                image = Image.open(file_path)
            
            if not image:
                return "❌ No valid image provided for analysis."
            
            # Determine analysis type based on query
            analysis_type = self._determine_analysis_type(query)
            
            # Create appropriate prompt
            prompt = self._create_vision_prompt(query, analysis_type)
            
            # Analyze with Gemini Vision
            response = await asyncio.to_thread(
                self.vision_model.generate_content,
                [prompt, image]
            )
            
            if response and response.text:
                return self._format_vision_response(response.text, analysis_type)
            else:
                return "❌ Could not analyze the image. Please try again."
                
        except Exception as e:
            logger.error(f"Error processing visual content: {e}")
            return f"❌ Error analyzing image: {str(e)}"
    
    async def _process_text_analysis(self, query: str) -> str:
        """Process advanced text analysis requests"""
        try:
            # Determine if this is a document processing request
            if any(term in query.lower() for term in ["document", "text", "analyze", "summarize"]):
                prompt = f"""
You are an advanced AI assistant with document processing capabilities. 

User request: "{query}"

Provide a helpful response about document processing capabilities or text analysis.
If the user is asking about capabilities, explain what you can do with documents and images.
"""
            else:
                prompt = f"""
You are an advanced AI assistant. Respond to this query with intelligent analysis:

Query: "{query}"

Provide a comprehensive and helpful response.
"""
            
            response = await asyncio.to_thread(
                self.text_model.generate_content,
                prompt
            )
            
            if response and response.text:
                return f"🤖 **Advanced AI Analysis**\n\n{response.text}"
            else:
                return "❌ Could not process the request. Please try again."
                
        except Exception as e:
            logger.error(f"Error in text analysis: {e}")
            return f"❌ Error processing request: {str(e)}"
    
    def _determine_analysis_type(self, query: str) -> str:
        """Determine the type of image analysis needed"""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ["business card", "contact", "card"]):
            return "business_card"
        elif any(term in query_lower for term in ["receipt", "invoice", "bill"]):
            return "receipt"
        elif any(term in query_lower for term in ["chart", "graph", "data", "plot"]):
            return "chart_analysis"
        elif any(term in query_lower for term in ["text", "ocr", "read", "extract"]):
            return "text_extraction"
        elif any(term in query_lower for term in ["document", "paper", "form"]):
            return "document"
        else:
            return "general_analysis"
    
    def _create_vision_prompt(self, query: str, analysis_type: str) -> str:
        """Create appropriate prompt for vision analysis"""
        base_prompt = f"User request: {query}\n\n"
        
        if analysis_type == "business_card":
            return base_prompt + """
Analyze this business card and extract:
- Name and title
- Company name
- Contact information (phone, email, address)
- Any other relevant details
Format the response clearly and professionally.
"""
        elif analysis_type == "receipt":
            return base_prompt + """
Analyze this receipt/invoice and extract:
- Business name and details
- Date and time
- Items purchased with prices
- Total amount
- Payment method if visible
- Any other relevant transaction details
"""
        elif analysis_type == "chart_analysis":
            return base_prompt + """
Analyze this chart/graph and provide:
- Type of chart (bar, line, pie, etc.)
- Key data points and trends
- Main insights and patterns
- Summary of what the data shows
"""
        elif analysis_type == "text_extraction":
            return base_prompt + """
Extract and transcribe all visible text from this image.
Maintain formatting and structure as much as possible.
If there are multiple sections, organize them clearly.
"""
        elif analysis_type == "document":
            return base_prompt + """
Analyze this document and provide:
- Document type and purpose
- Key information and content summary
- Important details or data
- Any actionable items or next steps
"""
        else:
            return base_prompt + """
Analyze this image and describe:
- What you see in the image
- Key objects, people, or elements
- Context and setting
- Any text or important details
- Overall purpose or meaning
"""
    
    def _format_vision_response(self, response_text: str, analysis_type: str) -> str:
        """Format the vision analysis response"""
        if analysis_type == "business_card":
            icon = "👤"
            title = "Business Card Analysis"
        elif analysis_type == "receipt":
            icon = "🧾"
            title = "Receipt/Invoice Analysis"
        elif analysis_type == "chart_analysis":
            icon = "📊"
            title = "Chart Analysis"
        elif analysis_type == "text_extraction":
            icon = "📝"
            title = "Text Extraction"
        elif analysis_type == "document":
            icon = "📄"
            title = "Document Analysis"
        else:
            icon = "🔍"
            title = "Image Analysis"
        
        return f"{icon} **{title}**\n\n{response_text}"


# Helper functions for image processing
def encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def download_image_from_url(url: str) -> bytes:
    """Download image from URL"""
    response = requests.get(url)
    response.raise_for_status()
    return response.content


# Advanced AI capabilities for future enhancements
class DocumentProcessor:
    """Advanced document processing capabilities"""
    
    @staticmethod
    async def extract_structured_data(image: Image.Image, data_type: str) -> Dict[str, Any]:
        """Extract structured data from documents"""
        # This can be enhanced with specialized models
        pass
    
    @staticmethod
    async def analyze_business_document(image: Image.Image) -> Dict[str, Any]:
        """Analyze business documents for key information"""
        # Enhanced business document analysis
        pass


class VisionAnalytics:
    """Advanced vision analytics capabilities"""
    
    @staticmethod
    async def detect_objects(image: Image.Image) -> List[Dict[str, Any]]:
        """Detect and classify objects in images"""
        # Object detection capabilities
        pass
    
    @staticmethod
    async def analyze_sentiment_from_image(image: Image.Image) -> Dict[str, Any]:
        """Analyze emotional content or sentiment from images"""
        # Sentiment analysis from visual content
        pass

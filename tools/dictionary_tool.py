"""
Dictionary tool using Free Dictionary API with Lingua Robot fallback
"""
import re
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from loguru import logger
from .base_tool import BaseTool
from config import config


class DictionaryTool(BaseTool):
    """Tool for dictionary lookups and word definitions using Free Dictionary API"""
    
    def __init__(self):
        super().__init__(config.DICTIONARY_TOOL_URL, "Dictionary")
        self.dictionary_keywords = [
            "define", "definition", "meaning", "what does", "dictionary",
            "synonym", "antonym", "pronunciation", "etymology", "translate"
        ]
        # Free Dictionary API (primary) - no API key required
        self.free_dict_url = "https://api.dictionaryapi.dev/api/v2/entries/en"
        # Lingua Robot API configuration (fallback)
        self.lingua_url = "https://lingua-robot.p.rapidapi.com"
        self.lingua_key = "4a27338f23msha420584e4872c6ap136366jsnb24a54a042da"
        self.lingua_host = "lingua-robot.p.rapidapi.com"
        self.timeout = aiohttp.ClientTimeout(total=10)
        
    def can_handle(self, query: str) -> bool:
        """Check if this tool can handle the query"""
        query_lower = query.lower().strip()
        logger.info(f"Dictionary tool: can_handle called with query: '{query}' (lower: '{query_lower}')")
        
        # Check for dictionary-related keywords
        for keyword in self.dictionary_keywords:
            if keyword in query_lower:
                logger.info(f"Dictionary tool: Keyword match found: '{keyword}'")
                return True
        
        # Check for patterns like "word meaning", "define word", etc.
        patterns = [
            r'\b\w+\s+meaning\b',
            r'\bdefine\s+\w+\b',
            r'\bwhat\s+does\s+\w+\s+mean\b',
            r'\bdefinition\s+of\s+\w+\b',
            r'\bpronunciation\s+of\s+\w+\b',
            r'\bsynonym\s+for\s+\w+\b',
            r'\bantonym\s+for\s+\w+\b',
            r'\bmeaning\s+of\s+\w+\b',
            r'\b\w+\s+definition\b'
        ]
        
        for pattern in patterns:
            if re.search(pattern, query_lower):
                logger.info(f"Dictionary tool: Pattern match found: '{pattern}'")
                return True
        
        # Additional check: if query contains "meaning" and has at least one word before it
        if "meaning" in query_lower:
            words = query_lower.split()
            if len(words) >= 2 and words[1] == "meaning":
                logger.info(f"Dictionary tool: 'meaning' pattern detected")
                return True
        
        logger.info(f"Dictionary tool: No matches found for query: '{query}'")
        return False
    
    def _extract_word(self, query: str) -> Optional[str]:
        """Extract the word to look up from the query"""
        query_lower = query.lower().strip()
        
        # Handle common patterns
        patterns = [
            r'define\s+(\w+)',
            r'definition\s+of\s+(\w+)',
            r'meaning\s+of\s+(\w+)',
            r'what\s+does\s+(\w+)\s+mean',
            r'(\w+)\s+meaning',
            r'(\w+)\s+definition',
            r'pronunciation\s+of\s+(\w+)',
            r'synonym\s+for\s+(\w+)',
            r'antonym\s+for\s+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                return match.group(1).strip('.,!?;:')
        
        # If no pattern matches, try to extract the first meaningful word
        # Remove common words
        query_lower = re.sub(r'\b(define|definition|meaning|what|does|mean|of|for|the|a|an|is|are|was|were|will|would|could|should|can|may|might)\b', '', query_lower)
        query_lower = re.sub(r'\b(synonym|antonym|pronunciation|etymology|translate|tell|me|about|give|show|find|look|up)\b', '', query_lower)
        
        # Clean up and extract the first word
        words = query_lower.strip().split()
        if words:
            # Special handling for "word meaning" pattern
            if len(words) >= 2 and words[1] == "meaning":
                return words[0].strip('.,!?;:')
            # Otherwise return the first word
            return words[0].strip('.,!?;:')
        
        return None
    
    async def execute(self, query: str) -> str:
        """Execute dictionary lookup using Free Dictionary API with Lingua Robot fallback"""
        logger.info(f"Dictionary tool: Processing query: '{query}'")
        word = self._extract_word(query)
        logger.info(f"Dictionary tool: Extracted word: '{word}'")
        
        if not word:
            logger.error("Dictionary tool: No word extracted from query")
            return "❌ Could not extract a word to look up from your query."
        
        logger.info(f"Dictionary tool: Looking up word '{word}' using Free Dictionary API")
        logger.info(f"Dictionary tool: Free Dictionary URL: {self.free_dict_url}/{word.lower()}")
        
        # Try Free Dictionary API first (no API key required)
        logger.info("Dictionary tool: Attempting Free Dictionary API...")
        try:
            result = await self._get_free_dictionary_definition(word)
            if result:
                logger.info("Dictionary tool: Free Dictionary API succeeded!")
                return result
            else:
                logger.warning("Dictionary tool: Free Dictionary API returned no result")
        except Exception as e:
            logger.error(f"Dictionary tool: Free Dictionary API failed with error: {e}")
        
        # Fallback to Lingua Robot API
        logger.info("Dictionary tool: Attempting Lingua Robot API...")
        try:
            result = await self._get_lingua_definition(word)
            if result:
                logger.info("Dictionary tool: Lingua Robot API succeeded!")
                return result
            else:
                logger.warning("Dictionary tool: Lingua Robot API returned no result")
        except Exception as e:
            logger.error(f"Dictionary tool: Lingua Robot API failed with error: {e}")
        
        # Final fallback: Use WebSearch to find definition with LLM analysis
        logger.info(f"Dictionary tool: All APIs failed, trying WebSearch fallback for '{word}'")
        try:
            from tools.web_search_tool import WebSearchTool
            web_search = WebSearchTool()
            search_query = f"definition meaning of {word} dictionary"
            logger.info(f"Dictionary tool: WebSearch query: '{search_query}'")
            
            web_result = await web_search.execute(search_query)
            if web_result and not web_result.strip().lower().startswith("sorry"):
                # Use intelligent agent's search analysis to format the result professionally
                logger.info("Dictionary tool: WebSearch successful, analyzing with LLM")
                
                # Create a context for the LLM analysis
                analysis_context = f"""
You are analyzing web search results to provide a professional dictionary definition.

Word: {word}
Search Query: {search_query}
Web Search Results: {web_result}

Please provide a professional dictionary-style definition that includes:
1. Clear, concise definition(s)
2. Part of speech information
3. Example usage if available
4. Professional formatting with emojis and markdown

Format the response as a proper dictionary entry, not as a list of websites.
"""
                
                # Use the intelligent agent's LLM to analyze the results
                from agents.intelligent_agent import IntelligentAgent
                agent = IntelligentAgent()
                
                # Get the LLM to analyze the search results
                analyzed_result = await agent._analyze_search_results(
                    f"definition of {word}", 
                    web_result, 
                    "WebSearch", 
                    None
                )
                
                # Format the final response
                formatted_result = f"📚 **Definition of '{word.title()}'**\n\n"
                formatted_result += analyzed_result
                formatted_result += f"\n\n📊 **Source:** Web Search Analysis (API unavailable)"
                logger.info("Dictionary tool: WebSearch + LLM analysis successful")
                return formatted_result
            else:
                logger.warning("Dictionary tool: WebSearch fallback also failed")
                return f"❌ Could not find definition for '{word}' in any dictionary service or web search."
        except Exception as e:
            logger.error(f"Dictionary tool: WebSearch fallback error: {e}")
            return f"❌ Could not find definition for '{word}' in any dictionary service."
    
    async def _get_free_dictionary_definition(self, word: str) -> Optional[str]:
        """Get definition from Free Dictionary API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.free_dict_url}/{word.lower()}"
                logger.info(f"Dictionary tool: Making request to Free Dictionary API: {url}")
                
                async with session.get(url) as response:
                    logger.info(f"Dictionary tool: Free Dictionary API response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Dictionary tool: Free Dictionary API data received: {len(str(data))} characters")
                        return self._format_free_dict_response(data, word)
                    elif response.status == 404:
                        logger.warning(f"Dictionary tool: Word '{word}' not found in Free Dictionary API")
                        return None
                    else:
                        error_text = await response.text()
                        logger.warning(f"Dictionary tool: Free Dictionary API error {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Dictionary tool: Error accessing Free Dictionary API: {e}")
            return None
    
    async def _get_lingua_definition(self, word: str) -> Optional[str]:
        """Get definition from Lingua Robot API (fallback)"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                headers = {
                    "X-RapidAPI-Key": self.lingua_key,
                    "X-RapidAPI-Host": self.lingua_host,
                    "Content-Type": "application/json"
                }
                
                url = f"{self.lingua_url}/language/v1/entries/en/{word.lower()}"
                logger.info(f"Dictionary tool: Making request to Lingua Robot API: {url}")
                logger.info(f"Dictionary tool: Using API key: {self.lingua_key[:10]}...")
                
                async with session.get(url, headers=headers) as response:
                    logger.info(f"Dictionary tool: Lingua Robot API response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Dictionary tool: Lingua Robot API data received: {len(str(data))} characters")
                        return self._format_lingua_response(data, word)
                    else:
                        error_text = await response.text()
                        logger.warning(f"Dictionary tool: Lingua Robot API error {response.status}: {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Dictionary tool: Error accessing Lingua Robot API: {e}")
            return None
    
    def _format_free_dict_response(self, data: list, word: str) -> str:
        """Format Free Dictionary API response"""
        try:
            response = f"📚 **Definition of '{word.title()}'**\n\n"
            
            if data and len(data) > 0:
                entry = data[0]
                
                # Pronunciation
                if "phonetic" in entry:
                    response += f"**Pronunciation:** {entry['phonetic']}\n\n"
                
                # Meanings
                if "meanings" in entry:
                    response += "**Definitions:**\n"
                    for i, meaning in enumerate(entry["meanings"][:3], 1):  # Limit to first 3 meanings
                        part_of_speech = meaning.get("partOfSpeech", "")
                        definitions = meaning.get("definitions", [])
                        
                        if part_of_speech:
                            response += f"\n{i}. **({part_of_speech})** "
                        else:
                            response += f"\n{i}. "
                        
                        if definitions:
                            response += f"{definitions[0]['definition']}\n"
                            
                            # Examples
                            if "example" in definitions[0]:
                                response += f"   💭 Example: \"{definitions[0]['example']}\"\n"
                        
                        response += "\n"
                
                response += f"📊 **Source:** Free Dictionary API\n"
                return response
            else:
                return f"❌ No definition found for '{word}' in Free Dictionary API."
                
        except Exception as e:
            logger.error(f"Error formatting Free Dictionary response: {e}")
            return f"Found definition for '{word}', but there was an error formatting the response."
    
    def _format_lingua_response(self, data: Dict[str, Any], word: str) -> str:
        """Format Lingua Robot API response"""
        try:
            response = f"📚 **Definition of '{word.title()}'**\n\n"
            
            # Check if we have results
            if "results" in data and data["results"]:
                result = data["results"][0]
                
                # Lexical entries
                if "lexicalEntries" in result:
                    for lexical_entry in result["lexicalEntries"][:3]:  # Limit to first 3 entries
                        # Part of speech
                        if "lexicalCategory" in lexical_entry:
                            pos = lexical_entry["lexicalCategory"].get("text", "")
                            if pos:
                                response += f"**({pos})**\n"
                        
                        # Entries with definitions
                        if "entries" in lexical_entry:
                            for entry in lexical_entry["entries"]:
                                # Senses (definitions)
                                if "senses" in entry:
                                    for i, sense in enumerate(entry["senses"][:3], 1):  # Limit to first 3 senses
                                        # Definition
                                        if "definitions" in sense:
                                            definition = sense["definitions"][0]
                                            response += f"{i}. {definition}\n"
                                        
                                        # Examples
                                        if "examples" in sense:
                                            for example in sense["examples"][:2]:  # Limit to first 2 examples
                                                if "text" in example:
                                                    response += f"   💭 Example: \"{example['text']}\"\n"
                                        
                                        response += "\n"
                        
                        response += "\n"
                
                # Pronunciation
                if "pronunciations" in result:
                    for pronunciation in result["pronunciations"][:2]:  # Limit to first 2 pronunciations
                        if "phoneticSpelling" in pronunciation:
                            response += f"**Pronunciation:** {pronunciation['phoneticSpelling']}\n"
                            break
                
                response += f"📊 **Source:** Lingua Robot API\n"
                return response
            else:
                return f"❌ No definition found for '{word}' in Lingua Robot dictionary."
                
        except Exception as e:
            logger.error(f"Error formatting Lingua Robot response: {e}")
            return f"Found definition for '{word}', but there was an error formatting the response."
    
    def get_description(self) -> str:
        """Get tool description"""
        return "Look up word definitions, pronunciations, examples, and lexical information using Free Dictionary API with Lingua Robot API and intelligent WebSearch analysis fallbacks"

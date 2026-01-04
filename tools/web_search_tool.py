"""
Web search tool using Smithery Tavily search server
"""
import re
from typing import Dict, Any, List
from loguru import logger
from .base_tool import BaseTool
from .smithery_client import SmitherySearchClient
from .fallback_apis import FallbackSearchAPI
from config import config
import time


class WebSearchTool(BaseTool):
    """Tool for web search using Tavily"""
    
    def __init__(self):
        super().__init__(config.WEB_SEARCH_TOOL_URL, "WebSearch")
        self.search_keywords = [
            "search", "find", "look up", "google", "what is", "who is", "where is",
            "when is", "how to", "latest", "news", "information about", "tell me about",
            "meaning of", "means", "explain", "describe"
        ]
        # Simple in-memory cache for faster repeated searches
        self._cache = {}
        self._cache_size_limit = 30  # Smaller cache for search (results change frequently)
    
    def can_handle(self, query: str) -> bool:
        """Check if query requires web search"""
        query_lower = query.lower()
        
        # Direct search keywords
        for keyword in self.search_keywords:
            if keyword in query_lower:
                return True
        
        # Question patterns that likely need web search
        search_patterns = [
            r"what.*is.*\?",
            r"who.*is.*\?",
            r"where.*is.*\?",
            r"when.*is.*\?",
            r"how.*to.*\?",
            r"why.*is.*\?",
            r"latest.*news",
            r"current.*events",
            r"information.*about",
            r"tell.*me.*about",
            r"find.*out.*about",
            r"meaning.*of",
            r".*means.*\?",
            r"search.*meaning"
        ]
        
        for pattern in search_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # If query contains specific topics that need current info
        current_info_topics = [
            "stock price", "exchange rate", "news", "current events",
            "latest", "recent", "today", "this week", "this month"
        ]
        
        for topic in current_info_topics:
            if topic in query_lower:
                return True
        
        return False
    
    def _extract_search_query(self, query: str) -> str:
        """Extract and clean search query"""
        # Remove common prefixes
        prefixes_to_remove = [
            "search for", "find", "look up", "google", "tell me about",
            "what is", "who is", "where is", "when is", "how to",
            "information about", "find out about", "search meaning of",
            "meaning of", "what does", "explain"
        ]

        cleaned_query = query.lower()
        for prefix in prefixes_to_remove:
            if cleaned_query.startswith(prefix):
                cleaned_query = cleaned_query[len(prefix):].strip()
                break

        # Handle "X meaning" or "X means" patterns
        if cleaned_query.endswith(" meaning"):
            cleaned_query = cleaned_query[:-8].strip()
        elif " means" in cleaned_query:
            cleaned_query = cleaned_query.replace(" means", "").strip()

        # Remove question marks and clean up
        cleaned_query = cleaned_query.rstrip("?").strip()

        # For meaning queries, add "meaning" or "definition" to get better results
        if any(word in query.lower() for word in ["meaning", "means", "define"]):
            if not any(word in cleaned_query for word in ["meaning", "definition", "define"]):
                cleaned_query = f"{cleaned_query} meaning definition"

        return cleaned_query if cleaned_query else query
    
    async def execute(self, query: str, **kwargs) -> str:
        """Perform web search"""
        try:
            search_query = self._extract_search_query(query)
            logger.info(f"Performing web search for: {search_query}")

            # Check cache first for faster response (cache for 10 minutes)
            cache_key = f"{search_query.lower()}"
            if cache_key in self._cache:
                cached_data = self._cache[cache_key]
                if cached_data.get('timestamp', 0) + 600 > time.time():  # 10 minute cache
                    logger.info(f"Cache hit for search: {search_query}")
                    return cached_data['result']
                else:
                    # Remove expired cache entry
                    del self._cache[cache_key]

            # Try Smithery Tavily search API first
            if config.SMITHERY_API_TOKEN and config.SMITHERY_API_TOKEN != "your_smithery_api_token_here":
                try:
                    async with SmitherySearchClient() as client:
                        search_result = await client.search(search_query, max_results=5)

                        if search_result and "result" in search_result:
                            search_data = search_result["result"]
                            result = self._format_smithery_search_response(search_data, search_query)
                            # Cache the result
                            self._cache_result(cache_key, result)
                            return result
                except Exception as e:
                    logger.warning(f"Smithery search API failed: {e}")

            # Fallback to alternative search API
            logger.info("Using fallback search API")
            fallback_api = FallbackSearchAPI()
            search_data = await fallback_api.search(search_query, max_results=5)

            if search_data:
                result = self._format_fallback_search_response(search_data, search_query)
                # Cache the result
                self._cache_result(cache_key, result)
                return result
            else:
                return f"Sorry, I couldn't find information about '{search_query}'. Please try again later."

        except Exception as e:
            logger.error(f"Error in web search tool: {e}")
            return "Sorry, I encountered an error while searching. Please try again."
    
    def _format_smithery_search_response(self, search_data: Dict[str, Any], query: str) -> str:
        """Format Smithery search results into readable response"""
        try:
            logger.debug(f"Formatting search data: {search_data}")

            response = f"🔍 **Search Results for: {query}**\n\n"

            # The Smithery Tavily server returns data in a specific format
            if isinstance(search_data, dict):
                content = search_data.get("content", [])
                if content and isinstance(content, list):
                    search_text = content[0].get("text", "") if content else ""
                    response += f"📊 **Search Results:**\n{search_text}\n"
                else:
                    # Try to extract results from the response structure
                    results = search_data.get("results", [])
                    if results:
                        response += "📄 **Top Results:**\n"
                        for i, result in enumerate(results[:3], 1):
                            title = result.get("title", "No title")
                            url = result.get("url", "")
                            snippet = result.get("content", result.get("snippet", "No description available"))

                            if len(snippet) > 200:
                                snippet = snippet[:200] + "..."

                            response += f"\n{i}. **{title}**\n"
                            response += f"   {snippet}\n"
                            if url:
                                response += f"   🔗 {url}\n"
                    else:
                        response += f"📊 **Search Information:**\n{str(search_data)}\n"
            else:
                response += f"📊 **Search Results:**\n{str(search_data)}\n"

            return response

        except Exception as e:
            logger.error(f"Error formatting Smithery search response: {e}")
            return f"Found search results for '{query}', but there was an error formatting the response."

    def _format_fallback_search_response(self, search_data: Dict[str, Any], query: str) -> str:
        """Format fallback search results into professional, analyzed response"""
        try:
            response = f"🔍 **Professional Analysis: {query}**\n\n"

            # Add direct answer if available
            answer = search_data.get("answer", "")
            if answer:
                response += f"💡 **Executive Summary:**\n{answer}\n\n"

            # Add search results with professional formatting
            results = search_data.get("results", [])
            if results:
                response += "📊 **Key Information Sources:**\n\n"
                
                # Categorize results by type
                official_sources = []
                news_articles = []
                reference_sources = []
                other_sources = []
                
                for result in results[:5]:  # Process top 5 results
                    title = result.get("title", "No title")
                    url = result.get("url", "")
                    content = result.get("content", "No description available")
                    
                    # Categorize based on URL and title
                    url_lower = url.lower()
                    title_lower = title.lower()
                    
                    if any(keyword in url_lower for keyword in ['wikipedia', 'encyclopedia', 'dictionary']):
                        reference_sources.append((title, url, content))
                    elif any(keyword in url_lower for keyword in ['news', 'article', 'blog']):
                        news_articles.append((title, url, content))
                    elif any(keyword in url_lower for keyword in ['official', 'company', 'corp', 'inc', 'ltd']):
                        official_sources.append((title, url, content))
                    else:
                        other_sources.append((title, url, content))
                
                # Display official sources first
                if official_sources:
                    response += "🏢 **Official Sources:**\n"
                    for i, (title, url, content) in enumerate(official_sources[:2], 1):
                        response += self._format_result_item(i, title, url, content)
                    response += "\n"
                
                # Display reference sources
                if reference_sources:
                    response += "📚 **Reference Information:**\n"
                    for i, (title, url, content) in enumerate(reference_sources[:2], 1):
                        response += self._format_result_item(i, title, url, content)
                    response += "\n"
                
                # Display news articles
                if news_articles:
                    response += "📰 **Recent News & Updates:**\n"
                    for i, (title, url, content) in enumerate(news_articles[:2], 1):
                        response += self._format_result_item(i, title, url, content)
                    response += "\n"
                
                # Display other sources
                if other_sources and not (official_sources or reference_sources or news_articles):
                    response += "🔗 **Additional Resources:**\n"
                    for i, (title, url, content) in enumerate(other_sources[:3], 1):
                        response += self._format_result_item(i, title, url, content)
                    response += "\n"

            # Add professional insights
            response += self._generate_insights(query, results)
            
            # Add source info
            source = search_data.get("source", "")
            if source:
                response += f"\n📊 **Data Source:** {source}\n"

            if search_data.get('note'):
                response += f"\n💡 *{search_data['note']}*\n"

            return response

        except Exception as e:
            logger.error(f"Error formatting fallback search response: {e}")
            return f"Found search results for '{query}', but there was an error formatting the response."

    def _format_result_item(self, index: int, title: str, url: str, content: str) -> str:
        """Format individual search result item with professional styling"""
        # Clean and truncate content
        if len(content) > 150:
            content = content[:150] + "..."
        
        # Format URL for better display
        display_url = url.replace("https://", "").replace("http://", "")
        if len(display_url) > 50:
            display_url = display_url[:47] + "..."
        
        formatted_item = f"{index}. **{title}**\n"
        formatted_item += f"   📝 {content}\n"
        formatted_item += f"   🔗 **[Visit Source]({url})**\n\n"
        
        return formatted_item

    def _generate_insights(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Generate professional insights based on search results"""
        insights = "\n💼 **Professional Insights:**\n"
        
        # Analyze query type and provide relevant insights
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in ['company', 'corp', 'inc', 'ltd', 'business']):
            insights += "• **Company Profile:** This appears to be a business entity search\n"
            insights += "• **Research Tip:** Check official company websites for the most accurate information\n"
            insights += "• **Verification:** Cross-reference with multiple sources for comprehensive analysis\n"
        elif any(keyword in query_lower for keyword in ['how to', 'guide', 'tutorial', 'steps']):
            insights += "• **How-To Guide:** This is an instructional search\n"
            insights += "• **Best Practice:** Follow official documentation when available\n"
            insights += "• **Verification:** Check multiple sources to ensure accuracy\n"
        elif any(keyword in query_lower for keyword in ['what is', 'definition', 'meaning']):
            insights += "• **Definition Search:** This is a conceptual inquiry\n"
            insights += "• **Source Quality:** Academic and official sources are most reliable\n"
            insights += "• **Context:** Consider the context and domain of the term\n"
        else:
            insights += "• **General Information:** This is a general knowledge search\n"
            insights += "• **Source Evaluation:** Consider the credibility of information sources\n"
            insights += "• **Timeliness:** Check the date of information for relevance\n"
        
        insights += "\n🔍 **Next Steps:**\n"
        insights += "• Click the provided links for detailed information\n"
        insights += "• Verify information across multiple sources\n"
        insights += "• Check for the most recent updates on official websites\n"
        
        return insights
    
    def _format_search_response(self, search_data: Dict[str, Any], query: str) -> str:
        """Legacy format method for backward compatibility"""
        return self._format_fallback_search_response(search_data, query)
    
    def get_description(self) -> str:
        """Get tool description"""
        return "Search the web for current information, news, and answers to questions"
    
    def _cache_result(self, cache_key: str, result: str):
        """Cache the result for faster future lookups"""
        if len(self._cache) >= self._cache_size_limit:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }

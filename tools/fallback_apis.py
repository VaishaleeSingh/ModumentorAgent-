"""
Fallback APIs for when Smithery tools are not available
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
from loguru import logger
from config import config


class FallbackWeatherAPI:
    """Fallback weather API using OpenWeatherMap free tier"""
    
    def __init__(self):
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.api_key = config.OPENWEATHER_API_KEY
    
    async def get_current_weather(self, city: str) -> Optional[Dict[str, Any]]:
        """Get current weather using OpenWeatherMap API"""
        if not self.api_key or self.api_key == "your_openweather_api_key_here":
            return self._get_demo_weather(city)
        
        try:
            url = f"{self.base_url}/weather"
            params = {
                "q": city,
                "appid": self.api_key,
                "units": "metric"
            }
            
            # Add timeout for faster response
            timeout = aiohttp.ClientTimeout(total=4.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_openweather_data(data)
                    else:
                        logger.warning(f"OpenWeatherMap API error: {response.status}")
                        return self._get_demo_weather(city)
                        
        except Exception as e:
            logger.error(f"Error calling OpenWeatherMap API: {e}")
            return self._get_demo_weather(city)
    
    def _format_openweather_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format OpenWeatherMap data to our standard format"""
        try:
            return {
                "location": data.get("name", "Unknown"),
                "temperature": f"{data['main']['temp']:.1f}°C",
                "condition": data["weather"][0]["description"].title(),
                "humidity": f"{data['main']['humidity']}%",
                "wind_speed": f"{data['wind'].get('speed', 0) * 3.6:.1f} km/h",
                "feels_like": f"{data['main']['feels_like']:.1f}°C",
                "pressure": f"{data['main']['pressure']} hPa"
            }
        except Exception as e:
            logger.error(f"Error formatting OpenWeatherMap data: {e}")
            return self._get_demo_weather(data.get("name", "Unknown"))
    
    def _get_demo_weather(self, city: str) -> Dict[str, Any]:
        """Return demo weather data when API is not available"""
        import random
        
        conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Clear"]
        temp = random.randint(15, 30)
        
        return {
            "location": city,
            "temperature": f"{temp}°C",
            "condition": random.choice(conditions),
            "humidity": f"{random.randint(40, 80)}%",
            "wind_speed": f"{random.randint(5, 25)} km/h",
            "feels_like": f"{temp + random.randint(-3, 3)}°C",
            "pressure": f"{random.randint(1000, 1030)} hPa",
            "note": "Demo data - Get real weather by adding OpenWeatherMap API key"
        }


class FallbackSearchAPI:
    """Fallback search API using Tavily or DuckDuckGo"""

    def __init__(self):
        self.tavily_url = "https://api.tavily.com/search"
        self.duckduckgo_url = "https://api.duckduckgo.com"
        self.tavily_key = config.TAVILY_API_KEY

    async def search(self, query: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
        """Perform search using Tavily API first, then DuckDuckGo fallback"""
        # Try Tavily API first if we have the key
        if self.tavily_key and self.tavily_key != "your_tavily_api_key_here":
            try:
                return await self._search_tavily(query, max_results)
            except Exception as e:
                logger.warning(f"Tavily API failed: {e}")

        # Fallback to DuckDuckGo
        return await self._search_duckduckgo(query, max_results)

    async def _search_tavily(self, query: str, max_results: int) -> Optional[Dict[str, Any]]:
        """Search using Tavily API"""
        try:
            payload = {
                "api_key": self.tavily_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": True,
                "include_raw_content": False
            }
            
            # Add timeout for faster response
            timeout = aiohttp.ClientTimeout(total=6.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.tavily_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_tavily_data(data, query)
                    else:
                        logger.warning(f"Tavily API error: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error calling Tavily API: {e}")
            return None

    async def _search_duckduckgo(self, query: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
        """Perform search using DuckDuckGo Instant Answer API"""
        try:
            url = f"{self.duckduckgo_url}/"
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }

            # Add timeout for faster response
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_duckduckgo_data(data, query)
                    else:
                        logger.warning(f"DuckDuckGo API error: {response.status}")
                        return self._get_demo_search(query)

        except Exception as e:
            logger.error(f"Error calling DuckDuckGo API: {e}")
            return self._get_demo_search(query)
    
    def _format_tavily_data(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Format Tavily data to our standard format"""
        try:
            results = []

            # Extract results from Tavily response
            for result in data.get("results", []):
                results.append({
                    "title": result.get("title", "No title"),
                    "content": result.get("content", "No description available"),
                    "url": result.get("url", "")
                })

            return {
                "query": query,
                "results": results,
                "answer": data.get("answer", ""),
                "source": "Tavily Search API"
            }

        except Exception as e:
            logger.error(f"Error formatting Tavily data: {e}")
            return self._get_demo_search(query)

    def _format_duckduckgo_data(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Format DuckDuckGo data to our standard format"""
        try:
            results = []
            
            # Add instant answer if available
            if data.get("Abstract"):
                results.append({
                    "title": f"About {query}",
                    "content": data["Abstract"],
                    "url": data.get("AbstractURL", "")
                })
            
            # Add related topics
            for topic in data.get("RelatedTopics", [])[:3]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text", "")[:50] + "...",
                        "content": topic.get("Text", ""),
                        "url": topic.get("FirstURL", "")
                    })
            
            return {
                "query": query,
                "results": results,
                "answer": data.get("Abstract", ""),
                "source": "DuckDuckGo Instant Answer"
            }
            
        except Exception as e:
            logger.error(f"Error formatting DuckDuckGo data: {e}")
            return self._get_demo_search(query)
    
    def _get_demo_search(self, query: str) -> Dict[str, Any]:
        """Return demo search data when API is not available"""
        return {
            "query": query,
            "results": [
                {
                    "title": f"Information about {query}",
                    "content": f"This is demo search data for '{query}'. For real search results, configure Smithery API token or Tavily API key.",
                    "url": "https://example.com"
                },
                {
                    "title": f"Learn more about {query}",
                    "content": f"Additional information and resources related to {query} would appear here with real search APIs.",
                    "url": "https://example.com/learn"
                }
            ],
            "answer": f"Demo answer about {query}. Configure real APIs for actual search results.",
            "source": "Demo Data",
            "note": "Demo data - Get real search by adding Smithery or Tavily API key"
        }


class FallbackDictionaryAPI:
    """Fallback dictionary API using Free Dictionary API"""
    
    def __init__(self):
        self.base_url = "https://api.dictionaryapi.dev/api/v2/entries/en"
    
    async def get_definitions(self, word: str) -> Optional[Dict[str, Any]]:
        """Get word definitions using Free Dictionary API"""
        try:
            url = f"{self.base_url}/{word}"
            
            # Add timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=10.0)  # increased for slow networks
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_dictionary_data(data, word)
                    else:
                        logger.warning(f"Dictionary API error: {response.status}")
                        return self._get_demo_definition(word)
                        
        except asyncio.TimeoutError:
            logger.warning("Dictionary API timed out (network may be slow), using demo data")
            return self._get_demo_definition(word)
        except Exception as e:
            logger.error(f"Error calling Dictionary API: {e}")
            return self._get_demo_definition(word)
    
    def _format_dictionary_data(self, data: list, word: str) -> Dict[str, Any]:
        """Format dictionary data to our standard format"""
        try:
            if not data:
                return self._get_demo_definition(word)
            
            entry = data[0]
            definitions = []
            
            for meaning in entry.get("meanings", []):
                part_of_speech = meaning.get("partOfSpeech", "")
                for definition in meaning.get("definitions", [])[:2]:  # Limit to 2 per part of speech
                    definitions.append({
                        "part_of_speech": part_of_speech,
                        "definition": definition.get("definition", ""),
                        "example": definition.get("example", "")
                    })
            
            return {
                "word": word,
                "pronunciation": entry.get("phonetic", ""),
                "definitions": definitions,
                "source": "Free Dictionary API"
            }
            
        except Exception as e:
            logger.error(f"Error formatting dictionary data: {e}")
            return self._get_demo_definition(word)
    
    def _get_demo_definition(self, word: str) -> Dict[str, Any]:
        """Return demo definition when API is not available"""
        return {
            "word": word,
            "pronunciation": f"/{word}/",
            "definitions": [
                {
                    "part_of_speech": "noun",
                    "definition": f"Demo definition for '{word}'. This is placeholder data due to network connectivity issues.",
                    "example": f"Example usage of {word} in a sentence."
                }
            ],
            "source": "Demo Data",
            "note": "Demo data - Network connectivity issues detected. Try again later or check your internet connection."
        }

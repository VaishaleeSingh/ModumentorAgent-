"""
Weather tool using Smithery weather server
"""
import asyncio
import re
import time
from typing import Dict, Any, Optional
from loguru import logger

from .base_tool import BaseTool
from .fallback_apis import FallbackWeatherAPI
from .web_search_tool import WebSearchTool
from config import config


class WeatherTool(BaseTool):
    """Tool for getting weather information"""

    def __init__(self):
        super().__init__("", "Weather")  # Empty tool_url since we're not using Smithery directly
        self.description = "Get current weather information for any location"
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        self.fallback_search = WebSearchTool()

    def can_handle(self, query: str) -> bool:
        """Check if this tool can handle the query"""
        weather_keywords = [
            'weather', 'temperature', 'forecast', 'climate', 'humidity', 
            'wind', 'rain', 'snow', 'sunny', 'cloudy', 'storm', 'hot', 'cold'
        ]
        
        query_lower = query.lower()
        
        # Check for weather-related keywords
        if any(keyword in query_lower for keyword in weather_keywords):
            return True
        
        # Check for location patterns (city, country, etc.)
        location_patterns = [
            r'\b(weather|temperature|forecast)\s+(?:of|in|at)\s+([a-zA-Z\s,]+)',
            r'\b([a-zA-Z\s,]+)\s+(?:weather|temperature|forecast)',
            r'\b(weather|temperature|forecast)\s+([a-zA-Z\s,]+)'
        ]
        
        for pattern in location_patterns:
            if re.search(pattern, query_lower):
                return True
        
        return False

    def _extract_location(self, query: str) -> str:
        """Extract location from query"""
        query_lower = query.lower()
        
        # Remove weather-related words
        weather_words = ['weather', 'temperature', 'forecast', 'climate', 'humidity', 'wind', 'rain', 'snow', 'sunny', 'cloudy', 'storm', 'hot', 'cold', 'of', 'in', 'at', 'the']
        
        # Split query into words and filter out weather words
        words = query_lower.split()
        location_words = [word for word in words if word not in weather_words and len(word) > 2]
        
        if location_words:
            # Join the remaining words as location
            location = ' '.join(location_words).strip()
            # Clean up common artifacts
            location = re.sub(r'[^\w\s,]', '', location).strip()
            return location.title()
        
        return "Unknown Location"

    async def execute(self, query: str, **kwargs) -> str:
        """Execute the weather tool"""
        try:
            location = self._extract_location(query)
            logger.info(f"Getting weather for location: {location}")
            
            # Check cache first
            cache_key = f"weather_{location.lower()}"
            if cache_key in self.cache:
                cached_time, cached_result = self.cache[cache_key]
                if time.time() - cached_time < self.cache_duration:
                    return cached_result

            # Try Smithery weather API first
            if config.SMITHERY_API_TOKEN and config.SMITHERY_API_TOKEN != "your_smithery_api_token_here":
                try:
                    from .smithery_client import SmitheryClient
                    smithery_client = SmitheryClient()
                    
                    result = await smithery_client.call_tool(
                        "get_current_weather",
                        {"city": location}
                    )
                    
                    if result and result.get("status") == 200:
                        weather_data = result.get("data", {})
                        formatted_result = self._format_smithery_weather_response(weather_data, location)
                        # Cache the result
                        self._cache_result(cache_key, formatted_result)
                        return formatted_result
                except Exception as e:
                    logger.warning(f"Smithery weather API failed: {e}")

            # Fallback to alternative weather API
            logger.info("Using fallback weather API")
            fallback_api = FallbackWeatherAPI()
            weather_data = await fallback_api.get_current_weather(location)

            if weather_data and not weather_data.get("note", "").startswith("Demo data"):
                # Real weather data found
                result = self._format_fallback_weather_response(weather_data, location)
                # Cache the result
                self._cache_result(cache_key, result)
                return result
            else:
                # No real weather data available, use web search as fallback
                logger.info(f"No weather data found for {location}, using web search fallback")
                return await self._get_weather_info_via_web_search(location)

        except Exception as e:
            logger.error(f"Error in weather tool: {e}")
            return "Sorry, I encountered an error while getting weather information. Please try again."

    async def _get_weather_info_via_web_search(self, location: str) -> str:
        """Get weather information using web search when weather APIs fail"""
        try:
            # Search for weather information about the location
            search_query = f"current weather {location} temperature climate"
            search_result = await self.fallback_search.execute(search_query)
            
            if search_result and "Search Results" in search_result:
                # Format the search results as a weather report
                response = f"🌤️ **🌍 Weather Information: {location}** 🌤️\n\n"
                response += "📊 **📈 Information Found:**\n"
                response += f"🔍 **Search Results for weather in {location}:**\n\n"
                
                # Extract the main content from search results
                lines = search_result.split('\n')
                content_lines = []
                in_content = False
                
                for line in lines:
                    if "**Search Results:**" in line:
                        in_content = True
                        continue
                    if in_content and line.strip():
                        if line.startswith("**") and "**" in line[2:]:
                            # Skip section headers
                            continue
                        if "Note:" in line or "Demo data" in line:
                            break
                        content_lines.append(line)
                        if len(content_lines) >= 10:  # Limit content
                            break
                
                # Add the content
                if content_lines:
                    response += '\n'.join(content_lines[:8])  # Limit to 8 lines
                else:
                    response += f"Found information about {location} but specific weather data is not available.\n"
                
                response += f"\n💡 **Note:** This information is gathered from web search as real-time weather data is not available for {location}.\n"
                response += f"\n🕐 **Last Updated:** {self._get_current_time()}\n"
                response += f"\n{'─' * 50}\n"
                response += f"🌤️ **Weather information provided by ModuMentor AI via web search** 🌤️\n"
                
                return response
            else:
                return f"Sorry, I couldn't find weather information for {location}. The location might not exist or weather data might not be available."
                
        except Exception as e:
            logger.error(f"Error in web search fallback for weather: {e}")
            return f"Sorry, I couldn't get weather information for {location}. Please try again later."

    def _format_smithery_weather_response(self, weather_data: Dict[str, Any], location: str) -> str:
        """Format Smithery weather data into attractive, professional response with rich emojis"""
        try:
            logger.debug(f"Formatting weather data: {weather_data}")

            # The Smithery weather server returns data in a specific format
            # Extract the weather information from the response
            if isinstance(weather_data, dict):
                # Try to extract temperature and weather info
                content = weather_data.get("content", [])
                if content and isinstance(content, list):
                    weather_text = content[0].get("text", "") if content else ""
                else:
                    weather_text = str(weather_data)

                # Create attractive weather response with rich formatting
                response = f"🌤️ **🌍 Weather Report: {location}** 🌤️\n\n"
                response += "📊 **📈 Current Conditions:**\n"
                response += f"{weather_text}\n"
                
                # Add timestamp with clock emoji
                response += f"\n🕐 **Last Updated:** {self._get_current_time()}\n"
                
                # Add decorative footer
                response += f"\n{'─' * 50}\n"
                response += f"🌤️ **Weather data provided by Smithery Weather Service** 🌤️\n"
                
                return response
            else:
                # If it's a string response, format it nicely
                response = f"🌤️ **🌍 Weather Report: {location}** 🌤️\n\n"
                response += "📊 **📈 Current Conditions:**\n"
                response += f"{str(weather_data)}\n"
                
                # Add timestamp with clock emoji
                response += f"\n🕐 **Last Updated:** {self._get_current_time()}\n"
                
                # Add decorative footer
                response += f"\n{'─' * 50}\n"
                response += f"🌤️ **Weather data provided by Smithery Weather Service** 🌤️\n"
                
                return response

        except Exception as e:
            logger.error(f"Error formatting Smithery weather response: {e}")
            return f"Weather data received for {location}, but there was an error formatting the response."

    def _format_fallback_weather_response(self, weather_data: Dict[str, Any], location: str) -> str:
        """Format fallback weather data into attractive, professional response with rich emojis"""
        try:
            # Get weather data with fallbacks
            temp = weather_data.get('temperature', 'N/A')
            condition = weather_data.get('condition', 'N/A')
            humidity = weather_data.get('humidity', 'N/A')
            wind_speed = weather_data.get('wind_speed', 'N/A')
            feels_like = weather_data.get('feels_like', 'N/A')
            pressure = weather_data.get('pressure', 'N/A')
            
            # Get weather emoji based on condition
            weather_emoji = self._get_weather_emoji(condition)
            
            # Create attractive weather response with rich formatting
            response = f"{weather_emoji} **🌍 Weather Report: {location}** {weather_emoji}\n\n"
            
            # Main weather info with rich emojis
            response += "📊 **📈 Current Conditions:**\n"
            response += f"🌡️ **Temperature:** {temp}\n"
            response += f"☁️ **Weather:** {condition}\n"
            response += f"💧 **Humidity:** {humidity}\n"
            response += f"💨 **Wind:** {wind_speed}\n"
            
            # Additional details if available
            if feels_like and feels_like != 'N/A':
                response += f"🌡️ **Feels Like:** {feels_like}\n"
            
            if pressure and pressure != 'N/A':
                response += f"📊 **Pressure:** {pressure}\n"
            
            # Add weather insights with rich emojis
            response += self._get_enhanced_weather_insights(condition, temp, humidity)
            
            # Add note if available
            if weather_data.get('note'):
                response += f"\n💡 *{weather_data['note']}*\n"
            
            # Add timestamp with clock emoji
            response += f"\n🕐 **Last Updated:** {self._get_current_time()}\n"
            
            # Add decorative footer
            response += f"\n{'─' * 50}\n"
            response += f"🌤️ **Weather data provided by ModuMentor AI** 🌤️\n"
            
            return response

        except Exception as e:
            logger.error(f"Error formatting fallback weather response: {e}")
            return f"Weather data received for {location}, but there was an error formatting the response."

    def _get_weather_emoji(self, condition: str) -> str:
        """Get appropriate weather emoji based on condition"""
        condition_lower = condition.lower()
        
        if any(word in condition_lower for word in ['sunny', 'clear', 'fair']):
            return "☀️"
        elif any(word in condition_lower for word in ['cloudy', 'overcast', 'clouds']):
            return "☁️"
        elif any(word in condition_lower for word in ['rain', 'drizzle', 'shower']):
            return "🌧️"
        elif any(word in condition_lower for word in ['storm', 'thunder', 'lightning']):
            return "⛈️"
        elif any(word in condition_lower for word in ['snow', 'blizzard', 'sleet']):
            return "❄️"
        elif any(word in condition_lower for word in ['fog', 'mist', 'haze']):
            return "🌫️"
        elif any(word in condition_lower for word in ['windy', 'breeze']):
            return "🌪️"
        else:
            return "🌤️"

    def _get_enhanced_weather_insights(self, condition: str, temp: str, humidity: str) -> str:
        """Generate enhanced weather insights with rich emojis"""
        insights = "\n💼 **🎯 Weather Insights & Recommendations:**\n"
        
        condition_lower = condition.lower()
        temp_value = self._extract_temp_value(temp)
        
        # Temperature insights with rich emojis
        if temp_value != 'N/A':
            if temp_value > 30:
                insights += "🔥 **Hot Weather Alert:** Stay hydrated and avoid prolonged sun exposure\n"
                insights += "   💧 Drink plenty of water | 🏖️ Seek shade | 🧴 Use sunscreen\n"
            elif temp_value > 25:
                insights += "☀️ **Warm Weather:** Perfect for outdoor activities\n"
                insights += "   🚶‍♂️ Great for walking | 🏃‍♀️ Ideal for exercise | 🌳 Enjoy nature\n"
            elif temp_value > 15:
                insights += "🌤️ **Mild Weather:** Comfortable conditions for most activities\n"
                insights += "   🎯 Perfect temperature | 🚴‍♂️ Good for cycling | 🏕️ Great for camping\n"
            elif temp_value > 5:
                insights += "❄️ **Cool Weather:** Consider wearing a jacket\n"
                insights += "   🧥 Layer up | ☕ Hot drinks recommended | 🧣 Keep warm\n"
            else:
                insights += "🥶 **Cold Weather:** Bundle up and stay warm\n"
                insights += "   🧤 Wear gloves | 🧥 Heavy coat needed | 🏠 Stay indoors if possible\n"
        
        # Condition-specific insights with rich emojis
        if any(word in condition_lower for word in ['rain', 'drizzle', 'shower']):
            insights += "☔ **Rain Alert:** Carry an umbrella and wear waterproof shoes\n"
            insights += "   🌂 Bring umbrella | 👢 Waterproof footwear | 🚗 Drive carefully\n"
        elif any(word in condition_lower for word in ['snow', 'blizzard']):
            insights += "❄️ **Snow Alert:** Drive carefully and dress warmly\n"
            insights += "   🚗 Slow driving | 🧤 Warm gloves | 🧥 Heavy coat\n"
        elif any(word in condition_lower for word in ['storm', 'thunder']):
            insights += "⛈️ **Storm Alert:** Stay indoors and avoid outdoor activities\n"
            insights += "   🏠 Stay inside | ⚡ Avoid electronics | 📱 Keep phone charged\n"
        elif any(word in condition_lower for word in ['fog', 'mist']):
            insights += "🌫️ **Fog Alert:** Drive with caution and use low beam lights\n"
            insights += "   🚗 Slow down | 💡 Low beams | 🚶‍♂️ Be extra careful\n"
        elif any(word in condition_lower for word in ['clear', 'sunny']):
            insights += "☀️ **Clear Skies:** Great weather for outdoor activities\n"
            insights += "   🏃‍♀️ Perfect for running | 🚴‍♂️ Great for cycling | 🏕️ Ideal for camping\n"
        elif any(word in condition_lower for word in ['cloudy', 'overcast']):
            insights += "☁️ **Cloudy Conditions:** Moderate UV exposure\n"
            insights += "   🧴 Still use sunscreen | 🌳 Good for outdoor activities | 📸 Great for photos\n"
        
        # Humidity insights with rich emojis
        if humidity != 'N/A':
            humidity_value = self._extract_humidity_value(humidity)
            if humidity_value > 80:
                insights += "💧 **High Humidity:** May feel warmer than actual temperature\n"
                insights += "   🧊 Stay cool | 💧 Drink more water | 🏠 Use air conditioning\n"
            elif humidity_value < 30:
                insights += "🏜️ **Low Humidity:** Stay hydrated and moisturize\n"
                insights += "   💧 Drink extra water | 🧴 Use moisturizer | 💨 Use humidifier\n"
        
        # Add general tips
        insights += "\n💡 **Pro Tips:**\n"
        insights += "   📱 Check weather updates regularly\n"
        insights += "   🎒 Always be prepared for weather changes\n"
        insights += "   🌍 Stay informed about local weather alerts\n"
        
        return insights

    def _extract_temp_value(self, temp_str: str) -> float:
        """Extract numeric temperature value from string"""
        try:
            import re
            # Extract first number from temperature string
            match = re.search(r'(\d+(?:\.\d+)?)', temp_str)
            if match:
                return float(match.group(1))
            return 'N/A'
        except:
            return 'N/A'

    def _extract_humidity_value(self, humidity_str: str) -> float:
        """Extract numeric humidity value from string"""
        try:
            import re
            # Extract first number from humidity string
            match = re.search(r'(\d+(?:\.\d+)?)', humidity_str)
            if match:
                return float(match.group(1))
            return 'N/A'
        except:
            return 'N/A'

    def _get_current_time(self) -> str:
        """Get current time in a readable format"""
        from datetime import datetime
        return datetime.now().strftime("%I:%M %p, %B %d, %Y")
    
    def _format_weather_response(self, weather_data: Dict[str, Any], location: str) -> str:
        """Legacy format method for backward compatibility"""
        return self._format_fallback_weather_response(weather_data, location)
    
    def get_description(self) -> str:
        """Get tool description"""
        return "Get current weather conditions and forecasts for any location worldwide"
    
    def _cache_result(self, cache_key: str, result: str):
        """Cache the result for faster future lookups"""
        self.cache[cache_key] = (time.time(), result)

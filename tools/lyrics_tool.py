"""
Lyrics tool for finding song lyrics and music information
"""
import re
from typing import Dict, Any, Optional
from loguru import logger
from .base_tool import BaseTool
from .smithery_client import SmitheryClient
from config import config


class LyricsClient(SmitheryClient):
    """Client for lyrics operations using Smithery MCP"""

    def __init__(self):
        super().__init__("https://server.smithery.ai/@lyrics-ai/lyrics-mcp")
    
    async def search_lyrics(self, song_title: str, artist: str = None) -> Dict[str, Any]:
        """Search for song lyrics"""
        params = {"song": song_title}
        if artist:
            params["artist"] = artist
        
        return await self.call_tool("search_lyrics", params)
    
    async def get_song_info(self, song_title: str, artist: str = None) -> Dict[str, Any]:
        """Get song information"""
        params = {"song": song_title}
        if artist:
            params["artist"] = artist
        
        return await self.call_tool("get_song_info", params)


class LyricsTool(BaseTool):
    """Tool for finding song lyrics and music information"""
    
    def __init__(self):
        super().__init__("https://server.smithery.ai/@lyrics-ai/lyrics-mcp", "Lyrics")
        self.lyrics_client = LyricsClient()
        self.lyrics_keywords = [
            "lyrics", "song", "music", "sing", "verse", "chorus", "artist", "album",
            "track", "melody", "tune", "composition", "songwriter", "musician"
        ]
    
    def can_handle(self, query: str) -> bool:
        """Check if this tool can handle the query"""
        query_lower = query.lower()
        
        # Check for lyrics-specific keywords
        lyrics_indicators = [
            "lyrics", "song lyrics", "words of", "text of", "sing",
            "what are the lyrics", "lyrics of", "lyrics for"
        ]
        
        if any(indicator in query_lower for indicator in lyrics_indicators):
            return True
        
        # Check for song title patterns
        song_patterns = [
            r"lyrics?\s+(?:of|for|to)\s+(.+)",
            r"(.+)\s+lyrics?",
            r"song\s+(.+)",
            r"what\s+are\s+the\s+lyrics?\s+(?:of|for|to)\s+(.+)"
        ]
        
        for pattern in song_patterns:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    def get_description(self) -> str:
        """Get tool description"""
        return "Lyrics: Find song lyrics, music information, artist details, and song recommendations"
    
    async def execute(self, query: str, **kwargs) -> str:
        """Execute lyrics search with appropriate copyright handling"""
        try:
            # Extract song and artist information
            song_info = self._parse_lyrics_query(query)
            song_title = song_info.get("song", "")
            artist = song_info.get("artist", "")
            
            logger.info(f"Searching for lyrics: {song_title} by {artist if artist else 'unknown artist'}")
            
            # Try to get lyrics using Smithery MCP first
            try:
                lyrics_result = await self.lyrics_client.search_lyrics(song_title, artist)
                if lyrics_result and "lyrics" in lyrics_result:
                    return self._format_lyrics_response(lyrics_result, song_title, artist)
            except Exception as e:
                logger.warning(f"Smithery lyrics search failed: {e}")
            
            # Fallback to providing helpful guidance
            return self._provide_lyrics_guidance(song_title, artist)
            
        except Exception as e:
            logger.error(f"Error in lyrics tool: {e}")
            return "Sorry, I encountered an error while searching for lyrics. Please try again."
    
    def _parse_lyrics_query(self, query: str) -> Dict[str, str]:
        """Parse the query to extract song and artist information"""
        query_lower = query.lower().strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            "lyrics of", "lyrics for", "lyrics to", "song lyrics of", "song lyrics for",
            "what are the lyrics of", "what are the lyrics for", "find lyrics for",
            "search lyrics for", "get lyrics of", "show lyrics of", "lyrics"
        ]
        
        for prefix in prefixes_to_remove:
            if query_lower.startswith(prefix):
                query_lower = query_lower[len(prefix):].strip()
                break
        
        # Try to extract artist and song
        # Pattern: "song by artist" or "artist - song"
        patterns = [
            r"(.+?)\s+by\s+(.+)",
            r"(.+?)\s+-\s+(.+)",
            r"(.+?)\s+from\s+(.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                return {
                    "song": match.group(1).strip(),
                    "artist": match.group(2).strip()
                }
        
        # If no artist found, treat entire query as song title
        return {
            "song": query_lower.strip(),
            "artist": ""
        }
    
    def _format_lyrics_response(self, lyrics_data: Dict[str, Any], song_title: str, artist: str) -> str:
        """Format lyrics response with copyright considerations"""
        try:
            lyrics = lyrics_data.get("lyrics", "")
            song_info = lyrics_data.get("song_info", {})
            
            # Provide a brief excerpt and guidance
            lines = lyrics.split('\n')
            excerpt = '\n'.join(lines[:8]) if len(lines) > 8 else lyrics
            
            response = f"🎵 **{song_title}"
            if artist:
                response += f" by {artist}"
            response += "**\n\n"
            
            if song_info:
                if song_info.get("album"):
                    response += f"📀 **Album:** {song_info['album']}\n"
                if song_info.get("year"):
                    response += f"📅 **Year:** {song_info['year']}\n"
                response += "\n"
            
            response += f"🎼 **Lyrics Preview:**\n```\n{excerpt}\n```\n\n"
            
            if len(lines) > 8:
                response += "📝 **Note:** This is a preview. For complete lyrics, please visit:\n"
                response += "• Official music platforms (Spotify, Apple Music)\n"
                response += "• Licensed lyrics sites (Genius.com, AZLyrics.com)\n"
                response += "• Artist's official website\n\n"
            
            response += "⚖️ *Lyrics are copyrighted material. Please support the artist by using official sources.*"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting lyrics response: {e}")
            return self._provide_lyrics_guidance(song_title, artist)
    
    def _provide_lyrics_guidance(self, song_title: str, artist: str) -> str:
        """Provide professional guidance on finding lyrics with clickable links"""
        try:
            response = f"🎵 **Professional Lyrics Search: {song_title}"
            if artist:
                response += f" by {artist}"
            response += "**\n\n"
            
            # Create search-friendly query
            search_query = f"{song_title}"
            if artist:
                search_query += f" {artist}"
            search_query += " lyrics"
            
            response += "🔍 **Where to Find Complete Lyrics:**\n\n"
            
            # Streaming Platforms (with clickable links)
            response += "🎧 **Streaming Platforms:**\n"
            platforms = [
                ("Spotify", f"https://open.spotify.com/search/{search_query.replace(' ', '%20')}"),
                ("Apple Music", f"https://music.apple.com/search?term={search_query.replace(' ', '%20')}"),
                ("YouTube Music", f"https://music.youtube.com/search?q={search_query.replace(' ', '%20')}"),
                ("Amazon Music", f"https://music.amazon.com/search/{search_query.replace(' ', '%20')}")
            ]
            
            for platform, url in platforms:
                response += f"• **[🎵 {platform}]({url})** - Official lyrics display\n"
            response += "\n"
            
            # Licensed Lyrics Websites
            response += "📝 **Licensed Lyrics Websites:**\n"
            lyrics_sites = [
                ("Genius.com", f"https://genius.com/search?q={search_query.replace(' ', '%20')}", "Comprehensive lyrics database with annotations"),
                ("AZLyrics.com", f"https://search.azlyrics.com/search.php?q={search_query.replace(' ', '%20')}", "Large collection of song lyrics"),
                ("LyricFind.com", f"https://www.lyricfind.com/search?q={search_query.replace(' ', '%20')}", "Licensed lyrics provider"),
                ("MetroLyrics.com", f"https://www.metrolyrics.com/search.html?search={search_query.replace(' ', '%20')}", "Popular lyrics platform")
            ]
            
            for site, url, description in lyrics_sites:
                response += f"• **[📄 {site}]({url})** - {description}\n"
            response += "\n"
            
            # Artist Official Sources
            response += "👤 **Artist Official Sources:**\n"
            if artist:
                artist_search = artist.replace(' ', '%20')
                response += f"• **[🏠 Official Website](https://www.google.com/search?q={artist_search}+official+website)** - Artist's official site\n"
                response += f"• **[📱 Social Media](https://www.google.com/search?q={artist_search}+social+media)** - Official social accounts\n"
                response += f"• **[💿 Album Information](https://www.google.com/search?q={artist_search}+{song_title.replace(' ', '%20')}+album)** - Album liner notes\n"
            else:
                response += "• **[🏠 Official Website](https://www.google.com/search?q=official+website)** - Artist's official site\n"
                response += "• **[📱 Social Media](https://www.google.com/search?q=social+media)** - Official social accounts\n"
                response += "• **[💿 Album Information](https://www.google.com/search?q=album+information)** - Album liner notes\n"
            response += "\n"
            
            # Quick Search Options
            response += "⚡ **Quick Search Options:**\n"
            quick_searches = [
                ("Google Search", f"https://www.google.com/search?q={search_query.replace(' ', '+')}"),
                ("YouTube Search", f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"),
                ("Bing Search", f"https://www.bing.com/search?q={search_query.replace(' ', '+')}")
            ]
            
            for search_engine, url in quick_searches:
                response += f"• **[🔍 {search_engine}]({url})** - General search results\n"
            response += "\n"
            
            # Professional Insights
            response += "💼 **Professional Insights:**\n"
            response += "• **Copyright Protection:** Song lyrics are protected intellectual property\n"
            response += "• **Legal Access:** Use official sources to support artists and respect copyright\n"
            response += "• **Quality Assurance:** Official platforms provide the most accurate lyrics\n"
            response += "• **Real-time Features:** Many streaming services display lyrics while playing\n"
            response += "\n"
            
            # Next Steps
            response += "🎯 **Recommended Next Steps:**\n"
            response += "1. **Click the streaming platform links** for official lyrics display\n"
            response += "2. **Visit licensed lyrics websites** for comprehensive information\n"
            response += "3. **Check artist's official sources** for the most accurate content\n"
            response += "4. **Use search engines** to find additional resources\n"
            response += "\n"
            
            response += "⚖️ **Legal Notice:** Song lyrics are copyrighted material. Please use official sources to support artists and respect copyright laws.\n\n"
            response += "💡 **Pro Tip:** Many streaming services now display lyrics in real-time while you listen!"
            
            return response
            
        except Exception as e:
            logger.error(f"Error providing lyrics guidance: {e}")
            return f"Sorry, I encountered an error while providing guidance for '{song_title}'. Please try searching for the lyrics manually on music platforms."

"""
Configuration settings for the Autogen Telegram Bot
"""
import os
from typing import Optional
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables (try multiple locations for cloud compatibility)
def load_environment():
    """Load environment variables with cloud platform compatibility"""
    # Try loading from .env file (local development)
    env_loaded = load_dotenv()
    if env_loaded:
        logger.info("✅ Loaded environment variables from .env file")
    else:
        logger.info("ℹ️ No .env file found, using system environment variables")

    # Also try loading from common cloud locations
    for env_file in ['.env.local', '.env.production']:
        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
            logger.info(f"✅ Loaded additional environment from {env_file}")

load_environment()

class Config:
    """Configuration class for the bot"""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Gemini API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
    
    # Smithery Configuration
    SMITHERY_API_TOKEN: str = os.getenv("SMITHERY_API_TOKEN", "")
    SMITHERY_ENABLED: bool = os.getenv("SMITHERY_ENABLED", "true").lower() == "true"
    WEATHER_TOOL_URL: str = "https://server.smithery.ai/@isdaniel/mcp_weather_server"
    WEB_SEARCH_TOOL_URL: str = "https://server.smithery.ai/@tavily-ai/tavily-mcp"
    DICTIONARY_TOOL_URL: str = "https://server.smithery.ai/@emro624/dictionary-mcp-main"

    # Alternative API Keys for fallback
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # Google Sheets & Gmail Configuration
    GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")
    GOOGLE_SHEETS_API_KEY: str = os.getenv("GOOGLE_SHEETS_API_KEY", "")
    GMAIL_ADDRESS: str = os.getenv("GMAIL_ADDRESS", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    
    # Email Service API (No password required - just API key)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "ModuMentor Bot <bot@modumentor.ai>")
    
    # Project Configuration
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "ModuMentor")
    PROJECT_LOGO_URL: str = os.getenv("PROJECT_LOGO_URL", "/favicon.ico")
    PROJECT_FAVICON_URL: str = os.getenv("PROJECT_FAVICON_URL", "/favicon.ico")
    
    # Bot Configuration
    MAX_MESSAGE_LENGTH: int = 4096  # Telegram message limit
    RESPONSE_TIMEOUT: int = 10  # seconds (reduced from 15)
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")
    
    # Tool Configuration
    TOOL_TIMEOUT: int = 5  # seconds (reduced from 8)
    MAX_RETRIES: int = 1  # reduced from 2 for faster fallback
    
    # Performance Optimization
    ENABLE_FAST_MODE: bool = os.getenv("ENABLE_FAST_MODE", "true").lower() == "true"
    SKIP_SMITHERY_ON_TIMEOUT: bool = True  # Skip Smithery if it times out once
    USE_CACHE_FIRST: bool = True  # Check cache before making API calls
    PARALLEL_REQUESTS: bool = True  # Enable parallel API requests where possible
    
    # Quota Management
    GEMINI_QUOTA_LIMIT: int = 50  # Free tier limit
    GEMINI_QUOTA_RESET_HOUR: int = 0  # UTC hour when quota resets (midnight UTC)
    ENABLE_QUOTA_MONITORING: bool = True
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration with detailed debugging"""
        logger.info("🔍 Validating environment variables...")

        # Check all environment variables
        all_env_vars = {
            "TELEGRAM_BOT_TOKEN": cls.TELEGRAM_BOT_TOKEN,
            "GEMINI_API_KEY": cls.GEMINI_API_KEY,
            "GEMINI_MODEL": cls.GEMINI_MODEL,
            "PORT": os.getenv("PORT", "8080"),
        }

        # Log what we found (without exposing sensitive values)
        for var_name, var_value in all_env_vars.items():
            if var_value:
                masked_value = var_value[:8] + "..." if len(var_value) > 8 else "SET"
                logger.info(f"✅ {var_name}: {masked_value}")
            else:
                logger.warning(f"❌ {var_name}: NOT SET")

        # Check required variables
        required_vars = [
            ("TELEGRAM_BOT_TOKEN", cls.TELEGRAM_BOT_TOKEN),
            ("GEMINI_API_KEY", cls.GEMINI_API_KEY),
        ]

        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)

        if missing_vars:
            logger.error(f"💥 Missing required environment variables: {', '.join(missing_vars)}")
            logger.error("💡 Make sure to set these variables in your cloud platform dashboard:")
            for var in missing_vars:
                logger.error(f"   - {var}")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        logger.info("✅ All required environment variables are set")
        return True

# Global config instance
config = Config()

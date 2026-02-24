"""
Configuration module with validation
"""
import os
from dotenv import load_dotenv
from typing import Optional
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Configuration error"""
    pass


class Config:
    """Application configuration with validation"""
    
    # Green API (required)
    GREEN_API_ID_INSTANCE = os.getenv('GREEN_API_ID_INSTANCE')
    GREEN_API_TOKEN_INSTANCE = os.getenv('GREEN_API_TOKEN_INSTANCE')
    GREEN_API_URL = "https://api.green-api.com"
    
    # Group ID for reports (required)
    GROUP_ID = os.getenv('GROUP_ID', '')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/database.db')
    
    # Upload settings
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads/photos')
    MAX_PHOTO_SIZE = int(os.getenv('MAX_PHOTO_SIZE', '10485760'))  # 10MB default
    
    # Redis (optional)
    REDIS_URL = os.getenv('REDIS_URL')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/bot.log')
    
    # Test phone (optional)
    YOUR_PHONE = os.getenv('YOUR_PHONE', '')
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate required configuration
        Raises ConfigError if validation fails
        """
        errors = []
        
        # Required Green API settings
        if not cls.GREEN_API_ID_INSTANCE:
            errors.append("GREEN_API_ID_INSTANCE is required")
        if not cls.GREEN_API_TOKEN_INSTANCE:
            errors.append("GREEN_API_TOKEN_INSTANCE is required")
        
        # Validate GROUP_ID format
        if not cls.GROUP_ID:
            errors.append("GROUP_ID is required for sending reports")
        elif '@' not in cls.GROUP_ID:
            errors.append("GROUP_ID must include @g.us or @c.us suffix")
        
        # Create necessary directories
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(os.path.dirname(cls.LOG_FILE), exist_ok=True)
        os.makedirs('data', exist_ok=True)
        
        if errors:
            error_msg = "Configuration errors:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ConfigError(error_msg)
        
        # Log successful configuration
        logger.info("✅ Configuration validated successfully")
        logger.info(f"📁 Upload folder: {cls.UPLOAD_FOLDER}")
        logger.info(f"📊 Log level: {cls.LOG_LEVEL}")
        
        return True
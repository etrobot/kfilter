"""
Configuration module for loading environment variables
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Look for .env file in the project root (parent of backend directory)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Admin configuration
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')

# ZAI Deepsearch configuration
ZAI_BEARER_TOKEN = os.getenv('ZAI_BEARER_TOKEN', '')
ZAI_COOKIE_STR = os.getenv('ZAI_COOKIE_STR', '')

# THS API configuration (if needed)
THS_COOKIE_V = os.getenv('THS_COOKIE_V', 'A5lFEWDLFZlL3MkNmn0O1b5bro52JoyfdxqxbLtOFUA_wrfwA3adqAdqwTFI')

def is_zai_configured() -> bool:
    """Check if ZAI credentials are properly configured"""
    return bool(ZAI_BEARER_TOKEN and ZAI_COOKIE_STR and 
                ZAI_BEARER_TOKEN != 'your_bearer_token_here' and 
                ZAI_COOKIE_STR != 'your_cookie_string_here')

def get_zai_credentials() -> tuple[str, str]:
    """Get ZAI credentials"""
    return ZAI_BEARER_TOKEN, ZAI_COOKIE_STR
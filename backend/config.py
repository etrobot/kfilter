"""
Configuration module for loading environment variables
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from typing import Tuple, Dict, Any

# Load environment variables from .env file
# Look for .env file in the project root (parent of backend directory)
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
env_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=env_path)

# JSON config file path (preferred over .env)
CONFIG_JSON_PATH = BASE_DIR / 'config.json'

# Admin configuration (static, from env)
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')

def _load_config_json() -> Dict[str, Any]:
    """Load JSON config from disk if exists, otherwise return empty dict."""
    try:
        if CONFIG_JSON_PATH.is_file():
            with open(CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        # Silently ignore read errors and fall back to env
        pass
    return {}

def _save_config_json(data: Dict[str, Any]) -> None:
    """Persist JSON config to disk atomically."""
    CONFIG_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CONFIG_JSON_PATH.with_suffix('.json.tmp')
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, CONFIG_JSON_PATH)

def _get_env_or_default(key: str, default: str = '') -> str:
    value = os.getenv(key)
    return value if value is not None else default


# THS API configuration (if needed)
THS_COOKIE_V = os.getenv('THS_COOKIE_V', 'A5lFEWDLFZlL3MkNmn0O1b5bro52JoyfdxqxbLtOFUA_wrfwA3adqAdqwTFI')

def is_zai_configured() -> bool:
    """Check if ZAI credentials are properly configured (always read latest)."""
    bearer, cookie =get_zai_credentials()
    return bool(bearer and cookie and 
                bearer != 'your_bearer_token_here' and 
                cookie != 'your_cookie_string_here')

def get_zai_credentials() -> Tuple[str, str]:
    """Get ZAI credentials (always read latest)."""
    return _load_config_json().get('ZAI_BEARER_TOKEN').strip(), _load_config_json().get('ZAI_COOKIE_STR').strip()

def set_zai_credentials(bearer_token: str, cookie_str: str) -> None:
    """Persist ZAI credentials to backend/config.json."""
    data = _load_config_json()
    data['ZAI_BEARER_TOKEN'] = bearer_token
    data['ZAI_COOKIE_STR'] = cookie_str
    _save_config_json(data)

def get_openai_config() -> Tuple[str, str]:
    """Get OpenAI API configuration (API key and base URL)."""
    cfg = _load_config_json()
    api_key = (cfg.get('OPENAI_API_KEY') or '').strip()
    base_url = (cfg.get('OPENAI_BASE_URL') or '').strip()
    
    return api_key, base_url

def is_openai_configured() -> bool:
    """Check if OpenAI API is properly configured."""
    api_key, _ = get_openai_config()
    return bool(api_key and api_key != 'your_openai_api_key_here')

def set_system_config(config_data: dict) -> None:
    """Persist system configuration (ZAI + OpenAI) to backend/config.json."""
    data = _load_config_json()
    
    # Update ZAI configuration if provided
    if 'ZAI_BEARER_TOKEN' in config_data:
        data['ZAI_BEARER_TOKEN'] = config_data['ZAI_BEARER_TOKEN']
    if 'ZAI_COOKIE_STR' in config_data:
        data['ZAI_COOKIE_STR'] = config_data['ZAI_COOKIE_STR']
    
    # Update OpenAI configuration if provided
    if 'OPENAI_API_KEY' in config_data:
        data['OPENAI_API_KEY'] = config_data['OPENAI_API_KEY']
    if 'OPENAI_BASE_URL' in config_data:
        data['OPENAI_BASE_URL'] = config_data['OPENAI_BASE_URL']
    
    _save_config_json(data)
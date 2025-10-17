import requests, json, uuid
from typing import Generator, Dict, Optional, Any
import logging
from datetime import datetime
import re
import os
from threading import Lock
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib.parse
import hmac
import hashlib
import base64

class ResponseStore:
    _instance = None
    _lock = Lock()
    _store: Dict[str, str] = {}
    _last_response: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ResponseStore, cls).__new__(cls)
        return cls._instance

    def save_response(self, response_id: str, response: str) -> None:
        with self._lock:
            self._store[response_id] = response
            self._last_response = response

    def get_response(self, response_id: Optional[str] = None) -> Optional[str]:
        with self._lock:
            if response_id:
                return self._store.get(response_id)
            return self._last_response


class ZAIChatClient:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize ZAI Chat Client with configuration.
        
        Args:
            config: Configuration dictionary. If None, will use default configuration.
        """
        # Use provided config or default values
        self.config = config or {}
        
        # Core authentication settings
        self.base_url = self.config.get('base_url', 'https://chat.z.ai')
        self.bearer_token = self.config.get('bearer_token', 'token')
        self.user_id = self.config.get('user_id', 'a8085b86-4e72-405c-9eaf-020ec25043ae')
        
        self.response_store = ResponseStore()
        self._setup_headers_and_cookies()
        self._setup_session_with_retry()

    def _setup_headers_and_cookies(self):
        """Setup base headers using configuration."""
        self.base_headers = {
            'X-FE-Version': self.config.get('fe_version', 'prod-fe-1.0.95'),
            'sec-ch-ua-platform': f'"{self.config.get("platform", "macOS")}"',
            'Authorization': f'Bearer {self.bearer_token}',
            'Referer': self.config.get('referer', 'https://chat.z.ai/c/d272520f-17f8-4384-9801-2b7e2bead6f5'),
            'Accept-Language': self.config.get('accept_language', 'en-US'),
            'sec-ch-ua': self.config.get('sec_ch_ua', '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"'),
            'sec-ch-ua-mobile': self.config.get('sec_ch_ua_mobile', '?0'),
            'User-Agent': self.config.get('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'),
            'Content-Type': 'application/json',
        }
    
    def _generate_signature(self, params: Dict[str, Any], content: str) -> Dict[str, str]:
        """Generate signature using the algorithm pattern.
        
        Args:
            params: Request parameters including timestamp, requestId, user_id
            content: The message content to sign
            
        Returns:
            Dictionary containing signature and timestamp
        """
        def _hmac_sha256(key: bytes, msg: bytes) -> str:
            return hmac.new(key, msg, hashlib.sha256).hexdigest()

        # Validate required parameters
        for param in ["timestamp", "requestId", "user_id"]:
            if param not in params or not params.get(param):
                raise ValueError(f"Missing required parameter: {param}")

        request_time = int(params.get("timestamp", datetime.now().timestamp() * 1000))
        signature_key = self.config.get('signature_key', 'junjie')
        expire_minutes = self.config.get('signature_expire_minutes', 5)

        # Level 1 signature: Time-based signature with configurable expiry
        signature_expire = request_time // (expire_minutes * 60 * 1000)
        signature_1_plaintext = str(signature_expire)
        signature_1 = _hmac_sha256(signature_key.encode('utf-8'), signature_1_plaintext.encode('utf-8'))

        # Level 2 signature: Content and parameters
        content_encoded = base64.b64encode(content.encode('utf-8')).decode('ascii')
        signature_params = str(','.join([f"{k},{params[k]}" for k in sorted(params.keys())]))
        signature_2_plaintext = f"{signature_params}|{content_encoded}|{str(request_time)}"
        signature_2 = _hmac_sha256(signature_1.encode('utf-8'), signature_2_plaintext.encode('utf-8'))

        return {
            "signature": signature_2,
            "timestamp": str(request_time)
        }

    def _get_headers_with_signature(self, timestamp: str, request_params: Dict[str, Any], content: str = ""):
        """Generate headers with dynamic signature for the given timestamp and content"""
        headers = self.base_headers.copy()
        
        try:
            # Generate dynamic signature
            signature_data = self._generate_signature(request_params, content)
            headers['X-Signature'] = signature_data['signature']
        except Exception as e:
            logging.warning(f"Failed to generate signature: {e}. Using fallback.")
            # Fallback to static signature if generation fails
            headers['X-Signature'] = '33e8ed07967b76a11cc6788b85d41fe2ad3a34671161f07929a659314994dc9f'
        
        return headers

    def _setup_session_with_retry(self):
        """Setup requests session with retry strategy for handling timeouts and server errors"""
        self.session = requests.Session()
        
        # Configure retry strategy using configuration
        retry_strategy = Retry(
            total=self.config.get('max_retries', 3),
            status_forcelist=self.config.get('retry_status_codes', [429, 500, 502, 503, 504]),
            allowed_methods=["HEAD", "GET", "POST"],
            backoff_factor=self.config.get('backoff_factor', 2),
            raise_on_status=False
        )
        
        # Mount the adapter to the session
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set timeouts from configuration
        connect_timeout = self.config.get('connect_timeout', 30)
        read_timeout = self.config.get('read_timeout', 180)
        self.timeout = (connect_timeout, read_timeout)

    def stream_chat_completion(
        self, 
        messages: list, 
        model: Optional[str] = None,
        response_id: Optional[str] = None
    ) -> Generator[str, None, str]:
        """
        Stream chat completion from ZAI API

        Args:
            messages: List of message dictionaries with role and content
            model: Model to use for completion
            response_id: Optional ID to store the response for later retrieval

        Yields:
            Generator that yields chunks of the response
            
        Returns:
            The complete response text
        """
        logging.info("[DEBUG] stream_chat_completion called")
        if not response_id:
            response_id = str(uuid.uuid4())
        
        # Use default model from configuration if not provided
        if not model:
            model = self.config.get('default_model', 'GLM-4-6-API-V1')

        # Build query parameters from configuration
        screen_width = self.config.get('screen_width', '1920')
        screen_height = self.config.get('screen_height', '1080')
        viewport_width = self.config.get('viewport_width', '1040')
        viewport_height = self.config.get('viewport_height', '968')
        
        base_query_params = {
            'user_id': self.user_id,
            'version': self.config.get('version', '0.0.1'),
            'platform': self.config.get('platform_param', 'web'),
            'token': self.bearer_token,
            'user_agent': urllib.parse.quote(self.config.get('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36')),
            'language': self.config.get('language', 'zh-CN'),
            'languages': self.config.get('languages', 'zh-CN,zh-TW,en-US,en,ja'),
            'timezone': self.config.get('timezone', 'Asia/Shanghai'),
            'cookie_enabled': 'true',
            'screen_width': screen_width,
            'screen_height': screen_height,
            'screen_resolution': f'{screen_width}x{screen_height}',
            'viewport_height': viewport_height,
            'viewport_width': viewport_width,
            'viewport_size': f'{viewport_width}x{viewport_height}',
            'color_depth': self.config.get('color_depth', '24'),
            'pixel_ratio': self.config.get('pixel_ratio', '2'),
            'current_url': urllib.parse.quote(self.config.get('referer', 'https://chat.z.ai/c/d272520f-17f8-4384-9801-2b7e2bead6f5')),
            'pathname': '/c/d272520f-17f8-4384-9801-2b7e2bead6f5',
            'search': '',
            'hash': '',
            'host': 'chat.z.ai',
            'hostname': 'chat.z.ai',
            'protocol': 'https:',
            'referrer': '',
            'title': urllib.parse.quote('Z.ai Chat - Free AI powered by GLM-4.6 & GLM-4.5'),
            'timezone_offset': self.config.get('timezone_offset', '-480'),
            'is_mobile': 'false',
            'is_touch': 'false',
            'max_touch_points': '0',
            'browser_name': self.config.get('browser_name', 'Chrome'),
            'os_name': self.config.get('os_name', 'Mac OS')
        }
        
        # Build features configuration
        features_list = [
            {'type': 'mcp', 'server': 'vibe-coding', 'status': 'hidden'},
            {'type': 'mcp', 'server': 'ppt-maker', 'status': 'hidden'},
            {'type': 'mcp', 'server': 'image-search', 'status': 'hidden'},
            {'type': 'mcp', 'server': 'deep-research', 'status': 'pinned'},
            {'type': 'web_search', 'server': 'web_search_h', 'status': 'hidden'},
            {'type': 'mcp', 'server': 'deep-web-search', 'status': 'hidden'},
            {'type': 'mcp', 'server': 'advanced-search', 'status': 'hidden'}
        ]
        
        json_data = {
            'stream': True,
            'model': model,
            'messages': messages,
            'params': {},
            'mcp_servers': self.config.get('mcp_servers', ['deep-research']),
            'features': {
                'image_generation': self.config.get('enable_image_generation', False),
                'web_search': self.config.get('enable_web_search', True),
                'auto_web_search': self.config.get('enable_auto_web_search', False),
                'preview_mode': self.config.get('preview_mode', True),
                # 'flags': self.config.get('flags', ['deep_research']),
                'flags': [],
                'features': features_list,
                'enable_thinking': self.config.get('enable_thinking', False),
            },
            'variables': {
                '{{USER_NAME}}': self.config.get('user_name', 'ken196502@mailfence.com'),
                '{{USER_LOCATION}}': self.config.get('user_location', 'Unknown'),
                '{{CURRENT_DATETIME}}': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '{{CURRENT_DATE}}': datetime.now().strftime('%Y-%m-%d'),
                '{{CURRENT_TIME}}': datetime.now().strftime('%H:%M:%S'),
                '{{CURRENT_WEEKDAY}}': datetime.now().strftime('%A'),
                '{{CURRENT_TIMEZONE}}': self.config.get('timezone', 'Asia/Shanghai'),
                '{{USER_LANGUAGE}}': self.config.get('user_language', 'en-US'),
            },
            'model_item': {
                'id': model,
                'name': self.config.get('model_name', 'GLM-4.6'),
                'owned_by': self.config.get('model_owned_by', 'openai'),
                'openai': {
                    'id': model,
                    'name': model,
                    'owned_by': self.config.get('model_owned_by', 'openai'),
                    'openai': {'id': model},
                    'urlIdx': self.config.get('model_url_idx', 1),
                },
                'urlIdx': self.config.get('model_url_idx', 1),
            },
            'chat_id': str(uuid.uuid4()),
            'id': str(uuid.uuid4())
        }

        # Base URL for the chat completion endpoint
        url = f'{self.base_url}/api/chat/completions'

        # Retry logic for the entire request using configuration
        max_retries = self.config.get('max_retries', 3)
        retry_delay = self.config.get('retry_delay', 20)
        last_exception = None

        for attempt in range(max_retries):
            full_response = ""
            try:
                timestamp = str(int(time.time() * 1000))
                request_id = str(uuid.uuid4())
                dynamic_query_params = base_query_params.copy()
                dynamic_query_params.update({
                    'timestamp': timestamp,
                    'requestId': request_id,
                    'signature_timestamp': timestamp,
                    'local_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                    'utc_time': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
                })

                query_string = urllib.parse.urlencode(dynamic_query_params)
                full_url = f'{url}?{query_string}'

                logging.info(f"[DEBUG] Attempt {attempt + 1}/{max_retries} for chat completion request")
                
                # Extract the last user message content for signature generation
                last_user_message = ""
                for message in messages:
                    if message.get("role") == "user" and message.get("content"):
                        content = message.get("content")
                        if isinstance(content, str):
                            last_user_message = content
                        elif isinstance(content, list):
                            texts = []
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    texts.append(item.get("text", ""))
                                    break
                            last_user_message = "".join(texts)
                
                # Prepare signature parameters
                signature_params = {
                    'timestamp': timestamp,
                    'requestId': request_id,
                    'user_id': self.user_id
                }
                
                # Generate headers with signature for this specific request
                headers = self._get_headers_with_signature(timestamp, signature_params, last_user_message)
                full_response = ""
                html_tags = set()
                
                with self.session.post(
                    full_url,
                    headers=headers,
                    json=json_data,
                    stream=True,
                    timeout=self.timeout
                ) as response:
                    logging.debug(f"Response status code: {response.status_code}")
                    response.raise_for_status()
                    # Use a more sophisticated approach to track output
                    last_output = ""
                    output_buffer = ""
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            if decoded_line.startswith('data: '):
                                data = json.loads(decoded_line[6:])
                                try:
                                    # Handle different response types
                                    if data.get('type') == 'chat:completion':
                                        # Check for delta_content (incremental updates)
                                        if 'delta_content' in data['data']:
                                            content = data['data']['delta_content']
                                        # Check for edit_content (full content updates)
                                        # elif 'edit_content' in data['data']:
                                        #     content = data['data']['edit_content']
                                        # Check for content (direct content)
                                        elif 'content' in data['data']:
                                            content = data['data']['content']
                                        else:
                                            content = ""

                                        # Handle different phases
                                        phase = data['data'].get('phase', '')
                                        if phase == 'thinking':
                                            # Skip thinking phase content or handle it differently
                                            continue
                                    else:
                                        content = ""
                                    # Ensure we only keep plain text
                                    if isinstance(content, dict):
                                        # Drop JSON objects to avoid non-plain text
                                        content = ""

                                    def clean_to_plain_text(text: str) -> str:
                                        if not text:
                                            return ""
                                        # Remove fenced code blocks (```...```), including json/xml/etc
                                        text = re.sub(r"```[\s\S]*?```", "", text, flags=re.DOTALL)
                                        # Remove <summary>...</summary>
                                        text = re.sub(r"<summary[\s\S]*?</summary>", "", text, flags=re.DOTALL)
                                        # Replace <a ...>inner</a> with just inner text
                                        text = re.sub(r"<a\s+[^>]*>(.*?)</a>", r"\1", text, flags=re.DOTALL)
                                        # Strip remaining tags like <...>
                                        text = re.sub(r"<[^>]+>", "", text)
                                        # Process each line
                                        cleaned_lines = []
                                        for line in text.splitlines():
                                            # Skip empty lines
                                            ls = line.strip()
                                            if not ls:
                                                continue
                                            # Skip lines starting with >
                                            if ls.startswith('>'):
                                                continue
                                            # Skip lines that look like standalone JSON
                                            if (ls.startswith("{") and ls.endswith("}") and ":" in ls) or (ls.startswith("[") and ls.endswith("]") and ":" in ls):
                                                continue
                                            # Skip lines containing unicode escape sequences (like \u4e09\u805a)
                                            if re.search(r'\\u[0-9a-fA-F]{4}', line):
                                                continue
                                            # Skip lines that look like they contain encoded content
                                            if re.search(r'%[0-9a-fA-F]{2}', line):
                                                continue
                                            # Skip lines that look like they contain encoded HTML entities
                                            if re.search(r'&[a-z]+;', line):
                                                continue
                                            # Skip lines that look like they contain URL-encoded content
                                            if re.search(r'%[0-9A-F]{2}', line):
                                                continue
                                            cleaned_lines.append(line)
                                        text = "\n".join(cleaned_lines)
                                        # Collapse excessive whitespace
                                        text = re.sub(r"\n{3,}", "\n\n", text)
                                        text = re.sub(r"[\t\x0b\x0c\r]", " ", text)
                                        return text.strip()

                                    content = clean_to_plain_text(content)

                                    # Track any tags we might have encountered (for logging only)
                                    other_tags = re.findall(r'<[^>]+>', content)
                                    for tag in other_tags:
                                        html_tags.add(tag)

                                    i = 0
                                    while i < min(len(last_output), len(content)) and last_output[i] == content[i]:
                                        i += 1

                                    # If text is completely different or shorter than last_output
                                    # (model might have restarted or modified content)
                                    if i < len(last_output) * 0.8:  # Less than 80% match
                                        # Consider it a restart
                                        logging.debug("\n[DEBUG] Content restart detected")
                                        new_text = content
                                        output_buffer = ""
                                    else:
                                        # Normal incremental update
                                        new_text = content[i:]

                                    last_output = content

                                    # Detect and handle duplicates in the stream
                                    if new_text and not output_buffer.endswith(new_text):
                                        if os.getenv('TESTING'):
                                            new_text = new_text.rstrip('\n')
                                        output_buffer += new_text
                                       # Do not append any XML/HTML back into the stream
                                        full_response += new_text
                                        yield new_text
                                except Exception as e:
                                    logging.error(f"Failed to extract content: {e}")
                            else:
                                logging.debug(decoded_line)
                    
                    self.response_store.save_response(response_id, full_response)

                    if html_tags:
                        logging.info("\n[INFO] 收集到的HTML标签:")
                        for tag in sorted(html_tags):
                            logging.info(f"  {tag}")

                    return full_response

            except requests.exceptions.ChunkedEncodingError as e:
                last_exception = e
                logging.info(f"[STREAM] Chunked encoding ended early: {e}")
                if full_response.strip():
                    logging.info("[STREAM] Returning collected partial response")
                    self.response_store.save_response(response_id, full_response)
                    return full_response
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logging.info(f"[RETRY] Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                logging.error(f"[RETRY] All {max_retries} attempts failed due to chunked encoding errors")
                raise e

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, 
                    requests.exceptions.HTTPError) as e:
                last_exception = e
                logging.warning(f"[RETRY] Attempt {attempt + 1} failed with {type(e).__name__}: {str(e)}")
                
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logging.info(f"[RETRY] Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    logging.error(f"[RETRY] All {max_retries} attempts failed. Last error: {str(e)}")
                    raise e
                    
            except Exception as e:
                # For other exceptions, don't retry
                logging.error(f"[ERROR] Non-retryable error occurred: {type(e).__name__}: {str(e)}")
                raise e
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Initialize with configuration
    config = {
        'bearer_token': 'your_bearer_token_here',
        'user_id': 'your_user_id_here'
    }
    
    client = ZAIChatClient(config=config)
    
    # Example with response ID
    response_id = str(uuid.uuid4())
    messages = [
        {
            'role': 'user',
            'content': "BTC or ETH, which one is better?"
        }
    ]
    
    # Stream the response
    logging.info("Streaming response:")
    response_chunks = []
    for chunk in client.stream_chat_completion(messages, response_id=response_id):
        response_chunks.append(chunk)
    logging.info("".join(response_chunks))
    
    logging.info("Chat completed")
    
    # Later, retrieve the response by ID
    stored_response = client.response_store.get_response(response_id)
    logging.info("Retrieved stored response: %s", stored_response[:100] + "..." if stored_response else "No response found")


def create_zai_client_from_config() -> Optional[ZAIChatClient]:
    """Create ZAI client from configuration.
    
    Returns:
        ZAIChatClient instance if configuration is available, None otherwise.
    """
    try:
        # Import here to avoid circular imports
        from .services import get_zai_client_config
        
        config = get_zai_client_config()
        if not config or not config.get('bearer_token') or not config.get('user_id'):
            logging.warning("ZAI client configuration not available")
            return None
            
        return ZAIChatClient(config=config)
        
    except Exception as e:
        logging.error(f"Failed to create ZAI client from config: {e}")
        return None


import requests, json, uuid
from typing import Generator, Dict, Optional, Any
import logging
from datetime import datetime
import re
import os
from threading import Lock

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
    def __init__(self, base_url="https://chat.z.ai", bearer_token='token', cookie_str='cookie_str'):
        self.base_url = base_url
        self.bearer_token = bearer_token
        self.cookie_str = cookie_str
        self.response_store = ResponseStore()
        self._setup_headers_and_cookies()

    def _setup_headers_and_cookies(self):
        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US',
            'Authorization': f'Bearer {self.bearer_token}',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Origin': 'https://chat.z.ai',
            'Referer': 'https://chat.z.ai/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'X-FE-Version': 'prod-fe-1.0.67',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }

        # Parse cookie string into dict for requests
        self.cookies = {}
        if self.cookie_str:
            for cookie in self.cookie_str.split(';'):
                if '=' in cookie:
                    key, value = cookie.strip().split('=', 1)
                    self.cookies[key] = value

    def stream_chat_completion(
        self, 
        messages: list, 
        model: str = "0727-360B-API",
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
            
        full_response = ""
        json_data = {
            'stream': True,
            'model': model,
            'messages': messages,
            'params': {},
            'mcp_servers': [
                'deep-web-search',
            ],
            'features': {
                'image_generation': False,
                'web_search': False,
                'auto_web_search': False,
                'preview_mode': True,
                'flags': [],
                'features': [
                    {
                        'type': 'mcp',
                        'server': 'deep-web-search',
                        'status': 'selected',
                    },
                    {
                        'type': 'mcp',
                        'server': 'vibe-coding',
                        'status': 'hidden',
                    },
                    {
                        'type': 'mcp',
                        'server': 'ppt-maker',
                        'status': 'hidden',
                    },
                    {
                        'type': 'mcp',
                        'server': 'image-search',
                        'status': 'hidden',
                    },
                ],
                'enable_thinking': True,
            },
            'variables': {
                '{{USER_NAME}}': 'Guest-1747374205709',
                '{{USER_LOCATION}}': 'Unknown',
                '{{CURRENT_DATETIME}}': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '{{CURRENT_DATE}}': datetime.now().strftime('%Y-%m-%d'),
                '{{CURRENT_TIME}}': datetime.now().strftime('%H:%M:%S'),
                '{{CURRENT_WEEKDAY}}': datetime.now().strftime('%A'),
                '{{CURRENT_TIMEZONE}}': 'Asia/Shanghai',
                '{{USER_LANGUAGE}}': 'en-US',
            },
            'model_item': {
                'id': model,
                'name': 'GLM-4.5',
                'owned_by': 'openai',
                'openai': {
                    'id': model,
                    'name': model,
                    'owned_by': 'openai',
                    'openai': {
                        'id': model,
                    },
                    'urlIdx': 1,
                },
                'urlIdx': 1,
                'info': {
                    'id': model,
                    'user_id': '7080a6c5-5fcc-4ea4-a85f-3b3fac905cf2',
                    'base_model_id': None,
                    'name': 'GLM-4.5',
                    'params': {
                        'top_p': 0.95,
                        'temperature': 0.6,
                        'max_tokens': 80000,
                    },
                    'meta': {
                        'profile_image_url': '/static/favicon.png',
                        'description': 'Most advanced model, proficient in coding and tool use',
                        'capabilities': {
                            'vision': False,
                            'citations': False,
                            'preview_mode': False,
                            'web_search': False,
                            'language_detection': False,
                            'restore_n_source': False,
                            'mcp': True,
                            'file_qa': True,
                            'returnFc': True,
                            'returnThink': True,
                            'think': True,
                        },
                        'mcpServerIds': [
                            'deep-web-search',
                            'ppt-maker',
                            'image-search',
                            'vibe-coding',
                        ],
                        'tags': [],
                    },
                    'access_control': None,
                    'is_active': True,
                    'updated_at': 1753675170,
                    'created_at': 1753624357,
                },
                'actions': [],
                'tags': [],
            },
            'chat_id': 'local',
            'id': str(uuid.uuid4())
        }

        logging.debug(f"[DEBUG] Sending POST request to: {self.base_url}/api/chat/completions")
        # 创建一个集合来存储HTML标签
        html_tags = set()

        with requests.post(
            f'{self.base_url}/api/chat/completions',
            headers=self.headers,
            cookies=self.cookies,
            json=json_data,
            stream=True
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
            
            # Save the complete response
            self.response_store.save_response(response_id, full_response)
            
            # Log collected HTML tags if any
            if html_tags:
                logging.info("\n[INFO] 收集到的HTML标签:")
                for tag in sorted(html_tags):
                    logging.info(f"  {tag}")
                    
            return full_response


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Initialize with your token and cookie
    bearer_token = 'your_bearer_token_here'
    cookie_str = 'your_cookie_string_here'
    
    client = ZAIChatClient(bearer_token=bearer_token, cookie_str=cookie_str)
    
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
    for chunk in client.stream_chat_completion(messages, model="0727-360B-API", response_id=response_id):
        response_chunks.append(chunk)
    logging.info("".join(response_chunks))
    
    logging.info("Chat completed")
    
    # Later, retrieve the response by ID
    stored_response = client.response_store.get_response(response_id)
    logging.info("Retrieved stored response: %s", stored_response[:100] + "..." if stored_response else "No response found")


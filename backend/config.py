"""
Configuration module for loading environment variables
"""
import os
from pathlib import Path
import json
from typing import Tuple, Dict, Any

# Load environment variables from .env file
# Look for .env file in the project root (parent of backend directory)
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent

# JSON config file path (preferred over .env)
CONFIG_JSON_PATH = BASE_DIR / 'config.json'

def load_config_json() -> Dict[str, Any]:
    """Load JSON config from disk if exists, otherwise return empty dict."""
    try:
        if CONFIG_JSON_PATH.is_file():
            with open(CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        # Silently ignore read errors and fall back to env
        pass
    return {}

def save_config_json(data: Dict[str, Any]) -> None:
    """Persist JSON config to disk atomically."""
    CONFIG_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CONFIG_JSON_PATH.with_suffix('.json.tmp')
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, CONFIG_JSON_PATH)

# THS API configuration (if needed)
THS_COOKIE_V = os.getenv('THS_COOKIE_V', 'A5lFEWDLFZlL3MkNmn0O1b5bro52JoyfdxqxbLtOFUA_wrfwA3adqAdqwTFI')

def is_zai_configured() -> bool:
    """Check if ZAI credentials are properly configured (always read latest)."""
    bearer, cookie, user_id = get_zai_credentials()
    return bool(bearer and user_id and 
                bearer != 'your_bearer_token_here' and 
                user_id != 'your_user_id_here')

def get_zai_credentials() -> Tuple[str, str, str]:
    """Get ZAI credentials (always read latest).
    
    Returns:
        Tuple containing (bearer_token, cookie_str, user_id). Returns empty strings if not configured.
    """
    config = load_config_json()
    bearer = config.get('ZAI_BEARER_TOKEN', '')
    cookie = config.get('ZAI_COOKIE_STR', '')
    user_id = config.get('ZAI_USER_ID', '')
    return (bearer.strip() if bearer else '', 
            cookie.strip() if cookie else '',
            user_id.strip() if user_id else '')

def set_zai_credentials(bearer_token: str, cookie_str: str, user_id: str = '') -> None:
    """Persist ZAI credentials to backend/config.json."""
    data = load_config_json()
    data['ZAI_BEARER_TOKEN'] = bearer_token
    data['ZAI_COOKIE_STR'] = cookie_str
    if user_id:
        data['ZAI_USER_ID'] = user_id
    save_config_json(data)

def get_openai_config() -> Tuple[str, str]:
    """Get OpenAI API configuration (API key and base URL)."""
    cfg = load_config_json()
    api_key = (cfg.get('OPENAI_API_KEY') or '').strip()
    base_url = (cfg.get('OPENAI_BASE_URL') or '').strip()
    
    return api_key, base_url

def is_openai_configured() -> bool:
    """Check if OpenAI API is properly configured."""
    api_key, _ = get_openai_config()
    return bool(api_key and api_key != 'your_openai_api_key_here')

def set_system_config(config_data: dict) -> None:
    """Persist system configuration (ZAI + OpenAI) to backend/config.json."""
    data = load_config_json()
    
    # Update ZAI configuration if provided
    if 'ZAI_BEARER_TOKEN' in config_data:
        data['ZAI_BEARER_TOKEN'] = config_data['ZAI_BEARER_TOKEN']
        os.environ['ZAI_BEARER_TOKEN'] = config_data['ZAI_BEARER_TOKEN']
    if 'ZAI_COOKIE_STR' in config_data:
        data['ZAI_COOKIE_STR'] = config_data['ZAI_COOKIE_STR']
        os.environ['ZAI_COOKIE_STR'] = config_data['ZAI_COOKIE_STR']
    if 'ZAI_USER_ID' in config_data:
        data['ZAI_USER_ID'] = config_data['ZAI_USER_ID']
        os.environ['ZAI_USER_ID'] = config_data['ZAI_USER_ID']
    
    # Update OpenAI configuration if provided
    if 'OPENAI_API_KEY' in config_data:
        data['OPENAI_API_KEY'] = config_data['OPENAI_API_KEY']
        os.environ['OPENAI_API_KEY'] = config_data['OPENAI_API_KEY']
    if 'OPENAI_BASE_URL' in config_data:
        data['OPENAI_BASE_URL'] = config_data['OPENAI_BASE_URL']
        os.environ['OPENAI_BASE_URL'] = config_data['OPENAI_BASE_URL']
    
    save_config_json(data)


CATEGORY='''
# 二级市场投资研究七大方向
## 科技 (Technology)
### 产业替代革命
- 人工智能(AI)芯片与算力
- 半导体设备与材料(国产替代)
- 信创(IT基础设施国产化)
- 云计算与SaaS(替代传统软件)
### 需求层次飞跃
- 元宇宙与VR/AR(下一代交互)
- 自动驾驶解决方案
- 量子计算(远期算力飞跃)
### 环境剧变
- 网络安全(地缘博弈与数据安全)
- 卫星互联网(战略基础设施)

## 资源 (Resources)
### 产业替代革命
- 锂、钴、镍(新能源金属)
- 稀土(永磁电机核心材料)
- 铜(电动化与电网升级)
### 需求层次飞跃
- 工业金属(经济结构升级需求)
### 环境剧变
- 黄金(避险资产)
- 铀(能源自主与战略储备)
- 石油、天然气(地缘冲突与供给格局重塑)

## 金融 (Financials)
### 产业替代革命
- 金融科技(FinTech)(替代传统服务)
- 数字支付与数字货币
### 需求层次飞跃
- 财富管理(居民资产配置升级)
- 消费金融(提升消费能力)
### 环境剧变
- 黄金ETF(避险工具)
- 跨境金融(地缘格局变化)

## 消费 (Consumer)
### 产业替代革命
- 新能源汽车(终端产品)
- 智能家居(替代传统家电)
### 需求层次飞跃
- 高端白酒与奢侈品(社交与身份需求)
- 医美、护肤(颜值经济)
- 品牌服饰与国潮(文化自信)
- 预制菜与复合调味品(便捷生活)
- 旅游与航空(体验式消费)
- 电子烟(新型可选消费)
### 环境剧变
- 必选消费(粮油食品)(抗通胀防御)

## 医疗 (Healthcare)
### 产业替代革命
- 创新药(替代传统疗法)
- CXO(研发生产模式革新)
- 基因编辑与细胞治疗(技术革命)
### 需求层次飞跃
- 高端医疗器械(早筛、微创)
- 疫苗(预防升级)
- 连锁医疗服务(眼科、牙科、康复)
- 抗衰老与保健(长寿需求)
### 环境剧变
- 医疗器械(国产替代)
- 血制品、抗病毒药物(战略储备)

## 工业 (Industrials)
### 产业替代革命
- 工业机器人与自动化(机器换人)
- 激光设备(先进制造)
- 数控机床(工业母机国产化)
- 新能源设备(光伏风电设备)
### 需求层次飞跃
- 航空航天(大飞机产业链)
- 高端零部件(供应链升级)
### 环境剧变
- 国防军工(地缘冲突)
- 能源装备(能源安全)
- 物流供应链(供应链安全)

## 公用事业 (Utilities)
### 产业替代革命
- 光伏、风力发电站(绿色能源替代)
- 储能(电力系统变革)
- 特高压(能源资源配置)
### 需求层次飞跃
- (公用事业属性偏防御，需求飞跃性不强)
### 环境剧变
- 电力运营商(能源保供核心)
- 燃气、水务(通胀定价与防御)
'''


def filter_deepest_nodes(mapping: Dict[str, str]) -> Dict[str, str]:
    """过滤出最深层的节点"""
    filtered = {}
    for path in mapping:
        # 检查是否有更深的子路径
        is_deepest = True
        for other_path in mapping:
            if other_path.startswith(path + '/'):
                is_deepest = False
                break
        if is_deepest:
            filtered[path] = mapping[path]
    return filtered


def parse_category_hierarchy() -> Dict[str, str]:
    """直接解析CATEGORY为分类路径映射
    
    Returns:
        分类名称到完整路径的映射字典
    """
    mapping = {}
    lines = CATEGORY.split('\n')
    path_stack = []
    
    for line in lines:
        original_line = line
        line = line.strip()
        if not line or line == '---':
            continue
            
        # 确定层级
        level = 0
        if line.startswith('#'):
            # 标题层级：# 为 0级，## 为 1级，### 为 2级
            level = len([c for c in line if c == '#']) - 1
        elif line.startswith('-') or line.startswith('*'):
            # 列表层级：通过前导空格计算
            stripped = original_line.lstrip()
            indent_spaces = len(original_line) - len(stripped)
            level = (indent_spaces // 2) + 3  # 列表从第3级开始（在###标题后）
        else:
            continue
            
        # 清理文本
        cleaned = line
        if line.startswith('#'):
            cleaned = line.lstrip('#').strip()
        elif line.startswith('-') or line.startswith('*'):
            cleaned = line.lstrip('-*').strip()
        
        if cleaned:
            # 调整路径栈到当前层级
            while len(path_stack) > level:
                path_stack.pop()
            
            path_stack.append(cleaned)
            
            # 为叶子节点（具体分类）添加映射
            if level >= 3:  # 只为最深层的分类项添加映射
                full_path = "/".join(path_stack)
                mapping[cleaned] = full_path
    
    return mapping



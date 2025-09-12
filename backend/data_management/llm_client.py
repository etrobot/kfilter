from __future__ import annotations
import json
import logging
from typing import Dict, Any
import openai
from config import parse_category_hierarchy

logger = logging.getLogger(__name__)

def get_llm_client(scheme='openai'):
    """
    获取 OpenAI 或其他 LLM 服务的客户端

    Args:
        scheme: 客户端类型，支持 'openai' 和 'siliconflow'

    Returns:
        openai.Client: 配置好的客户端实例
    """
    try:
        # 从配置文件获取API Key和Base URL
        from config import get_openai_config
        api_key, base_url = get_openai_config()
        
        if not api_key:
            raise ValueError("OpenAI API Key 未配置，请在配置对话框中设置")
            
        client_kwargs = {'api_key': api_key}
        if base_url:
            client_kwargs['base_url'] = base_url
            
        client = openai.OpenAI(**client_kwargs)
        logger.info(f"已成功初始化 {scheme} 客户端")
        return client
    except Exception as e:
        logger.error(f"初始化 {scheme} 客户端出错: {e}")
        raise

def llm_gen_dict(client: openai.Client, model: str, query: str, format_example: Dict, stream: bool = False) -> Dict:
    """
    使用LLM生成符合指定格式的字典结果
    
    Args:
        client: OpenAI客户端实例
        model: 模型名称
        query: 查询内容
        format_example: 输出格式示例
        stream: 是否使用流式输出
        
    Returns:
        Dict: 解析后的字典结果
    """
    
    # 构建系统提示，强制输出为JSON格式
    system_prompt = f"""你是一个专业的加密货币分析师。请严格按照以下JSON格式输出结果，不要包含任何其他文字：

输出格式示例：
{json.dumps(format_example, ensure_ascii=False, indent=2)}

重要要求：
1. 输出必须是有效的JSON格式
2. 不要包含任何解释或额外文字
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.3,
            stream=stream
        )
        
        if stream:
            # 处理流式响应
            content = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content += chunk.choices[0].delta.content
        else:
            content = response.choices[0].message.content
        
        # 简单的JSON解析，假设LLM返回有效JSON
        result = json.loads(content)
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        # 返回默认格式
        return {}
    except Exception as e:
        logger.error(f"LLM调用失败: {e}")
        return {}


def evaluate_content_with_llm(content: str,model='gpt-oss-120b') -> Dict:
    """
    使用OpenAI API评估内容

    Args:
        model: 模型名称
        model: 模型名称
        content: 待评估的内容
        criteria_dict: 评估标准字典

    Returns:
        dict: 包含详细评估结果的字典，格式如下：
        {
            "overall_score": float,  # 总分
            "detailed_scores": dict,  # 各项详细分数
            "top_scoring_criterion": str,  # 最高分标准
            "top_score": float,  # 最高分数
        }
    """
    
    # 构建输出格式示例
    format_example = {
        "category":"叶节点分类",
        "criteria_name_1":{"score":"1-5", "explanation":"中文评分说明"},
        "criteria_name_2":{"score":"1-5", "explanation":"中文评分说明"},
        "criteria_name_...":{"score":"1-5", "explanation":"..."},
    }
    
    query = content + """
{
  "产业革命新旧替代": {
    "1分": "传统成熟行业，技术稳定无颠覆风险，但增长空间有限",
    "2分": "行业存在渐进式创新，但尚未形成替代趋势",
    "3分": "新技术已显现替代潜力，处于商业化早期阶段",
    "4分": "替代趋势明确，新技术/模式渗透率快速提升（10%-30%）",
    "5分": "革命性替代进行中，旧模式被快速淘汰，新势力确立主导地位（渗透率>30%）"
  },
  "政策利好": {
    "1分": "行业受政策限制或强监管，发展空间受限",
    "2分": "政策环境中性，无特别支持也无明显限制",
    "3分": "获得一般性政策支持（如纳入发展规划），但具体措施待落地",
    "4分": "获得实质性政策支持（如税收优惠、补贴、专项贷款等）",
    "5分": "国家级战略重点，多重政策红利叠加，监管环境极度友好"
  },
  "业绩爆发增长": {
    "1分": "业绩下滑或停滞，增长率≤0%",
    "2分": "温和增长，增长率0%-15%，与GDP增速相当",
    "3分": "较快增长，增长率15%-30%，显现成长性",
    "4分": "高速增长，增长率30%-50%，显著超越行业平均",
    "5分": "爆发式增长，增长率>50%，且可持续性较强"
  },
  "股权变更": {
    "1分": "大股东减持，核心管理层离职，股权结构不稳定",
    "2分": "股权结构稳定但无变化，缺乏外部资源注入",
    "3分": "引入战略投资者或实施股权激励，带来积极预期",
    "4分": "知名产业资本或国资入股，带来资源协同效应",
    "5分": "控制权变更，优质股东入驻，公司战略发生根本性转变"
  },
  "高层次需求爆发": {
    "1分": "需求萎缩，产品服务属于被淘汰或过度竞争范畴",
    "2分": "需求稳定，满足基本生活生产需要，增长缓慢",
    "3分": "需求升级，为提升效率或品质支付溢价的意愿增强",
    "4分": "新需求爆发，为健康、娱乐、自我实现等付费的意愿强烈",
    "5分": "创造新需求，定义新品类或新模式，市场空间彻底打开"
  },
  "题材新鲜度": {
    "1分": "陈旧题材，出现已超过5年，市场已充分消化，炒作价值耗尽",
    "2分": "传统题材，出现已3-5年，偶有反复但缺乏新意，市场反应平淡",
    "3分": "成熟题材，出现已1-3年，有新催化剂重新激活，获得关注",
    "4分": "新兴题材，出现已6个月-1年，概念相对新颖，具备想象空间",
    "5分": "全新题材，出现不足6个月，引发市场高度关注和资金追捧"
  }
}
"""+'并添加分类名称比如“激光设备(先进制造)”，必须来自以下分类：'+str(list(parse_category_hierarchy().keys()))
    
    # 使用 llm_gen_dict 来强约束输出为 python 字典
    client = get_llm_client()
    result = llm_gen_dict(client, model, query, format_example, stream=False)

    # 检查结果是否为空或无效
    if not result or not isinstance(result, dict):
        logger.warning("LLM返回空结果或无效格式")
        return {
            "criteria_result": {},
            "overall_score": 0,
            "detailed_scores": {},
            "top_scoring_criterion": "无",
            "top_score": 0,
        }
    
    # 过滤出有效的评分项（排除category等非评分字段）
    valid_criteria = {}
    for k, v in result.items():
        if isinstance(v, dict) and 'score' in v:
            try:
                # 确保score是数字
                score = float(v['score'])
                if 1 <= score <= 5:  # 有效分数范围
                    valid_criteria[k] = v
            except (ValueError, TypeError):
                logger.warning(f"无效的分数格式: {k} = {v}")
                continue
    
    if not valid_criteria:
        logger.warning("没有找到有效的评分项")
        return {
            "criteria_result": result,
            "overall_score": 0,
            "detailed_scores": result,
            "top_scoring_criterion": "无",
            "top_score": 0,
        }
    
    # 计算总分和最高分
    total_score = sum(float(v['score']) for v in valid_criteria.values()) / 5 * 100 / len(valid_criteria)
    top_item = max(valid_criteria.items(), key=lambda x: float(x[1]['score']))
    top_criterion = top_item[0]
    top_score = float(top_item[1]['score']) / 5 * 100
    
    return {
        "criteria_result": result,
        "overall_score": round(total_score, 2),
        "detailed_scores": result,  # Add this for compatibility
        "top_scoring_criterion": top_criterion,
        "top_score": round(top_score, 2),
    }
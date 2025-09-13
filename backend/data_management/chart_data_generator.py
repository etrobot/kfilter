"""
Chart data generation utilities for visualization components
"""
from __future__ import annotations
import logging
from typing import List, Dict, Any
from config import parse_category_hierarchy


logger = logging.getLogger(__name__)


def generate_category_based_sunburst_chart_data(sectors_data: List[dict]) -> dict:
    """基于AI评估的category分类路径生成多层旭日图数据
    
    Args:
        sectors_data: List of sector analysis results from extended_analysis_results.json
    
    Returns:
        Dict with multi-layer sunburst chart data structure based on category hierarchy
    """
    # 解析CATEGORY为分类路径映射
    category_mapping = parse_category_hierarchy()
    
    logger.info(f"解析到的分类映射: {len(category_mapping)} 个分类")
    for name, path in list(category_mapping.items())[:5]:  # 打印前5个作为示例
        logger.info(f"  {name} -> {path}")
    
    # 按分类层级组织数据
    category_hierarchy = {}
    
    # 处理每个板块的评估结果
    for sector in sectors_data:
        sector_name = sector.get("sector_name", "未知板块")
        sector_code = sector.get("sector_code", "")
        llm_evaluation = sector.get("llm_evaluation", {})
        
        if not llm_evaluation:
            continue
            
        criteria_result = llm_evaluation.get("criteria_result", {})
        overall_score = llm_evaluation.get("overall_score", 0)
        
        if overall_score <= 0:
            continue
        
        # 获取AI评估的分类
        ai_category = criteria_result.get("category", "")
        if not ai_category:
            continue
            
        logger.info(f"处理板块 {sector_name}({sector_code}), AI分类: {ai_category}, 总分: {overall_score}")
        
        # 查找匹配的分类路径
        matched_path = None
        matched_category = None
        
        # 首先尝试精确匹配
        if ai_category in category_mapping:
            matched_path = category_mapping[ai_category]
            matched_category = ai_category
        else:
            # 尝试部分匹配
            for category_name, path in category_mapping.items():
                if ai_category in category_name or category_name in ai_category:
                    matched_path = path
                    matched_category = category_name
                    break
            
            if not matched_path:
                # 尝试关键词匹配
                ai_keywords = ai_category.replace('(', ' ').replace(')', ' ').split()
                for category_name, path in category_mapping.items():
                    for keyword in ai_keywords:
                        if len(keyword) > 1 and keyword in category_name:
                            matched_path = path
                            matched_category = category_name
                            break
                    if matched_path:
                        break
        
        if matched_path:
            logger.info(f"  匹配到: {matched_category} -> {matched_path}")
            # 构建层级结构
            path_parts = matched_path.split('/')
            current_level = category_hierarchy
            
            # 为每一层创建结构并累计分数
            for i, part in enumerate(path_parts):
                if part not in current_level:
                    current_level[part] = {
                        "sectors": [],
                        "children": {},
                        "total_score": 0,
                        "sector_count": 0
                    }
                
                # 在每一层都累计分数
                current_level[part]["total_score"] += overall_score
                current_level[part]["sector_count"] += 1
                
                # 在最深层添加板块数据
                if i == len(path_parts) - 1:
                    current_level[part]["sectors"].append({
                        "name": sector_name,
                        "code": sector_code,
                        "value": round(overall_score, 1),
                        "category": ai_category
                    })
                
                current_level = current_level[part]["children"]
        else:
            logger.warning(f"  未找到匹配路径，AI分类: {ai_category}")
    
    # 构建旭日图数据结构
    def build_sunburst_node(name: str, data: dict) -> dict:
        """递归构建旭日图节点"""
        node = {
            "name": name,
            "value": round(data["total_score"], 1)
        }
        
        # 添加子节点
        children = []
        
        # 添加子分类
        for child_name, child_data in data["children"].items():
            if child_data["total_score"] > 0:
                children.append(build_sunburst_node(child_name, child_data))
        
        # 添加板块（叶子节点）
        if data["sectors"]:
            # 按分数排序
            sorted_sectors = sorted(data["sectors"], key=lambda x: x["value"], reverse=True)
            for sector in sorted_sectors:
                children.append({
                    "name": sector["name"],
                    "value": sector["value"],
                    "category": sector["category"]
                })
        
        if children:
            node["children"] = children
            
        return node
    
    # 构建根节点的子节点
    root_children = []
    total_value = 0
    
    for category_name, category_data in category_hierarchy.items():
        if category_data["total_score"] > 0:
            child_node = build_sunburst_node(category_name, category_data)
            root_children.append(child_node)
            total_value += category_data["total_score"]
    
    # 检查是否只有一个顶级分类，如果是则尝试展开其子分类
    if len(root_children) == 1 and "children" in root_children[0]:
        single_category = root_children[0]
        # 如果该分类有子分类，则将子分类提升为顶级分类
        if single_category["children"] and len(single_category["children"]) > 1:
            logger.info(f"检测到只有一个顶级分类 '{single_category['name']}'，将其子分类提升为顶级分类")
            root_children = single_category["children"]
        elif single_category["children"] and len(single_category["children"]) == 1:
            # 如果子分类也只有一个，继续向下展开
            sub_category = single_category["children"][0]
            if "children" in sub_category and sub_category["children"] and len(sub_category["children"]) > 1:
                logger.info(f"检测到单一子分类 '{sub_category['name']}'，继续展开其子分类")
                root_children = sub_category["children"]
            else:
                # 如果所有层级都只有一个分类，直接使用板块数据
                all_sectors = _get_all_sectors(single_category)
                if len(all_sectors) > 1:
                    logger.info(f"所有分类层级都只有单一分类，直接展示 {len(all_sectors)} 个板块")
                    root_children = all_sectors
    
    # 按总分排序
    root_children.sort(key=lambda x: x["value"], reverse=True)
    
    # 统计信息
    total_sectors = sum(len(_get_all_sectors(child)) for child in root_children)
    
    logger.info(f"生成基于分类层级的旭日图数据: {len(root_children)} 个顶级分类, 总计 {total_sectors} 个板块, 总分值: {total_value}")
    
    return {
        "name": "行业分类分析",
        "value": round(total_value, 1),
        "children": root_children
    }


def _get_all_sectors(node: dict) -> List[dict]:
    """递归获取节点下的所有板块"""
    sectors = []
    if "children" in node:
        for child in node["children"]:
            if "category" in child:  # 这是一个板块节点
                sectors.append(child)
            else:  # 这是一个分类节点，继续递归
                sectors.extend(_get_all_sectors(child))
    return sectors
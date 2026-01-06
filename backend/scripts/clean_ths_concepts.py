"""清理包含"同花顺"的概念的conceptStock数据

从concept_info表中找出name包含"同花顺"的概念的code，
然后清理concept_stock表中包含这些code的行。

运行方式: uv run python backend/scripts/clean_ths_concepts.py
"""

from __future__ import annotations

import logging
import sys
from sqlmodel import Session, select, delete

# 需要从项目根目录运行，所以需要添加路径
sys.path.insert(0, ".")

from models import ConceptInfo, ConceptStock, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def clean_ths_concepts():
    """清理包含'同花顺'的概念的conceptStock数据"""
    try:
        with Session(engine) as session:
            # 1. 从concept_info表中找出name包含"同花顺"的概念的code
            logger.info("正在查找包含'同花顺'的概念...")
            concepts = session.exec(
                select(ConceptInfo).where(ConceptInfo.name.like("%同花顺%"))
            ).all()
            
            if not concepts:
                logger.info("未找到包含'同花顺'的概念")
                return
            
            concept_codes = [concept.code for concept in concepts]
            logger.info(f"找到 {len(concept_codes)} 个包含'同花顺'的概念:")
            for concept in concepts:
                logger.info(f"  - {concept.code}: {concept.name}")
            
            # 2. 清理concept_stock表中包含这些code的行
            logger.info(f"\n正在清理concept_stock表中concept_code在这些code中的行...")
            
            # 先统计要删除的行数
            count_query = select(ConceptStock).where(
                ConceptStock.concept_code.in_(concept_codes)
            )
            rows_to_delete = session.exec(count_query).all()
            rows_count = len(rows_to_delete)
            
            if rows_count == 0:
                logger.info("concept_stock表中没有需要清理的数据")
                return
            
            logger.info(f"将删除 {rows_count} 条concept_stock记录")
            
            # 执行删除
            delete_stmt = delete(ConceptStock).where(
                ConceptStock.concept_code.in_(concept_codes)
            )
            result = session.exec(delete_stmt)
            session.commit()
            
            logger.info(f"✓ 成功删除 {rows_count} 条concept_stock记录")
            
    except Exception as e:
        logger.error(f"清理过程中出错: {e}", exc_info=True)
        raise


def main():
    """主函数"""
    logger.info("开始清理包含'同花顺'的概念的conceptStock数据...")
    try:
        clean_ths_concepts()
        logger.info("清理完成")
        return 0
    except Exception as e:
        logger.error(f"清理失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


"""
板块维度分析模块
分析行业板块资金排名和资金流向
"""

from typing import Dict, Tuple
import akshare as ak

from utils.fetch_utils import fetch_with_retry
from config import BLOCK_RANK_THRESHOLD


def analyze_block(stock_code: str, industry: str = "", main_type: str = "短线游资") -> Tuple[str, Dict]:
    """
    分析板块维度
    参数：
        stock_code: 股票代码
        industry: 行业名称
        main_type: 主力类型
    返回：(MD内容, JSON数据)
    """
    print(f"  正在分析板块维度...")

    stock_md_content = "#### 6. 板块维度\n"
    json_data = {}

    if industry:
        industry_fund_df, industry_error = fetch_with_retry(ak.stock_fund_flow_industry)
        if industry_fund_df is not None and not industry_fund_df.empty:
            # 查找行业排名
            industry_row = industry_fund_df[industry_fund_df['行业'] == industry]
            if not industry_row.empty:
                block_rank = industry_row.index[0] + 1
                block_net = industry_row.iloc[0]['净额']
                stock_md_content += f"- 所属行业：{industry}\n"
                stock_md_content += f"- 行业资金排名：第{block_rank}名（共{len(industry_fund_df)}个行业）\n"
                stock_md_content += f"- 行业净流入：{block_net}亿元\n"
                stock_md_content += f"- 信号判定：{'符合买入条件' if block_rank <= BLOCK_RANK_THRESHOLD else '不符合买入条件'}\n\n"
                json_data = {
                    "industry": industry,
                    "rank": int(block_rank),
                    "net_flow": float(block_net),
                    "total_industries": len(industry_fund_df),
                    "qualified": block_rank <= BLOCK_RANK_THRESHOLD,
                    "source": "akshare"
                }
            else:
                stock_md_content += f"- ❌ **数据获取失败**：未找到行业【{industry}】的数据\n"
                stock_md_content += "- 说明：行业名称可能不匹配，请检查配置\n"
                stock_md_content += "- 信号判定：**无法判断**\n\n"
                json_data = {
                    "error": f"未找到行业【{industry}】",
                    "qualified": None,
                    "source": "获取失败"
                }
        else:
            stock_md_content += f"- ❌ **数据获取失败**：{industry_error if industry_error else '未知错误'}\n"
            stock_md_content += "- 信号判定：**无法判断**\n\n"
            json_data = {
                "error": industry_error,
                "qualified": None,
                "source": "获取失败"
            }
    else:
        stock_md_content += "- ❌ **数据缺失**：行业信息未配置\n"
        stock_md_content += "- 说明：请在STOCK_LIST中配置industry字段\n"
        stock_md_content += "- 信号判定：**无法判断**\n\n"
        json_data = {
            "error": "行业信息未配置",
            "qualified": None,
            "source": "缺失"
        }

    return stock_md_content, json_data

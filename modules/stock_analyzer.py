"""
股票分析主模块
调用各个维度分析模块，汇总结果并生成综合判定
"""

from typing import Dict, Tuple
import datetime

from modules.dimensions.trend import analyze_trend
from modules.dimensions.main_chip import analyze_main_chip
from modules.dimensions.market_chip import analyze_market_chip
from modules.dimensions.fund_flow import analyze_fund_flow
from modules.dimensions.price_volume import analyze_price_volume
from modules.dimensions.block import analyze_block


def get_stock_data(stock_code: str, stock_name: str = "", main_type: str = "短线游资",
                   industry: str = "", target_date: datetime.date = None) -> Tuple[str, Dict]:
    """
    获取单只股票的完整分析数据
    参数：
        stock_code: 股票代码
        stock_name: 股票名称
        main_type: 主力类型
        industry: 行业
        target_date: 目标日期（用于获取历史数据），默认为None（获取最新数据）
    返回：(MD内容, JSON数据)
    """
    print(f"\n📊 开始分析 {stock_name}（{stock_code}）...")

    # 初始化返回内容
    stock_md_content = f"\n### {stock_name}（{stock_code}）| 主力类型：{main_type}\n"
    json_data = {
        "code": stock_code,
        "name": stock_name,
        "main_type": main_type,
        "industry": industry,
        "analysis": {}
    }

    # 依次调用各个维度分析模块

    # 1. 趋势维度（DK信号）
    trend_md, trend_json = analyze_trend(stock_code, main_type)
    stock_md_content += trend_md
    json_data["analysis"]["trend"] = trend_json

    # 2. 主力筹码维度
    main_chip_md, main_chip_json = analyze_main_chip(stock_code, main_type)
    stock_md_content += main_chip_md
    json_data["analysis"]["main_chip"] = main_chip_json

    # 3. 全市场筹码维度
    market_chip_md, market_chip_json = analyze_market_chip(stock_code, main_type)
    stock_md_content += market_chip_md
    json_data["analysis"]["market_chip"] = market_chip_json

    # 4. 主力资金维度
    fund_flow_md, fund_flow_json = analyze_fund_flow(stock_code, main_type)
    stock_md_content += fund_flow_md
    json_data["analysis"]["fund_flow"] = fund_flow_json

    # 5. 量价维度
    price_volume_md, price_volume_json = analyze_price_volume(stock_code, main_type, target_date)
    stock_md_content += price_volume_md
    json_data["analysis"]["price_volume"] = price_volume_json

    # 6. 板块维度
    # 提示：板块维度只能获取当前实时数据
    if target_date and target_date != datetime.date.today():
        stock_md_content += f"⚠️ **注意**：板块维度只能获取当前实时数据，历史数据不可用。\n\n"

    block_md, block_json = analyze_block(stock_code, industry, main_type)
    stock_md_content += block_md
    json_data["analysis"]["block"] = block_json

    # 7. 综合判定
    stock_md_content += "#### 综合判定\n"

    # 统计可用维度和符合买入条件的维度数
    qualified_count = 0
    available_count = 0

    # 趋势维度
    trend = json_data["analysis"].get("trend", {})
    if trend.get("qualified") is not None:
        available_count += 1
        if trend.get("qualified"):
            qualified_count += 1

    # 主力筹码维度（缺失不算）
    main_chip = json_data["analysis"].get("main_chip", {})
    if main_chip.get("qualified") is not None:
        available_count += 1
        if main_chip.get("qualified"):
            qualified_count += 1

    # 全市场筹码维度（缺失不算）
    market_chip = json_data["analysis"].get("market_chip", {})
    if market_chip.get("qualified") is not None:
        available_count += 1
        if market_chip.get("qualified"):
            qualified_count += 1

    # 主力资金维度
    fund_flow = json_data["analysis"].get("fund_flow", {})
    if fund_flow.get("qualified") is not None:
        available_count += 1
        if fund_flow.get("qualified"):
            qualified_count += 1

    # 量价维度
    price_volume = json_data["analysis"].get("price_volume", {})
    if price_volume.get("qualified") is not None:
        available_count += 1
        if price_volume.get("qualified"):
            qualified_count += 1

    # 板块维度
    block = json_data["analysis"].get("block", {})
    if block.get("qualified") is not None:
        available_count += 1
        if block.get("qualified"):
            qualified_count += 1

    # 决策逻辑
    if available_count == 0:
        decision = "无法判断"
        decision_detail = "所有维度数据均缺失"
    elif qualified_count == available_count:
        decision = "买入"
        decision_detail = f"所有可用维度（{available_count}个）全部符合买入条件"
    elif qualified_count >= available_count * 0.7:
        decision = "观望（偏积极）"
        decision_detail = f"{qualified_count}/{available_count}个维度符合（70%+）"
    elif qualified_count >= available_count * 0.5:
        decision = "观望"
        decision_detail = f"{qualified_count}/{available_count}个维度符合（50%-70%）"
    else:
        decision = "观望（偏消极）"
        decision_detail = f"仅{qualified_count}/{available_count}个维度符合（<50%）"

    stock_md_content += f"- 最终决策：{decision}\n"
    stock_md_content += f"- 决策详情：{decision_detail}\n"
    stock_md_content += f"- 可用维度：{available_count}/6\n"

    if available_count < 6:
        missing_dimensions = []
        if json_data["analysis"]["trend"].get("source") == "缺失":
            missing_dimensions.append("趋势（DK信号）")
        if json_data["analysis"]["main_chip"].get("source") == "缺失":
            missing_dimensions.append("主力筹码")
        if json_data["analysis"]["market_chip"].get("source") == "缺失":
            missing_dimensions.append("全市场筹码")
        if json_data["analysis"]["fund_flow"].get("source") == "获取失败":
            missing_dimensions.append("主力资金")
        if json_data["analysis"]["price_volume"].get("source") == "获取失败":
            missing_dimensions.append("量价")
        if json_data["analysis"]["block"].get("source") == "缺失":
            missing_dimensions.append("板块")
        if missing_dimensions:
            stock_md_content += f"- 缺失维度：{', '.join(missing_dimensions)}\n"

    stock_md_content += "\n---\n"

    json_data["decision"] = {
        "action": decision,
        "detail": decision_detail,
        "qualified_count": qualified_count,
        "available_count": available_count,
        "total_dimensions": 6
    }

    return stock_md_content, json_data

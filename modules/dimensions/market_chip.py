"""
全市场筹码维度分析模块
分析全市场筹码分布和获利情况
"""

from typing import Dict, Tuple
import pandas as pd

from utils.fetch_utils import get_chip_distribution


def analyze_market_chip(stock_code: str, main_type: str = "短线游资") -> Tuple[str, Dict]:
    """
    分析全市场筹码维度
    参数：
        stock_code: 股票代码（支持 "sh.600711" 或 "600711" 格式）
        main_type: 主力类型
    返回：(MD内容, JSON数据)
    """
    print(f"  正在分析全市场筹码维度...")

    # 处理股票代码：支持 "sh.600711" 或 "600711" 格式
    if '.' in stock_code:
        # 如果是完整代码（如 "sh.600711"），提取6位数字部分
        _, stock_code = stock_code.split('.')

    stock_md_content = "#### 3. 全市场筹码维度\n"
    json_data = {}

    # 尝试获取筹码分布数据
    chip_dist_df, chip_dist_error = get_chip_distribution(stock_code, period="day")

    if chip_dist_df is not None and not chip_dist_df.empty:
        # 成功获取筹码分布数据
        stock_md_content += f"- ✅ 成功获取筹码分布数据，共{len(chip_dist_df)}条记录\n"

        # 尝试提取关键指标（根据实际返回的列名调整）
        market_avg_cost = None
        market_profit_ratio = None
        chip_concentration = None
        chip_shape = None

        # 尝试识别关键列
        if '平均成本' in chip_dist_df.columns:
            market_avg_cost = float(chip_dist_df.iloc[-1]['平均成本'])
        if '获利比例' in chip_dist_df.columns:
            market_profit_ratio = float(chip_dist_df.iloc[-1]['获利比例'])
        if '筹码集中度' in chip_dist_df.columns:
            chip_concentration = float(chip_dist_df.iloc[-1]['筹码集中度'])
        if '筹码形态' in chip_dist_df.columns:
            chip_shape = str(chip_dist_df.iloc[-1]['筹码形态'])

        stock_md_content += f"- 市场平均成本：{market_avg_cost if market_avg_cost else 'N/A'}元\n"
        stock_md_content += f"- 市场获利比例：{market_profit_ratio if market_profit_ratio else 'N/A'}%\n"
        if chip_concentration is not None:
            stock_md_content += f"- 筹码集中度：{chip_concentration}%\n"
        if chip_shape:
            stock_md_content += f"- 筹码形态：{chip_shape}\n"

        # 判断是否符合买入条件
        qualified = False
        if market_profit_ratio is not None:
            # 获利比例在20%-60%之间为好
            qualified = 20 <= market_profit_ratio <= 60

        stock_md_content += f"- 信号判定：{'符合买入条件' if qualified else '不符合买入条件'}\n"
        stock_md_content += "#### 筹码分布数据\n"
        stock_md_content += chip_dist_df.iloc[-10:].to_markdown(index=True, tablefmt="pipe") + "\n\n"

        json_data = {
            "market_avg_cost": market_avg_cost,
            "market_profit_ratio": market_profit_ratio,
            "chip_concentration": chip_concentration,
            "chip_shape": chip_shape,
            "qualified": qualified,
            "source": "akshare",
            "detail_10d": chip_dist_df.iloc[-10:].to_dict('records')
        }
    else:
        # akshare接口不可用
        stock_md_content += "- ❌ **数据缺失**：全市场筹码分布数据\n"
        stock_md_content += f"- 说明：akshare接口不可用（{chip_dist_error}）\n"
        stock_md_content += "- 替代逻辑：暂无法计算全市场获利比例\n"
        stock_md_content += "- 信号判定：**无法判断**\n\n"
        json_data = {
            "market_avg_cost": None,
            "market_profit_ratio": None,
            "chip_concentration": None,
            "chip_shape": None,
            "qualified": None,
            "source": "缺失",
            "note": chip_dist_error
        }

    return stock_md_content, json_data

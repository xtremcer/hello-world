"""
主力筹码维度分析模块
分析主力持仓成本和获利情况
"""

from typing import Dict, Tuple
import pandas as pd

from utils.fetch_utils import get_chip_cost
from config import MAIN_CHIP_DATA


def analyze_main_chip(stock_code: str, main_type: str = "短线游资") -> Tuple[str, Dict]:
    """
    分析主力筹码维度
    参数：
        stock_code: 股票代码（支持 "sh.600711" 或 "600711" 格式）
        main_type: 主力类型
    返回：(MD内容, JSON数据)
    """
    print(f"  正在分析主力筹码维度...")

    # 处理股票代码：支持 "sh.600711" 或 "600711" 格式
    if '.' in stock_code:
        # 如果是完整代码（如 "sh.600711"），提取6位数字部分
        _, stock_code = stock_code.split('.')

    stock_md_content = "#### 2. 主力筹码维度\n"
    json_data = {}

    # 尝试获取筹码成本数据
    chip_cost_df, chip_cost_error = get_chip_cost(stock_code, adjust="qfq")

    if chip_cost_df is not None and not chip_cost_df.empty:
        # 成功获取筹码成本数据
        latest_chip_cost = chip_cost_df.iloc[-1]

        # 尝试提取关键指标（根据实际返回的列名调整）
        main_cost = None
        main_profit_ratio = None
        chip_shape = None

        # 尝试识别关键列
        if '平均成本' in chip_cost_df.columns:
            main_cost = float(latest_chip_cost['平均成本'])
        if '获利盘比例' in chip_cost_df.columns:
            main_profit_ratio = float(latest_chip_cost['获利盘比例'])
        if '筹码形态' in chip_cost_df.columns:
            chip_shape = str(latest_chip_cost['筹码形态'])

        stock_md_content += f"- 平均成本：{main_cost if main_cost else 'N/A'}元\n"
        stock_md_content += f"- 获利盘比例：{main_profit_ratio if main_profit_ratio else 'N/A'}%\n"
        if chip_shape:
            stock_md_content += f"- 筹码形态：{chip_shape}\n"

        profit_threshold = 10
        shape_qualified = "单峰密集" in chip_shape if chip_shape else False
        qualified = False
        if main_profit_ratio is not None:
            qualified = main_profit_ratio < profit_threshold and shape_qualified

        stock_md_content += f"- 信号判定：{'符合买入条件' if qualified else '不符合买入条件'}\n"
        stock_md_content += "#### 筹码成本数据\n"
        stock_md_content += chip_cost_df.iloc[-5:].to_markdown(index=True, tablefmt="pipe") + "\n\n"

        json_data = {
            "main_cost": main_cost,
            "main_profit_ratio": main_profit_ratio,
            "main_chip_shape": chip_shape,
            "qualified": qualified,
            "source": "akshare",
            "detail_5d": chip_cost_df.iloc[-5:].to_dict('records')
        }
    else:
        # akshare接口不可用，尝试使用手动配置
        chip_config = MAIN_CHIP_DATA.get(stock_code, {})
        if chip_config.get("main_cost"):
            main_cost = chip_config["main_cost"]
            main_profit_ratio = chip_config["main_profit_ratio"]
            main_chip_shape = chip_config["main_chip_shape"]
            stock_md_content += f"- 主力平均成本：{main_cost}元（手动配置）\n"
            stock_md_content += f"- 主力获利比例：{main_profit_ratio}%\n"
            stock_md_content += f"- 主力筹码形态：{main_chip_shape}\n"
            profit_threshold = 10 if main_type == "短线游资" else 10
            shape_qualified = "单峰密集" in main_chip_shape and "低位" in main_chip_shape
            stock_md_content += f"- 信号判定：{'符合买入条件' if (main_profit_ratio < profit_threshold and shape_qualified) else '不符合买入条件'}\n\n"
            json_data = {
                "main_cost": main_cost,
                "main_profit_ratio": main_profit_ratio,
                "main_chip_shape": main_chip_shape,
                "qualified": main_profit_ratio < profit_threshold and shape_qualified,
                "source": "手动配置",
                "note": f"akshare接口不可用：{chip_cost_error}"
            }
        else:
            stock_md_content += "- ❌ **数据缺失**：主力筹码数据未配置\n"
            stock_md_content += f"- 说明：akshare接口不可用（{chip_cost_error}），需手动配置或付费数据源\n"
            stock_md_content += "- 替代逻辑：暂无法判断主力持仓成本和获利情况\n"
            stock_md_content += "- 信号判定：**无法判断**（此维度不计入合格判定）\n\n"
            json_data = {
                "main_cost": None,
                "main_profit_ratio": None,
                "main_chip_shape": None,
                "qualified": None,
                "source": "缺失",
                "note": chip_cost_error
            }

    return stock_md_content, json_data

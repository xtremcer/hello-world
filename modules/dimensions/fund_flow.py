"""
主力资金维度分析模块
分析主力资金流入流出情况
"""

from typing import Dict, Tuple
import akshare as ak

from utils.fetch_utils import fetch_with_retry
from utils.helpers import get_market


def analyze_fund_flow(stock_code: str, main_type: str = "短线游资") -> Tuple[str, Dict]:
    """
    分析主力资金维度
    参数：
        stock_code: 股票代码（支持 "sh.600711" 或 "600711" 格式）
        main_type: 主力类型
    返回：(MD内容, JSON数据)
    """
    print(f"  正在分析主力资金维度...")

    # 处理股票代码：支持 "sh.600711" 或 "600711" 格式
    if '.' in stock_code:
        # 如果是完整代码（如 "sh.600711"），提取市场代码和6位数字
        market, stock_code = stock_code.split('.')
    else:
        # 如果只是6位数字（如 "600711"），自动判断市场
        market = get_market(stock_code)

    stock_md_content = "#### 4. 主力资金维度\n"
    json_data = {}

    fund_df, fund_error = fetch_with_retry(
        ak.stock_individual_fund_flow,
        stock=stock_code,
        market=market
    )

    if fund_df is not None and not fund_df.empty:
        fund_data = fund_df.iloc[-3:]  # 近3日数据

        # 参考旧版本做法：直接显示所有列，不进行列名过滤
        # 尝试计算净流入总额（查找包含"净流入"和"净额"的列）
        net_inflow_col = None
        for col in fund_data.columns:
            if '净流入' in col and '净额' in col:
                net_inflow_col = col
                break

        # 如果找到了净流入列，计算总额
        net_inflow = None
        if net_inflow_col:
            try:
                net_inflow = fund_data[net_inflow_col].sum()
                stock_md_content += f"- 近3日主力资金净流入总额：{round(net_inflow, 2)}元\n"
            except Exception as e:
                print(f"  ⚠️ 计算净流入总额失败：{str(e)}")
                stock_md_content += f"- ⚠️ 计算净流入总额失败：{str(e)}\n"
        else:
            stock_md_content += f"- ⚠️ 未找到净流入相关列\n"

        # 直接显示近5日主力资金明细（所有列）
        stock_md_content += "#### 近5日主力资金数据\n"
        stock_md_content += fund_df.iloc[-5:].round(2).to_markdown(index=True, tablefmt="pipe") + "\n\n"

        # JSON数据
        json_data = {
            "net_inflow_3d": round(float(net_inflow), 2) if net_inflow_col and net_inflow is not None else None,
            "detail_5d": fund_df.iloc[-5:].round(2).to_dict('records'),
            "source": "akshare",
            "qualified": None  # 待根据业务逻辑计算
        }
    else:
        stock_md_content += f"- ❌ **数据获取失败**：{fund_error if fund_error else '未知错误'}\n"
        stock_md_content += "- 说明：可能是休市时间或接口连接问题\n"
        stock_md_content += "- 替代逻辑：无法判断主力资金流向\n"
        stock_md_content += "- 信号判定：**无法判断**\n\n"
        json_data = {
            "error": fund_error,
            "qualified": None,
            "source": "获取失败"
        }

    return stock_md_content, json_data

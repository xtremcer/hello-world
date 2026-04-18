"""
量价维度分析模块
分析股价和成交量的关系
"""

from typing import Dict, Tuple
import datetime
import pandas as pd
import akshare as ak

from utils.fetch_utils import fetch_with_retry
from utils.helpers import get_market


def analyze_price_volume(stock_code: str, main_type: str = "短线游资", target_date: datetime.date = None) -> Tuple[str, Dict]:
    """
    分析量价维度
    参数：
        stock_code: 股票代码（支持 "sh.600711" 或 "600711" 格式）
        main_type: 主力类型
        target_date: 目标日期（用于获取历史数据）
    返回：(MD内容, JSON数据)
    """
    print(f"  正在分析量价维度...")

    # 处理股票代码：支持 "sh.600711" 或 "600711" 格式
    if '.' in stock_code:
        # 如果是完整代码（如 "sh.600711"），提取市场代码和6位数字
        market, stock_code = stock_code.split('.')
    else:
        # 如果只是6位数字（如 "600711"），自动判断市场
        market = get_market(stock_code)

    full_code = f"{market}{stock_code}"
    stock_md_content = "#### 5. 量价维度\n"
    json_data = {}

    # 计算日期范围
    if target_date:
        # 如果指定了目标日期，计算开始日期（目标日期前30天，确保有足够数据）
        start_date = (target_date - datetime.timedelta(days=30)).strftime("%Y%m%d")
        end_date = target_date.strftime("%Y%m%d")
        kline_df, kline_error = fetch_with_retry(
            ak.stock_zh_a_daily,
            symbol=full_code,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
    else:
        # 获取最新数据
        kline_df, kline_error = fetch_with_retry(
            ak.stock_zh_a_daily,
            symbol=full_code,
            adjust="qfq"
        )

    if kline_df is not None and not kline_df.empty:
        # 如果指定了目标日期，确保数据不超过目标日期
        if target_date:
            kline_df['date'] = pd.to_datetime(kline_df['date'])
            kline_df = kline_df[kline_df['date'] <= pd.Timestamp(target_date)]
            # 将日期列转换回字符串，便于JSON序列化
            kline_df['date'] = kline_df['date'].dt.strftime('%Y-%m-%d %H:%M:%S')

        kline_data = kline_df.iloc[-10:]
        latest_price = kline_data.iloc[-1]["close"]
        ma10 = kline_data["close"].rolling(10).mean().iloc[-1]
        vol_avg = kline_data["volume"].iloc[-10:-1].mean()
        latest_vol = kline_data.iloc[-1]["volume"]
        vol_multiple = round(latest_vol / vol_avg, 2) if vol_avg > 0 else 0
        break_ma10 = latest_price > ma10
        vol_qualified = vol_multiple >= 1.5
        stock_md_content += f"- 最新股价：{latest_price}元 | 10日均线：{round(ma10, 2)}元\n"
        stock_md_content += f"- 最新成交量：{latest_vol}手 | 较前9日均量放大：{vol_multiple}倍\n"
        stock_md_content += f"- 信号判定：{'符合买入条件' if (break_ma10 and vol_qualified) else '不符合买入条件'}\n"
        stock_md_content += "#### 近10日K线数据（前复权）\n"
        stock_md_content += kline_data.round(2).to_markdown(index=True, tablefmt="pipe") + "\n\n"

        json_data = {
            "latest_price": float(latest_price),
            "ma10": float(ma10),
            "latest_volume": int(latest_vol),
            "vol_multiple": vol_multiple,
            "break_ma10": bool(break_ma10),
            "qualified": bool(break_ma10 and vol_qualified),
            "kline_10d": kline_data.round(2).to_dict('records'),
            "source": "akshare"
        }
    else:
        stock_md_content += f"- ❌ **数据获取失败**：{kline_error if kline_error else '未知错误'}\n"
        stock_md_content += "- 说明：接口连接问题\n"
        stock_md_content += "- 信号判定：**无法判断**\n\n"
        json_data = {
            "error": kline_error,
            "qualified": None,
            "source": "获取失败"
        }

    return stock_md_content, json_data

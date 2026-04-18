"""
趋势维度分析模块（DK信号）
分析股票的DK趋势信号，判断买卖机会
"""

from typing import Dict, Tuple
import pandas as pd
import numpy as np
import akshare as ak

from utils.fetch_utils import fetch_with_retry
from utils.helpers import get_market
from utils.baostock_utils import get_trend_data


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """
    计算指数移动平均线（EMA）
    """
    return prices.ewm(span=period, adjust=False).mean()


def module1_get_data_baostock(stock_code: str, market: str) -> Tuple[pd.DataFrame, str]:
    """
    模块 1：baostock 数据获取（推荐）
    调用 baostock 接口，提取：日期、收盘价、最高价、成交量
    按日期升序排序

    优点：
    - 稳定性好
    - 无免费额度限制
    - QPS 限制约 20
    - 前复权设置（adjustflag=2），确保数据连续性
    """
    try:
        # 使用便捷函数获取趋势分析所需的数据
        df, error = get_trend_data(
            stock_code=stock_code,
            market=market,
            adjustflag="2"  # 前复权，确保数据连续性
        )

        if df is None or df.empty:
            return None, f"获取历史数据失败：{error}"

        # 按日期升序排序
        df = df.sort_values('date').reset_index(drop=True)

        # 确保数据类型正确
        df['date'] = pd.to_datetime(df['date'])
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

        # 删除缺失值
        df = df.dropna()

        return df, "成功"

    except Exception as e:
        return None, f"数据获取异常：{str(e)}"


def module1_get_data_akshare(stock_code: str, market: str) -> Tuple[pd.DataFrame, str]:
    """
    模块 1：AkShare 数据获取（备用）
    调用 stock_zh_a_hist 接口，提取：日期、收盘价、最高价、成交量
    按日期升序排序

    注意：akshare 接口稳定性较差，建议优先使用 baostock
    """
    try:
        # 获取历史数据
        hist_df, hist_error = fetch_with_retry(
            ak.stock_zh_a_hist,
            symbol=f"{market}{stock_code}",
            period="daily",
            adjust="qfq"
        )

        if hist_df is None or hist_df.empty:
            return None, f"获取历史数据失败：{hist_error}"

        # 提取所需字段
        df = hist_df[['日期', '收盘', '最高', '成交量']].copy()

        # 重命名列
        df.columns = ['date', 'close', 'high', 'volume']

        # 按日期升序排序
        df = df.sort_values('date').reset_index(drop=True)

        # 确保数据类型正确
        df['date'] = pd.to_datetime(df['date'])
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

        # 删除缺失值
        df = df.dropna()

        return df, "成功"

    except Exception as e:
        return None, f"数据获取异常：{str(e)}"


def module1_get_data(stock_code: str, market: str, data_source: str = "baostock") -> Tuple[pd.DataFrame, str]:
    """
    模块 1：数据获取（自动选择数据源）

    参数:
        stock_code: 股票代码
        market: 市场代码（sh/sz）
        data_source: 数据源（baostock/akshare/auto）

    返回:
        (DataFrame, 状态信息)

    优先级：baostock > akshare

    特性：
        - baostock 使用前复权（adjustflag=2），确保数据连续性
        - akshare 使用前复权（adjust="qfq"）
        - 自动切换数据源（baostock 失败时自动切换到 akshare）
    """
    if data_source == "baostock":
        # 优先使用 baostock
        df, status = module1_get_data_baostock(stock_code, market)
        if df is not None and not df.empty:
            return df, f"{status} (baostock 前复权)"
        else:
            # 如果 baostock 失败，尝试 akshare
            print(f"  ⚠️ baostock 获取失败，尝试使用 akshare 备用...")
            df, status = module1_get_data_akshare(stock_code, market)
            return df, f"{status} (akshare 备用)"

    elif data_source == "akshare":
        # 使用 akshare
        df, status = module1_get_data_akshare(stock_code, market)
        return df, f"{status} (akshare 前复权)"

    else:  # auto
        # 自动选择：优先 baostock
        df, status = module1_get_data_baostock(stock_code, market)
        if df is not None and not df.empty:
            return df, f"{status} (baostock 前复权)"
        else:
            print(f"  ⚠️ baostock 获取失败，尝试使用 akshare 备用...")
            df, status = module1_get_data_akshare(stock_code, market)
            return df, f"{status} (akshare 备用)"


def module2_calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    模块 2：指标计算
    计算 EMA5、EMA10（使用手机软件的参数）
    计算 MAV5（5 日均量）
    计算金叉 / 死叉
    计算 5 日新高 / 新低
    """
    # 计算 EMA5 和 EMA10（手机软件使用的参数）
    df['ema5'] = calculate_ema(df['close'], 5)
    df['ema10'] = calculate_ema(df['close'], 10)

    # 计算 MAV5（5 日均量）
    df['mav5'] = df['volume'].rolling(window=5).mean()

    # 计算金叉 / 死叉
    df['ema_diff'] = df['ema5'] - df['ema10']
    df['golden_cross'] = (df['ema_diff'] > 0) & (df['ema_diff'].shift(1) <= 0)
    df['death_cross'] = (df['ema_diff'] < 0) & (df['ema_diff'].shift(1) >= 0)

    # 计算 5 日最高价（用于 K 点判断）
    df['high_5d'] = df['high'].rolling(window=5).max()

    # 计算 5 日新高 / 新低（保留用于其他分析）
    df['high_close_5d'] = df['close'].rolling(window=5).max()
    df['low_close_5d'] = df['close'].rolling(window=5).min()
    df['new_high_5d'] = df['close'] == df['high_close_5d']
    df['new_low_5d'] = df['close'] == df['low_close_5d']

    return df


def module3_mark_dk_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    模块 3：DK 信号标记
    初始化信号列：0 = 无信号，1 = D 买点，-1 = K 卖点
    D 点条件：金叉（EMA5 > EMA10）+ 价格突破 EMA10
    K 点条件：从 5 日高点回落 > 3%
    注意：不去重，保留所有满足条件的信号
    优先级：D 点 > K 点（如果同时满足，优先选择 D 点）
    """
    # 初始化信号列
    df['signal'] = 0

    # D 点条件：金叉 + 价格突破 EMA10
    d_condition = (
        (df['ema5'] > df['ema10']) & (df['ema5'].shift(1) <= df['ema10'].shift(1)) &  # 1. 金叉
        (df['close'] > df['ema10'])  # 2. 价格突破 EMA10
    )

    # K 点条件：从 5 日高点回落 > 3%
    k_condition = (df['high_5d'] - df['close']) / df['high_5d'] > 0.03

    # 标记 D 点和 K 点
    df.loc[d_condition, 'signal'] = 1
    df.loc[k_condition, 'signal'] = -1

    # 优先级处理：如果同时满足 D 点和 K 点条件，优先选择 D 点
    df.loc[d_condition & k_condition, 'signal'] = 1

    return df


def module4_calculate_gain(df: pd.DataFrame) -> Tuple[float, int]:
    """
    模块 4：D 点后涨幅计算
    找到所有 D 点
    对每个 D 点，计算「D 点后所有交易日的最高价」
    用公式算出累计最大涨幅（保留 3 位小数，如 6.869%）
    返回：[最近D点的累计最大涨幅, 最近D点索引]
    """
    # 找到所有 D 点
    d_points = df[df['signal'] == 1].copy()

    if d_points.empty:
        return 0.0, -1

    # 计算每个 D 点后的累计最大涨幅
    d_gains = []
    for idx, row in d_points.iterrows():
        d_price = row['close']

        # 找到 D 点之后的数据
        future_data = df[df.index > idx]

        if future_data.empty:
            continue

        # 计算 D 点后所有交易日的最高价
        max_price = future_data['high'].max()

        # 计算累计最大涨幅
        if max_price > d_price:
            gain = ((max_price - d_price) / d_price) * 100
            d_gains.append({
                'date': row['date'],
                'd_index': idx,
                'd_price': d_price,
                'max_price': max_price,
                'gain': round(gain, 3)
            })

    # 返回最近 D 点的累计最大涨幅
    if not d_gains:
        return 0.0, -1

    latest_d = d_gains[-1]
    return latest_d['gain'], latest_d['d_index']


def analyze_trend(stock_code: str, main_type: str = "短线游资") -> Tuple[str, Dict]:
    """
    分析趋势维度（DK信号）
    参数：
        stock_code: 股票代码（支持 "sh.600711" 或 "600711" 格式）
        main_type: 主力类型
    返回：(MD内容, JSON数据)
    """
    print(f"  正在分析趋势维度（DK信号 - 自行计算）...")

    stock_md_content = "#### 1. 趋势维度（DK信号）\n"
    json_data = {}

    # 处理股票代码：支持 "sh.600711" 或 "600711" 格式
    if '.' in stock_code:
        # 如果是完整代码（如 "sh.600711"），提取市场代码和6位数字
        market, stock_code = stock_code.split('.')
    else:
        # 如果只是6位数字（如 "600711"），自动判断市场
        market = get_market(stock_code)

    try:
        # 模块 1：获取数据
        df, data_status = module1_get_data(stock_code, market)

        if df is None or df.empty:
            stock_md_content += f"- ❌ **数据获取失败**：{data_status}\n"
            stock_md_content += "- 说明：可能是网络问题或数据源维护中\n"
            stock_md_content += "- 信号判定：**无法判断**\n\n"
            json_data = {
                "signal": None,
                "qualified": None,
                "source": "获取失败",
                "note": data_status
            }
            return stock_md_content, json_data

        # 模块 2：计算指标
        df = module2_calculate_indicators(df)

        # 模块 3：标记 DK 信号
        df = module3_mark_dk_signals(df)

        # 模块 4：计算 D 点后涨幅
        latest_d_gain, latest_d_index = module4_calculate_gain(df)

        # 模块 5：结果输出

        # 获取最新的信号状态
        latest_row = df.iloc[-1]
        latest_signal = latest_row['signal']

        # 判断最新信号
        if latest_signal == 1:
            dk_signal_str = "D"
            signal_desc = "买入信号"
            qualified = True
        elif latest_signal == -1:
            dk_signal_str = "K"
            signal_desc = "卖出信号"
            qualified = False
        else:
            dk_signal_str = "无"
            signal_desc = "无信号"
            qualified = None

        # 统计历史信号
        d_count = (df['signal'] == 1).sum()
        k_count = (df['signal'] == -1).sum()

        stock_md_content += f"- 核心信号：{dk_signal_str} - {signal_desc}\n"
        stock_md_content += f"- 信号判定：{'符合买入条件（D点）' if dk_signal_str == 'D' else '符合卖出条件（K点）' if dk_signal_str == 'K' else '未达标'}\n"

        # 显示 D 点后涨幅
        if latest_d_index >= 0 and latest_d_gain > 0:
            stock_md_content += f"- 最近 D 点后累计最大涨幅：{latest_d_gain}%\n"

        # 显示历史信号统计
        stock_md_content += f"- 历史信号统计：D 点 {d_count} 个，K 点 {k_count} 个\n"

        # 显示最近 20 天的 DK 信号
        stock_md_content += "\n#### 近 20 日 DK 信号\n"
        recent_df = df.tail(20)[['date', 'close', 'signal']].copy()
        recent_df['signal_str'] = recent_df['signal'].map({1: 'D', -1: 'K', 0: '-'})
        recent_df['date'] = recent_df['date'].dt.strftime('%Y-%m-%d')
        recent_df.columns = ['日期', '收盘价', '信号', '信号类型']
        stock_md_content += recent_df.to_markdown(index=True, tablefmt="pipe") + "\n\n"

        # 显示最近 5 天的指标详情
        stock_md_content += "\n#### 近 5 日指标详情\n"
        indicator_df = df.tail(5)[['date', 'close', 'ema5', 'ema10', 'volume', 'mav5', 'signal']].copy()
        indicator_df['date'] = indicator_df['date'].dt.strftime('%Y-%m-%d')
        indicator_df['signal_str'] = indicator_df['signal'].map({1: 'D', -1: 'K', 0: '-'})
        indicator_df.columns = ['日期', '收盘价', 'EMA5', 'EMA10', '成交量', 'MAV5', '信号', '信号类型']
        stock_md_content += indicator_df.to_markdown(index=True, tablefmt="pipe") + "\n\n"

        json_data = {
            "signal": dk_signal_str,
            "signal_desc": signal_desc,
            "qualified": qualified,
            "source": "自行计算",
            "latest_d_gain": latest_d_gain if latest_d_index >= 0 else None,
            "d_count": int(d_count),
            "k_count": int(k_count),
            "detail_20d": recent_df.to_dict('records'),
            "indicator_5d": indicator_df.to_dict('records')
        }

    except Exception as e:
        stock_md_content += f"- ❌ **分析失败**：{str(e)}\n"
        stock_md_content += "- 说明：数据计算异常\n"
        stock_md_content += "- 信号判定：**无法判断**\n\n"
        json_data = {
            "signal": None,
            "qualified": None,
            "source": "计算失败",
            "note": str(e)
        }

    return stock_md_content, json_data

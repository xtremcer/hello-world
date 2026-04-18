# ==============================================
# 股票自动化分析脚本（改进版：真实数据+休市判断）
# 核心改进：
#   1. 添加休市判断逻辑
#   2. 使用真实akshare数据（行业资金流等）
#   3. 明确标注数据缺失情况
#   4. 添加数据获取重试机制
#   5. 支持自定义主力筹码数据（预留接口）
#   6. 添加高频反爬应对（智能重试 + 请求限速）
# ==============================================
import akshare as ak
import pandas as pd
import datetime
import os
import json
import argparse
import sys
import time
import numpy as np
from typing import Dict, Optional, Tuple
from retrying import retry

# ===================== 自定义 JSON 编码器 =====================
class NumpyJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理numpy和pandas的特殊类型"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif pd.isna(obj):
            return None
        return super().default(obj)

# ===================== 核心配置（易扩展）=====================
# 默认股票（可通过命令行参数 --code 覆盖）
DEFAULT_STOCK = {
    "code": "600711",
    "name": "盛屯矿业",
    "main_type": "短线游资",
    "industry": "能源金属"
}

# 目标股票列表（默认使用DEFAULT_STOCK，可通过命令行参数修改）
STOCK_LIST = [DEFAULT_STOCK.copy()]

# 输出目录配置（所有报告输出到当前目录）
OUTPUT_DIR_DEFAULT = "."

# 板块资金排名阈值（买入信号：前10）
BLOCK_RANK_THRESHOLD = 10

# 数据获取重试次数
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒

# 反爬应对配置（新增）
# 请求间隔延迟（秒），避免高频请求被封
REQUEST_DELAY_NORMAL = 1.0   # 正常请求延迟
REQUEST_DELAY_RETRY = 3.0    # 重试请求延迟
REQUEST_DELAY_FAILED = 5.0   # 失败后延迟

# 智能重试配置
RETRY_STOP_MAX_ATTEMPT = 3   # 最大重试次数
RETRY_WAIT_FIXED = 2000       # 重试间隔（毫秒）

# 主力筹码数据（预留接口，后续可手动配置或对接真实数据源）
MAIN_CHIP_DATA = {
    "600711": {
        "main_cost": None,  # None表示未配置，将标注为缺失
        "main_profit_ratio": None,
        "main_chip_shape": None
    },
    "002240": {
        "main_cost": None,
        "main_profit_ratio": None,
        "main_chip_shape": None
    }
}

# DK趋势信号（暂无akshare接口，需要手动配置或对接第三方数据源）
DK_SIGNAL_DATA = {
    "600711": None,  # None表示未配置
    "002240": None
}
# =================================================================

def is_trading_day(date: datetime.date = None) -> Tuple[bool, str]:
    """
    通过获取实际数据判断是否为交易日
    返回：(是否交易日, 原因说明)

    判断逻辑：
    - 获取上证指数（000001）的最新数据
    - 对比最新数据日期与目标日期
    - 一致 = 交易日，不一致 = 休市
    """
    if date is None:
        date = datetime.date.today()

    target_date_str = date.strftime("%Y-%m-%d")

    try:
        print(f"  正在获取上证指数数据以判断{target_date_str}是否为交易日...")

        # 获取上证指数日线数据
        index_df = ak.stock_zh_index_daily(symbol="sh000001")

        if index_df is None or index_df.empty:
            return False, "无法获取上证指数数据"

        # 将日期列转换为date对象
        index_df['date'] = pd.to_datetime(index_df['date']).dt.date
        trading_dates = set(index_df['date'].tolist())

        # 检查目标日期是否在交易日期中
        if date in trading_dates:
            return True, f"交易日（上证指数数据包含该日期）"
        else:
            return False, f"休市（上证指数数据不包含该日期：{target_date_str}）"

    except Exception as e:
        print(f"  ⚠️ 获取上证指数数据失败：{str(e)}")
        print(f"  💡 建议检查网络连接或稍后重试")
        return False, f"数据获取失败：{str(e)}"

def get_global_indices() -> Optional[Dict]:
    """
    获取全球主要指数数据
    返回：包含美股、港股等指数的字典
    """
    try:
        print("  正在获取全球指数数据...")

        # 获取全球指数实时行情
        global_df = fetch_with_retry(ak.index_global_spot_em)[0]

        if global_df is None or global_df.empty:
            return None

        # 提取关键指数
        indices = {}

        # 美股三大指数
        us_indices = {
            "道琼斯工业指数": ["道琼斯", "DOW", "道指"],
            "纳斯达克综合指数": ["纳斯达克", "NASDAQ", "纳指"],
            "标普500指数": ["标普500", "S&P 500", "标普"]
        }

        for idx_name, keywords in us_indices.items():
            # 搜索匹配的指数
            for keyword in keywords:
                match = global_df[global_df['名称'].str.contains(keyword, na=False)]
                if not match.empty:
                    row = match.iloc[0]
                    indices[idx_name] = {
                        "name": row['名称'],
                        "code": row['代码'],
                        "price": row['最新价'],
                        "change": row['涨跌幅'],
                        "volume": row['成交量']
                    }
                    break

        # 港股恒生指数
        hk_match = global_df[global_df['名称'].str.contains('恒生指数', na=False)]
        if not hk_match.empty:
            row = hk_match.iloc[0]
            indices["恒生指数"] = {
                "name": row['名称'],
                "code": row['代码'],
                "price": row['最新价'],
                "change": row['涨跌幅'],
                "volume": row['成交量']
            }

        # 如果获取的指数太少，尝试港股指数接口
        if len(indices) < 2:
            hk_index_df = fetch_with_retry(ak.stock_hk_index_spot_em)[0]
            if hk_index_df is not None and not hk_index_df.empty:
                hsi = hk_index_df[hk_index_df['指数名称'].str.contains('恒生指数', na=False)]
                if not hsi.empty:
                    row = hsi.iloc[0]
                    indices["恒生指数"] = {
                        "name": row['指数名称'],
                        "code": row['指数代码'],
                        "price": row['最新价'],
                        "change": row['涨跌幅'],
                        "volume": row['成交量']
                    }

        return indices if indices else None

    except Exception as e:
        print(f"  ⚠️ 获取全球指数数据失败：{str(e)}")
        return None

def get_global_financial_news() -> Optional[str]:
    """
    获取海外金融新闻
    返回：新闻内容字符串
    """
    try:
        print("  正在获取海外金融新闻...")

        # 获取美股新闻（东方财富）
        news_df, news_error = fetch_with_retry(
            ak.stock_news_em,
            symbol="美股"
        )

        if news_df is None or news_df.empty:
            return None

        # 拼接新闻内容（取前10条）
        news_content = ""
        count = 0
        max_news = 10

        for idx, row in news_df.iterrows():
            if count >= max_news:
                break

            # 尝试获取标题和链接
            if '新闻标题' in row and '发布时间' in row:
                news_content += f"\n**{row['新闻标题']}**\n"
                news_content += f"- 发布时间: {row['发布时间']}\n"
                if '新闻链接' in row:
                    news_content += f"- 链接: {row['新闻链接']}\n"
                news_content += "\n"
                count += 1
            elif '标题' in row and '时间' in row:
                news_content += f"\n**{row['标题']}**\n"
                news_content += f"- 发布时间: {row['时间']}\n"
                if '链接' in row:
                    news_content += f"- 链接: {row['链接']}\n"
                news_content += "\n"
                count += 1
            elif len(row) >= 2:
                news_content += f"\n**{row.iloc[0]}**\n"
                news_content += f"- 发布时间: {row.iloc[1]}\n"
                if len(row) >= 3:
                    news_content += f"- 链接: {row.iloc[2]}\n"
                news_content += "\n"
                count += 1

        return news_content if news_content else None

    except Exception as e:
        print(f"  ⚠️ 获取海外金融新闻失败：{str(e)}")
        return None

def generate_market_brief(target_date: datetime.date, reason: str) -> Tuple[str, Dict]:
    """
    生成休市简报内容（不包含主标题）
    返回：(MD内容, JSON数据)
    """
    print(f"\n📰 生成休市简报内容：{target_date}")

    # 1. 获取全球指数数据
    global_indices = get_global_indices()

    # 2. 获取海外金融新闻
    financial_news = get_global_financial_news()

    # 3. 生成MD内容（不包含主标题）
    date_str = target_date.strftime("%Y-%m-%d")
    md_content = f"""## 📅 休市信息

**日期**: {date_str}

**A股状态**: 休市

**原因说明**: {reason}

> 💡 虽然A股休市，但海外市场仍在交易，以下是全球市场概览：

---

## 🌍 海外市场概览

"""

    # 添加全球指数内容
    if global_indices:
        md_content += "### 全球主要指数\n\n"

        # 美股
        us_indices = [k for k in global_indices.keys() if "纳斯达克" in k or "道琼斯" in k or "标普" in k]
        if us_indices:
            md_content += "#### 🇺🇸 美股市场\n\n"
            for idx_name in us_indices:
                idx_data = global_indices[idx_name]
                change_val = float(idx_data['change']) if idx_data['change'] else 0
                change_sign = "📈" if change_val > 0 else "📉" if change_val < 0 else "➡️"

                md_content += f"- **{idx_name}**\n"
                md_content += f"  - 最新价: {idx_data['price']}\n"
                md_content += f"  - 涨跌幅: {idx_data['change']}% {change_sign}\n"
                md_content += f"  - 成交量: {idx_data.get('volume', 'N/A')}\n\n"

        # 港股
        if "恒生指数" in global_indices:
            idx_data = global_indices["恒生指数"]
            change_val = float(idx_data['change']) if idx_data['change'] else 0
            change_sign = "📈" if change_val > 0 else "📉" if change_val < 0 else "➡️"

            md_content += "#### 🇭🇰 港股市场\n\n"
            md_content += f"- **{idx_data['name']}**\n"
            md_content += f"  - 最新价: {idx_data['price']}\n"
            md_content += f"  - 涨跌幅: {idx_data['change']}% {change_sign}\n"
            md_content += f"  - 成交量: {idx_data.get('volume', 'N/A')}\n\n"

        # 市场分析
        md_content += "### 📊 市场分析\n\n"
        md_content += "**简要评述**：\n"

        # 分析整体走势
        changes = []
        for idx_name, idx_data in global_indices.items():
            if idx_data['change']:
                try:
                    changes.append(float(idx_data['change']))
                except (ValueError, TypeError):
                    pass

        if changes:
            avg_change = sum(changes) / len(changes)
            if avg_change > 1:
                md_content += f"- 海外市场整体表现强劲，平均涨跌幅为 **{avg_change:.2f}%**，市场情绪积极\n"
            elif avg_change > 0:
                md_content += f"- 海外市场整体温和上涨，平均涨跌幅为 **{avg_change:.2f}%**\n"
            elif avg_change > -1:
                md_content += f"- 海外市场整体小幅回调，平均涨跌幅为 **{avg_change:.2f}%**\n"
            else:
                md_content += f"- 海外市场整体承压，平均涨跌幅为 **{avg_change:.2f}%**，市场情绪谨慎\n"

        md_content += "\n**风险提示**：\n"
        md_content += "- 海外市场波动可能对A股开盘产生影响，请关注相关板块\n"
        md_content += "- 建议关注美股中概股表现，作为A股相关板块的风向标\n"
        md_content += "- 注意汇率波动和宏观政策变化\n\n"
    else:
        md_content += "⚠️ 暂时无法获取全球指数数据，可能是网络问题或数据源维护中。\n\n"

    # 添加新闻内容
    md_content += "---\n\n"
    md_content += "## 📰 海外金融新闻\n\n"

    if financial_news:
        md_content += financial_news
    else:
        md_content += "⚠️ 暂时无法获取海外金融新闻，可能是网络问题或数据源维护中。\n\n"

    md_content += "\n---\n\n"
    md_content += "## 💡 温馨提示\n\n"
    md_content += f"- 下一个交易日请关注A股开市表现\n"
    md_content += f"- 海外市场走势可作为参考，但请结合A股自身基本面分析\n"
    md_content += f"- 建议关注板块轮动和资金流向变化\n"
    md_content += f"- 如需查看历史交易分析报告，请使用 `--force` 参数运行\n"

    # 4. 生成JSON数据
    json_data = {
        "report_date": date_str,
        "report_type": "A股休市简报",
        "trading_status": "休市",
        "reason": reason,
        "global_indices": {},
        "financial_news": financial_news if financial_news else None,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if global_indices:
        for idx_name, idx_data in global_indices.items():
            json_data["global_indices"][idx_name] = {
                "name": idx_data['name'],
                "code": idx_data['code'],
                "price": idx_data['price'],
                "change": idx_data['change'],
                "volume": idx_data.get('volume', 'N/A')
            }

    return md_content, json_data

def get_market(code):
    """根据股票代码自动判断交易所"""
    if code.startswith('60') or code.startswith('68'):
        return 'sh'
    elif code.startswith('00') or code.startswith('30'):
        return 'sz'
    else:
        return 'sh'

def fetch_with_retry(func, *args, **kwargs):
    """
    带重试机制的数据获取函数（改进版：添加延迟和智能重试）
    """
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            # 正常请求延迟（避免高频）
            if attempt == 0:
                time.sleep(REQUEST_DELAY_NORMAL)
            # 重试请求延迟（更久）
            else:
                delay = REQUEST_DELAY_RETRY if attempt < MAX_RETRIES - 1 else REQUEST_DELAY_FAILED
                print(f"  ⚠️ 数据获取失败，{delay}秒后重试 ({attempt + 1}/{MAX_RETRIES})...")
                time.sleep(delay)

            return func(*args, **kwargs), None
        except Exception as e:
            last_error = str(e)
            # 失败后延迟，减少被封风险
            if attempt < MAX_RETRIES - 1:
                time.sleep(REQUEST_DELAY_RETRY)
            else:
                print(f"  ❌ 数据获取失败，已达最大重试次数")
    return None, last_error

# ===================== 智能重试装饰器 =====================

def should_retry(exception):
    """
    判断是否应该重试
    - ConnectionError: 网络连接错误
    - RuntimeError: 运行时错误（可能是反爬）
    - 超时错误
    """
    return isinstance(exception, (ConnectionError, RuntimeError, TimeoutError))

# ===================== 新增接口函数（带智能重试） =====================

@retry(
    stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT,
    wait_fixed=RETRY_WAIT_FIXED,
    retry_on_exception=should_retry
)
def get_dk_signal_safe(stock_code: str, period: str = "day") -> pd.DataFrame:
    """
    获取个股DK信号数据（带智能重试）
    """
    return ak.stock_dk_signal(symbol=stock_code, period=period)

@retry(
    stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT,
    wait_fixed=RETRY_WAIT_FIXED,
    retry_on_exception=should_retry
)
def get_chip_distribution_safe(stock_code: str, period: str = "day") -> pd.DataFrame:
    """
    获取个股筹码分布数据（带智能重试）
    """
    return ak.stock_chip_distribution(symbol=stock_code, period=period)

@retry(
    stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT,
    wait_fixed=RETRY_WAIT_FIXED,
    retry_on_exception=should_retry
)
def get_chip_cost_safe(stock_code: str, adjust: str = "qfq") -> pd.DataFrame:
    """
    获取个股筹码成本数据（带智能重试）
    """
    return ak.stock_chip_cost(symbol=stock_code, adjust=adjust)

# ===================== 新增接口函数（调用层） =====================

def get_dk_signal(stock_code: str, period: str = "day") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    获取个股DK信号数据（带智能重试和请求延迟）
    参数：
        stock_code: 股票代码（6位数字，无需前缀）
        period: 周期，可选 day/week/month
    返回：(DK信号DataFrame, 错误信息)
    """
    print(f"  正在获取{stock_code}的DK信号数据...")

    try:
        # 调用带智能重试的函数
        dk_df = get_dk_signal_safe(stock_code, period)

        if dk_df is not None and not dk_df.empty:
            print(f"  ✅ 成功获取DK信号数据，共{len(dk_df)}条记录")
            return dk_df, None
        else:
            error_msg = "DK信号数据为空"
            print(f"  ⚠️ {error_msg}")
            return None, error_msg

    except AttributeError as e:
        error_msg = f"akshare无此接口：stock_dk_signal - {str(e)}"
        print(f"  ⚠️ {error_msg}")
        return None, error_msg
    except Exception as e:
        error_msg = f"获取DK信号失败：{str(e)}"
        print(f"  ⚠️ {error_msg}")
        return None, error_msg

def get_chip_distribution(stock_code: str, period: str = "day") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    获取个股筹码分布数据（带智能重试和请求延迟）
    参数：
        stock_code: 股票代码（6位数字，无需前缀）
        period: 周期，可选 day/week/month
    返回：(筹码分布DataFrame, 错误信息)
    """
    print(f"  正在获取{stock_code}的筹码分布数据...")

    try:
        # 调用带智能重试的函数
        chip_df = get_chip_distribution_safe(stock_code, period)

        if chip_df is not None and not chip_df.empty:
            print(f"  ✅ 成功获取筹码分布数据，共{len(chip_df)}条记录")
            return chip_df, None
        else:
            error_msg = "筹码分布数据为空"
            print(f"  ⚠️ {error_msg}")
            return None, error_msg

    except AttributeError as e:
        error_msg = f"akshare无此接口：stock_chip_distribution - {str(e)}"
        print(f"  ⚠️ {error_msg}")
        return None, error_msg
    except Exception as e:
        error_msg = f"获取筹码分布失败：{str(e)}"
        print(f"  ⚠️ {error_msg}")
        return None, error_msg

def get_chip_cost(stock_code: str, adjust: str = "qfq") -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    获取个股筹码峰与成本分析数据（带智能重试和请求延迟）
    参数：
        stock_code: 股票代码（6位数字，无需前缀）
        adjust: 复权类型，qfq(前复权)/hfq(后复权)/None(不复权)
    返回：(筹码成本DataFrame, 错误信息)
    """
    print(f"  正在获取{stock_code}的筹码成本数据...")

    try:
        # 调用带智能重试的函数
        chip_cost_df = get_chip_cost_safe(stock_code, adjust)

        if chip_cost_df is not None and not chip_cost_df.empty:
            print(f"  ✅ 成功获取筹码成本数据，共{len(chip_cost_df)}条记录")
            return chip_cost_df, None
        else:
            error_msg = "筹码成本数据为空"
            print(f"  ⚠️ {error_msg}")
            return None, error_msg

    except AttributeError as e:
        error_msg = f"akshare无此接口：stock_chip_cost - {str(e)}"
        print(f"  ⚠️ {error_msg}")
        return None, error_msg
    except Exception as e:
        error_msg = f"获取筹码成本失败：{str(e)}"
        print(f"  ⚠️ {error_msg}")
        return None, error_msg

# ============================================================

def get_stock_data(stock_code, stock_name="", main_type="短线游资", industry="", target_date=None):
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
    market = get_market(stock_code)
    full_code = f"{market}{stock_code}"

    # 初始化返回内容
    stock_md_content = f"\n### {stock_name}（{stock_code}）| 主力类型：{main_type}\n"
    json_data = {
        "code": stock_code,
        "name": stock_name,
        "main_type": main_type,
        "industry": industry,
        "analysis": {}
    }

    # 1. 趋势维度（DK信号）
    stock_md_content += "#### 1. 趋势维度（DK信号）\n"

    # 优先尝试从akshare获取DK信号
    dk_df, dk_error = get_dk_signal(stock_code, period="day")

    if dk_df is not None and not dk_df.empty:
        # 成功获取DK信号数据
        latest_dk = dk_df.iloc[-1]  # 获取最新的DK信号

        # 解析DK信号数据
        dk_signal_str = "无信号"
        signal_desc = "无信号"
        strength = 0.0

        # 尝试识别DK信号字段（根据实际返回的列名调整）
        if 'dk_signal' in dk_df.columns:
            dk_signal_value = latest_dk['dk_signal']
            dk_signal_str = str(dk_signal_value)
            signal_desc = "多信号（D点）" if dk_signal_str == 'D' else "空信号（K点）" if dk_signal_str == 'K' else "无信号"

            # 如果有信号描述列
            if 'signal_desc' in dk_df.columns:
                signal_desc = latest_dk['signal_desc']

            # 如果有强度列
            if 'strength' in dk_df.columns:
                strength = float(latest_dk['strength'])

        stock_md_content += f"- 核心信号：{dk_signal_str} - {signal_desc}\n"
        if strength > 0:
            stock_md_content += f"- 信号强度：{strength:.2f}\n"
        stock_md_content += f"- 信号判定：{'符合买入条件（D点）' if dk_signal_str == 'D' else '符合卖出条件（K点）' if dk_signal_str == 'K' else '未达标'}\n"
        stock_md_content += "#### 近5日DK信号数据\n"
        stock_md_content += dk_df.iloc[-5:].to_markdown(index=True, tablefmt="pipe") + "\n\n"

        json_data["analysis"]["trend"] = {
            "signal": dk_signal_str,
            "signal_desc": signal_desc,
            "strength": strength,
            "qualified": dk_signal_str == 'D',
            "source": "akshare",
            "detail_5d": dk_df.iloc[-5:].to_dict('records')
        }
    else:
        # akshare接口不可用，尝试使用手动配置
        dk_signal = DK_SIGNAL_DATA.get(stock_code)
        if dk_signal:
            stock_md_content += f"- 核心信号：{dk_signal}（手动配置）\n"
            stock_md_content += f"- 信号判定：{'符合买入条件（D点）' if 'D点' in dk_signal else '符合卖出条件（K点）/未达标'}\n"
            stock_md_content += f"- 数据来源：手动配置\n\n"
            json_data["analysis"]["trend"] = {
                "signal": dk_signal,
                "qualified": 'D点' in dk_signal,
                "source": "手动配置",
                "note": f"akshare接口不可用：{dk_error}"
            }
        else:
            stock_md_content += "- ❌ **数据缺失**：DK趋势信号未配置\n"
            stock_md_content += f"- 说明：akshare接口不可用（{dk_error}），需手动配置或对接第三方数据源\n"
            stock_md_content += "- 信号判定：**无法判断**\n\n"
            json_data["analysis"]["trend"] = {
                "signal": None,
                "qualified": None,
                "source": "缺失",
                "note": dk_error
            }

    # 2. 主力筹码维度
    stock_md_content += "#### 2. 主力筹码维度\n"

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

        json_data["analysis"]["main_chip"] = {
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
            json_data["analysis"]["main_chip"] = {
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
            json_data["analysis"]["main_chip"] = {
                "main_cost": None,
                "main_profit_ratio": None,
                "main_chip_shape": None,
                "qualified": None,
                "source": "缺失",
                "note": chip_cost_error
            }

    # 3. 全市场筹码维度
    stock_md_content += "#### 3. 全市场筹码维度\n"

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

        json_data["analysis"]["market_chip"] = {
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
        json_data["analysis"]["market_chip"] = {
            "market_avg_cost": None,
            "market_profit_ratio": None,
            "chip_concentration": None,
            "chip_shape": None,
            "qualified": None,
            "source": "缺失",
            "note": chip_dist_error
        }

    # 4. 主力资金维度（使用akshare）
    stock_md_content += "#### 4. 主力资金维度\n"
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
        if net_inflow_col:
            try:
                net_inflow = fund_data[net_inflow_col].sum()
                stock_md_content += f"- 近3日主力资金净流入总额：{round(net_inflow, 2)}万元\n"
            except Exception as e:
                print(f"  ⚠️ 计算净流入总额失败：{str(e)}")
                stock_md_content += f"- ⚠️ 计算净流入总额失败：{str(e)}\n"
        else:
            stock_md_content += f"- ⚠️ 未找到净流入相关列\n"

        # 直接显示近5日主力资金明细（所有列）
        stock_md_content += "#### 近5日主力资金数据\n"
        stock_md_content += fund_df.iloc[-5:].round(2).to_markdown(index=True, tablefmt="pipe") + "\n\n"

        # JSON数据
        json_data["analysis"]["fund_flow"] = {
            "net_inflow_3d": round(float(net_inflow), 2) if net_inflow_col else None,
            "detail_5d": fund_df.iloc[-5:].round(2).to_dict('records'),
            "source": "akshare"
        }
    else:
        stock_md_content += f"- ❌ **数据获取失败**：{fund_error if fund_error else '未知错误'}\n"
        stock_md_content += "- 说明：可能是休市时间或接口连接问题\n"
        stock_md_content += "- 替代逻辑：无法判断主力资金流向\n"
        stock_md_content += "- 信号判定：**无法判断**\n\n"
        json_data["analysis"]["fund_flow"] = {
            "error": fund_error,
            "qualified": None,
            "source": "获取失败"
        }

    # 5. 量价维度（使用akshare）
    stock_md_content += "#### 5. 量价维度\n"

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
        json_data["analysis"]["price_volume"] = {
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
        json_data["analysis"]["price_volume"] = {
            "error": kline_error,
            "qualified": None,
            "source": "获取失败"
        }

    # 6. 板块维度（使用akshare）
    stock_md_content += "#### 6. 板块维度\n"

    # 提示：板块维度只能获取当前实时数据
    if target_date and target_date != datetime.date.today():
        stock_md_content += f"⚠️ **注意**：板块维度只能获取当前实时数据，历史数据不可用。\n\n"

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
                json_data["analysis"]["block"] = {
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
                json_data["analysis"]["block"] = {
                    "error": f"未找到行业【{industry}】",
                    "qualified": None,
                    "source": "获取失败"
                }
        else:
            stock_md_content += f"- ❌ **数据获取失败**：{industry_error if industry_error else '未知错误'}\n"
            stock_md_content += "- 信号判定：**无法判断**\n\n"
            json_data["analysis"]["block"] = {
                "error": industry_error,
                "qualified": None,
                "source": "获取失败"
            }
    else:
        stock_md_content += "- ❌ **数据缺失**：行业信息未配置\n"
        stock_md_content += "- 说明：请在STOCK_LIST中配置industry字段\n"
        stock_md_content += "- 信号判定：**无法判断**\n\n"
        json_data["analysis"]["block"] = {
            "error": "行业信息未配置",
            "qualified": None,
            "source": "缺失"
        }

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

def write_run_log(log_path, content, is_success=True):
    """封装日志写入函数"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_prefix = "[SUCCESS]" if is_success else "[ERROR]"
    log_content = f"{current_time} {log_prefix} - {content}\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_content)
        print(f"✅ 日志已追加：{log_content.strip()}")
    except Exception as e:
        print(f"❌ 日志写入失败：{str(e)}")

def check_directory_permission(dir_path):
    """检查目录写入权限"""
    if os.access(dir_path, os.W_OK):
        return True
    print(f"⚠️ 目录{dir_path}无写入权限，尝试自动提权...")
    try:
        os.chmod(dir_path, 0o775)
        return os.access(dir_path, os.W_OK)
    except Exception as e:
        print(f"❌ 提权失败：{str(e)}，请手动执行 chmod 775 {dir_path}")
        return False

def main():
    """主函数：生成当日分析报告"""
    global STOCK_LIST  # 声明使用全局变量

    # 1. 参数解析
    parser = argparse.ArgumentParser(description='股票主升浪策略分析工具（改进版）')
    parser.add_argument('--output', type=str, help=f'输出目录路径（默认：{OUTPUT_DIR_DEFAULT}）')
    parser.add_argument('--json-only', action='store_true', help='仅输出JSON格式')
    parser.add_argument('--md-only', action='store_true', help='仅输出MD格式')
    parser.add_argument('--force', action='store_true', help='强制运行，忽略休市判断')
    parser.add_argument('--date', type=str, help='指定分析日期（YYYY-MM-DD），默认今天')
    parser.add_argument('--code', type=str, help=f'指定股票代码（默认：{DEFAULT_STOCK["code"]}），如：600711、002240')
    parser.add_argument('--name', type=str, help=f'指定股票名称（默认：{DEFAULT_STOCK["name"]}）')
    args = parser.parse_args()

    # 2. 日期处理
    if args.date:
        try:
            target_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"❌ 日期格式错误：{args.date}，请使用YYYY-MM-DD格式")
            sys.exit(1)
    else:
        target_date = datetime.date.today()

    # 2.5. 股票代码处理
    if args.code:
        # 如果用户指定了股票代码，使用用户指定的
        custom_stock = DEFAULT_STOCK.copy()
        custom_stock["code"] = args.code
        if args.name:
            custom_stock["name"] = args.name
        STOCK_LIST = [custom_stock]
        print(f"📈 使用自定义股票：{custom_stock['name']}（{custom_stock['code']}）")
    else:
        print(f"📈 使用默认股票：{DEFAULT_STOCK['name']}（{DEFAULT_STOCK['code']}）")

    # 3. 休市判断（决定报告内容类型）
    if not args.force:
        is_trading, reason = is_trading_day(target_date)
        if not is_trading:
            trading_status = "休市日"
            print(f"⚠️ {target_date} 为{reason}，报告内容将包含海外市场信息...")
        else:
            trading_status = "交易日"
            print(f"✅ {target_date} 为交易日，报告内容将包含A股分析...")
    else:
        trading_status = "交易日"  # 强制运行视为交易日
        print(f"⚠️ 强制运行模式，视为交易日...")

    # 4. 基础初始化（统一生成主升浪策略分析报告）
    today_date = target_date.strftime("%Y-%m-%d")
    today_date_fmt = target_date.strftime("%Y_%m_%d")  # 文件名使用下划线格式
    output_dir = args.output if args.output else OUTPUT_DIR_DEFAULT

    # 统一报告名称
    md_report_name = f"{today_date_fmt}_主升浪策略分析报告.md"
    json_report_name = f"{today_date_fmt}_主升浪策略分析报告.json"

    md_report_path = os.path.join(output_dir, md_report_name)
    json_report_path = os.path.join(output_dir, json_report_name)
    run_log_path = os.path.join(output_dir, "run_log.txt")

    # 5. 检查输出目录
    if not os.path.exists(output_dir):
        print(f"⚠️ 输出目录不存在，自动创建：{output_dir}")
        os.makedirs(output_dir, exist_ok=True)

    if not check_directory_permission(output_dir):
        print("❌ 无目录写入权限，程序退出")
        sys.exit(1)

    # 6. 根据交易日状态生成报告内容
    stock_data_content = ""
    json_results = {
        "report_date": today_date,
        "report_type": "主升浪策略分析",
        "trading_status": trading_status,
        "stocks": []
    }

    if trading_status == "休市日":
        # 休市日：生成海外市场简报内容
        print(f"\n📰 生成休市日简报内容...")
        md_content, json_data = generate_market_brief(target_date, reason)
        stock_data_content = md_content
        json_results["market_brief"] = json_data
    else:
        # 交易日：生成A股分析内容
        print(f"\n📊 开始分析 {len(STOCK_LIST)} 只股票...")

        # 提示：板块维度只能获取当前实时数据
        if args.date and args.date != datetime.date.today().strftime("%Y-%m-%d"):
            print(f"⚠️  注意：指定历史日期时，板块维度只能获取当前实时数据！")

        for stock in STOCK_LIST:
            print(f"  - 正在分析 {stock['name']}（{stock['code']}）...")
            md_content, json_data = get_stock_data(
                stock["code"],
                stock["name"],
                stock.get("main_type", "短线游资"),
                stock.get("industry", ""),
                target_date=target_date
            )
            stock_data_content += md_content
            json_results["stocks"].append(json_data)

            # 批量获取时添加延迟，避免高频请求被封
            if len(STOCK_LIST) > 1:
                stock_index = STOCK_LIST.index(stock)
                if stock_index < len(STOCK_LIST) - 1:  # 不是最后一个股票
                    print(f"  ⏳ 等待 {REQUEST_DELAY_NORMAL} 秒后处理下一只股票...")
                    time.sleep(REQUEST_DELAY_NORMAL)

    # 8. 拼接最终MD内容
    final_md_content = f"""# 股票主升浪策略分析报告 {today_date}

> **报告生成时间**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> **数据来源**: akshare + 手动配置
> **交易状态**: {trading_status}

{stock_data_content}

{STRATEGY_EXPLAIN_MD}
"""

    # 9. 写入MD报告
    if not args.json_only:
        try:
            with open(md_report_path, "w", encoding="utf-8") as f:
                f.write(final_md_content)
            print(f"✅ MD报告已生成：{md_report_path}")
            write_run_log(run_log_path, f"生成MD报告：{md_report_name}")
        except Exception as e:
            error_msg = f"MD报告写入失败：{str(e)}"
            print(f"❌ {error_msg}")
            write_run_log(run_log_path, error_msg, is_success=False)
            sys.exit(1)

    # 10. 写入JSON报告
    if not args.md_only:
        try:
            with open(json_report_path, "w", encoding="utf-8") as f:
                json.dump(json_results, f, ensure_ascii=False, indent=2, cls=NumpyJSONEncoder)
            print(f"✅ JSON报告已生成：{json_report_path}")
            write_run_log(run_log_path, f"生成JSON报告：{json_report_name}")
        except Exception as e:
            error_msg = f"JSON报告写入失败：{str(e)}"
            print(f"❌ {error_msg}")
            write_run_log(run_log_path, error_msg, is_success=False)
            sys.exit(1)

    # 11. 输出摘要
    print(f"\n📊 分析完成！")
    print(f"   - 总股票数：{len(STOCK_LIST)}")
    decision_stats = {}
    for stock in json_results["stocks"]:
        action = stock["decision"]["action"]
        decision_stats[action] = decision_stats.get(action, 0) + 1

    for action, count in decision_stats.items():
        print(f"   - {action}信号：{count}")

# ===================== 策略说明（融入MD报告）=====================
STRATEGY_EXPLAIN_MD = """
## 散户主升浪交易策略（改进版）

### 核心目标
只抓主力主升浪拉升段利润，规避吸筹、洗盘、出货阶段风险

### 数据来源说明
- **akshare免费接口**: K线数据、主力资金数据、行业资金流数据
- **需手动配置**: DK趋势信号、主力筹码数据（akshare无免费接口）
- **暂无法获取**: 全市场筹码分布数据

### 买入信号（必须同时满足6项）
1. 趋势维度：DK信号出现D点（机会信号）⚠️ 需手动配置
2. 主力筹码：主力获利＜10% + 低位单峰密集 ⚠️ 需手动配置
3. 全市场筹码：全市场获利20%-60% + 单峰密集 ⚠️ 暂无法获取
4. 主力资金：连续3日净流入 + 占成交额＞5%
5. 量价维度：放量1.5倍以上 + 突破10日均线
6. 板块维度：所属行业资金排名前10

### 卖出信号（满足任意2项及以上）
1. 趋势维度：DK信号出现K点（风险信号）
2. 主力筹码：主力获利＞30%（游资）/50%（机构） + 高位发散
3. 全市场筹码：全市场获利＞70% + 高位发散
4. 主力资金：连续2日净流出 + 大额出逃
5. 量价维度：放量滞涨（成交量放大但股价不涨）
6. 板块维度：板块资金排名跌出前10 + 资金大幅流出

### 数据边界说明
- ✅ 免费可得：K线数据、主力资金、行业资金流（akshare）
- ⚠️ 需手动配置：DK信号、主力筹码（akshare无免费接口）
- ❌ 暂无法获取：全市场筹码分布、板块资金排名（需要付费数据源）
- ❌ 完全无法获取：主力精确操盘计划、真实持仓成本、资金真实身份

## 核心概念通俗解释

### 1. DK趋势信号
- 定义：股价的"红绿灯"——D点（绿灯）= 主力拉升启动；K点（红灯）= 主力出货下跌
- 用法：只在D点买，K点必卖
- ⚠️ **注意**：akshare无此接口，需手动配置或对接第三方数据源

### 2. 主力筹码分布
- 定义：只算主力的持仓成本/获利情况，看主力是否赚钱、要不要出货
- 关键：主力获利＜10%=安全，＞30%（游资）/50%（机构）= 要出货
- ⚠️ **注意**：akshare无免费的主力筹码接口，需付费数据源或手动配置

### 3. 全市场筹码分布
- 定义：所有投资者的持仓成本，看散户抛压大小
- 关键：全市场获利＞70%=抛压大，必跌；20%-60%=抛压小，易涨
- ❌ **注意**：akshare暂无此接口

### 4. 获利比例
- 主力获利比例：主力卖股票能赚的比例；全市场获利比例：所有人赚钱的比例
- 用法：主力获利看主力动向，全市场获利看散户抛压

### 5. 筹码峰
- 定义：筹码集中的价格区间，单峰=筹码集中，发散=筹码分散
- 关键：低位单峰=主力锁仓拉升；高位发散=主力出货

## 如何配置缺失数据

### 配置DK趋势信号
编辑脚本中的 `DK_SIGNAL_DATA` 字典：
```python
DK_SIGNAL_DATA = {
    "600711": "D点（机会信号）",  # 或 "K点（风险信号）"
    "002240": "D点（机会信号）"
}
```

### 配置主力筹码数据
编辑脚本中的 `MAIN_CHIP_DATA` 字典：
```python
MAIN_CHIP_DATA = {
    "600711": {
        "main_cost": 13.90,        # 主力平均成本
        "main_profit_ratio": 2.09,  # 主力获利比例（%）
        "main_chip_shape": "低位单峰密集"
    }
}
```
"""
# =================================================================

if __name__ == "__main__":
    main()

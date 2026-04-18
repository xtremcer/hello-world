"""
数据获取工具函数
包含带重试机制的数据获取函数
"""

import time
import pandas as pd
from typing import Tuple, Optional
from retrying import retry
import akshare as ak

from config import (
    MAX_RETRIES,
    REQUEST_DELAY_NORMAL,
    REQUEST_DELAY_RETRY,
    REQUEST_DELAY_FAILED,
    RETRY_STOP_MAX_ATTEMPT,
    RETRY_WAIT_FIXED
)


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


def should_retry(exception):
    """
    判断是否应该重试
    - ConnectionError: 网络连接错误
    - RuntimeError: 运行时错误（可能是反爬）
    - 超时错误
    """
    return isinstance(exception, (ConnectionError, RuntimeError, TimeoutError))


# ===================== 带智能重试的接口函数 =====================

@retry(
    stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT,
    wait_fixed=RETRY_WAIT_FIXED,
    retry_on_exception=should_retry
)
def get_dk_signal_safe(stock_code: str, period: str = "day") -> pd.DataFrame:
    """获取个股DK信号数据（带智能重试）"""
    return ak.stock_dk_signal(symbol=stock_code, period=period)


@retry(
    stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT,
    wait_fixed=RETRY_WAIT_FIXED,
    retry_on_exception=should_retry
)
def get_chip_distribution_safe(stock_code: str, period: str = "day") -> pd.DataFrame:
    """获取个股筹码分布数据（带智能重试）"""
    return ak.stock_chip_distribution(symbol=stock_code, period=period)


@retry(
    stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT,
    wait_fixed=RETRY_WAIT_FIXED,
    retry_on_exception=should_retry
)
def get_chip_cost_safe(stock_code: str, adjust: str = "qfq") -> pd.DataFrame:
    """获取个股筹码成本数据（带智能重试）"""
    return ak.stock_chip_cost(symbol=stock_code, adjust=adjust)


# ===================== 调用层接口函数 =====================

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

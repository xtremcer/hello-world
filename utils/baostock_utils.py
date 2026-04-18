"""
baostock 数据获取工具（优化版）
提供稳定的历史K线数据获取功能，支持批量获取和频率控制

特性：
1. 前复权设置（adjustflag=2），确保数据连续性
2. 批量获取时控制频率，避免触发限制（QPS 约 20）
3. 通用于所有个股（A股、指数、ETF 等）
4. 支持分页获取，一次最多 100 条
5. 自动重试机制
"""

import baostock as bs
import pandas as pd
from typing import Tuple, Optional, List, Dict
import logging
import time

logger = logging.getLogger(__name__)

# ===================== baostock 配置 =====================
# 前复权设置（确保数据连续性）
DEFAULT_ADJUSTFLAG = "2"  # 1=后复权, 2=前复权, 3=不复权

# 频率控制配置（避免触发限制）
QPS_LIMIT = 20  # 每秒最多 20 次查询
REQUEST_INTERVAL = 0.1  # 请求间隔（秒），确保不超过 QPS 限制

# 分页配置
PAGE_SIZE = 100  # 每页数据量（baostock 限制最多 100 条）

# 重试配置
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 1  # 重试延迟（秒）


# ===================== 全局状态管理 =====================
class BaostockManager:
    """baostock 全局状态管理器"""

    _instance = None
    _logged_in = False
    _request_count = 0
    _last_request_time = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self._logged_in

    def set_logged_in(self, status: bool):
        """设置登录状态"""
        self._logged_in = status

    def control_frequency(self):
        """控制请求频率，避免触发 QPS 限制"""
        current_time = time.time()
        if current_time - self._last_request_time < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - (current_time - self._last_request_time))
        self._last_request_time = time.time()
        self._request_count += 1


# 创建全局管理器
baostock_manager = BaostockManager()


# ===================== 基础函数 =====================
def baostock_login() -> bool:
    """
    登录 baostock（全局单例，避免重复登录）

    返回: 是否成功
    """
    if baostock_manager.is_logged_in():
        logger.debug("已登录 baostock，跳过重复登录")
        return True

    try:
        lg = bs.login()
        if lg.error_code != '0':
            logger.error(f"登录 baostock 失败：{lg.error_msg}")
            return False
        baostock_manager.set_logged_in(True)
        logger.info("登录 baostock 成功")
        return True
    except Exception as e:
        logger.error(f"登录 baostock 异常：{str(e)}")
        return False


def baostock_logout() -> bool:
    """
    登出 baostock（全局单例，避免重复登出）

    返回: 是否成功
    """
    if not baostock_manager.is_logged_in():
        logger.debug("未登录 baostock，跳过登出")
        return True

    try:
        lg = bs.logout()
        if lg.error_code != '0':
            logger.error(f"登出 baostock 失败：{lg.error_msg}")
            return False
        baostock_manager.set_logged_in(False)
        logger.info("登出 baostock 成功")
        return True
    except Exception as e:
        logger.error(f"登出 baostock 异常：{str(e)}")
        return False


def _validate_code(code: str) -> Tuple[bool, str]:
    """
    验证股票代码格式

    参数:
        code: 股票代码（如 "sh.600711"）

    返回:
        (是否有效, 错误信息)
    """
    if not code or not isinstance(code, str):
        return False, "股票代码不能为空"

    parts = code.split('.')
    if len(parts) != 2:
        return False, "股票代码格式错误，应为 '市场.代码' 格式（如 'sh.600711'）"

    market, stock_code = parts

    # 验证市场代码
    if market not in ['sh', 'sz']:
        return False, f"市场代码错误：{market}，应为 'sh' 或 'sz'"

    # 验证股票代码（6 位数字）
    if not stock_code.isdigit() or len(stock_code) != 6:
        return False, f"股票代码错误：{stock_code}，应为 6 位数字"

    return True, ""


def _convert_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    转换数据类型，确保数据连续性

    参数:
        df: 原始 DataFrame

    返回:
        转换后的 DataFrame
    """
    # 转换日期列
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])

    # 转换数值列
    numeric_fields = ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn', 'pctChg']
    for field in numeric_fields:
        if field in df.columns:
            df[field] = pd.to_numeric(df[field], errors='coerce')

    # 删除空行
    df = df.dropna()

    # 按日期升序排序
    if 'date' in df.columns:
        df = df.sort_values('date').reset_index(drop=True)

    return df


def _query_with_retry(
    query_func,
    *args,
    max_retries: int = MAX_RETRIES,
    retry_delay: float = RETRY_DELAY,
    **kwargs
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    带重试机制的查询函数

    参数:
        query_func: 查询函数
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        *args, **kwargs: 查询函数的参数

    返回:
        (DataFrame, 错误信息)
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            # 控制请求频率
            baostock_manager.control_frequency()

            # 执行查询
            result, error = query_func(*args, **kwargs)

            if result is not None and not result.empty:
                return result, None

            last_error = error

            if attempt < max_retries - 1:
                logger.warning(f"查询失败，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})：{error}")
                time.sleep(retry_delay)

        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                logger.warning(f"查询异常，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})：{e}")
                time.sleep(retry_delay)

    error_msg = f"查询失败，已达最大重试次数：{last_error}"
    logger.error(error_msg)
    return None, error_msg


# ===================== 单个股查询函数 =====================
def query_single_stock(
    code: str,
    fields: str = "date,open,high,low,close,volume,amount",
    start_date: str = None,
    end_date: str = None,
    frequency: str = "d",
    adjustflag: str = DEFAULT_ADJUSTFLAG,
    validate: bool = True
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    查询单个股票的历史K线数据（推荐使用）

    参数:
        code: 股票代码（如 "sh.600711"）
        fields: 字段列表（逗号分隔），支持：date,open,high,low,close,volume,amount,turn,tradestatus,pctChg,isST
        start_date: 开始日期（格式 "YYYY-MM-DD"），默认查询最近 2 年数据
        end_date: 结束日期（格式 "YYYY-MM-DD"）
        frequency: 数据类型（d=日k线、w=周、m=月）
        adjustflag: 复权类型（1=后复权、2=前复权、3=不复权）
        validate: 是否验证股票代码格式

    返回:
        (DataFrame, 错误信息)

    特性：
        - 前复权设置（adjustflag=2），确保数据连续性
        - 自动重试机制
        - 频率控制，避免触发限制
    """
    # 验证股票代码格式
    if validate:
        is_valid, error_msg = _validate_code(code)
        if not is_valid:
            return None, error_msg

    # 如果没有指定开始日期，默认查询最近 2 年的数据
    if start_date is None:
        from datetime import datetime, timedelta
        start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

    # 登录 baostock
    if not baostock_login():
        return None, "登录 baostock 失败"

    def _query() -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """内部查询函数"""
        try:
            # baostock 的 query_history_k_data_plus 会一次性返回所有数据，不需要分页
            rs = bs.query_history_k_data_plus(
                code,
                fields,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag=adjustflag
            )

            if rs.error_code != '0':
                error_msg = f"查询失败（{rs.error_code}）：{rs.error_msg}"
                return None, error_msg

            # 读取所有数据
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                return None, "查询结果为空"

            df = pd.DataFrame(data_list, columns=rs.fields)

            # 转换数据类型
            df = _convert_dataframe(df)

            return df, None

        except Exception as e:
            return None, f"查询异常：{str(e)}"

    # 执行查询（带重试）
    return _query_with_retry(_query)


# ===================== 批量查询函数 =====================
def query_multiple_stocks(
    codes: List[str],
    fields: str = "date,open,high,low,close,volume,amount",
    start_date: str = None,
    end_date: str = None,
    frequency: str = "d",
    adjustflag: str = DEFAULT_ADJUSTFLAG,
    validate: bool = True,
    show_progress: bool = True
) -> Dict[str, Tuple[Optional[pd.DataFrame], Optional[str]]]:
    """
    批量查询多个股票的历史K线数据

    参数:
        codes: 股票代码列表（如 ["sh.600711", "sz.000001"]）
        fields: 字段列表（逗号分隔）
        start_date: 开始日期（格式 "YYYY-MM-DD"）
        end_date: 结束日期（格式 "YYYY-MM-DD"）
        frequency: 数据类型（d=日k线、w=周、m=月）
        adjustflag: 复权类型（1=后复权、2=前复权、3=不复权）
        validate: 是否验证股票代码格式
        show_progress: 是否显示进度

    返回:
        {股票代码: (DataFrame, 错误信息)}

    特性：
        - 自动控制频率，避免触发 QPS 限制
        - 前复权设置（adjustflag=2），确保数据连续性
        - 通用于所有个股（A股、指数、ETF 等）
        - 支持进度显示
    """
    results = {}
    total = len(codes)
    failed = 0

    # 登录 baostock
    if not baostock_login():
        for code in codes:
            results[code] = (None, "登录 baostock 失败")
        return results

    for i, code in enumerate(codes, 1):
        # 显示进度
        if show_progress:
            logger.info(f"正在获取 [{i}/{total}] {code} 的数据...")

        # 查询单个股票
        df, error = query_single_stock(
            code=code,
            fields=fields,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag=adjustflag,
            validate=validate
        )

        results[code] = (df, error)

        if df is None:
            failed += 1

    # 显示汇总信息
    if show_progress:
        success = total - failed
        logger.info(f"批量查询完成：成功 {success}/{total}，失败 {failed}/{total}")

    return results


# ===================== 便捷查询函数 =====================
def get_stock_data(
    stock_code: str,
    market: str = None,
    fields: List[str] = None,
    start_date: str = None,
    end_date: str = None,
    frequency: str = "d",
    adjustflag: str = DEFAULT_ADJUSTFLAG
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    便捷函数：获取股票数据（自动处理市场代码）

    参数:
        stock_code: 股票代码（6 位数字，如 "600711"）
        market: 市场代码（sh/sz），如果为空，则自动判断
        fields: 字段列表（如 ["date", "close", "volume"]）
        start_date: 开始日期（格式 "YYYY-MM-DD"）
        end_date: 结束日期（格式 "YYYY-MM-DD"）
        frequency: 数据类型（d=日k线、w=周、m=月）
        adjustflag: 复权类型（1=后复权、2=前复权、3=不复权）

    返回:
        (DataFrame, 错误信息)

    特性：
        - 自动判断市场代码（sh/sz）
        - 支持字段列表格式
        - 前复权设置（adjustflag=2），确保数据连续性
    """
    from utils.helpers import get_market

    # 获取市场代码
    if market is None:
        market = get_market(stock_code)

    # 构造完整代码
    code = f"{market}.{stock_code}"

    # 构造字段字符串
    if fields is None:
        fields_str = "date,open,high,low,close,volume,amount"
    else:
        fields_str = ",".join(fields)

    # 查询数据
    return query_single_stock(
        code=code,
        fields=fields_str,
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        adjustflag=adjustflag,
        validate=False
    )


def get_trend_data(
    stock_code: str,
    market: str = None,
    start_date: str = None,
    end_date: str = None,
    adjustflag: str = DEFAULT_ADJUSTFLAG
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    便捷函数：获取趋势分析所需的数据（日期、收盘价、最高价、成交量）

    参数:
        stock_code: 股票代码（6 位数字，如 "600711"）
        market: 市场代码（sh/sz），如果为空，则自动判断
        start_date: 开始日期（格式 "YYYY-MM-DD"）
        end_date: 结束日期（格式 "YYYY-MM-DD"）
        adjustflag: 复权类型（1=后复权、2=前复权、3=不复权）

    返回:
        (DataFrame, 错误信息)

    DataFrame 列：date, close, high, volume
    """
    return get_stock_data(
        stock_code=stock_code,
        market=market,
        fields=["date", "close", "high", "volume"],
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag=adjustflag
    )


def get_price_volume_data(
    stock_code: str,
    market: str = None,
    start_date: str = None,
    end_date: str = None,
    adjustflag: str = DEFAULT_ADJUSTFLAG
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    便捷函数：获取量价分析所需的数据（日期、收盘价、成交量）

    参数:
        stock_code: 股票代码（6 位数字，如 "600711"）
        market: 市场代码（sh/sz），如果为空，则自动判断
        start_date: 开始日期（格式 "YYYY-MM-DD"）
        end_date: 结束日期（格式 "YYYY-MM-DD"）
        adjustflag: 复权类型（1=后复权、2=前复权、3=不复权）

    返回:
        (DataFrame, 错误信息)

    DataFrame 列：date, close, volume
    """
    return get_stock_data(
        stock_code=stock_code,
        market=market,
        fields=["date", "close", "volume"],
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag=adjustflag
    )


def get_stock_info(stock_code: str, market: str = None) -> Tuple[Optional[Dict], Optional[str]]:
    """
    获取股票基本信息（名称+行业）（通过baostock接口）

    参数:
        stock_code: 股票代码（6 位数字，如 "600711"）
        market: 市场代码（sh/sz），如果为空，则自动判断

    返回:
        ({'name': 股票名称, 'industry': 行业名称}, 错误信息)
        如果获取失败，返回 (None, 错误信息)
    """
    from utils.helpers import get_market

    # 获取市场代码
    if market is None:
        market = get_market(stock_code)

    # 构造完整代码
    code = f"{market}.{stock_code}"

    # 登录 baostock
    if not baostock_login():
        return None, "登录 baostock 失败"

    try:
        # 查询行业分类
        rs = bs.query_stock_industry(code)

        if rs.error_code != '0':
            baostock_logout()
            return None, f"查询失败（{rs.error_code}）：{rs.error_msg}"

        # 读取结果
        while (rs.error_code == '0') & rs.next():
            row_data = rs.get_row_data()
            if len(row_data) >= 4:
                # baostock query_stock_industry 返回格式（实际测试）：
                # row_data[0]: 日期
                # row_data[1]: 股票代码 (sz.002240)
                # row_data[2]: 股票名称 (盛新锂能)
                # row_data[3]: 行业名称 (C32有色金属冶炼和压延加工业)
                # row_data[4]: 分类 (证监会行业分类)
                stock_name = row_data[2].strip() if row_data[2] else None
                industry = row_data[3].strip() if row_data[3] else None
                if stock_name or industry:
                    baostock_logout()
                    return {
                        'name': stock_name,
                        'industry': industry
                    }, None

        baostock_logout()
        return None, "未找到股票信息"

    except Exception as e:
        baostock_logout()
        return None, f"查询异常：{str(e)}"


def get_stock_industry(stock_code: str, market: str = None) -> Tuple[Optional[str], Optional[str]]:
    """
    获取股票所属行业分类（通过baostock接口）

    参数:
        stock_code: 股票代码（6 位数字，如 "600711"）
        market: 市场代码（sh/sz），如果为空，则自动判断

    返回:
        (行业名称, 错误信息)
        如果获取失败，返回 (None, 错误信息)
    """
    info, error = get_stock_info(stock_code, market)
    if info and info.get('industry'):
        return info['industry'], None
    return None, error


def get_stock_name(stock_code: str, market: str = None) -> Tuple[Optional[str], Optional[str]]:
    """
    获取股票名称（通过baostock接口）

    参数:
        stock_code: 股票代码（6 位数字，如 "600711"）
        market: 市场代码（sh/sz），如果为空，则自动判断

    返回:
        (股票名称, 错误信息)
        如果获取失败，返回 (None, 错误信息)
    """
    info, error = get_stock_info(stock_code, market)
    if info and info.get('name'):
        return info['name'], None
    return None, error

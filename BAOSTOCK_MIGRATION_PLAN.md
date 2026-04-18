# akshare 与 baostock 平替方案分析

## 一、akshare 接口使用情况

### 1.1 趋势维度（trend.py）
- **接口**: `ak.stock_zh_a_hist`
- **功能**: 获取历史K线数据（日期、收盘、最高、成交量）
- **字段**: date, close, high, volume

### 1.2 主力资金维度（fund_flow.py）
- **接口**: `ak.stock_individual_fund_flow`
- **功能**: 获取个股主力资金流向数据
- **字段**: 日期、主力净流入、主力净流入率等

### 1.3 量价维度（price_volume.py）
- **接口**: `ak.stock_zh_a_daily`
- **功能**: 获取历史K线数据（前复权）
- **字段**: date, open, close, high, low, volume, amount, etc.

### 1.4 板块维度（block.py）
- **接口**: `ak.stock_fund_flow_industry`
- **功能**: 获取行业资金流向排名
- **字段**: 行业名称、行业净流入、排名等

### 1.5 休市简报（market_brief.py）
- **接口**: `ak.stock_zh_index_daily`
- **功能**: 获取上证指数日线数据
- **字段**: date, close, high, low, volume, amount
- **接口**: `ak.index_global_spot_em`
- **功能**: 获取全球指数实时行情
- **字段**: 指数名称、最新价、涨跌幅等

### 1.6 主力筹码维度（main_chip.py）
- **接口**: `ak.stock_chip_cost`
- **功能**: 获取个股筹码成本数据
- **状态**: akshare 无此接口，需手动配置

### 1.7 市场筹码维度（market_chip.py）
- **接口**: `ak.stock_chip_distribution`
- **功能**: 获取个股筹码分布数据
- **状态**: akshare 无此接口，需手动配置

## 二、baostock 接口能力分析

### 2.1 历史K线数据
- **接口**: `bs.query_history_k_data_plus`
- **功能**: 获取股票历史K线数据
- **参数**:
  - code: 股票代码（如 "sh.600711"）
  - fields: 字段列表（date,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pctChg,isST）
  - start_date: 开始日期（格式 "YYYY-MM-DD"）
  - end_date: 结束日期（格式 "YYYY-MM-DD"）
  - frequency: 数据类型（d=日k线、w=周、m=月）
  - adjustflag: 复权类型（1=后复权、2=前复权、3=不复权）
- **优点**:
  - ✅ 无免费额度限制
  - ✅ QPS 限制约 20（每秒查询次数）
  - ✅ 稳定性好
  - ✅ 支持前复权/后复权/不复权
- **限制**:
  - ❌ 一次最多获取 100 条数据（需分页获取）
  - ❌ 不支持实时数据（T+1）

### 2.2 指数数据
- **接口**: `bs.query_history_k_data_plus`
- **功能**: 获取指数历史数据
- **示例**: 上证指数代码 "sh.000001"

### 2.3 不支持的功能
- ❌ 主力资金流向数据
- ❌ 行业资金流向排名
- ❌ 全球指数实时行情
- ❌ 筹码分布数据
- ❌ 筹码成本数据

## 三、平替方案

### 3.1 可以用 baostock 平替的模块

| 模块 | akshare 接口 | baostock 接口 | 平替难度 |
|-----|------------|--------------|---------|
| **趋势维度** | `stock_zh_a_hist` | `query_history_k_data_plus` | ⭐ 简单 |
| **量价维度** | `stock_zh_a_daily` | `query_history_k_data_plus` | ⭐ 简单 |
| **休市简报** | `stock_zh_index_daily` | `query_history_k_data_plus` | ⭐ 简单 |

### 3.2 不能用 baostock 平替的模块

| 模块 | akshare 接口 | 原因 | 替代方案 |
|-----|------------|------|---------|
| **主力资金维度** | `stock_individual_fund_flow` | baostock 无此接口 | 保留 akshare 或手动计算 |
| **板块维度** | `stock_fund_flow_industry` | baostock 无此接口 | 保留 akshare 或手动配置 |
| **全球指数** | `index_global_spot_em` | baostock 无此接口 | 保留 akshare |
| **主力筹码维度** | `stock_chip_cost` | akshare 无此接口 | 手动配置 |
| **市场筹码维度** | `stock_chip_distribution` | akshare 无此接口 | 手动配置 |

## 四、实施方案

### 4.1 优先平替的模块（建议）

#### 4.1.1 创建 baostock 数据获取工具
```python
# utils/baostock_utils.py

import baostock as bs
import pandas as pd
from typing import Tuple, Optional

def baostock_login() -> bool:
    """登录 baostock"""
    lg = bs.login()
    return lg.error_code == '0'

def baostock_logout() -> bool:
    """登出 baostock"""
    lg = bs.logout()
    return lg.error_code == '0'

def query_history_k_data(
    code: str,
    fields: str = "date,open,high,low,close,volume,amount",
    start_date: str = None,
    end_date: str = None,
    frequency: str = "d",
    adjustflag: str = "2"
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    查询历史K线数据

    参数:
        code: 股票代码（如 "sh.600711"）
        fields: 字段列表
        start_date: 开始日期（格式 "YYYY-MM-DD"）
        end_date: 结束日期（格式 "YYYY-MM-DD"）
        frequency: 数据类型（d=日k线、w=周、m=月）
        adjustflag: 复权类型（1=后复权、2=前复权、3=不复权）

    返回:
        (DataFrame, 错误信息)
    """
    try:
        rs = bs.query_history_k_data_plus(
            code,
            fields,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag=adjustflag
        )

        if rs.error_code != '0':
            return None, f"查询失败：{rs.error_msg}"

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        df = pd.DataFrame(data_list, columns=rs.fields)

        # 转换数据类型
        numeric_fields = ['open', 'high', 'low', 'close', 'volume', 'amount']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')

        return df, None

    except Exception as e:
        return None, f"查询异常：{str(e)}"
```

#### 4.1.2 更新 trend.py 模块
```python
# modules/dimensions/trend.py

from utils.baostock_utils import baostock_login, baostock_logout, query_history_k_data

def module1_get_data(stock_code: str, market: str) -> Tuple[pd.DataFrame, str]:
    """
    模块 1：数据获取（使用 baostock）
    """
    try:
        # 登录 baostock
        if not baostock_login():
            return None, "登录 baostock 失败"

        # 构造股票代码
        code = f"{market}.{stock_code}"

        # 获取历史数据（前复权）
        df, error = query_history_k_data(
            code=code,
            fields="date,close,high,volume",
            adjustflag="2"  # 前复权
        )

        # 登出 baostock
        baostock_logout()

        if df is None or df.empty:
            return None, f"获取历史数据失败：{error}"

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
```

#### 4.1.3 更新 price_volume.py 模块
```python
# modules/dimensions/price_volume.py

from utils.baostock_utils import baostock_login, baostock_logout, query_history_k_data

def analyze_price_volume(stock_code: str, main_type: str = "短线游资", target_date: datetime.date = None) -> Tuple[str, Dict]:
    """
    分析量价维度（使用 baostock）
    """
    try:
        # 登录 baostock
        if not baostock_login():
            stock_md_content += "- ❌ **数据获取失败**：登录 baostock 失败\n"
            return stock_md_content, json_data

        # 构造股票代码
        code = f"{market}{stock_code}"

        # 计算日期范围
        if target_date:
            start_date = (target_date - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = target_date.strftime("%Y-%m-%d")
        else:
            start_date = None
            end_date = None

        # 获取历史数据（前复权）
        kline_df, kline_error = query_history_k_data(
            code=code,
            fields="date,close,volume",
            start_date=start_date,
            end_date=end_date,
            adjustflag="2"  # 前复权
        )

        # 登出 baostock
        baostock_logout()

        # 后续处理逻辑...

    except Exception as e:
        stock_md_content += f"- ❌ **数据获取失败**：{str(e)}\n"
        return stock_md_content, json_data
```

### 4.2 保留 akshare 的模块

| 模块 | 原因 |
|-----|------|
| **主力资金维度** | baostock 无此接口，akshare 提供免费接口 |
| **板块维度** | baostock 无此接口，akshare 提供免费接口 |
| **全球指数** | baostock 无此接口，akshare 提供免费接口 |

### 4.3 手动配置的模块

| 模块 | 原因 | 替代方案 |
|-----|------|---------|
| **主力筹码维度** | akshare 和 baostock 都无此接口 | 在 config.py 中手动配置 |
| **市场筹码维度** | akshare 和 baostock 都无此接口 | 在 config.py 中手动配置 |

## 五、数据源配置策略

### 5.1 推荐配置

```python
# config.py

# 数据源配置
DATA_SOURCE_CONFIG = {
    # 使用 baostock 的模块
    "trend": "baostock",  # 趋势维度
    "price_volume": "baostock",  # 量价维度
    "market_brief": "baostock",  # 休市简报

    # 保留 akshare 的模块
    "fund_flow": "akshare",  # 主力资金维度
    "block": "akshare",  # 板块维度
    "global_indices": "akshare",  # 全球指数

    # 手动配置的模块
    "main_chip": "manual",  # 主力筹码维度
    "market_chip": "manual",  # 市场筹码维度
}
```

### 5.2 备份策略

```python
# 数据源备份策略
DATA_SOURCE_BACKUP = {
    "trend": {
        "primary": "baostock",
        "backup": "akshare",  # 如果 baostock 失败，使用 akshare
        "timeout": 30  # 超时时间（秒）
    },
    "price_volume": {
        "primary": "baostock",
        "backup": "akshare",
        "timeout": 30
    }
}
```

## 六、性能对比

| 指标 | akshare | baostock |
|-----|---------|----------|
| 免费额度 | 有限制（未明确） | 无明确限制 |
| QPS 限制 | 不明确（可能较低） | 约 20 |
| 稳定性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 数据覆盖 | 广（K线、资金、板块等） | 窄（主要是K线和指数） |
| 实时性 | 支持（部分接口） | T+1 |
| 一次获取数据量 | 无限制 | 最多 100 条（需分页） |

## 七、总结

### 7.1 建议
1. **优先平替**：趋势维度、量价维度、休市简报使用 baostock
2. **保留 akshare**：主力资金维度、板块维度、全球指数使用 akshare
3. **手动配置**：主力筹码维度、市场筹码维度在 config.py 中配置

### 7.2 优势
- ✅ 提高稳定性（baostock 稳定性好）
- ✅ 降低限流风险（baostock QPS 约 20）
- ✅ 无免费额度限制
- ✅ 降低依赖（多数据源）

### 7.3 风险
- ⚠️ baostock 一次最多获取 100 条数据（需分页）
- ⚠️ baostock 不支持实时数据（T+1）
- ⚠️ 需要增加代码复杂度（管理多个数据源）

# baostock 优化使用文档

## 一、核心特性

### 1. 前复权设置（确保数据连续性）
- **参数**: `adjustflag="2"`
- **效果**: 确保历史数据连续性，避免因除权除息导致的价格跳变
- **适用**: 所有个股（A股、指数、ETF 等）

### 2. 频率控制（避免触发限制）
- **配置**: `QPS_LIMIT = 20`（每秒最多 20 次查询）
- **请求间隔**: `REQUEST_INTERVAL = 0.1` 秒
- **效果**: 自动控制请求频率，避免触发 baostock 限制

### 3. 批量获取（支持多股票查询）
- **函数**: `query_multiple_stocks()`
- **支持**: 一次查询多只股票
- **特性**: 自动频率控制，无需手动延迟

### 4. 通用性（通用于所有个股）
- **支持**: A 股（sh/sz）、指数、ETF 等
- **自动判断**: 自动判断市场代码（sh/sz）
- **格式统一**: 统一的返回格式（DataFrame）

## 二、使用方法

### 2.1 基础使用（推荐）

#### 趋势分析数据
```python
from utils.baostock_utils import get_trend_data

# 获取趋势分析所需的数据（日期、收盘价、最高价、成交量）
df, error = get_trend_data(
    stock_code="600711",
    market="sh",
    adjustflag="2"  # 前复权，确保数据连续性
)

if df is not None:
    print(df.tail(10))
```

#### 量价分析数据
```python
from utils.baostock_utils import get_price_volume_data

# 获取量价分析所需的数据（日期、收盘价、成交量）
df, error = get_price_volume_data(
    stock_code="600711",
    market="sh",
    adjustflag="2"  # 前复权
)

if df is not None:
    print(df.tail(10))
```

### 2.2 高级使用

#### 自定义字段查询
```python
from utils.baostock_utils import query_single_stock

# 查询自定义字段
df, error = query_single_stock(
    code="sh.600711",
    fields="date,open,high,low,close,volume,amount,turn,pctChg",
    start_date="2025-01-01",
    end_date="2026-04-10",
    adjustflag="2"  # 前复权
)

if df is not None:
    print(df.tail(10))
```

#### 批量查询
```python
from utils.baostock_utils import query_multiple_stocks

# 批量查询多只股票
results = query_multiple_stocks(
    codes=["sh.600711", "sz.000001", "sz.000002"],
    fields="date,close,high,volume",
    adjustflag="2",  # 前复权
    show_progress=True
)

# 处理结果
for code, (df, error) in results.items():
    if df is not None:
        print(f"{code}: {len(df)} 条数据")
    else:
        print(f"{code}: {error}")
```

## 三、配置说明

### 3.1 前复权设置
```python
DEFAULT_ADJUSTFLAG = "2"  # 1=后复权, 2=前复权, 3=不复权
```

| 复权类型 | 参数 | 说明 | 适用场景 |
|---------|------|------|---------|
| 前复权 | "2" | 从当前向前调整历史价格 | **推荐**（趋势分析、DK信号） |
| 后复权 | "1" | 从历史向后调整当前价格 | 回测分析 |
| 不复权 | "3" | 原始价格 | 参考对比 |

### 3.2 频率控制配置
```python
QPS_LIMIT = 20  # 每秒最多 20 次查询
REQUEST_INTERVAL = 0.1  # 请求间隔（秒）
```

**建议**:
- 批量查询时使用 `query_multiple_stocks()`，无需手动控制频率
- 单个查询时系统会自动控制频率
- 避免在循环中直接调用 `query_single_stock()`，应使用批量查询函数

### 3.3 分页配置
```python
PAGE_SIZE = 100  # 每页数据量（baostock 限制最多 100 条）
```

**说明**:
- 系统会自动分页获取数据，无需手动处理
- 一次查询可以获取任意数量的数据

## 四、通用性示例

### 4.1 A 股股票
```python
# 沪市 A 股
df, error = get_trend_data(stock_code="600711", market="sh")

# 深市 A 股
df, error = get_trend_data(stock_code="000001", market="sz")
```

### 4.2 指数
```python
from utils.baostock_utils import query_single_stock

# 上证指数
df, error = query_single_stock(code="sh.000001", adjustflag="2")

# 深证成指
df, error = query_single_stock(code="sz.399001", adjustflag="2")
```

### 4.3 ETF
```python
from utils.baostock_utils import query_single_stock

# 沪市 ETF
df, error = query_single_stock(code="sh.510300", adjustflag="2")

# 深市 ETF
df, error = query_single_stock(code="sz.159919", adjustflag="2")
```

## 五、最佳实践

### 5.1 选择数据源
```python
# 趋势维度、量价维度：使用 baostock（稳定）
from utils.baostock_utils import get_trend_data
df, error = get_trend_data(stock_code="600711", market="sh")

# 主力资金、板块、全球指数：使用 akshare（baostock 不支持）
import akshare as ak
df = ak.stock_individual_fund_flow(stock="600711", market="sh")
```

### 5.2 批量查询
```python
# ✅ 推荐：使用批量查询函数
results = query_multiple_stocks(
    codes=["sh.600711", "sz.000001", "sz.000002"],
    show_progress=True
)

# ❌ 不推荐：手动循环查询（可能触发限流）
for code in codes:
    df, error = query_single_stock(code=code)  # 可能触发限流
```

### 5.3 异常处理
```python
from utils.baostock_utils import get_trend_data

df, error = get_trend_data(stock_code="600711", market="sh")

if df is None or df.empty:
    if "登录" in error:
        print("登录失败，请检查网络连接")
    elif "查询结果为空" in error:
        print("查询结果为空，请检查股票代码或日期范围")
    else:
        print(f"其他错误：{error}")
else:
    print(f"成功获取 {len(df)} 条数据")
```

## 六、常见问题

### Q1: 为什么使用前复权？
**A**: 前复权可以确保历史数据连续性，避免因除权除息导致的价格跳变，适合趋势分析和 DK 信号计算。

### Q2: 批量查询时需要手动控制频率吗？
**A**: 不需要。`query_multiple_stocks()` 函数会自动控制频率，确保不超过 QPS 限制。

### Q3: 如何判断查询是否成功？
**A**: 检查返回的 `df` 是否为 None 或空：
```python
if df is not None and not df.empty:
    # 查询成功
    pass
else:
    # 查询失败
    print(f"错误：{error}")
```

### Q4: 可以查询多长时间的数据？
**A**: baostock 可以查询上市以来的所有历史数据，系统会自动分页获取。

### Q5: 如何确保数据连续性？
**A**: 使用 `adjustflag="2"`（前复权），系统会自动处理除权除息，确保数据连续性。

## 七、性能优化建议

1. **批量查询**: 一次查询多只股票，而不是逐个查询
2. **按需查询**: 只查询需要的字段，减少数据传输量
3. **缓存数据**: 对于不常变化的数据，可以缓存到本地
4. **异常重试**: 使用系统内置的重试机制，不要手动重复查询

## 八、测试验证

运行测试脚本验证功能：
```bash
python test_baostock_optimized.py
```

测试内容包括：
1. 全局状态管理
2. 单个股票查询
3. 批量查询（频率控制）
4. 前复权设置
5. 异常处理

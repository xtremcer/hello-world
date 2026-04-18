# 股票自动化分析程序 - 项目文档

## 项目概述
- **名称**: 股票自动化分析程序（模块化重构版）
- **功能**: 基于 Python 的股票量化交易策略分析工具，支持趋势、主力筹码、市场筹码、资金流向、量价、板块等 6 个维度的独立分析，自动生成 Markdown 格式分析报告。

## 项目结构

```
stock/
├── config.py                    # 配置管理
├── main.py                      # 主程序入口
├── requirements.txt             # 依赖包列表
├── README.md                    # 项目说明文档
├── QUICKSTART.md               # 快速入门指南
├── UPDATE_LOG.md               # 更新日志
├── REPORT_LOCATION.md          # 报告存放位置说明
├── TREND_MODULE_UPDATE.md      # 趋势模块更新说明
│
├── utils/                      # 工具模块
│   ├── __init__.py
│   ├── helpers.py              # 辅助函数（股票代码格式化等）
│   └── fetch_utils.py          # 数据获取工具（带重试机制）
│
├── modules/                    # 核心模块
│   ├── __init__.py
│   ├── market_brief.py         # 市场概览
│   ├── stock_analyzer.py       # 股票分析器（主分析逻辑）
│   └── dimensions/             # 各维度分析模块
│       ├── __init__.py
│       ├── trend.py            # 趋势维度（DK 信号）- 已重写
│       ├── main_chip.py        # 主力筹码维度
│       ├── market_chip.py      # 市场筹码维度
│       ├── fund_flow.py        # 资金流向维度
│       ├── price_volume.py     # 量价维度
│       └── block.py            # 板块维度
```

## 模块说明

### 核心模块

#### 1. config.py
**功能**: 集中管理所有配置
- 股票列表（TARGET_STOCKS）
- DK 信号配置（DK_SIGNAL_CONFIG）
- 主力筹码配置（MAIN_CHIP_CONFIG）
- 报告输出目录（OUTPUT_DIR = /mnt/nas/stock）

#### 2. main.py
**功能**: 主程序入口
- 遍历股票列表
- 调用各维度分析模块
- 实时显示模块完成情况（成功/失败/缺失）
- 生成并保存 Markdown 报告

#### 3. utils/helpers.py
**功能**: 辅助函数
- `get_market(stock_code)`: 根据股票代码判断交易所（sh/sz）

#### 4. utils/fetch_utils.py
**功能**: 数据获取工具
- `fetch_with_retry(func, **kwargs)`: 带重试机制的数据获取函数

#### 5. modules/market_brief.py
**功能**: 市场概览
- 获取 A 股市场基本信息

#### 6. modules/stock_analyzer.py
**功能**: 股票分析器（核心逻辑）
- `analyze_single_stock(stock_code)`: 分析单只股票的所有维度
- `print_module_status(modules_status)`: 打印各模块完成情况

### 维度模块

#### 1. modules/dimensions/trend.py（已重写）
**功能**: 趋势维度分析（DK 信号）
**实现方式**: 5 模块方案
- **模块 1**: `module1_get_data()` - AkShare 数据获取
  - 调用 `stock_zh_a_hist` 接口
  - 提取：日期、收盘价、最高价、成交量
  - 按日期升序排序
- **模块 2**: `module2_calculate_indicators()` - 指标计算
  - 计算 EMA12、EMA26
  - 计算 MAV5（5 日均量）
  - 计算金叉/死叉
  - 计算 5 日新高/新低
- **模块 3**: `module3_mark_dk_signals()` - DK 信号标记
  - D 点条件：金叉 + 5 日新高 + 成交量放大 > MAV5 + 价格突破 EMA26
  - K 点条件：死叉 + 5 日新低 + 成交量放大 > MAV5 + 价格跌破 EMA26
  - 去重：连续信号只保留第一个
- **模块 4**: `module4_calculate_gain()` - D 点后涨幅计算
  - 计算每个 D 点后所有交易日的最高价
  - 计算累计最大涨幅（保留 3 位小数）
  - 返回最近 D 点的累计最大涨幅
- **模块 5**: 结果输出（集成在 `analyze_trend()` 函数中）
  - 生成 Markdown 格式输出
  - 显示最近 20 日 DK 信号
  - 显示最近 5 日指标详情

**测试状态**:
- ✅ 模块 2（指标计算）：已通过模拟数据测试
- ✅ 模块 3（DK 信号标记）：已通过模拟数据测试
- ✅ 模块 4（D 点后涨幅计算）：已通过模拟数据测试
- ⚠️ 模块 1（数据获取）：因 akshare 接口连接问题暂未完成实际数据测试

#### 2. modules/dimensions/main_chip.py
**功能**: 主力筹码维度
- 分析主力资金持仓变化
- 判断主力筹码分布情况

#### 3. modules/dimensions/market_chip.py
**功能**: 市场筹码维度
- 分析市场整体筹码分布
- 判断筹码集中度

#### 4. modules/dimensions/fund_flow.py
**功能**: 资金流向维度
- 分析主力资金流入流出
- 判断资金面情况

#### 5. modules/dimensions/price_volume.py
**功能**: 量价维度
- 分析价格与成交量关系
- 判断量价配合情况

#### 6. modules/dimensions/block.py
**功能**: 板块维度
- 分析所属板块表现
- 判断板块强弱

## 技术栈
- Python 3.12
- akshare（数据获取）
- pandas（数据处理）
- numpy（数值计算）
- retrying（重试机制）

## 编码规范
- 遵循 Python PEP 8 规范
- 使用类型注解
- 函数文档包含详细说明

## 报告输出
- 保存位置: `/mnt/nas/stock/`
- 文件格式: Markdown (.md)
- 文件命名: `{股票代码}_{股票名称}_分析报告.md`

## 测试脚本

### 1. test_trend_sys2.py
**用途**: 完整测试 trend.py 模块（使用重试机制）
**输入**: 股票代码（默认 600711）
**功能**: 测试数据获取和 DK 信号计算

### 2. test_akshare_simple.py
**用途**: 简单测试 akshare 数据获取
**功能**: 测试 akshare 接口连接

### 3. test_akshare_connection.py
**用途**: 测试 akshare 基础连接
**功能**: 测试股票基本信息获取

### 4. test_akshare_interfaces.py
**用途**: 测试不同的 akshare 接口
**功能**: 测试多种历史数据接口

### 5. test_trend_mock2.py
**用途**: 使用模拟数据测试 trend.py 模块逻辑
**功能**: 验证模块 2-4 的核心逻辑（已完成测试）

## 测试结果总结

### 已完成测试
- ✅ akshare 基础连接正常（股票基本信息获取）
- ✅ trend.py 模块核心逻辑（模块 2-4）通过模拟数据测试
- ✅ EMA 指标计算正常
- ✅ 金叉/死叉判断正常
- ✅ DK 信号标记正常
- ✅ D 点后涨幅计算正常

### 未完成测试
- ⚠️ 模块 1（数据获取）：akshare 历史数据接口连接不稳定
  - 错误: `Connection aborted: Remote end closed connection without response`
  - 原因: 可能是数据源服务器问题或网络限制
  - 建议: 在网络环境稳定时重新测试

## 运行方式

### 1. 运行主程序
```bash
cd /workspace/projects/stock
python3 main.py
```

### 2. 运行测试脚本
```bash
cd /workspace/projects/stock
python3 test_trend_mock2.py  # 模拟数据测试
python3 test_trend_sys2.py   # 完整模块测试（需要网络连接）
```

## 依赖安装
```bash
pip install -r requirements.txt
```

## 配置修改
所有配置集中在 `config.py` 中：
- 修改股票列表：编辑 `TARGET_STOCKS`
- 修改输出目录：编辑 `OUTPUT_DIR`
- 修改 DK 信号配置：编辑 `DK_SIGNAL_CONFIG`

## 更新日志
详见 `UPDATE_LOG.md`

## 趋势模块更新说明
详见 `TREND_MODULE_UPDATE.md`

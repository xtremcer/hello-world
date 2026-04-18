# Stock 项目目录结构

```
stock/
├── main.py                      # 主程序入口
├── config.py                    # 核心配置文件（股票列表、输出目录等）
├── config_data_sources.py       # 数据源配置（Tushare、聚宽等）
├── config_local_example.py      # 本地配置示例（不提交Git）
├── requirements.txt             # Python依赖列表
├── stock_auto.py               # 单文件备份版本
├── baostock_login_explanation.py # baostock登录说明
├── .gitignore                   # Git忽略配置

├── modules/                     # 功能模块目录
│   ├── stock_analyzer.py       # 股票分析主模块
│   ├── market_brief.py          # 市场简报模块
│   └── dimensions/              # 六大维度分析模块
│       ├── trend.py            # 趋势维度（DK信号）
│       ├── main_chip.py        # 主力筹码维度
│       ├── market_chip.py      # 全市场筹码维度
│       ├── fund_flow.py        # 主力资金维度
│       ├── price_volume.py     # 量价维度
│       └── block.py            # 板块维度

├── utils/                       # 工具函数目录
│   ├── baostock_utils.py       # baostock数据获取工具
│   ├── fetch_utils.py          # 数据获取工具
│   └── helpers.py              # 辅助函数

├── ai/                          # AI相关工具
│   └── analyze_with_ai.py      # AI分析功能

├── assets/                      # 资源文件目录
│   └── *.csv/*.md               # 测试数据

└── *.md                         # 项目文档
    ├── README.md                # 项目说明
    ├── QUICKSTART.md            # 快速开始
    ├── BAOSTOCK_USAGE_GUIDE.md  # baostock使用指南
    └── ...
```

## 核心文件说明

### 主程序
- **main.py**: 程序入口，解析命令行参数，调用分析模块

### 配置文件
- **config.py**: 核心配置
  - `DEFAULT_STOCK`: 默认股票
  - `STOCK_LIST`: 股票列表
  - `OUTPUT_DIR_DEFAULT`: 输出目录（/mnt/nas/data）
  - `DK_SIGNAL_DATA`: DK信号数据
  - `MAIN_CHIP_DATA`: 主力筹码数据

- **config_data_sources.py**: 数据源配置
  - Tushare、聚宽、优矿等数据源配置

### 功能模块
- **trend.py**: 趋势维度（DK信号）
  - EMA5/EMA10 计算
  - D点/K点识别
  - 匹配率100%

- **price_volume.py**: 量价维度
  - 成交量分析
  - 放量突破判断

- **fund_flow.py**: 主力资金维度
  - 资金流向分析
  - 净流入/净流出

- **block.py**: 板块维度
  - 行业资金排名
  - 板块热度分析

- **main_chip.py**: 主力筹码维度
  - 主力成本分析
  - 获利比例计算

- **market_chip.py**: 全市场筹码维度
  - 筹码分布分析
  - 获利比例统计

### 工具函数
- **baostock_utils.py**: baostock数据获取
  - `get_trend_data()`: 获取趋势数据
  - `get_price_volume_data()`: 获取量价数据
  - 前复权设置（adjustflag=2）
  - 频率控制（QPS约20）

- **fetch_utils.py**: 数据获取工具
  - 重试机制
  - 错误处理

- **helpers.py**: 辅助函数
  - `write_run_log()`: 写入运行日志
  - `get_market()`: 获取市场代码

## 使用方法

```bash
# 基本运行
python3 main.py

# 指定股票
python3 main.py --code 600711 --name 盛屯矿业

# 指定日期
python3 main.py --code 600711 --date 2026-04-01 --force

# 指定输出目录
python3 main.py --output /mnt/nas/data
```

## 输出文件

运行后会在 `/mnt/nas/data` 目录生成：
- `YYYY_MM_DD_主升浪策略分析报告.md`
- `YYYY_MM_DD_主升浪策略分析报告.json`

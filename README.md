# 股票自动化分析工具（模块化版）

## 项目说明

这是一个基于Python的股票量化交易策略分析工具，**已完全模块化重构**，支持独立运行和n8n工作流集成。

## 核心功能

- 股票量化分析报告生成
- 休市简报（海外市场数据）
- 支持双格式输出（Markdown + JSON）
- **模块化设计，易于扩展和维护**

## 项目结构

```
/mnt/nas/stock/
├── main.py                    # 主程序入口
├── config.py                  # 配置文件（所有常量和参数）
├── requirements.txt           # 依赖包列表
├── README.md                  # 项目说明（本文件）
├── run_log.txt                # 运行日志
├── utils/                     # 工具模块
│   ├── __init__.py
│   ├── helpers.py            # 通用工具函数（日志、权限、编码器等）
│   └── fetch_utils.py        # 数据获取工具（重试、延迟、智能重试）
├── modules/                   # 核心分析模块
│   ├── __init__.py
│   ├── market_brief.py       # 休市简报模块（全球指数+新闻）
│   ├── stock_analyzer.py     # 股票分析主模块（汇总各维度）
│   └── dimensions/           # 维度分析子模块
│       ├── __init__.py
│       ├── trend.py          # 1. 趋势维度（DK信号）
│       ├── main_chip.py      # 2. 主力筹码维度
│       ├── market_chip.py    # 3. 全市场筹码维度
│       ├── fund_flow.py      # 4. 主力资金维度
│       ├── price_volume.py   # 5. 量价维度
│       └── block.py          # 6. 板块维度
├── ai/                        # AI分析相关（保留兼容）
│   └── analyze_with_ai.py
├── ai_prompt.txt              # AI分析提示词（用于n8n配置）
└── *.md / *.json              # 生成的报告文件（按日期命名）
```

## 快速开始

### 安装依赖

```bash
cd /mnt/nas/stock
pip install -r requirements.txt
```

### 运行主程序

```bash
cd /mnt/nas/stock
python main.py
```

### 强制运行（跳过休市判断）

```bash
python main.py --force
```

### 仅生成JSON（用于n8n集成）

```bash
python main.py --json-only
```

### 指定日期运行

```bash
python main.py --date 2026-04-10
```

### 指定股票代码

```bash
python main.py --code 600711 --name 盛屯矿业
```

## 输出文件

### 交易日报告
- `2026_04_10_主升浪策略分析报告.md` - Markdown格式
- `2026_04_10_主升浪策略分析报告.json` - JSON格式

### 休市简报
- `2026_04_12_休市简报.md` - Markdown格式
- `2026_04_12_休市简报.json` - JSON格式

### 日志文件
- `run_log.txt` - 运行日志

## 模块说明

### 核心模块

1. **config.py** - 配置文件
   - 所有常量和参数配置
   - 包括默认股票、重试策略、DK信号、主力筹码等数据配置
   - 易于修改和维护

2. **main.py** - 主程序入口
   - 参数解析和命令行接口
   - 调用各个分析模块
   - 生成最终报告文件

3. **modules/stock_analyzer.py** - 股票分析主模块
   - 调用6个维度分析模块
   - 汇总分析结果
   - 生成综合判定

### 维度分析模块

4. **modules/dimensions/trend.py** - 趋势维度（DK信号）
   - 分析DK趋势信号
   - 判断买卖机会

5. **modules/dimensions/main_chip.py** - 主力筹码维度
   - 分析主力持仓成本和获利情况

6. **modules/dimensions/market_chip.py** - 全市场筹码维度
   - 分析全市场筹码分布和获利比例

7. **modules/dimensions/fund_flow.py** - 主力资金维度
   - 分析主力资金流入流出情况

8. **modules/dimensions/price_volume.py** - 量价维度
   - 分析股价和成交量的关系

9. **modules/dimensions/block.py** - 板块维度
   - 分析行业板块资金排名和资金流向

10. **modules/market_brief.py** - 休市简报模块
    - 获取全球指数数据
    - 获取海外金融新闻
    - 生成休市简报

### 工具模块

11. **utils/helpers.py** - 通用工具函数
    - JSON编码器
    - 日志写入
    - 目录权限检查
    - 交易所判断

12. **utils/fetch_utils.py** - 数据获取工具
    - 带重试机制的数据获取
    - 智能重试和延迟
    - DK信号、筹码分布等接口封装

## 如何扩展和修改

### 添加新股票

编辑 `config.py` 文件中的 `STOCK_LIST`：

```python
STOCK_LIST = [
    {
        "code": "600711",
        "name": "盛屯矿业",
        "main_type": "短线游资",
        "industry": "能源金属"
    },
    {
        "code": "002240",
        "name": "威华股份",
        "main_type": "短线游资",
        "industry": "能源金属"
    }
]
```

### 配置缺失数据

编辑 `config.py` 文件：

```python
# 配置DK趋势信号
DK_SIGNAL_DATA = {
    "600711": "D点（机会信号）",  # 或 "K点（风险信号）"
    "002240": "D点（机会信号）"
}

# 配置主力筹码数据
MAIN_CHIP_DATA = {
    "600711": {
        "main_cost": 13.90,        # 主力平均成本
        "main_profit_ratio": 2.09,  # 主力获利比例（%）
        "main_chip_shape": "低位单峰密集"
    }
}
```

### 修改重试策略

编辑 `config.py` 文件：

```python
MAX_RETRIES = 3              # 最大重试次数
RETRY_DELAY = 2              # 重试延迟（秒）
REQUEST_DELAY_NORMAL = 1.0   # 正常请求延迟
REQUEST_DELAY_RETRY = 3.0    # 重试请求延迟
```

### 添加新维度分析

1. 在 `modules/dimensions/` 下创建新模块文件（如 `custom_dimension.py`）
2. 定义分析函数，格式为：

```python
def analyze_custom_dimension(stock_code: str, main_type: str = "短线游资") -> Tuple[str, Dict]:
    """
    分析自定义维度
    参数：
        stock_code: 股票代码
        main_type: 主力类型
    返回：(MD内容, JSON数据)
    """
    # 实现分析逻辑
    md_content = "#### 自定义维度\n"
    json_data = {}

    # 返回结果
    return md_content, json_data
```

3. 在 `modules/stock_analyzer.py` 中调用新模块：

```python
from modules.dimensions.custom_dimension import analyze_custom_dimension

# 在 get_stock_data 函数中添加
custom_md, custom_json = analyze_custom_dimension(stock_code, main_type)
stock_md_content += custom_md
json_data["analysis"]["custom"] = custom_json
```

## 配置定时任务

### crontab配置

```bash
# 每个交易日15:30运行
30 15 * * 1-5 cd /mnt/nas/stock && python main.py >> run_log.txt 2>&1

# 每天运行（自动判断是否为交易日）
30 15 * * * cd /mnt/nas/stock && python main.py >> run_log.txt 2>&1
```

### systemd配置（可选）

创建服务文件：`/etc/systemd/system/stock-auto.service`

```ini
[Unit]
Description=Stock Auto Analysis Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/mnt/nas/stock
ExecStart=/usr/bin/python3 /mnt/nas/stock/main.py
StandardOutput=append:/mnt/nas/stock/run_log.txt
StandardError=append:/mnt/nas/stock/run_log.txt

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable stock-auto
sudo systemctl start stock-auto
```

## 数据来源说明

- **akshare免费接口**: K线数据、主力资金数据、行业资金流数据
- **需手动配置**: DK趋势信号、主力筹码数据（akshare无免费接口）
- **暂无法获取**: 全市场筹码分布数据

## 买入信号（必须同时满足6项）

1. 趋势维度：DK信号出现D点（机会信号）⚠️ 需手动配置
2. 主力筹码：主力获利＜10% + 低位单峰密集 ⚠️ 需手动配置
3. 全市场筹码：全市场获利20%-60% + 单峰密集 ⚠️ 暂无法获取
4. 主力资金：连续3日净流入 + 占成交额＞5%
5. 量价维度：放量1.5倍以上 + 突破10日均线
6. 板块维度：所属行业资金排名前10

## 卖出信号（满足任意2项及以上）

1. 趋势维度：DK信号出现K点（风险信号）
2. 主力筹码：主力获利＞30%（游资）/50%（机构） + 高位发散
3. 全市场筹码：全市场获利＞70% + 高位发散
4. 主力资金：连续2日净流出 + 大额出逃
5. 量价维度：放量滞涨（成交量放大但股价不涨）
6. 板块维度：板块资金排名跌出前10 + 资金大幅流出

## 注意事项

1. **模块化优势**：每个维度独立分析，可单独修改或替换
2. **配置集中**：所有配置集中在 `config.py`，易于管理
3. **扩展性强**：新增维度只需添加模块文件并注册调用
4. **兼容性**：保留原有输出格式和命名规则，与旧版本完全兼容
5. **错误处理**：每个模块独立处理错误，不会影响其他模块运行

## 版本历史

### v2.0.0（模块化版）
- 完全重构为模块化架构
- 每个维度独立为模块文件
- 配置文件集中管理
- 提高可维护性和扩展性
- 保持原有功能兼容

### v1.0.0（原版）
- 单文件架构
- 基础分析功能

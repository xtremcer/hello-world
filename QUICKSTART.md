# 股票分析模块化项目 - 快速开始

## 📁 项目位置

所有文件已复制到：`/workspace/projects/stock/`

## 🚀 使用方法

### 1. 进入项目目录

```bash
cd /workspace/projects/stock
```

### 2. 查看项目结构

```bash
tree -L 3
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 运行程序

```bash
# 默认运行（自动判断交易日）
python main.py

# 强制运行（跳过休市判断）
python main.py --force

# 仅生成JSON格式
python main.py --json-only

# 指定日期运行
python main.py --date 2026-04-10

# 指定股票代码
python main.py --code 600711 --name 盛屯矿业
```

## 📊 项目结构

```
/workspace/projects/stock/
├── main.py                    # ⭐ 主程序入口（新）
├── config.py                  # ⭐ 配置文件
├── requirements.txt           # ⭐ 依赖包
├── README.md                  # 📖 详细文档
│
├── modules/                   # 🧩 核心分析模块
│   ├── market_brief.py       # 休市简报
│   ├── stock_analyzer.py     # 股票分析主模块
│   └── dimensions/           # 6个维度分析
│       ├── trend.py          # 1. 趋势维度
│       ├── main_chip.py      # 2. 主力筹码
│       ├── market_chip.py    # 3. 全市场筹码
│       ├── fund_flow.py      # 4. 主力资金
│       ├── price_volume.py   # 5. 量价
│       └── block.py          # 6. 板块
│
├── utils/                     # 🛠️ 工具模块
│   ├── helpers.py            # 日志、权限、编码器
│   └── fetch_utils.py        # 数据获取工具
│
├── ai/                        # 🤖 AI分析模块（保留）
│   └── analyze_with_ai.py
├── ai_prompt.txt              # AI提示词
├── run_log.txt                # 运行日志
└── stock_auto.py              # 原版备份（保留兼容）
```

## ✨ 模块化优势

1. **易于维护**：每个维度独立为模块文件
2. **配置集中**：所有配置在 config.py
3. **扩展性强**：新增维度只需添加模块
4. **代码清晰**：职责分明，便于理解

## 📝 配置说明

### 添加新股票

编辑 `config.py` 文件：

```python
STOCK_LIST = [
    {
        "code": "600711",
        "name": "盛屯矿业",
        "main_type": "短线游资",
        "industry": "能源金属"
    },
    # 添加更多股票...
]
```

### 配置DK信号

编辑 `config.py` 文件：

```python
DK_SIGNAL_DATA = {
    "600711": "D点（机会信号）",  # 或 "K点（风险信号）"
    "002240": "D点（机会信号）"
}
```

### 配置主力筹码

编辑 `config.py` 文件：

```python
MAIN_CHIP_DATA = {
    "600711": {
        "main_cost": 13.90,        # 主力平均成本
        "main_profit_ratio": 2.09,  # 主力获利比例（%）
        "main_chip_shape": "低位单峰密集"
    }
}
```

## 📦 输出文件

- 交易日报告：`2026_04_10_主升浪策略分析报告.md/json`
- 休市简报：`2026_04_12_休市简报.md/json`
- 运行日志：`run_log.txt`

## 🔧 修改重试策略

编辑 `config.py` 文件：

```python
MAX_RETRIES = 3              # 最大重试次数
RETRY_DELAY = 2              # 重试延迟（秒）
REQUEST_DELAY_NORMAL = 1.0   # 正常请求延迟
REQUEST_DELAY_RETRY = 3.0    # 重试请求延迟
```

## 📖 详细文档

查看完整文档：`README.md`

## ⚠️ 注意事项

1. 首次运行前必须安装依赖：`pip install -r requirements.txt`
2. 新的主程序是 `main.py`，不再使用 `stock_auto.py`
3. 所有配置都在 `config.py` 文件中
4. 保持原有输出格式和命名规则，完全兼容

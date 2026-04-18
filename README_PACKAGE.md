# Stock 模块化项目 - 打包说明

## 📦 打包信息

- **文件名**: `stock_modularized.tar.gz`
- **大小**: 86 KB
- **文件数**: 83 个
- **打包时间**: 2026-04-12

## 🚀 快速开始

### 1. 解压文件
```bash
tar -xzvf stock_modularized.tar.gz
cd stock
```

### 2. 安装依赖
```bash
# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 或使用 uv（如果已安装）
uv pip install -r requirements.txt
```

### 3. 运行程序
```bash
# 使用默认配置运行
python3 main.py

# 指定股票代码和名称
python3 main.py --code 600711 --name 盛屯矿业

# 指定输出目录
python3 main.py --output /mnt/nas/stock

# 强制运行（忽略休市判断）
python3 main.py --force
```

## 📁 项目结构

```
stock/
├── main.py                    # 主程序
├── config.py                  # 配置文件
├── config_data_sources.py     # 数据源配置
├── requirements.txt           # 依赖列表
├── modules/                   # 模块目录
│   ├── dimensions/           # 维度分析模块
│   │   ├── trend.py          # 趋势维度（DK信号）
│   │   ├── price_volume.py   # 量价维度
│   │   ├── fund_flow.py      # 主力资金维度
│   │   ├── block.py          # 板块维度
│   │   ├── main_chip.py      # 主力筹码维度
│   │   └── market_chip.py    # 全市场筹码维度
│   ├── market_brief.py       # 市场简报
│   └── stock_analyzer.py     # 股票分析器
├── utils/                     # 工具目录
│   ├── baostock_utils.py     # baostock 数据获取工具
│   ├── fetch_utils.py        # 数据获取工具
│   └── helpers.py            # 辅助函数
├── assets/                    # 资源目录
│   └── *.csv                 # 测试数据
├── test_*.py                  # 测试脚本
└── *.py                       # 其他脚本
```

## 🎯 核心功能

### 1. 趋势维度（DK信号）
- **D 点（买入信号）**: 金叉（EMA5 > EMA10）+ 价格突破 EMA10
- **K 点（卖出信号）**: 从 5 日高点回落 > 3%
- **匹配率**: 100%（已验证）
- **数据源**: baostock（前复权，adjustflag=2）

### 2. 数据源
- **baostock**: 趋势维度、量价维度（推荐，稳定，免费）
- **akshare**: 主力资金、板块数据（备用）

### 3. 六大维度分析
1. 趋势维度（DK信号）
2. 主力筹码维度
3. 全市场筹码维度
4. 主力资金维度
5. 量价维度
6. 板块维度

## 🔧 配置说明

### 修改股票列表
编辑 `config.py` 文件：
```python
DEFAULT_STOCK = {
    "code": "600711",
    "name": "盛屯矿业",
    "main_type": "短线游资",
    "industry": "能源金属"
}

STOCK_LIST = [DEFAULT_STOCK.copy()]
```

### 修改输出目录
编辑 `config.py` 文件：
```python
OUTPUT_DIR_DEFAULT = "/mnt/nas/stock"  # 修改为你想要的路径
```

### 配置数据源
编辑 `config_data_sources.py` 文件（如果需要使用 Tushare 等付费数据源）：
```python
TUSHARE_CONFIG = {
    "enabled": True,
    "token": "你的token",
}
```

## 📊 输出格式

程序会生成两种格式的报告：
- **JSON 格式**: 结构化数据，方便程序读取
- **MD 格式**: Markdown 格式，方便阅读

## 🧪 测试脚本

项目包含多个测试脚本，用于验证功能：

- `test_baostock_simple.py`: 测试 baostock 连接
- `test_dk_direct.py`: 测试 DK 信号计算
- `verify_trend_logic.py`: 验证趋势逻辑
- `test_baostock_login.py`: 测试登录机制

运行测试：
```bash
python3 test_baostock_simple.py
python3 test_dk_direct.py
python3 verify_trend_logic.py
```

## ⚠️ 注意事项

1. **baostock 是免费的**：不需要账号密码，直接使用即可
2. **频率限制**：baostock QPS 约 20，已内置频率控制
3. **前复权**：使用前复权数据（adjustflag=2），确保数据连续性
4. **EMA 参数**：使用 EMA5/EMA10（匹配手机软件）
5. **网络环境**：确保网络连接正常，能访问 baostock 服务器

## 📚 依赖包

主要依赖包：
- baostock>=0.8.9
- akshare>=1.18.54
- pandas>=1.5.0
- numpy>=1.23.0
- retrying>=1.4.2

## 🆘 常见问题

### Q1: 如何修改 DK 信号判断逻辑？
A: 编辑 `modules/dimensions/trend.py` 文件，修改 `module3_mark_dk_signals` 函数。

### Q2: 如何添加新的股票？
A: 编辑 `config.py` 文件，在 `STOCK_LIST` 中添加新的股票字典。

### Q3: 如何修改输出目录？
A: 编辑 `config.py` 文件，修改 `OUTPUT_DIR_DEFAULT` 变量。

### Q4: baostock 需要账号吗？
A: 不需要！baostock 是免费的公共接口，直接使用 `bs.login()` 即可。

### Q5: 如何使用 Tushare？
A: 编辑 `config_data_sources.py` 文件，配置你的 Tushare token。

## 📞 支持

如果遇到问题，请检查：
1. 网络连接是否正常
2. 依赖包是否正确安装
3. 配置文件是否正确
4. 测试脚本是否能正常运行

## 🎉 开始使用

解压后，运行以下命令开始使用：
```bash
cd stock
pip install -r requirements.txt
python3 main.py --code 600711 --name 盛屯矿业 --force
```

祝使用愉快！

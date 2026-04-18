# 📁 报告文件保存位置说明

## ✅ 已修改配置

现在报告文件会**固定保存在 `/mnt/nas/stock/` 目录**。

## 📍 报告保存位置

### 主目录
```
/mnt/nas/stock/
```

### 具体文件

#### 交易日报告
```
/mnt/nas/stock/2026_04_12_主升浪策略分析报告.md
/mnt/nas/stock/2026_04_12_主升浪策略分析报告.json
```

#### 休市简报
```
/mnt/nas/stock/2026_04_12_休市简报.md
/mnt/nas/stock/2026_04_12_休市简报.json
```

#### 运行日志
```
/mnt/nas/stock/run_log.txt
```

## 🚀 使用方法

### 方法1：在任何目录运行（推荐）

```bash
# 在任何目录运行，报告都会保存到 /mnt/nas/stock/
~/stock/venv/bin/python /mnt/nas/stock/main.py
```

### 方法2：进入目录运行

```bash
# 先进入目录
cd /mnt/nas/stock

# 运行程序
~/stock/venv/bin/python main.py

# 报告同样保存到当前目录 /mnt/nas/stock/
```

### 方法3：指定其他输出目录

```bash
# 报告保存到 /tmp 目录
~/stock/venv/bin/python /mnt/nas/stock/main.py --output /tmp
```

## 📊 文件命名规则

### 报告文件命名

- **格式**: `YYYY_MM_DD_报告名称.扩展名`
- **示例**: `2026_04_12_主升浪策略分析报告.md`

### 日志文件

- **文件名**: `run_log.txt`
- **位置**: `/mnt/nas/stock/run_log.txt`
- **内容**: 每次运行的日志记录

## 🔍 查看报告

### 查看最新的报告

```bash
# 进入目录
cd /mnt/nas/stock

# 查看最新的 Markdown 报告
ls -lt *.md | head -5

# 查看最新的 JSON 报告
ls -lt *.json | head -5

# 查看运行日志
cat run_log.txt

# 或查看最近的日志行
tail -20 run_log.txt
```

### 查看特定日期的报告

```bash
# 查看今天的报告
cat 2026_04_12_主升浪策略分析报告.md

# 查看指定日期的报告
cat 2026_04_10_主升浪策略分析报告.md
```

## 📋 目录结构

```
/mnt/nas/stock/
├── main.py                              # 主程序
├── config.py                            # 配置文件
├── requirements.txt                     # 依赖包
│
├── modules/                             # 模块目录
│   ├── market_brief.py
│   ├── stock_analyzer.py
│   └── dimensions/
│
├── utils/                               # 工具目录
│   ├── helpers.py
│   └── fetch_utils.py
│
├── ai/                                  # AI模块（保留）
│   └── analyze_with_ai.py
│
├── 2026_04_12_主升浪策略分析报告.md     # ⭐ 最新报告
├── 2026_04_12_主升浪策略分析报告.json  # ⭐ 最新报告
├── 2026_04_11_主升浪策略分析报告.md     # 历史报告
├── 2026_04_11_主升浪策略分析报告.json  # 历史报告
├── run_log.txt                          # 运行日志
│
└── stock_auto.py                        # 原版备份
```

## 🎯 配置说明

### 当前配置（已修改）

```python
# config.py
OUTPUT_DIR_DEFAULT = "/mnt/nas/stock"
```

### 如果需要修改输出目录

编辑 `/mnt/nas/stock/config.py` 文件：

```python
# 修改为你想要的目录
OUTPUT_DIR_DEFAULT = "/your/custom/path"
```

## 📝 定时任务中的路径

### Crontab 配置

```bash
# 报告会自动保存到 /mnt/nas/stock/
30 15 * * 1-5 ~/stock/venv/bin/python /mnt/nas/stock/main.py >> /mnt/nas/stock/run_log.txt 2>&1
```

### Systemd 配置

```ini
[Service]
WorkingDirectory=/mnt/nas/stock
ExecStart=/root/stock/venv/bin/python /mnt/nas/stock/main.py
StandardOutput=append:/mnt/nas/stock/run_log.txt
StandardError=append:/mnt/nas/stock/run_log.txt
```

## ✅ 总结

1. **报告位置**: `/mnt/nas/stock/`
2. **文件命名**: `YYYY_MM_DD_报告名称.扩展名`
3. **查看方法**: `cat /mnt/nas/stock/2026_04_12_主升浪策略分析报告.md`
4. **运行日志**: `/mnt/nas/stock/run_log.txt`
5. **历史报告**: 所有报告都保存在同一目录，方便管理

**无论你在哪个目录运行程序，报告都会固定保存到 `/mnt/nas/stock/` 目录！** 🎉

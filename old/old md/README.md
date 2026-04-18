# 股票自动化分析工具

## 项目说明

这是一个基于Python的股票量化交易策略分析工具，支持独立运行和n8n工作流集成。

## 核心功能

- 股票量化分析报告生成
- 休市简报（海外市场数据）
- 支持双格式输出（Markdown + JSON）

## 文件结构

```
/mnt/nas/stock/
├── stock_auto.py          # 主程序
├── ai_prompt.txt          # AI分析提示词（用于n8n配置）
├── ai/                    # AI分析相关
│   └── analyze_with_ai.py # AI分析脚本
├── README.md              # 项目说明（本文件）
├── run_log.txt            # 运行日志
└── *.md / *.json          # 生成的报告文件（按日期命名）
```

## 快速开始

### 运行主程序

```bash
cd /mnt/nas/stock
python stock_auto.py
```

### 强制运行（跳过休市判断）

```bash
python stock_auto.py --force
```

### 仅生成JSON（用于n8n集成）

```bash
python stock_auto.py --json-only
```

### 指定日期运行

```bash
python stock_auto.py --date 2026-04-10
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

## 配置定时任务

### crontab配置

```bash
# 每个交易日15:30运行
30 15 * * 1-5 cd /mnt/nas/stock && python stock_auto.py >> run_log.txt 2>&1

# 每天运行（自动判断是否为交易日）
30 15 * * * cd /mnt/nas/stock && python stock_auto.py >> run_log.txt 2>&1
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
ExecStart=/usr/bin/python3 /mnt/nas/stock/stock_auto.py
StandardOutput=append:/mnt/nas/stock/run_log.txt
StandardError=append:/mnt/nas/stock/run_log.txt

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
systemctl daemon-reload
systemctl enable stock-auto.service
systemctl start stock-auto.service
```

## AI分析（可选）

AI分析脚本位于 `ai/analyze_with_ai.py`，使用方法：

```bash
cd /mnt/nas/stock/ai
python analyze_with_ai.py
```

### n8n集成

AI提示词位于根目录的 `ai_prompt.txt`，可直接复制到n8n的AI Agent节点配置中。

## 数据来源

- A股数据：akshare
- 全球指数：akshare
- 新闻联播：akshare

## 注意事项

1. **网络依赖**：需要联网获取数据
2. **运行时间**：建议在A股收盘后（15:30-16:00）运行
3. **文件命名**：所有报告使用下划线格式（如：2026_04_12）
4. **日志管理**：日志会自动追加到 `run_log.txt`

## 技术栈

- Python 3.12
- akshare（数据源）
- argparse（命令行参数）

## 支持

如有问题，请检查 `run_log.txt` 日志文件。

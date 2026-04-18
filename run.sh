#!/bin/bash
# 快捷运行脚本 - 股票主升浪策略分析工具

# 项目目录
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# 激活虚拟环境
cd "$PROJECT_DIR"
source venv/bin/activate

# 运行主程序
python main.py "$@"

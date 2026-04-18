# ===================== 敏感配置文件（本地配置，不提交到 Git） =====================

# ⚠️ 重要：此文件包含敏感信息，请勿提交到 Git！
# 将此文件添加到 .gitignore

import os

# ===================== Tushare 配置 =====================
TUSHARE_CONFIG = {
    "enabled": os.getenv("TUSHARE_ENABLED", "false").lower() == "true",
    "token": os.getenv("TUSHARE_TOKEN", ""),  # 从环境变量读取
}

# ===================== 聚宽 JoinQuant 配置 =====================
JOINQUANT_CONFIG = {
    "enabled": os.getenv("JOINQUANT_ENABLED", "false").lower() == "true",
    "username": os.getenv("JOINQUANT_USERNAME", ""),  # 从环境变量读取
    "password": os.getenv("JOINQUANT_PASSWORD", ""),  # 从环境变量读取
}

# ===================== 优矿 Uqer 配置 =====================
UQER_CONFIG = {
    "enabled": os.getenv("UQER_ENABLED", "false").lower() == "true",
    "username": os.getenv("UQER_USERNAME", ""),  # 从环境变量读取
    "password": os.getenv("UQER_PASSWORD", ""),  # 从环境变量读取
}

# ===================== Baostock 配置（免费，无需账号） =====================
BAOSTOCK_CONFIG = {
    "enabled": True,  # baostock 默认启用
    "qps_limit": 20,  # QPS 限制
    "adjustflag": "2",  # 前复权
}

# ===================== 使用说明 =====================
# 1. 设置环境变量（推荐方式）：
#    export TUSHARE_TOKEN="你的token"
#    export JOINQUANT_USERNAME="你的账号"
#    export JOINQUANT_PASSWORD="你的密码"
#
# 2. 或者直接在此文件中配置（不推荐，不安全）
#
# 3. 在代码中导入使用：
#    from config_local import TUSHARE_CONFIG
#    token = TUSHARE_CONFIG["token"]

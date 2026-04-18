# ===================== 数据源配置（账号相关） =====================

# ===================== Tushare 配置 =====================
# Tushare 是专业的财经数据接口，支持免费和付费版本
# 免费版本：每分钟 200 次查询
# 付费版本：更高频率，更多数据

# 如果你有 Tushare 账号，请在这里配置你的 token
TUSHARE_CONFIG = {
    "enabled": False,  # 是否启用 Tushare
    "token": "",  # 你的 Tushare token（请勿泄露）
    # 获取方式：https://tushare.pro/register
}

# ===================== 聚宽 JoinQuant 配置 =====================
# 聚宽是量化交易平台，需要账号密码
# 免费账号：有限制的 API 调用

JOINQUANT_CONFIG = {
    "enabled": False,  # 是否启用聚宽
    "username": "",  # 你的聚宽账号
    "password": "",  # 你的聚宽密码（请勿泄露）
}

# ===================== 优矿 Uqer 配置 =====================
# 优矿是量化交易平台，需要账号密码

UQER_CONFIG = {
    "enabled": False,  # 是否启用优矿
    "username": "",  # 你的优矿账号
    "password": "",  # 你的优矿密码（请勿泄露）
}

# ===================== 数据源优先级 =====================
# 当前项目使用的数据源优先级：
# 1. 趋势维度：baostock（免费，稳定）
# 2. 量价维度：baostock（免费，稳定）
# 3. 主力资金：akshare（免费，备用）
# 4. 板块数据：akshare（免费，备用）

# 如果启用了其他数据源，可以在这里调整优先级
DATA_SOURCE_PRIORITY = {
    "trend": ["baostock", "tushare", "akshare"],  # 趋势维度优先级
    "price_volume": ["baostock", "tushare", "akshare"],  # 量价维度优先级
    "fund_flow": ["akshare", "tushare"],  # 主力资金优先级
    "block": ["akshare", "tushare"],  # 板块数据优先级
}

# ===================== 安全提示 =====================
# ⚠️ 重要：不要将账号密码提交到 Git 仓库！
# 建议：
# 1. 将此文件添加到 .gitignore
# 2. 使用环境变量存储敏感信息
# 3. 使用单独的配置文件（如 config_local.py），不提交到 Git

# 环境变量示例：
# export TUSHARE_TOKEN="你的token"
# export JOINQUANT_USERNAME="你的账号"
# export JOINQUANT_PASSWORD="你的密码"

# 在代码中读取环境变量：
# import os
# token = os.getenv("TUSHARE_TOKEN", "")

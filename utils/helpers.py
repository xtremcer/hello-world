"""
通用工具函数
包含日志、权限检查、编码器等工具函数
"""

import json
import datetime
import os
from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np


class NumpyJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理numpy和pandas的特殊类型"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif pd.isna(obj):
            return None
        return super().default(obj)


def write_run_log(log_path, content, is_success=True):
    """封装日志写入函数"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_prefix = "[SUCCESS]" if is_success else "[ERROR]"
    log_content = f"{current_time} {log_prefix} - {content}\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_content)
        print(f"✅ 日志已追加：{log_content.strip()}")
    except Exception as e:
        print(f"❌ 日志写入失败：{str(e)}")


def check_directory_permission(dir_path):
    """检查目录写入权限"""
    if os.access(dir_path, os.W_OK):
        return True
    print(f"⚠️ 目录{dir_path}无写入权限，尝试自动提权...")
    try:
        os.chmod(dir_path, 0o775)
        return os.access(dir_path, os.W_OK)
    except Exception as e:
        print(f"❌ 提权失败：{str(e)}，请手动执行 chmod 775 {dir_path}")
        return False


def get_market(code):
    """根据股票代码自动判断交易所"""
    if code.startswith('60') or code.startswith('68'):
        return 'sh'
    elif code.startswith('00') or code.startswith('30'):
        return 'sz'
    else:
        return 'sh'

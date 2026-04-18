"""
休市日简报模块
获取全球指数和海外金融新闻，生成休市简报
"""

import datetime
from typing import Dict, Optional, Tuple
import akshare as ak

from utils.fetch_utils import fetch_with_retry


def is_trading_day(date: datetime.date = None) -> Tuple[bool, str]:
    """
    判断是否为交易日
    方法：
    1. 首先通过周末判断，如果是周末直接判定为休市
    2. 工作日通过数据验证（获取最新数据看日期是否匹配）来判断
    返回：(是否交易日, 原因说明)
    """
    if date is None:
        date = datetime.date.today()

    target_date_str = date.strftime("%Y-%m-%d")

    # 方法0：首先判断是否是周末，周末直接判定为休市
    weekday = date.weekday()
    if weekday >= 5:  # 5=周六, 6=周日
        return False, f"休市（周末：星期{weekday+1}）"

    # 方法1：尝试通过 baostock 获取数据验证最新日期
    # 说明：baostock v0.9.1 没有 query_trade_date 接口，所以改用数据验证
    try:
        print(f"  💡 {target_date_str} 是工作日，正在通过数据验证是否为交易日...")
        import baostock as bs
        from utils.baostock_utils import get_trend_data

        # 用上证指数验证（上证指数代码 000001）
        df, error = get_trend_data("000001", "sh")

        if df is not None and not df.empty:
            latest_date = df.iloc[-1]['date']
            # latest_date 是 datetime 对象
            if hasattr(latest_date, 'date'):
                latest_date = latest_date.date()
            else:
                latest_date = datetime.date.fromisoformat(str(latest_date).split()[0])

            if latest_date == date:
                return True, f"交易日（baostock最新数据日期匹配：{latest_date}）"
            else:
                return False, f"休市（数据未更新：最新日期{latest_date} ≠ 目标日期{target_date}）"
        else:
            raise Exception(f"baostock获取数据失败：{error}")

    except Exception as e:
        print(f"  ⚠️ baostock数据验证失败：{str(e)}，尝试使用备用方法...")

    # 备用方法1：使用akshare交易日历接口
    try:
        print(f"  💡 使用备用方法：获取akshare交易日历...")
        import akshare as ak
        import pandas as pd

        # 获取上海证券交易所交易日历
        trade_date_df = ak.tool_trade_date_hist_sina()

        if trade_date_df is not None and not trade_date_df.empty:
            # 将日期列转换为date对象
            if 'trade_date' in trade_date_df.columns:
                trade_date_df['trade_date'] = pd.to_datetime(trade_date_df['trade_date']).dt.date
                trading_dates = set(trade_date_df['trade_date'].tolist())
            elif 'date' in trade_date_df.columns:
                trade_date_df['date'] = pd.to_datetime(trade_date_df['date']).dt.date
                trading_dates = set(trade_date_df['date'].tolist())
            else:
                # 使用第一列作为日期列
                first_col = trade_date_df.columns[0]
                trade_date_df[first_col] = pd.to_datetime(trade_date_df[first_col]).dt.date
                trading_dates = set(trade_date_df[first_col].tolist())

            # 检查目标日期是否在交易日历中
            if date in trading_dates:
                return True, f"交易日（akshare交易日历包含该日期）"
            else:
                return False, f"休市（akshare交易日历不包含该日期：{target_date_str}）"
        else:
            raise Exception("交易日历数据为空")
    except Exception as e:
        print(f"  ⚠️ 备用方法也失败：{str(e)}，使用默认判断")

    # 所有方法都失败，工作日默认判断为交易日
    print(f"  ⚠️ 无法验证，按工作日默认判定为交易日")
    return True, f"交易日（工作日，默认判断）"


def get_global_indices() -> Optional[Dict]:
    """
    获取全球主要指数数据
    使用单独接口获取：
    - 美股三大指数：道琼斯、纳斯达克、标普500 -> stock_us_daily
    - 港股恒生指数 -> stock_hk_daily
    返回：包含美股、港股等指数的字典
    """
    try:
        print("  正在获取全球指数数据...")

        indices = {}

        # 美股三大指数
        # 使用 stock_us_daily 分别获取
        us_config = [
            {"name": "道琼斯工业指数", "symbol": ".DJI"},
            {"name": "纳斯达克综合指数", "symbol": ".IXIC"},
            {"name": "标普500指数", "symbol": ".INX"},
        ]

        for config in us_config:
            try:
                df = ak.stock_us_daily(symbol=config["symbol"])
                if df is not None and not df.empty and len(df) >= 2:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2]
                    change = latest['close'] - prev['close']
                    change_pct = change / prev['close'] * 100
                    indices[config["name"]] = {
                        "name": config["name"],
                        "code": config["symbol"],
                        "price": float(latest['close']),
                        "change": round(float(change_pct), 2),
                        "volume": int(latest['volume']),
                    }
            except Exception as e:
                print(f"    ⚠️ 获取 {config['name']} 失败：{str(e)}")
                continue

        # 港股恒生指数
        try:
            df = ak.stock_hk_daily(symbol="HSI")
            if df is not None and not df.empty and len(df) >= 2:
                latest = df.iloc[-1]
                prev = df.iloc[-2]
                change = latest['close'] - prev['close']
                change_pct = change / prev['close'] * 100
                indices["恒生指数"] = {
                    "name": "恒生指数",
                    "code": "HSI",
                    "price": float(latest['close']),
                    "change": round(float(change_pct), 2),
                    "volume": float(latest['volume']),
                }
        except Exception as e:
            print(f"    ⚠️ 获取恒生指数失败：{str(e)}")

        return indices if indices else None

    except Exception as e:
        print(f"  ⚠️ 获取全球指数数据失败：{str(e)}")
        return None


def get_global_financial_news() -> Optional[str]:
    """
    获取海外金融新闻
    使用 ak.futures_news_shmet 获取最新财经新闻
    返回：新闻内容字符串
    """
    try:
        print("  正在获取海外金融新闻...")

        # 获取最新财经新闻（上海金属网）
        news_df = ak.futures_news_shmet()

        if news_df is None or news_df.empty:
            return None

        # 拼接新闻内容（取前10条最新）
        news_content = ""
        count = 0
        max_news = 10

        # 按发布时间倒序，最新的在前
        if '发布时间' in news_df.columns and '内容' in news_df.columns:
            # 已经是按时间排序，取前10条
            for idx, row in news_df.head(max_news).iterrows():
                publish_time = row['发布时间']
                content = row['内容']
                # 截断过长内容
                if len(content) > 100:
                    content = content[:97] + "..."
                news_content += f"- **{content}**\n  发布时间: {publish_time}\n\n"
                count += 1

        return news_content if news_content else None

    except Exception as e:
        print(f"  ⚠️ 获取海外金融新闻失败：{str(e)}")
        return None


def generate_market_brief(target_date: datetime.date, reason: str) -> Tuple[str, Dict]:
    """
    生成休市简报内容（不包含主标题）
    返回：(MD内容, JSON数据)
    """
    print(f"\n📰 生成休市简报内容：{target_date}")

    # 1. 获取全球指数数据
    global_indices = get_global_indices()

    # 2. 获取海外金融新闻
    financial_news = get_global_financial_news()

    # 3. 生成MD内容（不包含主标题）
    date_str = target_date.strftime("%Y-%m-%d")
    md_content = f"""## 📅 休市信息

**日期**: {date_str}

**A股状态**: 休市

**原因说明**: {reason}

> 💡 虽然A股休市，但海外市场仍在交易，以下是全球市场概览：

---

## 🌍 海外市场概览

"""

    # 添加全球指数内容
    if global_indices:
        md_content += "### 全球主要指数\n\n"

        # 美股
        us_indices = [k for k in global_indices.keys() if "纳斯达克" in k or "道琼斯" in k or "标普" in k]
        if us_indices:
            md_content += "#### 🇺🇸 美股市场\n\n"
            for idx_name in us_indices:
                idx_data = global_indices[idx_name]
                change_val = float(idx_data['change']) if idx_data['change'] else 0
                change_sign = "📈" if change_val > 0 else "📉" if change_val < 0 else "➡️"

                md_content += f"- **{idx_name}**\n"
                md_content += f"  - 最新价: {idx_data['price']:.2f}\n"
                md_content += f"  - 涨跌幅: {idx_data['change']}% {change_sign}\n"
                md_content += f"  - 成交量: {idx_data['volume']:,}\n\n"

        # 港股
        if "恒生指数" in global_indices:
            idx_data = global_indices["恒生指数"]
            change_val = float(idx_data['change']) if idx_data['change'] else 0
            change_sign = "📈" if change_val > 0 else "📉" if change_val < 0 else "➡️"

            md_content += "#### 🇭🇰 港股市场\n\n"
            md_content += f"- **{idx_data['name']}**\n"
            md_content += f"  - 最新价: {idx_data['price']:.2f}\n"
            md_content += f"  - 涨跌幅: {idx_data['change']}% {change_sign}\n"
            md_content += f"  - 成交量: {idx_data['volume']:.0f}\n\n"

        # 市场分析
        md_content += "### 📊 市场分析\n\n"
        md_content += "**简要评述**：\n"

        # 分析整体走势
        changes = []
        for idx_name, idx_data in global_indices.items():
            if idx_data['change'] is not None:
                try:
                    changes.append(float(idx_data['change']))
                except (ValueError, TypeError):
                    pass

        if changes:
            avg_change = sum(changes) / len(changes)
            if avg_change > 1:
                md_content += f"- 海外市场整体表现强劲，平均涨跌幅为 **{avg_change:.2f}%**，市场情绪积极\n"
            elif avg_change > 0:
                md_content += f"- 海外市场整体温和上涨，平均涨跌幅为 **{avg_change:.2f}%**\n"
            elif avg_change > -1:
                md_content += f"- 海外市场整体小幅回调，平均涨跌幅为 **{avg_change:.2f}%**\n"
            else:
                md_content += f"- 海外市场整体承压，平均涨跌幅为 **{avg_change:.2f}%**，市场情绪谨慎\n"

        md_content += "\n**风险提示**：\n"
        md_content += "- 海外市场波动可能对A股开盘产生影响，请关注相关板块\n"
        md_content += "- 建议关注美股中概股表现，作为A股相关板块的风向标\n"
        md_content += "- 注意汇率波动和宏观政策变化\n\n"
    else:
        md_content += "⚠️ 暂时无法获取全球指数数据，可能是网络问题或数据源维护中。\n\n"

    # 添加新闻内容
    md_content += "---\n\n"
    md_content += "## 📰 最新财经新闻\n\n"

    if financial_news:
        md_content += financial_news
    else:
        md_content += "⚠️ 暂时无法获取最新财经新闻，可能是网络问题或数据源维护中。\n\n"

    md_content += "\n---\n\n"
    md_content += "## 💡 温馨提示\n\n"
    md_content += f"- 下一个交易日请关注A股开市表现\n"
    md_content += f"- 海外市场走势可作为参考，但请结合A股自身基本面分析\n"
    md_content += f"- 建议关注板块轮动和资金流向变化\n"
    md_content += f"- 如需查看历史交易分析报告，请使用 `--force` 参数运行\n"

    # 4. 生成JSON数据
    json_data = {
        "report_date": date_str,
        "report_type": "A股休市简报",
        "trading_status": "休市",
        "reason": reason,
        "global_indices": {},
        "financial_news": financial_news if financial_news else None,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if global_indices:
        for idx_name, idx_data in global_indices.items():
            json_data["global_indices"][idx_name] = {
                "name": idx_data['name'],
                "code": idx_data['code'],
                "price": idx_data['price'],
                "change": idx_data['change'],
                "volume": idx_data['volume'],
            }

    return md_content, json_data

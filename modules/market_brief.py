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
    通过baostock交易日历判断是否为交易日
    返回：(是否交易日, 原因说明)

    判断逻辑：
    - 使用baostock的交易日历接口获取所有交易日
    - 检查目标日期是否在交易日历中
    - 在 = 交易日，不在 = 休市
    """
    if date is None:
        date = datetime.date.today()

    target_date_str = date.strftime("%Y-%m-%d")

    try:
        print(f"  正在获取交易日历数据以判断{target_date_str}是否为交易日...")

        # 方法1：使用baostock交易日历接口（推荐）
        try:
            import baostock as bs

            # 登录baostock
            lg = bs.login()
            if lg.error_code != '0':
                raise Exception(f"baostock登录失败：{lg.error_msg}")

            # 获取交易日历（query_trade_date接口）
            # 参数说明：year=年, quarter=季度
            year = date.year
            quarter = (date.month - 1) // 3 + 1

            rs = bs.query_trade_date(
                year=str(year),
                quarter=str(quarter)
            )

            if rs.error_code != '0':
                raise Exception(f"获取交易日历失败：{rs.error_msg}")

            # 读取交易日数据
            trade_dates = []
            while (rs.error_code == '0') & rs.next():
                row_data = rs.get_row_data()
                if len(row_data) >= 3:  # calendar_date, is_trading_day, current_quarter
                    trade_date_str = row_data[0]
                    is_trading = row_data[1]  # '1'表示交易日，'0'表示休市
                    if is_trading == '1':
                        trade_dates.append(trade_date_str)

            # 登出baostock
            bs.logout()

            if not trade_dates:
                raise Exception("交易日历数据为空")

            # 检查目标日期是否在交易日历中
            if target_date_str in trade_dates:
                return True, f"交易日（baostock交易日历包含该日期）"
            else:
                return False, f"休市（baostock交易日历不包含该日期：{target_date_str}）"

        except Exception as e:
            print(f"  ⚠️ baostock交易日历接口调用失败：{str(e)}，尝试使用备用方法...")
            raise e

    except Exception as e:
        # 备用方法1：使用akshare交易日历接口
        try:
            print(f"  💡 使用备用方法1：获取akshare交易日历...")
            import akshare as ak

            # 获取上海证券交易所交易日历
            trade_date_df = ak.tool_trade_date_hist_sina()

            if trade_date_df is not None and not trade_date_df.empty:
                # 将日期列转换为date对象
                import pandas as pd

                # 假设列名为 trade_date
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
            print(f"  ⚠️ 备用方法1也失败：{str(e)}，尝试备用方法2...")
            raise e

    except Exception as e:
        # 备用方法2：尝试获取实时数据判断
        try:
            print(f"  💡 使用备用方法2：获取上证指数实时数据...")
            import akshare as ak

            # 尝试获取实时指数数据
            index_df = fetch_with_retry(ak.index_zh_a_spot_em)[0]

            if index_df is not None and not index_df.empty:
                # 获取上证指数（000001）的最新数据
                sh_index = index_df[index_df['代码'] == '000001']

                if not sh_index.empty:
                    # 如果能获取到实时数据，说明当前是交易时间
                    current_hour = datetime.datetime.now().hour

                    # 判断当前时间是否在交易时段
                    # A股交易时间：9:30-11:30, 13:00-15:00
                    is_trading_time = (
                        (9 <= current_hour < 12) or (13 <= current_hour < 15)
                    )

                    if is_trading_time:
                        return True, f"交易日（当前处于交易时段）"
                    else:
                        # 非交易时段，判断是否为交易日（排除周末）
                        weekday = date.weekday()
                        if weekday < 5:  # 0-4表示周一到周五
                            return True, f"交易日（工作日，非周末）"
                        else:
                            return False, f"休市（周末）"
                else:
                    raise Exception("无法找到上证指数数据")

        except Exception as backup_error:
            print(f"  ⚠️ 备用方法2也失败：{str(backup_error)}")

        # 所有方法都失败，返回保守判断
        weekday = date.weekday()
        if weekday < 5:  # 0-4表示周一到周五
            print(f"  ⚠️ 无法准确判断，按工作日默认为交易日")
            return True, f"交易日（工作日，默认判断）"
        else:
            print(f"  ⚠️ 无法准确判断，按周末默认为休市")
            return False, f"休市（周末，默认判断）"


def get_global_indices() -> Optional[Dict]:
    """
    获取全球主要指数数据
    返回：包含美股、港股等指数的字典
    """
    try:
        print("  正在获取全球指数数据...")

        # 获取全球指数实时行情
        global_df = fetch_with_retry(ak.index_global_spot_em)[0]

        if global_df is None or global_df.empty:
            return None

        # 提取关键指数
        indices = {}

        # 美股三大指数
        us_indices = {
            "道琼斯工业指数": ["道琼斯", "DOW", "道指"],
            "纳斯达克综合指数": ["纳斯达克", "NASDAQ", "纳指"],
            "标普500指数": ["标普500", "S&P 500", "标普"]
        }

        for idx_name, keywords in us_indices.items():
            # 搜索匹配的指数
            for keyword in keywords:
                match = global_df[global_df['名称'].str.contains(keyword, na=False)]
                if not match.empty:
                    row = match.iloc[0]
                    indices[idx_name] = {
                        "name": row['名称'],
                        "code": row['代码'],
                        "price": row['最新价'],
                        "change": row['涨跌幅'],
                        "volume": row['成交量']
                    }
                    break

        # 港股恒生指数
        hk_match = global_df[global_df['名称'].str.contains('恒生指数', na=False)]
        if not hk_match.empty:
            row = hk_match.iloc[0]
            indices["恒生指数"] = {
                "name": row['名称'],
                "code": row['代码'],
                "price": row['最新价'],
                "change": row['涨跌幅'],
                "volume": row['成交量']
            }

        # 如果获取的指数太少，尝试港股指数接口
        if len(indices) < 2:
            hk_index_df = fetch_with_retry(ak.stock_hk_index_spot_em)[0]
            if hk_index_df is not None and not hk_index_df.empty:
                hsi = hk_index_df[hk_index_df['指数名称'].str.contains('恒生指数', na=False)]
                if not hsi.empty:
                    row = hsi.iloc[0]
                    indices["恒生指数"] = {
                        "name": row['指数名称'],
                        "code": row['指数代码'],
                        "price": row['最新价'],
                        "change": row['涨跌幅'],
                        "volume": row['成交量']
                    }

        return indices if indices else None

    except Exception as e:
        print(f"  ⚠️ 获取全球指数数据失败：{str(e)}")
        return None


def get_global_financial_news() -> Optional[str]:
    """
    获取海外金融新闻
    返回：新闻内容字符串
    """
    try:
        print("  正在获取海外金融新闻...")

        # 获取美股新闻（东方财富）
        news_df, news_error = fetch_with_retry(
            ak.stock_news_em,
            symbol="美股"
        )

        if news_df is None or news_df.empty:
            return None

        # 拼接新闻内容（取前10条）
        news_content = ""
        count = 0
        max_news = 10

        for idx, row in news_df.iterrows():
            if count >= max_news:
                break

            # 尝试获取标题和链接
            if '新闻标题' in row and '发布时间' in row:
                news_content += f"\n**{row['新闻标题']}**\n"
                news_content += f"- 发布时间: {row['发布时间']}\n"
                if '新闻链接' in row:
                    news_content += f"- 链接: {row['新闻链接']}\n"
                news_content += "\n"
                count += 1
            elif '标题' in row and '时间' in row:
                news_content += f"\n**{row['标题']}**\n"
                news_content += f"- 发布时间: {row['时间']}\n"
                if '链接' in row:
                    news_content += f"- 链接: {row['链接']}\n"
                news_content += "\n"
                count += 1
            elif len(row) >= 2:
                news_content += f"\n**{row.iloc[0]}**\n"
                news_content += f"- 发布时间: {row.iloc[1]}\n"
                if len(row) >= 3:
                    news_content += f"- 链接: {row.iloc[2]}\n"
                news_content += "\n"
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
                md_content += f"  - 最新价: {idx_data['price']}\n"
                md_content += f"  - 涨跌幅: {idx_data['change']}% {change_sign}\n"
                md_content += f"  - 成交量: {idx_data.get('volume', 'N/A')}\n\n"

        # 港股
        if "恒生指数" in global_indices:
            idx_data = global_indices["恒生指数"]
            change_val = float(idx_data['change']) if idx_data['change'] else 0
            change_sign = "📈" if change_val > 0 else "📉" if change_val < 0 else "➡️"

            md_content += "#### 🇭🇰 港股市场\n\n"
            md_content += f"- **{idx_data['name']}**\n"
            md_content += f"  - 最新价: {idx_data['price']}\n"
            md_content += f"  - 涨跌幅: {idx_data['change']}% {change_sign}\n"
            md_content += f"  - 成交量: {idx_data.get('volume', 'N/A')}\n\n"

        # 市场分析
        md_content += "### 📊 市场分析\n\n"
        md_content += "**简要评述**：\n"

        # 分析整体走势
        changes = []
        for idx_name, idx_data in global_indices.items():
            if idx_data['change']:
                try:
                    changes.append(float(idx_data['change']))
                except:
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
    md_content += "## 📰 海外金融新闻\n\n"

    if financial_news:
        md_content += financial_news
    else:
        md_content += "⚠️ 暂时无法获取海外金融新闻，可能是网络问题或数据源维护中。\n\n"

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
                "volume": idx_data.get('volume', 'N/A')
            }

    return md_content, json_data

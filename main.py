"""
股票主升浪策略分析工具主程序
模块化版本 - 支持独立运行和扩展
"""

import argparse
import datetime
import json
import os
import sys
import time

# 添加当前目录到 Python 路径，确保能找到 utils 和 modules 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    DEFAULT_STOCK,
    STOCK_LIST,
    OUTPUT_DIR_DEFAULT,
    STRATEGY_EXPLAIN_MD,
    REQUEST_DELAY_NORMAL
)

from modules.market_brief import is_trading_day, generate_market_brief
from modules.stock_analyzer import get_stock_data

from utils.helpers import write_run_log, check_directory_permission, NumpyJSONEncoder


def print_module_status(json_data, stock_name):
    """
    打印模块完成情况
    """
    analysis = json_data.get("analysis", {})

    # 维度名称映射
    dimension_names = {
        "trend": "趋势维度（DK信号）",
        "main_chip": "主力筹码维度",
        "market_chip": "全市场筹码维度",
        "fund_flow": "主力资金维度",
        "price_volume": "量价维度",
        "block": "板块维度"
    }

    print(f"\n  📊 {stock_name} 维度完成情况：")

    success_count = 0
    failed_count = 0
    missing_count = 0

    for key, name in dimension_names.items():
        if key in analysis:
            result = analysis[key]
            source = result.get("source", "")

            if source == "akshare":
                print(f"     ✅ {name}: 成功")
                success_count += 1
            elif source == "手动配置":
                print(f"     ✅ {name}: 成功（手动配置）")
                success_count += 1
            elif source == "缺失":
                print(f"     ❌ {name}: 数据缺失")
                missing_count += 1
            elif source == "获取失败":
                print(f"     ❌ {name}: 获取失败")
                failed_count += 1
            else:
                print(f"     ⚠️ {name}: {source}")

    print(f"\n  📈 统计：成功 {success_count} 个，失败 {failed_count} 个，缺失 {missing_count} 个")

    return {
        "success": success_count,
        "failed": failed_count,
        "missing": missing_count,
        "total": len(dimension_names)
    }


def main():
    """主函数：生成当日分析报告"""
    global STOCK_LIST  # 声明使用全局变量

    # 1. 参数解析
    parser = argparse.ArgumentParser(description='股票主升浪策略分析工具（模块化版）')
    parser.add_argument('--output', type=str, help=f'输出目录路径（默认：{OUTPUT_DIR_DEFAULT}）')
    parser.add_argument('--json-only', action='store_true', help='仅输出JSON格式')
    parser.add_argument('--md-only', action='store_true', help='仅输出MD格式')
    parser.add_argument('--force', action='store_true', help='强制运行，忽略休市判断')
    parser.add_argument('--date', type=str, help='指定分析日期（YYYY-MM-DD），默认今天')
    parser.add_argument('--code', type=str, help=f'指定股票代码（默认：{DEFAULT_STOCK["code"]}），如：600711、002240')
    parser.add_argument('--name', type=str, help=f'指定股票名称（默认：{DEFAULT_STOCK["name"]}）')
    args = parser.parse_args()

    # 2. 日期处理
    if args.date:
        try:
            target_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"❌ 日期格式错误：{args.date}，请使用YYYY-MM-DD格式")
            sys.exit(1)
    else:
        target_date = datetime.date.today()

    # 2.5. 股票代码处理
    if args.code:
        # 如果用户指定了股票代码，使用用户指定的
        custom_stock = DEFAULT_STOCK.copy()
        custom_stock["code"] = args.code
        if args.name:
            custom_stock["name"] = args.name
        STOCK_LIST = [custom_stock]
        print(f"📈 使用自定义股票：{custom_stock['name']}（{custom_stock['code']}）")
    else:
        print(f"📈 使用默认股票：{DEFAULT_STOCK['name']}（{DEFAULT_STOCK['code']}）")

    # 3. 休市判断（决定报告内容类型）
    if not args.force:
        is_trading, reason = is_trading_day(target_date)
        if not is_trading:
            trading_status = "休市日"
            print(f"⚠️ {target_date} 为{reason}，报告内容将包含海外市场信息...")
        else:
            # 交易日历判断为交易日，再通过实际数据验证最新日期
            # 如果最新数据日期不等于目标日期，说明今天休市（数据未更）
            print(f"✅ {target_date} 交易日历判断为交易日，正在验证数据是否更新...")
            try:
                import baostock as bs
                from utils.baostock_utils import get_trend_data
                # 用默认股票验证数据是否更新
                test_code = DEFAULT_STOCK["code"].replace("sh.", "").replace("sz.", "")
                test_market = "sh" if test_code.startswith("6") else "sz"
                df, error = get_trend_data(test_code, test_market)
                if df is not None and not df.empty:
                    latest_date = df.iloc[-1]['date']
                    # latest_date 是 datetime 对象
                    if hasattr(latest_date, 'date'):
                        latest_date = latest_date.date()
                    else:
                        latest_date = datetime.date.fromisoformat(str(latest_date).split()[0])

                    if latest_date != target_date:
                        # 最新数据日期不等于目标日期，判定为休市
                        trading_status = "休市日"
                        print(f"⚠️ 数据验证失败：最新数据日期为 {latest_date}，目标日期为 {target_date}，数据未更新，判定为休市...")
                        reason = f"数据未更新（最新日期：{latest_date}）"
                    else:
                        trading_status = "交易日"
                        print(f"✅ 数据验证通过：最新数据日期 {latest_date} 与目标日期一致，确认是交易日...")
                else:
                    # 获取数据失败，保持原判断
                    trading_status = "交易日"
                    print(f"⚠️ 数据验证失败：{error}，保持交易日判断...")
            except Exception as e:
                # 验证出错，保持原判断
                trading_status = "交易日"
                print(f"⚠️ 数据验证异常：{str(e)}，保持交易日判断...")
    else:
        trading_status = "交易日"  # 强制运行视为交易日
        print(f"⚠️ 强制运行模式，视为交易日...")

    # 4. 基础初始化（统一生成主升浪策略分析报告）
    today_date = target_date.strftime("%Y-%m-%d")
    today_date_fmt = target_date.strftime("%Y_%m_%d")  # 文件名使用下划线格式
    output_dir = args.output if args.output else OUTPUT_DIR_DEFAULT

    # 统一报告名称
    md_report_name = f"{today_date_fmt}_主升浪策略分析报告.md"
    json_report_name = f"{today_date_fmt}_主升浪策略分析报告.json"

    md_report_path = os.path.join(output_dir, md_report_name)
    json_report_path = os.path.join(output_dir, json_report_name)
    run_log_path = os.path.join(output_dir, "run_log.txt")

    # 5. 检查输出目录
    if not os.path.exists(output_dir):
        print(f"⚠️ 输出目录不存在，自动创建：{output_dir}")
        os.makedirs(output_dir, exist_ok=True)

    if not check_directory_permission(output_dir):
        print("❌ 无目录写入权限，程序退出")
        sys.exit(1)

    # 6. 根据交易日状态生成报告内容
    stock_data_content = ""
    json_results = {
        "report_date": today_date,
        "report_type": "主升浪策略分析" if trading_status == "交易日" else "A股休市简报",
        "trading_status": trading_status,
        "stocks": []
    }

    # 模块完成情况统计
    total_success = 0
    total_failed = 0
    total_missing = 0

    if trading_status == "休市日":
        # 休市日：生成海外市场简报内容
        print(f"\n📰 生成休市日简报内容...")

        # 获取全球指数
        print("  🌍 获取全球指数数据...")
        md_content, json_data = generate_market_brief(target_date, reason)

        # 显示休市简报模块完成情况
        global_indices = json_data.get("global_indices", {})
        financial_news = json_data.get("financial_news")

        print(f"\n  📊 休市简报模块完成情况：")
        if global_indices:
            print(f"     ✅ 全球指数数据: 成功（{len(global_indices)}个指数）")
            total_success += 1
        else:
            print(f"     ❌ 全球指数数据: 获取失败")
            total_failed += 1

        if financial_news:
            print(f"     ✅ 海外金融新闻: 成功")
            total_success += 1
        else:
            print(f"     ❌ 海外金融新闻: 获取失败")
            total_failed += 1

        stock_data_content = md_content
        json_results["market_brief"] = json_data

    else:
        # 交易日：生成A股分析内容
        print(f"\n📊 开始分析 {len(STOCK_LIST)} 只股票...")

        # 提示：板块维度只能获取当前实时数据
        if args.date and args.date != datetime.date.today().strftime("%Y-%m-%d"):
            print(f"⚠️  注意：指定历史日期时，板块维度只能获取当前实时数据！")

        for stock_idx, stock in enumerate(STOCK_LIST, 1):
            print(f"\n{'='*60}")
            print(f"  [{stock_idx}/{len(STOCK_LIST)}] 正在分析 {stock['name']}（{stock['code']}）...")
            print(f"{'='*60}")

            md_content, json_data = get_stock_data(
                stock["code"],
                stock["name"],
                stock.get("main_type", "短线游资"),
                stock.get("industry", ""),
                target_date=target_date
            )

            # 打印模块完成情况
            status = print_module_status(json_data, stock['name'])

            # 统计总数
            total_success += status["success"]
            total_failed += status["failed"]
            total_missing += status["missing"]

            stock_data_content += md_content
            json_results["stocks"].append(json_data)

            # 批量获取时添加延迟，避免高频请求被封
            if len(STOCK_LIST) > 1:
                stock_index = STOCK_LIST.index(stock)
                if stock_index < len(STOCK_LIST) - 1:  # 不是最后一个股票
                    print(f"\n  ⏳ 等待 {REQUEST_DELAY_NORMAL} 秒后处理下一只股票...")
                    time.sleep(REQUEST_DELAY_NORMAL)

    # 7. 生成报告
    print(f"\n{'='*60}")
    print(f"📝 生成报告文件...")
    print(f"{'='*60}")

    # 8. 拼接最终MD内容
    final_md_content = f"""# 股票主升浪策略分析报告 {today_date}

> **报告生成时间**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> **数据来源**: akshare + 手动配置
> **交易状态**: {trading_status}

{stock_data_content}

{STRATEGY_EXPLAIN_MD}
"""

    # 9. 写入MD报告
    if not args.json_only:
        try:
            with open(md_report_path, "w", encoding="utf-8") as f:
                f.write(final_md_content)
            print(f"✅ MD报告已生成：{md_report_path}")
            write_run_log(run_log_path, f"生成MD报告：{md_report_name}")
        except Exception as e:
            error_msg = f"MD报告写入失败：{str(e)}"
            print(f"❌ {error_msg}")
            write_run_log(run_log_path, error_msg, is_success=False)
            sys.exit(1)

    # 10. 写入JSON报告
    if not args.md_only:
        try:
            with open(json_report_path, "w", encoding="utf-8") as f:
                json.dump(json_results, f, ensure_ascii=False, indent=2, cls=NumpyJSONEncoder)
            print(f"✅ JSON报告已生成：{json_report_path}")
            write_run_log(run_log_path, f"生成JSON报告：{json_report_name}")
        except Exception as e:
            error_msg = f"JSON报告写入失败：{str(e)}"
            print(f"❌ {error_msg}")
            write_run_log(run_log_path, error_msg, is_success=False)
            sys.exit(1)

    # 11. 输出摘要
    print(f"\n{'='*60}")
    print(f"📊 分析完成！")
    print(f"{'='*60}")

    # 模块完成情况总览
    total_modules = total_success + total_failed + total_missing
    if total_modules > 0:
        print(f"\n📈 模块完成情况总览：")
        print(f"   - 总模块数：{total_modules}")
        print(f"   - ✅ 成功：{total_success}")
        print(f"   - ❌ 失败：{total_failed}")
        print(f"   - ⚠️  缺失：{total_missing}")
        success_rate = (total_success / total_modules * 100) if total_modules > 0 else 0
        print(f"   - 📊 成功率：{success_rate:.1f}%")

    print(f"\n📋 分析结果：")
    print(f"   - 总股票数：{len(STOCK_LIST)}")

    if trading_status == "交易日":
        decision_stats = {}
        for stock in json_results["stocks"]:
            action = stock["decision"]["action"]
            decision_stats[action] = decision_stats.get(action, 0) + 1

        print(f"\n   🎯 投资决策统计：")
        for action, count in decision_stats.items():
            print(f"      - {action}：{count}")
    else:
        print(f"   - 报告类型：休市简报")
        if json_results.get("market_brief", {}).get("global_indices"):
            print(f"   - 全球指数数：{len(json_results['market_brief']['global_indices'])}")

    print(f"\n📁 输出文件：")
    print(f"   - {md_report_path}")
    print(f"   - {json_report_path}")


if __name__ == "__main__":
    main()

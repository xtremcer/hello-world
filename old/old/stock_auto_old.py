# ==============================================
# 股票自动化分析脚本（每日独立MD报告版）
# 适配环境：Ubuntu服务器 + Python虚拟环境 + NAS存储
# 目标股票：600711（盛屯矿业）、002240（盛新锂能）
# 核心功能：每日生成带日期的MD报告，数据结构化，大模型友好
# ==============================================
import akshare as ak
import datetime
import os

# ===================== 核心配置（无需修改）=====================
# 目标股票代码
STOCK1 = "600711"  # 盛屯矿业
STOCK2 = "002240"  # 盛新锂能
# NAS存储目录（已适配权限）
NAS_STOCK_DIR = "/mnt/nas/stock/data"
# =================================================================

def get_market(code):
    """
    根据股票代码自动判断交易所
    规则：60/68开头→沪市(sh)；00/30开头→深市(sz)；默认沪市
    """
    if code.startswith('60') or code.startswith('68'):
        return 'sh'
    elif code.startswith('00') or code.startswith('30'):
        return 'sz'
    else:
        return 'sh'  # 默认上海市场

def get_stock_data(stock_code):
    """
    获取单只股票的完整数据（K线+主力资金）
    返回：结构化MD格式字符串（表格形式，无错乱）
    """
    market = get_market(stock_code)
    full_code = f"{market}{stock_code}"
    
    # 初始化返回内容
    stock_md_content = f"\n### 股票代码：{stock_code}\n"
    
    # 1. 获取近10日K线数据（前复权）
    try:
        kline_df = ak.stock_zh_a_daily(symbol=full_code, adjust="qfq")
        kline_data = kline_df.iloc[-10:]  # 取最近10日
        # 转为MD表格（确保列对齐，无错行）
        stock_md_content += "#### 近10日K线数据\n"
        stock_md_content += kline_data.to_markdown(index=True, tablefmt="pipe") + "\n\n"
    except Exception as e:
        stock_md_content += f"**K线数据获取失败**：{str(e)}\n\n"
    
    # 2. 获取近5日主力资金数据
    try:
        fund_df = ak.stock_individual_fund_flow(stock=stock_code, market=market)
        fund_data = fund_df.iloc[-5:]  # 取最近5日
        # 转为MD表格（结构化，无错乱）
        stock_md_content += "#### 近5日主力资金数据\n"
        stock_md_content += fund_data.to_markdown(index=True, tablefmt="pipe") + "\n"
    except Exception as e:
        stock_md_content += f"**主力资金数据获取失败**：{str(e)}\n"
    
    # 分隔线，区分不同股票
    stock_md_content += "\n---\n"
    return stock_md_content

# ===================== AI分析提示词（完整保留原版规则）=====================
AI_PROMPT_MD = """
## 量化分析规则（严格执行）
1. 主力资金：连续3-5日净流入、占成交额＞10%为合格；连续2日净流出为预警
2. 筹码状态：免费数据缺失，需手动补充Level-2获利比例/筹码峰数据
3. 量价匹配：成交量放大1.5倍以上+突破5/10日均线=确认有效；放量滞涨=风险信号
4. 板块联动：免费数据缺失
5. 止损条件：跌破5日均线 OR 主力资金连续2日流出
6. 卖出条件：主力资金连续2日流出 + 获利比例＞70% + 放量滞涨

## 输出格式要求（禁止添加任何额外内容）
股票代码：XXX
主力资金：结论 + 核心数据支撑
筹码状态：免费数据缺失，需手动补充
量价匹配：结论 + 核心数据支撑
板块联动：免费数据缺失
最终决策：买入 / 持仓 / 卖出 / 观望
风险提示：止损条件是否触发（是 / 否）
"""
# =========================================================================

def main():
    """主函数：生成当日MD报告 + 追加运行日志"""
    # 1. 生成当日日期（仅日期，格式：YYYY-MM-DD，无时间）
    today_date = datetime.date.today().strftime("%Y_%m_%d")
    # 2. 定义文件路径
    md_report_name = f"{today_date}_股票分析报告.md"
    md_report_path = os.path.join(NAS_STOCK_DIR, md_report_name)
    run_log_path = os.path.join(NAS_STOCK_DIR, "run_log.txt")
    
    # 3. 生成MD报告完整内容
    final_md_content = f"""# 股票自动化分析报告 {today_date}

{get_stock_data(STOCK1)}
{get_stock_data(STOCK2)}

{AI_PROMPT_MD}
"""
    
    # 4. 写入当日MD报告（独立文件，无覆盖）
    try:
        with open(md_report_path, "w", encoding="utf-8") as f:
            f.write(final_md_content)
        print(f"✅ 当日MD报告已生成：{md_report_path}")
    except Exception as e:
        print(f"❌ MD报告写入失败：{str(e)}")
        return
    
    # 5. 追加运行日志（保留历史记录，不覆盖）
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_content = f"{current_time} - 成功生成报告：{md_report_name} | 存储路径：{md_report_path}\n"
    try:
        with open(run_log_path, "a", encoding="utf-8") as f:
            f.write(log_content)
        print(f"✅ 运行日志已追加：{run_log_path}")
    except Exception as e:
        print(f"❌ 日志写入失败：{str(e)}")

if __name__ == "__main__":
    # 先检查NAS目录是否存在
    if not os.path.exists(NAS_STOCK_DIR):
        print(f"⚠️ NAS目录不存在，自动创建：{NAS_STOCK_DIR}")
        os.makedirs(NAS_STOCK_DIR, exist_ok=True)
    # 执行主函数
    main()
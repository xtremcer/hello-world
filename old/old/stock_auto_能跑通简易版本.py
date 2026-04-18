# 固定股票：600711 盛屯矿业 | 002240 伟星新材
# 输出路径：/mnt/nas/stock（NAS 映射目录）
import akshare as ak
import datetime
import os

# 你的股票
STOCK1 = "600711"
STOCK2 = "002240"
# ========== 核心修改：输出路径改为 NAS 目录 ==========
REPORT_FILE = "/mnt/nas/stock/stock_report.txt"  # 分析报告
LOG_PATH = "/mnt/nas/stock/run_log.txt"          # 运行日志
# ===================================================

def get_market(code):
    return "sh" if code.startswith("6") else "sz"

def get_stock_data(stock_code):
    market = get_market(stock_code)
    try:
        kline = ak.stock_zh_a_daily(symbol=f"{market}{stock_code}", adjust="qfq").iloc[-10:]
        fund = ak.stock_individual_fund_flow(stock=stock_code, market=market).iloc[-5:]
        return f"【股票 {stock_code}】\n近10日K线：\n{kline.to_string()}\n\n近5日主力资金：\n{fund.to_string()}\n"
    except Exception as e:
        return f"【{stock_code} 数据失败】{str(e)}"

AI_PROMPT = """
=== 分析规则 ===
1.主力资金：连续3-5日净流入=合格，2日净流出=预警
2.量价：放量1.5倍+突破均线=有效
3.止损：跌破5日均线/资金连续流出
免费无筹码/板块数据，需手动补充
"""

if __name__ == "__main__":
    now = datetime.datetime.now().strftime("%Y_%m_%d %H:%M")
    res = f"===== {now} 分析报告 =====\n\n"
    res += get_stock_data(STOCK1) + "\n" + get_stock_data(STOCK2)
    res += f"\n===== AI分析规则 =====\n{AI_PROMPT}"
    
    # 写入 NAS 目录
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(res)
    
    # 记录运行日志到 NAS
    log_content = f"{now} - 报告已生成：{REPORT_FILE}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_content)
    
    print(f"✅ 运行成功！报告路径：{REPORT_FILE}")
    print(f"✅ 日志路径：{LOG_PATH}")

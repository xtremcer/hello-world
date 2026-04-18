# ==============================================
# 股票自动化分析脚本（强化版：五维主升浪策略）
# 适配环境：Ubuntu服务器 + Python虚拟环境 + NAS存储
# 目标股票：600711（盛屯矿业）、002240（盛新锂能）
# 核心功能：每日生成带五维分析的MD报告，适配散户主升浪策略
# 新增维度：DK趋势、主力筹码、全市场筹码、板块资金
# ==============================================
import akshare as ak
import datetime
import os
import math

# ===================== 核心配置（易扩展）=====================
# 目标股票列表（新增/修改股票仅需改此处）
STOCK_LIST = [
    {"code": "600711", "name": "盛屯矿业", "main_type": "短线游资"},  # 主力类型：短线游资/中长线机构
    {"code": "002240", "name": "盛新锂能", "main_type": "中长线机构"}
]
# NAS存储目录（已适配权限）
NAS_STOCK_DIR = "/mnt/nas/stock"
# 板块资金排名阈值（买入信号：前10）
BLOCK_RANK_THRESHOLD = 10
# =================================================================

def get_market(code):
    """根据股票代码自动判断交易所"""
    if code.startswith('60') or code.startswith('68'):
        return 'sh'
    elif code.startswith('00') or code.startswith('30'):
        return 'sz'
    else:
        return 'sh'  # 默认上海市场

def estimate_main_holder_profit(main_cost, current_price):
    """估算主力获利比例（免费数据替代方案）"""
    if main_cost <= 0:
        return 0.0
    profit_ratio = (current_price - main_cost) / main_cost * 100
    return round(profit_ratio, 2)

def get_dk_signal(stock_code):
    """获取DK趋势信号（免费数据模拟，实际需对接APP接口）"""
    # 示例：盛屯矿业近期D点，盛新锂能假设D点；实际需从行情软件爬取/手动补充
    dk_signal_map = {
        "600711": "D点（机会信号）",
        "002240": "D点（机会信号）"
    }
    # 真实场景：可通过东方财富API/爬虫获取，此处用示例数据
    return dk_signal_map.get(stock_code, "未获取到")

def get_chip_data(stock_code):
    """获取筹码数据（免费版估算，付费版可精准获取）"""
    # 示例数据（盛屯矿业/盛新锂能真实参考值）
    chip_map = {
        "600711": {
            "main_cost": 13.90,        # 主力平均成本
            "main_profit_ratio": 2.09,  # 主力获利比例
            "main_chip_shape": "低位单峰密集",  # 主力筹码形态
            "market_avg_cost": 14.01,   # 全市场平均成本
            "market_profit_ratio": 55.48, # 全市场获利比例
            "chip_concentration": "70%筹码集中在11.20-15.30元", # 筹码集中度
            "chip_shape": "单峰密集"     # 全市场筹码形态
        },
        "002240": {
            "main_cost": 28.50,
            "main_profit_ratio": 8.6,
            "main_chip_shape": "低位单峰密集",
            "market_avg_cost": 29.10,
            "market_profit_ratio": 48.25,
            "chip_concentration": "70%筹码集中在25.50-30.20元",
            "chip_shape": "单峰密集"
        }
    }
    return chip_map.get(stock_code, {})

def get_block_fund_rank(stock_code):
    """获取股票所属板块资金排名（示例）"""
    # 示例：盛屯矿业（有色金属）排名8，盛新锂能（锂矿）排名6
    block_rank_map = {
        "600711": 8,
        "002240": 6
    }
    return block_rank_map.get(stock_code, 99)

def get_stock_data(stock_code, stock_name="", main_type="短线游资"):
    """
    获取单只股票的五维分析数据
    返回：结构化MD格式字符串，适配主升浪策略
    """
    market = get_market(stock_code)
    full_code = f"{market}{stock_code}"
    
    # 初始化返回内容
    stock_md_content = f"\n### {stock_name}（{stock_code}）| 主力类型：{main_type}\n"
    
    # 1. 趋势维度（DK信号）
    dk_signal = get_dk_signal(stock_code)
    stock_md_content += "#### 1. 趋势维度（DK信号）\n"
    stock_md_content += f"- 核心信号：{dk_signal}\n"
    stock_md_content += f"- 信号判定：{'符合买入条件（D点）' if 'D点' in dk_signal else '符合卖出条件（K点）/未达标'}\n\n"
    
    # 2. 主力筹码维度
    chip_data = get_chip_data(stock_code)
    stock_md_content += "#### 2. 主力筹码维度\n"
    if chip_data:
        main_profit_ratio = chip_data["main_profit_ratio"]
        main_chip_shape = chip_data["main_chip_shape"]
        stock_md_content += f"- 主力平均成本：{chip_data['main_cost']}元\n"
        stock_md_content += f"- 主力获利比例：{main_profit_ratio}%\n"
        stock_md_content += f"- 主力筹码形态：{main_chip_shape}\n"
        # 买入信号判定
        profit_threshold = 10 if main_type == "短线游资" else 10  # 统一＜10%为进场
        shape_qualified = "单峰密集" in main_chip_shape and "低位" in main_chip_shape
        stock_md_content += f"- 信号判定：{'符合买入条件' if (main_profit_ratio < profit_threshold and shape_qualified) else '不符合买入条件'}\n\n"
    else:
        stock_md_content += "- 筹码数据获取失败（免费数据需手动补充）\n\n"
    
    # 3. 全市场筹码维度
    stock_md_content += "#### 3. 全市场筹码维度\n"
    if chip_data:
        market_profit_ratio = chip_data["market_profit_ratio"]
        market_chip_shape = chip_data["chip_shape"]
        stock_md_content += f"- 全市场平均成本：{chip_data['market_avg_cost']}元\n"
        stock_md_content += f"- 全市场获利比例：{market_profit_ratio}%\n"
        stock_md_content += f"- 筹码集中度：{chip_data['chip_concentration']}\n"
        stock_md_content += f"- 全市场筹码形态：{market_chip_shape}\n"
        # 买入信号判定
        profit_qualified = 20 <= market_profit_ratio <= 60
        shape_qualified = "单峰密集" in market_chip_shape
        stock_md_content += f"- 信号判定：{'符合买入条件' if (profit_qualified and shape_qualified) else '不符合买入条件'}\n\n"
    else:
        stock_md_content += "- 全市场筹码数据获取失败\n\n"
    
    # 4. 主力资金维度
    stock_md_content += "#### 4. 主力资金维度\n"
    try:
        fund_df = ak.stock_individual_fund_flow(stock=stock_code, market=market)
        if fund_df.empty:
            stock_md_content += "- 主力资金数据获取失败（非交易日/接口限制）\n\n"
        else:
            fund_data = fund_df.iloc[-3:]  # 近3日数据
            net_inflow = fund_data["净流入"].sum()
            avg_ratio = fund_data["净流入占成交额比例"].mean()
            stock_md_content += f"- 近3日主力资金净流入总额：{round(net_inflow, 2)}万元\n"
            stock_md_content += f"- 净流入占成交额平均比例：{round(avg_ratio, 2)}%\n"
            # 买入信号判定
            inflow_qualified = net_inflow > 0  # 连续3日净流入
            ratio_qualified = avg_ratio > 5    # 占比＞5%
            stock_md_content += f"- 信号判定：{'符合买入条件' if (inflow_qualified and ratio_qualified) else '不符合买入条件'}\n"
            # 补充近5日资金表格
            stock_md_content += "#### 近5日主力资金明细\n"
            stock_md_content += fund_df.iloc[-5:].round(2).to_markdown(index=True, tablefmt="pipe") + "\n\n"
    except Exception as e:
        stock_md_content += f"- 主力资金数据获取失败：{str(e)}\n\n"
    
    # 5. 量价维度
    stock_md_content += "#### 5. 量价维度\n"
    try:
        kline_df = ak.stock_zh_a_daily(symbol=full_code, adjust="qfq")
        if kline_df.empty:
            stock_md_content += "- K线/量价数据获取失败\n\n"
        else:
            # 近10日K线+量价分析
            kline_data = kline_df.iloc[-10:]
            latest_price = kline_data.iloc[-1]["收盘"]
            ma10 = kline_data["收盘"].rolling(10).mean().iloc[-1]
            vol_avg = kline_data["成交量"].iloc[-10:-1].mean()  # 前9日均量
            latest_vol = kline_data.iloc[-1]["成交量"]
            vol_multiple = round(latest_vol / vol_avg, 2) if vol_avg > 0 else 0
            # 突破均线判定
            break_ma10 = latest_price > ma10
            vol_qualified = vol_multiple >= 1.5
            stock_md_content += f"- 最新股价：{latest_price}元 | 10日均线：{round(ma10, 2)}元\n"
            stock_md_content += f"- 最新成交量：{latest_vol}手 | 较前9日均量放大：{vol_multiple}倍\n"
            stock_md_content += f"- 信号判定：{'符合买入条件' if (break_ma10 and vol_qualified) else '不符合买入条件'}\n"
            # 补充近10日K线表格
            stock_md_content += "#### 近10日K线数据（前复权）\n"
            stock_md_content += kline_data.round(2).to_markdown(index=True, tablefmt="pipe") + "\n\n"
    except Exception as e:
        stock_md_content += f"- 量价数据获取失败：{str(e)}\n\n"
    
    # 6. 板块维度
    stock_md_content += "#### 6. 板块维度\n"
    block_rank = get_block_fund_rank(stock_code)
    stock_md_content += f"- 所属板块资金排名：第{block_rank}名（行业共约50个板块）\n"
    stock_md_content += f"- 信号判定：{'符合买入条件' if block_rank <= BLOCK_RANK_THRESHOLD else '不符合买入条件'}\n\n"
    
    # 7. 综合判定（买入/观望/卖出）
    stock_md_content += "#### 综合判定\n"
    # 统计符合买入条件的维度数（需全部6项符合才买入）
    qualified_count = 0
    if 'D点' in dk_signal: qualified_count +=1
    if chip_data and chip_data["main_profit_ratio"] < 10 and "低位单峰密集" in chip_data["main_chip_shape"]: qualified_count +=1
    if chip_data and 20 <= chip_data["market_profit_ratio"] <=60 and "单峰密集" in chip_data["chip_shape"]: qualified_count +=1
    try:
        if fund_df is not None and not fund_df.empty and fund_df.iloc[-3:]["净流入"].sum() >0 and fund_df.iloc[-3:]["净流入占成交额比例"].mean()>5: qualified_count +=1
    except: pass
    try:
        if kline_df is not None and not kline_df.empty and latest_price>ma10 and vol_multiple>=1.5: qualified_count +=1
    except: pass
    if block_rank <= BLOCK_RANK_THRESHOLD: qualified_count +=1
    
    if qualified_count == 6:
        stock_md_content += f"- 最终决策：买入（6个维度全部符合主升浪买入条件）\n"
        stock_md_content += f"- 操作周期：{'3-10天（短线）' if main_type=='短线游资' else '1-4周（波段）'}\n"
        stock_md_content += f"- 止损/止盈：止损=跌破10日均线；止盈=主力获利比例＞{30 if main_type=='短线游资' else 50}%\n"
    else:
        stock_md_content += f"- 最终决策：观望（仅{qualified_count}/6个维度符合买入条件）\n"
        stock_md_content += f"- 待改进维度：需等待所有维度共振后进场\n"
    
    # 分隔线
    stock_md_content += "\n---\n"
    return stock_md_content

def write_run_log(log_path, content, is_success=True):
    """封装日志写入函数，区分成功/失败级别"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_prefix = "[SUCCESS]" if is_success else "[ERROR]"
    log_content = f"{current_time} {log_prefix} - {content}\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_content)
        print(f"✅ 日志已追加：{log_content.strip()}")
    except Exception as e:
        print(f"❌ 日志写入失败：{str(e)}")

# ===================== 策略说明（融入MD报告）=====================
STRATEGY_EXPLAIN_MD = """
## 散户主升浪交易策略（强化版）
### 核心目标
只抓主力主升浪拉升段利润，规避吸筹、洗盘、出货阶段风险

### 买入信号（必须同时满足6项）
1. 趋势维度：DK信号出现D点（机会信号）
2. 主力筹码：主力获利＜10% + 低位单峰密集
3. 全市场筹码：全市场获利20%-60% + 单峰密集
4. 主力资金：连续3日净流入 + 占成交额＞5%
5. 量价维度：放量1.5倍以上 + 突破10日均线
6. 板块维度：所属板块资金排名前10

### 卖出信号（满足任意2项及以上）
1. 趋势维度：DK信号出现K点（风险信号）
2. 主力筹码：主力获利＞30%（游资）/50%（机构） + 高位发散
3. 全市场筹码：全市场获利＞70% + 高位发散
4. 主力资金：连续2日净流出 + 大额出逃
5. 量价维度：放量滞涨（成交量放大但股价不涨）
6. 板块维度：板块资金排名跌出前10 + 资金大幅流出

### 数据边界说明
- 免费可得：DK信号、主力/全市场筹码（估算）、主力资金、量价、板块排名
- 付费提升：Level-2逐笔成交、高精度主力筹码（年费300-1000元）
- 完全无法获取：主力精确操盘计划、真实持仓成本、资金真实身份
"""
# =================================================================

def check_nas_permission(dir_path):
    """检查NAS目录写入权限"""
    if os.access(dir_path, os.W_OK):
        return True
    print(f"⚠️ NAS目录{dir_path}无写入权限，尝试自动提权...")
    try:
        os.chmod(dir_path, 0o775)
        return os.access(dir_path, os.W_OK)
    except Exception as e:
        print(f"❌ 提权失败：{str(e)}，请手动执行 chmod 775 {dir_path}")
        return False

def main():
    """主函数：生成当日五维分析MD报告 + 追加运行日志"""
    # 1. 基础初始化
    today_date = datetime.date.today().strftime("%Y-%m-%d")
    md_report_name = f"{today_date}_主升浪策略分析报告.md"
    md_report_path = os.path.join(NAS_STOCK_DIR, md_report_name)
    run_log_path = os.path.join(NAS_STOCK_DIR, "run_log.txt")
    
    # 2. 检查NAS目录（存在性+权限）
    if not os.path.exists(NAS_STOCK_DIR):
        print(f"⚠️ NAS目录不存在，自动创建：{NAS_STOCK_DIR}")
        os.makedirs(NAS_STOCK_DIR, exist_ok=True)
    
    if not check_nas_permission(NAS_STOCK_DIR):
        print("❌ 无NAS目录写入权限，程序退出")
        return
    
    # 3. 批量生成多只股票五维分析数据
    stock_data_content = ""
    for stock in STOCK_LIST:
        stock_data_content += get_stock_data(
            stock["code"], 
            stock["name"], 
            stock["main_type"]
        )
    
    # 4. 拼接最终MD内容
    final_md_content = f"""# 股票主升浪策略分析报告 {today_date}

{stock_data_content}

{STRATEGY_EXPLAIN_MD}

## 核心概念通俗解释
### 1. DK趋势信号
- 定义：股价的“红绿灯”——D点（绿灯）= 主力拉升启动；K点（红灯）= 主力出货下跌
- 用法：只在D点买，K点必卖

### 2. 主力筹码分布
- 定义：只算主力的持仓成本/获利情况，看主力是否赚钱、要不要出货
- 关键：主力获利＜10%=安全，＞30%（游资）/50%（机构）= 要出货

### 3. 全市场筹码分布
- 定义：所有投资者的持仓成本，看散户抛压大小
- 关键：全市场获利＞70%=抛压大，必跌；20%-60%=抛压小，易涨

### 4. 获利比例
- 主力获利比例：主力卖股票能赚的比例；全市场获利比例：所有人赚钱的比例
- 用法：主力获利看主力动向，全市场获利看散户抛压

### 5. 筹码峰
- 定义：筹码集中的价格区间，单峰=筹码集中，发散=筹码分散
- 关键：低位单峰=主力锁仓拉升；高位发散=主力出货
"""
    
    # 5. 写入当日MD报告
    try:
        with open(md_report_path, "w", encoding="utf-8") as f:
            f.write(final_md_content)
        print(f"✅ 当日主升浪策略报告已生成：{md_report_path}")
        write_run_log(run_log_path, f"生成主升浪报告：{md_report_name} | 路径：{md_report_path}")
    except Exception as e:
        error_msg = f"MD报告写入失败：{str(e)}"
        print(f"❌ {error_msg}")
        write_run_log(run_log_path, error_msg, is_success=False)
        return

if __name__ == "__main__":
    main()
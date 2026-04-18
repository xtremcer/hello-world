"""
使用AI分析股票报告
"""
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.runtime_ctx.context import Context, new_context
from langchain_core.messages import SystemMessage, HumanMessage

# 读取股票报告
with open('./600711_完整分析报告.md', 'r', encoding='utf-8') as f:
    report_content = f.read()

# 创建AI客户端
ctx = new_context(method="invoke")
client = LLMClient(ctx=ctx)

# 设置系统提示词
system_prompt = """你是一位资深的股票量化分析师，拥有10年以上A股市场分析经验。
你的任务是对提供的股票分析报告进行深度解读和评价，并给出专业的投资建议。

分析要点：
1. 评估报告的维度完整性和数据可靠性
2. 分析股票当前的技术面和基本面情况
3. 指出报告中的关键风险点
4. 给出具体的操作建议（买入、持有、卖出、观望）
5. 评估当前时点是否适合建仓

输出格式要求：
- 使用Markdown格式
- 条理清晰，观点明确
- 数据驱动，避免主观臆断
- 必须包含风险提示
"""

# 构建消息
messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=f"请对以下股票分析报告进行深度解读和专业评价：\n\n{report_content}")
]

print("正在使用AI分析股票报告...\n")

# 调用AI
response = client.invoke(
    messages=messages,
    model="doubao-seed-2-0-pro-260215",
    temperature=0.7,
    thinking="enabled"
)

# 提取文本内容
def get_text_content(content):
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        if content and isinstance(content[0], str):
            return " ".join(content)
        else:
            return " ".join(item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text")
    return str(content)

analysis_text = get_text_content(response.content)

# 保存AI分析结果
with open('./600711_AI分析报告.md', 'w', encoding='utf-8') as f:
    f.write(analysis_text)

print("✅ AI分析完成！\n")
print("=" * 80)
print(analysis_text)
print("=" * 80)
print(f"\n分析结果已保存到：600711_AI分析报告.md")

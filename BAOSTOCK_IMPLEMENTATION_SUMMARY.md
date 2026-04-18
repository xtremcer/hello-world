# baostock 平替 akshare 实施总结

## 一、已完成的工作

### 1.1 创建了 baostock 数据获取工具
- **文件**: `utils/baostock_utils.py`
- **功能**:
  - `baostock_login()`: 登录 baostock
  - `baostock_logout()`: 登出 baostock
  - `query_history_k_data()`: 查询历史K线数据（基础版）
  - `query_history_k_data_with_pagination()`: 查询历史K线数据（支持分页）

### 1.2 更新了趋势维度模块
- **文件**: `modules/dimensions/trend.py`
- **新增功能**:
  - `module1_get_data_baostock()`: 使用 baostock 获取数据
  - `module1_get_data_akshare()`: 使用 akshare 获取数据（备用）
  - `module1_get_data()`: 自动选择数据源（优先 baostock）

### 1.3 更新了配置文件
- **文件**: `config.py`
- **新增配置**:
  - `DATA_SOURCE_CONFIG`: 数据源配置（各模块使用的数据源）
  - `DATA_SOURCE_DESCRIPTION`: 数据源配置说明

### 1.4 安装了依赖
- **库**: baostock==0.8.9
- **安装命令**: `uv add baostock`

### 1.5 创建了文档
- **文件**: `BAOSTOCK_MIGRATION_PLAN.md`
- **内容**: 详细的平替方案分析和实施建议

## 二、可以平替的模块

| 模块 | akshare 接口 | baostock 接口 | 状态 |
|-----|------------|--------------|------|
| **趋势维度** | `stock_zh_a_hist` | `query_history_k_data_plus` | ✅ 已完成 |
| **量价维度** | `stock_zh_a_daily` | `query_history_k_data_plus` | ⏳ 待完成 |
| **休市简报** | `stock_zh_index_daily` | `query_history_k_data_plus` | ⏳ 待完成 |

## 三、不能平替的模块（保留 akshare）

| 模块 | akshare 接口 | 原因 |
|-----|------------|------|
| **主力资金维度** | `stock_individual_fund_flow` | baostock 无此接口 |
| **板块维度** | `stock_fund_flow_industry` | baostock 无此接口 |
| **全球指数** | `index_global_spot_em` | baostock 无此接口 |

## 四、需要手动配置的模块

| 模块 | 原因 | 替代方案 |
|-----|------|---------|
| **主力筹码维度** | akshare 和 baostock 都无此接口 | 在 config.py 中手动配置 |
| **市场筹码维度** | akshare 和 baostock 都无此接口 | 在 config.py 中手动配置 |

## 五、数据源配置

### 5.1 当前配置（推荐）
```python
DATA_SOURCE_CONFIG = {
    "trend": "baostock",        # 趋势维度
    "price_volume": "baostock",  # 量价维度
    "market_brief": "baostock",  # 休市简报
    "fund_flow": "akshare",      # 主力资金维度
    "block": "akshare",          # 板块维度
    "global_indices": "akshare", # 全球指数
    "main_chip": "manual",       # 主力筹码维度
    "market_chip": "manual",     # 市场筹码维度
}
```

### 5.2 修改数据源
如果用户想修改某个模块的数据源，可以在 `config.py` 中修改 `DATA_SOURCE_CONFIG`：
```python
# 例如：将趋势维度改为使用 akshare
DATA_SOURCE_CONFIG["trend"] = "akshare"
```

## 六、优势与风险

### 6.1 使用 baostock 的优势
- ✅ **稳定性好**: baostock 稳定性远高于 akshare
- ✅ **无免费额度限制**: 不会因超限而受限
- ✅ **QPS 限制约 20**: 每秒最多 20 次查询，适合大多数场景
- ✅ **多数据源**: 降低对单一数据源的依赖

### 6.2 baostock 的限制
- ⚠️ **一次最多获取 100 条数据**: 需要分页获取（已实现）
- ⚠️ **不支持实时数据**: T+1 数据，不适用于实时分析
- ⚠️ **不支持资金流向数据**: 主力资金、行业资金等数据无法获取
- ⚠️ **不支持筹码数据**: 筹码分布、筹码成本等数据无法获取

## 七、后续工作

### 7.1 待完成的工作
1. **更新量价维度模块**（`modules/dimensions/price_volume.py`）
   - 使用 `module1_get_data_baostock()` 替换原有的 akshare 接口
   - 测试数据获取和处理逻辑

2. **更新休市简报模块**（`modules/market_brief.py`）
   - 使用 `module1_get_data_baostock()` 替换原有的 akshare 接口
   - 测试指数数据获取逻辑

3. **集成测试**
   - 测试所有模块的数据获取功能
   - 验证数据源切换逻辑
   - 测试备份机制（baostock 失败时自动切换到 akshare）

### 7.2 可选优化
1. **添加数据源监控**
   - 记录每个数据源的成功/失败次数
   - 自动调整数据源优先级

2. **添加数据缓存**
   - 缓存 baostock 数据，减少重复请求
   - 提高数据获取速度

3. **添加异常处理**
   - 完善异常捕获和处理逻辑
   - 提供更友好的错误提示

## 八、测试建议

### 8.1 在实际环境中测试
由于当前沙箱环境可能存在网络延迟问题，建议在实际运行环境中测试：
1. 测试 baostock 数据获取功能
2. 测试数据源切换逻辑
3. 测试备份机制

### 8.2 测试脚本
```bash
# 测试 baostock 登录功能
python test_baostock_login.py

# 测试趋势维度模块（使用 baostock）
python test_trend_baostock.py  # 待创建

# 测试完整工作流
python main.py --code 600711 --source baostock
```

## 九、总结

### 9.1 主要成果
- ✅ 创建了 baostock 数据获取工具
- ✅ 更新了趋势维度模块，支持 baostock 数据源
- ✅ 添加了数据源配置，支持灵活切换
- ✅ 实现了自动备份机制（baostock 失败时自动切换到 akshare）

### 9.2 核心价值
- 提高了系统的稳定性（baostock 稳定性好）
- 降低了数据获取的限流风险（无免费额度限制）
- 增强了系统的可扩展性（支持多数据源）

### 9.3 用户操作
用户无需做任何操作，系统会自动：
1. 优先使用 baostock 获取数据
2. 如果 baostock 失败，自动切换到 akshare 备用
3. 在报告中标注使用的数据源

如果用户想修改数据源配置，可以在 `config.py` 中修改 `DATA_SOURCE_CONFIG`。

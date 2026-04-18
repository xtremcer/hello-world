"""
baostock 登录机制说明文档

## 测试结果总结

### baostock 登录方式
baostock 是**免费的公共数据接口**，**不需要账号密码登录**！

### 标准登录方法
```python
import baostock as bs

# 直接登录，无需账号密码
lg = bs.login()
if lg.error_code == '0':
    print("登录成功")
```

### 登录对象
- `lg.error_code`: 错误码（'0' 表示成功）
- `lg.error_msg`: 错误信息（'success' 表示成功）

### ❌ 不支持账号密码登录
```python
# 错误示例：baostock 不支持账号密码参数
lg = bs.login(username='xtremcer', password='Beinimadeshi@9')
# 报错：login() got an unexpected keyword argument 'username'
```

## baostock 优势

1. **完全免费**：不需要注册账号，不需要付费
2. **无额度限制**：每天可以获取任意数量的数据
3. **QPS 限制**：约每秒 20 次查询（已内置频率控制）
4. **数据覆盖**：A股、指数、ETF 等
5. **复权支持**：支持前复权、后复权、不复权

## 如果需要账号的数据源

如果你需要使用其他支持账号的数据源，可以考虑：

### 1. Tushare（推荐，有免费和付费版本）
```python
import tushare as ts

# 需要注册获取 token
ts.set_token('你的token')
pro = ts.pro_api()
```

### 2. 聚宽 JoinQuant（量化交易平台）
```python
from jqdatasdk import *

# 需要账号密码
auth('你的账号', '你的密码')
```

### 3. 优矿 Uqer（量化交易平台）
```python
from Uqer import *

# 需要账号密码
DataAPI.UserLogin('你的账号', '你的密码')
```

## 建议

### 如果你的需求是：
- 获取 A 股历史数据：baostock（推荐，免费）
- 获取实时行情：需要其他数据源
- 获取财务数据：baostock + Tushare（推荐）
- 获取主力资金：akshare + Tushare（推荐）

### 当前项目使用的数据源
1. **baostock**：趋势维度、量价维度（推荐，稳定）
2. **akshare**：主力资金、板块数据（备用）

## 结论

**baostock 不需要账号密码，直接使用 `bs.login()` 即可！**

如果你有其他数据源的账号（如 Tushare），我可以帮你集成到项目中。
"""

print(__doc__)

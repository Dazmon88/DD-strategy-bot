# StandX 网格交易策略教程

## 📋 简介

StandX 网格交易策略，自动执行做多做空订单管理，支持持仓自动平仓。

## 📊 策略逻辑

### 执行流程

1. **获取价格**: 获取当前 BTC-USD 价格
2. **生成网格**: 根据当前价格、价格间距和网格数量生成做多/做空网格数组
   - 做多数组：当前价格 - 价格间距 向下生成网格
   - 做空数组：当前价格 + 价格间距 向上生成网格
3. **查询订单**: 获取当前所有未成交订单
4. **计算撤单**: 找出不在目标网格中的订单
5. **执行撤单**: 批量撤销不需要的订单
6. **计算下单**: 找出目标网格中缺失的订单
7. **执行下单**: 为缺失的网格价格创建限价单
8. **检查持仓**: 如果检测到持仓，自动市价平仓
9. **循环执行**: 等待指定时间后重复上述流程

## ⚠️ 风险提示

### 主要风险

1. **市场风险**
   - 价格剧烈波动可能导致订单快速成交
   - 单边行情可能导致大量订单同时成交
   - 极端行情可能导致滑点损失

2. **技术风险**
   - 网络中断可能导致策略停止运行
   - API 限制可能导致订单失败
   - 程序错误可能导致异常交易

3. **资金风险**
   - 网格策略需要足够的资金支持
   - 订单数量过多可能导致资金分散
   - 持仓平仓可能产生额外损失

4. **操作风险**
   - 配置错误可能导致意外交易
   - 私钥泄露可能导致资金损失
   - 策略参数不当可能导致亏损

### 使用建议

- ✅ 先用小额资金测试策略
- ✅ 充分理解策略逻辑后再使用
- ✅ 定期检查策略运行状态
- ✅ 设置合理的网格参数
- ✅ 确保网络连接稳定
- ❌ 不要使用全部资金
- ❌ 不要在不理解的情况下使用
- ❌ 不要忽略风险提示

### 免责声明

**本策略仅供学习和研究使用。使用本策略进行交易的所有风险由使用者自行承担。作者不对任何交易损失负责。**

## 🔧 环境要求

- Python 3.9 或更高版本
- StandX 账户和私钥

## 📦 安装步骤

### Linux / Mac

```bash
# 1. 进入项目根目录
cd /path/to/DD-strategy-bot

# 2. 创建虚拟环境（推荐）
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt
```

### Windows

```powershell
# 1. 进入项目根目录
cd C:\path\to\DD-strategy-bot

# 2. 创建虚拟环境（推荐）
python -m venv venv

# 3. 激活虚拟环境
venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt
```

## ⚙️ 配置

编辑 `config.yaml` 文件：

```yaml
exchange:
  exchange_name: standx
  private_key: "你的私钥"  # 替换为你的 StandX 私钥
  chain: bsc              # 或 "solana"

symbol: BTC-USD          # 交易对

grid:
  upper_price: 200000    # 价格上限
  lower_price: 60000     # 价格下限
  price_step: 5          # 价格步长
  grid_count: 5          # 网格数量
  price_spread: 50       # 价格间距
  order_quantity: 0.0001 # 每单数量
  sleep_interval: 1      # 循环间隔（秒）
```

### 参数说明

- `price_step`: 网格价格间隔
- `grid_count`: 每个方向的网格数量
- `price_spread`: 当前价格与网格中心的距离
- `order_quantity`: 每个订单的交易数量
- `sleep_interval`: 策略循环间隔时间（秒）

## 🚀 运行策略

### Linux / Mac

```bash
# 确保在虚拟环境中
source venv/bin/activate

# 进入策略目录
cd strategys/strategy_standx

# 运行策略
python standx_mm.py
```

### Windows

```powershell
# 确保在虚拟环境中
venv\Scripts\activate

# 进入策略目录
cd strategys\strategy_standx

# 运行策略
python standx_mm.py
```

## 🛑 停止策略

按 `Ctrl + C` 停止策略运行

## ⚠️ 注意事项

- 确保私钥安全，不要泄露
- 建议先用小额资金测试
- 策略会持续运行，直到手动停止
- 注意网络连接稳定性
- 建议在 VPS 或服务器上运行

## 🔗 相关链接

- [StandX 官网](https://standx.com)
- [项目主 README](../README.md)

---

**作者**: [@ddazmon](https://twitter.com/ddazmon)  
**免责声明**: 本策略仅供学习使用，交易有风险，使用需谨慎。

#!/usr/bin/env python3
"""
StandX 策略脚本 - 获取 BTC 价格
"""
import sys
import os
import yaml
import time
from decimal import Decimal

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from adapters import create_adapter

config_path = os.path.join(current_dir, "config.yaml")

with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

STANDX_CONFIG = config['exchange']
SYMBOL = config['symbol']
GRID_CONFIG = config['grid']


def generate_grid_arrays(current_price, price_step, grid_count, price_spread):
    """根据当前价格和价格间距生成做多数组和做空数组"""
    if price_step <= 0:
        raise ValueError("price_step 必须大于 0")
    if grid_count < 0:
        raise ValueError("grid_count 必须大于等于 0")
    if price_spread < 0:
        raise ValueError("price_spread 必须大于等于 0")
    
    # 计算 bid 和 ask 价格
    bid_price = current_price - price_spread
    ask_price = current_price + price_spread
    
    # 将 bid 价格向下取整到最近的 price_step 倍数
    bid_base = int(bid_price / price_step) * price_step
    
    # 将 ask 价格向上取整到最近的 price_step 倍数
    ask_base = int((ask_price + price_step - 1) / price_step) * price_step
    
    # 做多数组：从 bid_base 向下 grid_count 个（包括 bid_base）
    long_grid = []
    for i in range(grid_count):
        price = bid_base - i * price_step
        long_grid.append(price)
    long_grid = sorted(long_grid)
    
    # 做空数组：从 ask_base 向上 grid_count 个（包括 ask_base）
    short_grid = []
    for i in range(grid_count):
        price = ask_base + i * price_step
        short_grid.append(price)
    short_grid = sorted(short_grid)
    
    return long_grid, short_grid


def get_pending_orders_arrays(adapter, symbol):
    """获取当前账号未成交订单数组，按做多和做空分类，同时返回价格到订单ID的映射
    
    Returns:
        (long_prices, short_prices, long_price_to_ids, short_price_to_ids):
        - long_prices: 做多价格数组
        - short_prices: 做空价格数组
        - long_price_to_ids: 做多价格到订单ID列表的字典映射
        - short_price_to_ids: 做空价格到订单ID列表的字典映射
    """
    try:
        open_orders = adapter.get_open_orders(symbol=symbol)
        
        # 做多订单：side 为 "buy" 或 "long"
        long_prices = []
        long_price_to_ids = {}  # 价格 -> 订单ID列表
        # 做空订单：side 为 "sell" 或 "short"
        short_prices = []
        short_price_to_ids = {}  # 价格 -> 订单ID列表
        
        for order in open_orders:
            # 只处理未成交的订单（状态为 pending, open, partially_filled）
            if order.status in ["pending", "open", "partially_filled"]:
                if order.price is not None:
                    price = int(float(order.price))
                    try:
                        order_id = int(order.order_id)
                    except (ValueError, TypeError):
                        continue  # 跳过无效的订单ID
                    
                    if order.side in ["buy", "long"]:
                        if price not in long_prices:
                            long_prices.append(price)
                        if price not in long_price_to_ids:
                            long_price_to_ids[price] = []
                        long_price_to_ids[price].append(order_id)
                    elif order.side in ["sell", "short"]:
                        if price not in short_prices:
                            short_prices.append(price)
                        if price not in short_price_to_ids:
                            short_price_to_ids[price] = []
                        short_price_to_ids[price].append(order_id)
        
        return sorted(long_prices), sorted(short_prices), long_price_to_ids, short_price_to_ids
    except NotImplementedError:
        # 如果适配器未实现，返回空数组
        return [], [], {}, {}
    except Exception as e:
        print(f"获取未成交订单失败: {e}")
        return [], [], {}, {}


def cancel_orders_by_prices(cancel_long, cancel_short, long_price_to_ids, short_price_to_ids, adapter):
    """根据价格列表撤单
    
    Args:
        cancel_long: 需要撤单的做多价格列表
        cancel_short: 需要撤单的做空价格列表
        long_price_to_ids: 做多价格到订单ID列表的字典映射
        short_price_to_ids: 做空价格到订单ID列表的字典映射
        adapter: 适配器实例
    """
    if not cancel_long and not cancel_short:
        return
    
    # 根据价格映射获取订单ID
    all_order_ids = []
    for price in cancel_long:
        if price in long_price_to_ids:
            all_order_ids.extend(long_price_to_ids[price])
    for price in cancel_short:
        if price in short_price_to_ids:
            all_order_ids.extend(short_price_to_ids[price])
    
    if not all_order_ids:
        return
    
    # 批量撤单
    try:
        if hasattr(adapter, 'cancel_orders_by_ids'):
            adapter.cancel_orders_by_ids(order_id_list=all_order_ids)
        else:
            # 如果适配器没有批量撤单方法，逐个撤单
            for order_id in all_order_ids:
                try:
                    adapter.cancel_order(order_id=str(order_id))
                except:
                    pass
    except:
        pass


def place_orders_by_prices(place_long, place_short, adapter, symbol, quantity):
    """根据价格列表下单
    
    Args:
        place_long: 需要下单的做多价格列表
        place_short: 需要下单的做空价格列表
        adapter: 适配器实例
        symbol: 交易对符号
        quantity: 订单数量
    """
    if not place_long and not place_short:
        return
    
    quantity_decimal = Decimal(str(quantity))
    
    # 做多订单：buy
    for price in place_long:
        try:
            order = adapter.place_order(
                symbol=symbol,
                side="buy",
                order_type="limit",
                quantity=quantity_decimal,
                price=Decimal(str(price)),
                time_in_force="gtc",
                reduce_only=False
            )
            print(f"[下单成功][多单] 价格={price}, 数量={quantity_decimal}, 订单ID={getattr(order, 'order_id', None)}")
        except Exception as e:
            print(f"[下单失败][多单] 价格={price}, 数量={quantity_decimal}, 错误={e}")
    
    # 做空订单：sell
    for price in place_short:
        try:
            order = adapter.place_order(
                symbol=symbol,
                side="sell",
                order_type="limit",
                quantity=quantity_decimal,
                price=Decimal(str(price)),
                time_in_force="gtc",
                reduce_only=False
            )
            print(f"[下单成功][空单] 价格={price}, 数量={quantity_decimal}, 订单ID={getattr(order, 'order_id', None)}")
        except Exception as e:
            print(f"[下单失败][空单] 价格={price}, 数量={quantity_decimal}, 错误={e}")


def calculate_cancel_orders(target_long, target_short, current_long, current_short):
    """计算需要撤单的多空数组
    
    Args:
        target_long: 目标做多数组（应该存在的订单价格）
        target_short: 目标做空数组（应该存在的订单价格）
        current_long: 当前做多数组（实际存在的订单价格）
        current_short: 当前做空数组（实际存在的订单价格）
    
    Returns:
        (cancel_long, cancel_short): 需要撤单的做多数组和做空数组
    """
    # 将目标数组转换为集合，便于查找
    target_long_set = set(target_long)
    target_short_set = set(target_short)
    
    # 撤单做多数组：在当前做多数组中，但不在目标做多数组中的价格
    cancel_long = [price for price in current_long if price not in target_long_set]
    
    # 撤单做空数组：在当前做空数组中，但不在目标做空数组中的价格
    cancel_short = [price for price in current_short if price not in target_short_set]
    
    return sorted(cancel_long), sorted(cancel_short)


def calculate_place_orders(target_long, target_short, current_long, current_short):
    """计算需要下单的多空数组
    
    Args:
        target_long: 目标做多数组（应该存在的订单价格）
        target_short: 目标做空数组（应该存在的订单价格）
        current_long: 当前做多数组（实际存在的订单价格）
        current_short: 当前做空数组（实际存在的订单价格）
    
    Returns:
        (place_long, place_short): 需要下单的做多数组和做空数组
    """
    # 将当前数组转换为集合，便于查找
    current_long_set = set(current_long)
    current_short_set = set(current_short)
    
    # 下单做多数组：在目标做多数组中，但不在当前做多数组中的价格
    place_long = [price for price in target_long if price not in current_long_set]
    
    # 下单做空数组：在目标做空数组中，但不在当前做空数组中的价格
    place_short = [price for price in target_short if price not in current_short_set]
    
    return sorted(place_long), sorted(place_short)


def close_position_if_exists(adapter, symbol):
    """检查持仓，如果有持仓则市价平仓
    
    在平仓之前，会先取消所有未成交订单以释放保证金，然后尝试平仓。
    如果平仓失败，会重试直到持仓被关闭。
    
    注意: StandX 适配器的持仓查询接口可能未实现，此功能可能无法使用
    
    Args:
        adapter: 适配器实例
        symbol: 交易对符号
    
    Returns:
        bool: 如果成功关闭持仓或没有持仓，返回 True；如果无法关闭持仓，返回 False
    """
    try:
        position = adapter.get_position(symbol)
        if position and position.size != Decimal("0"):
            print(f"检测到持仓: {position.size} {position.side}, 开始平仓流程...")
            
            # Step 1: 取消所有未成交订单以释放保证金
            print("步骤 1: 取消所有未成交订单以释放保证金...")
            try:
                # 优先使用 cancel_all_orders 方法（如果可用）
                if hasattr(adapter, 'cancel_all_orders'):
                    try:
                        adapter.cancel_all_orders(symbol=symbol)
                        print("已取消所有未成交订单")
                    except Exception as e:
                        print(f"使用 cancel_all_orders 失败: {e}，尝试逐个取消...")
                        # 回退到逐个取消
                        open_orders = adapter.get_open_orders(symbol=symbol)
                        if open_orders:
                            print(f"发现 {len(open_orders)} 个未成交订单，正在逐个取消...")
                            order_ids = []
                            for order in open_orders:
                                try:
                                    order_id = int(order.order_id)
                                    order_ids.append(order_id)
                                except (ValueError, TypeError):
                                    # 如果订单ID不是整数，尝试使用客户端订单ID
                                    if order.client_order_id:
                                        try:
                                            adapter.cancel_order(client_order_id=order.client_order_id, symbol=symbol)
                                        except:
                                            pass
                            
                            # 批量取消订单
                            if order_ids:
                                try:
                                    if hasattr(adapter, 'cancel_orders_by_ids'):
                                        adapter.cancel_orders_by_ids(order_id_list=order_ids)
                                        print(f"已取消 {len(order_ids)} 个订单")
                                    else:
                                        # 如果没有批量撤单方法，逐个撤单
                                        for order_id in order_ids:
                                            try:
                                                adapter.cancel_order(order_id=str(order_id), symbol=symbol)
                                            except:
                                                pass
                                        print(f"已尝试取消 {len(order_ids)} 个订单")
                                except Exception as e:
                                    print(f"取消订单时出错: {e}")
                else:
                    # 如果没有 cancel_all_orders 方法，手动获取并取消
                    open_orders = adapter.get_open_orders(symbol=symbol)
                    if open_orders:
                        print(f"发现 {len(open_orders)} 个未成交订单，正在取消...")
                        order_ids = []
                        for order in open_orders:
                            try:
                                order_id = int(order.order_id)
                                order_ids.append(order_id)
                            except (ValueError, TypeError):
                                if order.client_order_id:
                                    try:
                                        adapter.cancel_order(client_order_id=order.client_order_id, symbol=symbol)
                                    except:
                                        pass
                        
                        if order_ids:
                            try:
                                if hasattr(adapter, 'cancel_orders_by_ids'):
                                    adapter.cancel_orders_by_ids(order_id_list=order_ids)
                                    print(f"已取消 {len(order_ids)} 个订单")
                                else:
                                    for order_id in order_ids:
                                        try:
                                            adapter.cancel_order(order_id=str(order_id), symbol=symbol)
                                        except:
                                            pass
                                    print(f"已尝试取消 {len(order_ids)} 个订单")
                            except Exception as e:
                                print(f"取消订单时出错: {e}")
                    else:
                        print("没有未成交订单")
            except Exception as e:
                print(f"获取或取消订单时出错: {e}")
            
            # Step 2: 等待一小段时间让订单取消生效
            time.sleep(1)
            
            # Step 3: 尝试平仓
            print("步骤 2: 尝试市价平仓...")
            max_retries = 3
            retry_count = 0
            position_closed = False
            
            while retry_count < max_retries and not position_closed:
                try:
                    adapter.close_position(symbol, order_type="market")
                    print(f"平仓指令已发送 (尝试 {retry_count + 1}/{max_retries})")
                    
                    # Step 4: 等待并检查持仓是否已关闭
                    time.sleep(2)  # 等待平仓执行
                    
                    # 检查持仓状态
                    try:
                        updated_position = adapter.get_position(symbol)
                        if updated_position is None or updated_position.size == Decimal("0"):
                            position_closed = True
                            print("✓ 持仓已成功关闭")
                        else:
                            print(f"持仓仍存在: {updated_position.size} {updated_position.side}, 重试中...")
                            retry_count += 1
                            if retry_count < max_retries:
                                time.sleep(2)  # 等待后重试
                    except Exception as e:
                        # 如果无法查询持仓，假设平仓成功
                        print(f"无法验证持仓状态: {e}，假设平仓成功")
                        position_closed = True
                        
                except Exception as e:
                    print(f"平仓失败 (尝试 {retry_count + 1}/{max_retries}): {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(2)  # 等待后重试
            
            if not position_closed:
                print(f"⚠️ 警告: 经过 {max_retries} 次尝试后，持仓可能仍然存在")
                return False
            else:
                return True
        else:
            # 没有持仓
            return True
    except Exception as e:
        # 如果持仓查询失败，静默处理（StandX 可能没有持仓查询接口）
        # 但记录错误以便调试
        print(f"持仓查询失败: {e}")
        return True  # 假设没有持仓，继续运行


def run_strategy_cycle(adapter):
    """执行一次策略循环
    
    Args:
        adapter: 适配器实例
    """
    price_info = adapter.get_ticker(SYMBOL)
    last_price = price_info.get('last_price') or price_info.get('mid_price') or price_info.get('mark_price')
    print(f"{SYMBOL} 价格: {last_price:.2f}")
    
    long_grid, short_grid = generate_grid_arrays(
        last_price, 
        GRID_CONFIG['price_step'], 
        GRID_CONFIG['grid_count'],
        GRID_CONFIG['price_spread']
    )
    print(f"做多数组: {long_grid}")
    print(f"做空数组: {short_grid}")
    
    # 获取未成交订单数组和价格到订单ID的映射
    long_pending, short_pending, long_price_to_ids, short_price_to_ids = get_pending_orders_arrays(adapter, SYMBOL)
    print(f"当前做多数组: {long_pending}")
    print(f"当前做空数组: {short_pending}")
    
    # 计算需要撤单的数组
    cancel_long, cancel_short = calculate_cancel_orders(
        long_grid, short_grid, long_pending, short_pending
    )
    print(f"撤单做多数组: {cancel_long}")
    print(f"撤单做空数组: {cancel_short}")
    
    # 执行撤单
    cancel_orders_by_prices(
        cancel_long, cancel_short, long_price_to_ids, short_price_to_ids, adapter
    )
    
    # 计算需要下单的数组
    place_long, place_short = calculate_place_orders(
        long_grid, short_grid, long_pending, short_pending
    )
    print(f"下单做多数组: {place_long}")
    print(f"下单做空数组: {place_short}")
    
    # 执行下单
    place_orders_by_prices(
        place_long, place_short, adapter, SYMBOL, GRID_CONFIG.get('order_quantity', 0.001)
    )
    # 检查持仓，如果有持仓则市价平仓
    # 在平仓之前会先取消所有订单以释放保证金
    position_closed = close_position_if_exists(adapter, SYMBOL)
    
    # 如果持仓未能关闭，等待一段时间后重试
    if not position_closed:
        print("⚠️ 持仓关闭失败，等待 5 秒后重试...")
        time.sleep(5)
        position_closed = close_position_if_exists(adapter, SYMBOL)
        if not position_closed:
            print("⚠️ 持仓仍然存在，但继续运行策略循环...")


def main():
    try:
        adapter = create_adapter(STANDX_CONFIG)
        adapter.connect()
        
        sleep_interval = GRID_CONFIG.get('sleep_interval', 60)
        
        print("策略开始运行，按 Ctrl+C 停止...")
        print(f"休眠间隔: {sleep_interval} 秒\n")
        
        while True:
            try:
                run_strategy_cycle(adapter)
                print(f"\n等待 {sleep_interval} 秒后继续...\n")
                time.sleep(sleep_interval)
            except KeyboardInterrupt:
                print("\n\n策略已停止")
                break
            except Exception as e:
                print(f"策略循环错误: {e}")
                print(f"等待 {sleep_interval} 秒后重试...\n")
                time.sleep(sleep_interval)
        
    except Exception as e:
        print(f"错误: {e}")
        return None


if __name__ == "__main__":
    main()

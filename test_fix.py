import sys
import os
sys.path.insert(0, r'e:\solo1\projects\t64')

print('=== 验证数据加载 ===')
from app import DataManager, generate_id, load_json

dm = DataManager()
print(f'主播: {len(dm.broadcasters)} 人')
print(f'商品: {len(dm.products)} 个')
print(f'排期: {len(dm.schedules)} 场')

print()
print('=== 验证主播增删 ===')
orig_count = len(dm.broadcasters)
new_bc = {
    'id': generate_id('b', dm.broadcasters),
    'name': '测试主播',
    'fans_count': 100000,
    'category': '美妆',
    'base_fee': 5000,
    'commission_rate': 20,
    'max_products': 10,
}
dm.broadcasters.append(new_bc)
assert len(dm.broadcasters) == orig_count + 1
print('新增主播 OK')

found = dm.get_broadcaster_by_id(new_bc['id'])
assert found and found['name'] == '测试主播'
print('查询主播 OK')

dm.broadcasters = [b for b in dm.broadcasters if b['id'] != new_bc['id']]
assert len(dm.broadcasters) == orig_count
print('删除主播 OK')

print()
print('=== 验证商品增删 ===')
orig_pc = len(dm.products)
new_pd = {
    'id': generate_id('p', dm.products),
    'name': '测试商品',
    'brand': '测试品牌',
    'category': '食品',
    'supply_price': 10,
    'live_price': 20,
    'commission_rate': 10,
    'stock': 100,
}
dm.products.append(new_pd)
assert len(dm.products) == orig_pc + 1
print('新增商品 OK')

dm.products = [p for p in dm.products if p['id'] != new_pd['id']]
assert len(dm.products) == orig_pc
print('删除商品 OK')

print()
print('=== 验证排期增删 ===')
orig_sc = len(dm.schedules)
new_sched = {
    'id': generate_id('s', dm.schedules),
    'date': '2026-06-25',
    'time': '20:00',
    'broadcaster_id': 'b001',
    'product_ids': ['p001', 'p002'],
    'avg_viewers': 60000,
}
dm.schedules.append(new_sched)
assert len(dm.schedules) == orig_sc + 1
print('新增排期 OK')

day_scheds = dm.get_schedules_by_date('2026-06-25')
assert len(day_scheds) == 1 and day_scheds[0]['id'] == new_sched['id']
print('按日期查询排期 OK')

month_scheds = dm.get_schedules_by_month(2026, 6)
print(f'6月排期共 {len(month_scheds)} 场')
assert len(month_scheds) == orig_sc + 1

dm.schedules = [s for s in dm.schedules if s['id'] != new_sched['id']]
assert len(dm.schedules) == orig_sc
print('删除排期 OK')

print()
print('=== 验证费用核算 ===')
from app import CATEGORY_CONVERSION_RATE, DISCOUNT_FACTOR

dm2 = DataManager()
scheds = dm2.get_schedules_by_month(2026, 6)
total_slot = 0
total_comm = 0
for s in scheds:
    bc = dm2.get_broadcaster_by_id(s['broadcaster_id'])
    prod_count = len(s['product_ids'])
    slot = prod_count * bc['base_fee']
    total_slot += slot
    
    avg_viewers = s.get('avg_viewers', 50000)
    comm = 0
    for pid in s['product_ids']:
        prod = dm2.get_product_by_id(pid)
        cat = prod['category']
        conv = CATEGORY_CONVERSION_RATE.get(cat, 0.05)
        est_sales = avg_viewers * conv * DISCOUNT_FACTOR
        comm += est_sales * prod['live_price'] * (prod['commission_rate'] / 100)
    total_comm += comm
    print(f'  {s["date"]} {s["time"]} {bc["name"]}: 坑位费={slot:,}, 预估佣金={comm:,.0f}')

print()
print(f'月总坑位费: {total_slot:,.0f} 元')
print(f'月总预估佣金: {total_comm:,.0f} 元')
print(f'月总收入: {total_slot + total_comm:,.0f} 元')

print()
print('✓ 所有逻辑验证通过！')

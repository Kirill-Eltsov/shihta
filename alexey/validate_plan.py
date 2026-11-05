"""Independent assignment/resource validator. Synthetic contract, tonnes."""
from collections import Counter
from math import isfinite


def validate_plan(case, plan, atol=1e-8, rtol=1e-9):
    errors = []
    orders, recipes, stocks = case['orders'], case['recipes'], case['stocks']
    counts = Counter(row['order_id'] for row in plan)
    for oid in orders:
        if counts[oid] != 1:
            errors.append(f'order_count:{oid}:{counts[oid]}')
    used = {c: 0.0 for c in stocks}
    for row in plan:
        oid, rid = row['order_id'], row['recipe_id']
        if oid not in orders:
            errors.append(f'unknown_order:{oid}')
            continue
        if rid not in orders[oid]['candidates'] or rid not in recipes:
            errors.append(f'forbidden_recipe:{oid}:{rid}')
            continue
        demand = orders[oid]['demand_t']
        if not isfinite(demand) or demand <= 0:
            raise ValueError('demand_t must be finite and positive')
        for c, a in recipes[rid]['usage_t_per_t'].items():
            if not isfinite(a) or a < 0:
                raise ValueError('Invalid usage coefficient')
            if c not in stocks:
                errors.append(f'missing_stock:{c}')
                continue
            used[c] += demand * a
    for c, stock in stocks.items():
        if not isfinite(stock) or stock < 0:
            raise ValueError('Invalid stock')
        if used[c] > stock + atol + rtol * abs(stock):
            errors.append(f'stock_exceeded:{c}')
    return {'valid': not errors, 'errors': errors, 'used_t': used,
            'remaining_t': {c: stocks[c] - used[c] for c in stocks}}

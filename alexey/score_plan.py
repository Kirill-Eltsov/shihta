"""Objective recomputed with explicit q; never reads notebook global quality."""
from math import fsum, isfinite
from validate_plan import validate_plan


def score_plan(case, plan, q):
    check = validate_plan(case, plan)
    if not check['valid']:
        raise ValueError('Invalid plan: ' + '; '.join(check['errors']))
    terms = []
    for row in plan:
        key = (row['order_id'], row['recipe_id'])
        value = q[key]
        if not isfinite(value):
            raise ValueError('Missing/nonfinite q')
        terms.append(case['orders'][key[0]]['demand_t'] * value)
    return fsum(terms)

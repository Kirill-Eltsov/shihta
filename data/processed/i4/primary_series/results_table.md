# Первичная серия I4_primary_series_v1_reference

- protocol: `I4-A-09 (draft after G3) / I4_reference_v1`
- scenarios_sha256: `4d6b9ee09651c418987e40e94c1810365afbe91bdc52f063b59c16e11375b8c2`
- config_id: `i4_resource_milp_v1_k09`
- git_commit: `ae16f63eb1fac73c93f0a1539e85d4bb48b8fea4`
- generated_at: `2026-11-25T11:17:31.977629+00:00`
- time_budget_s: `120.0`
- repetitions: `4`

## Сводная таблица (primary repetition)

| scenario | method | status | objective | plan | median_time_s | valid |
|----------|--------|--------|-----------|------|---------------|-------|
| base | resource_milp | optimal | 2.50 | H/L/L | 0.729556 | True |
| base | greedy_quality | feasible | 2.35 | L/L/H | 0.691178 | True |
| deficit | resource_milp | infeasible | null | — | 0.693129 | False |
| deficit | greedy_quality | no_solution_found | null | — | 0.682448 | False |
| changed_q | resource_milp | optimal | 2.35 | L/L/H | 0.695980 | True |
| changed_q | greedy_quality | feasible | 1.65 | H/L/L | 0.694137 | True |

## Доля допустимых планов по всем повторам

- planned_runs: 24
- recorded_runs: 24
- valid_plans: 16
- valid_plan_share: 0.6666666666666666

## Примечание

Набор экземпляров — учебный `I4_reference_v1` (base/deficit/changed_q).
Производственные экземпляры в серию не входят.
Сравнение целей внутри сценария; `deficit` без плана исключается из сравнения целей,
но учитывается в знаменателе доли допустимых.

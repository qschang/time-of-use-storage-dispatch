# 分时电价下的储能调度账本

修复 `/app/storage_dispatch.py`，根据本地 UTF-8 JSON 的电池参数、分时电价和逐时负荷记录，生成可审计的储能调度结果。

输入顶层必须恰好包含 `battery`、`tariff`、`steps`。电池字段为 `capacity_kWh`、`initial_soc`、`min_soc`、`max_soc`、`max_charge_kW`、`max_discharge_kW`、`charge_efficiency`、`discharge_efficiency`；数值必须有限，SOC 位于 `[0,1]` 且满足 `min_soc <= initial_soc <= max_soc`，效率在 `(0,1]`。`tariff` 恰好包含与步骤数相同的非负 `energy_rates` 和非负 `demand_rate`。`steps` 有 1 至 96 条，每条恰好包含正的 `duration_h`、非负 `load_kW` 和非负 `solar_kW`。

每个时段先计算净负荷 `load_kW - solar_kW`。电池可以充电或放电，但不能同时进行；充放电功率、SOC 上下界和效率均必须满足。电网功率为净负荷减放电功率加充电功率。逐时能量费使用电网功率乘持续时间和该时段费率，需量费使用全账期电网功率峰值乘 `demand_rate`。调度必须确定性，并在同一输入重跑时保持输出字节不变。

输出是紧凑 UTF-8 JSON，末尾只有一个 LF，顶层键顺序为 `steps`、`summary`。每个步骤输出 `index`、`grid_kW`、`charge_kW`、`discharge_kW`、`soc_end`、`energy_cost`；摘要输出 `energy_cost`、`demand_charge`、`total_cost`、`peak_grid_kW`、`final_soc`。数值误差不超过 `1e-9` 相对误差和 `1e-12` 绝对误差。

这是一个耦合的能源账本：SOC 状态约束、充放电效率与功率边界、分时电价和需量峰值、以及确定性序列化必须同时成立。任何输入校验、数值计算或发布失败都必须以非零状态拒收，并保持已有输出字节不变，不留下临时文件或部分结果。

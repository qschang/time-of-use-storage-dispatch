"""Independent reference implementation used only by the verifier author."""
from __future__ import annotations
import json, math, os, sys
from pathlib import Path

FIELDS = ("capacity_kWh", "initial_soc", "min_soc", "max_soc", "max_charge_kW", "max_discharge_kW", "charge_efficiency", "discharge_efficiency")

def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def reject(code):
    sys.stderr.write(f"运行拒收: {code}\n")
    raise SystemExit(1)

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result

def validate(doc):
    if not isinstance(doc, dict) or set(doc) != {"battery", "tariff", "steps"}:
        reject("BAD_INPUT")
    battery, tariff, steps = doc["battery"], doc["tariff"], doc["steps"]
    if not isinstance(battery, dict) or not isinstance(tariff, dict) or not isinstance(steps, list):
        reject("BAD_INPUT")
    if not 1 <= len(steps) <= 96:
        reject("BAD_INPUT")
    if any(name not in battery or not number(battery[name]) for name in FIELDS):
        reject("BAD_INPUT")
    if battery["capacity_kWh"] <= 0 or not (0 <= battery["min_soc"] <= battery["initial_soc"] <= battery["max_soc"] <= 1):
        reject("BAD_INPUT")
    if battery["max_charge_kW"] < 0 or battery["max_discharge_kW"] < 0:
        reject("BAD_INPUT")
    if not (0 < battery["charge_efficiency"] <= 1 and 0 < battery["discharge_efficiency"] <= 1):
        reject("BAD_INPUT")
    if set(tariff) != {"energy_rates", "demand_rate"} or not isinstance(tariff["energy_rates"], list):
        reject("BAD_INPUT")
    if len(tariff["energy_rates"]) != len(steps) or not number(tariff["demand_rate"]):
        reject("BAD_INPUT")
    if tariff["demand_rate"] < 0 or any(not number(rate) or rate < 0 for rate in tariff["energy_rates"]):
        reject("BAD_INPUT")
    for step in steps:
        if not isinstance(step, dict) or set(step) != {"duration_h", "load_kW", "solar_kW"}:
            reject("BAD_INPUT")
        if any(not number(step[name]) for name in step) or step["duration_h"] <= 0 or step["load_kW"] < 0 or step["solar_kW"] < 0:
            reject("BAD_INPUT")
    return battery, tariff, steps

def dispatch(battery, tariff, steps):
    soc = battery["initial_soc"]
    rows, energy, peak = [], 0.0, 0.0
    for index, step in enumerate(steps):
        duration = step["duration_h"]
        net = step["load_kW"] - step["solar_kW"]
        discharge_room = (soc - battery["min_soc"]) * battery["capacity_kWh"] * battery["discharge_efficiency"] / duration
        discharge = min(max(net, 0.0), battery["max_discharge_kW"], max(discharge_room, 0.0))
        charge_room = (battery["max_soc"] - soc) * battery["capacity_kWh"] / (battery["charge_efficiency"] * duration)
        charge = min(max(-net, 0.0), battery["max_charge_kW"], max(charge_room, 0.0))
        grid = net - discharge + charge
        soc += (charge * battery["charge_efficiency"] - discharge / battery["discharge_efficiency"]) * duration / battery["capacity_kWh"]
        cost = grid * duration * tariff["energy_rates"][index]
        energy += cost
        peak = max(peak, grid)
        rows.append({"index": index, "grid_kW": round(grid, 10), "charge_kW": round(charge, 10), "discharge_kW": round(discharge, 10), "soc_end": round(soc, 10), "energy_cost": round(cost, 10)})
    summary = {"energy_cost": round(energy, 10), "demand_charge": round(peak * tariff["demand_rate"], 10), "total_cost": round(energy + peak * tariff["demand_rate"], 10), "peak_grid_kW": round(peak, 10), "final_soc": round(soc, 10)}
    return {"steps": rows, "summary": summary}

def main():
    if len(sys.argv) != 3:
        reject("BAD_INPUT")
    input_path, output_path = map(Path, sys.argv[1:])
    try:
        document = json.loads(input_path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)
        result = dispatch(*validate(document))
        temporary = output_path.with_name("." + output_path.name + ".tmp")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        os.replace(temporary, output_path)
    except SystemExit:
        raise
    except OSError:
        reject("IO_FAILURE")
    except (ValueError, TypeError, json.JSONDecodeError):
        reject("BAD_INPUT")

if __name__ == "__main__":
    main()

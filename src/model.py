"""Unit economics of four carbon removal pathways for Indian smallholder projects.

Every input comes from data/inputs.csv as a (low, base, high) triple with its source.
All results are model outputs built on those inputs, not observed project results.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACRES_PER_HA = 2.47105
CO2_PER_C = 44.0 / 12.0
PATHWAYS = ["biochar", "erw", "arr", "soil"]
LABELS = {
    "biochar": "Biochar (cotton stalk)",
    "erw": "Enhanced rock weathering",
    "arr": "Agroforestry (ARR)",
    "soil": "Regen-ag soil carbon",
}


def load_inputs(path: Path | None = None) -> dict[str, dict]:
    path = path or ROOT / "data" / "inputs.csv"
    rows = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k in ("low", "base", "high"):
                r[k] = float(r[k])
            if not r["low"] <= r["base"] <= r["high"]:
                raise ValueError(f"{r['id']}: need low <= base <= high")
            rows[r["id"]] = r
    return rows


def scenario(inputs: dict[str, dict], which: str = "base") -> dict[str, float]:
    return {k: v[which] for k, v in inputs.items()}


def pv_factor(delay_years: float, rate: float) -> float:
    """Value today of 1 USD of credit revenue that arrives after `delay_years`."""
    return (1.0 + rate) ** (-delay_years)


def evaluate(p: dict[str, float]) -> dict[str, dict[str, float]]:
    """Per-acre and per-tonne economics for each pathway under one set of inputs."""
    out: dict[str, dict[str, float]] = {}
    fx, r = p["fx"], p["r"]

    # Biochar: stalk from one acre -> biochar -> durable tCO2e
    stalk_acre = p["stalk_ha"] / ACRES_PER_HA
    biochar_acre = stalk_acre * p["yield_biochar"]
    co2e_per_t_biochar = p["carbon_biochar"] * CO2_PER_C * p["perm_biochar"]
    credited = biochar_acre * co2e_per_t_biochar
    margin_t = p["price_biochar"] - p["cost_biochar"]
    out["biochar"] = dict(
        credited_t_acre=credited,
        revenue_acre=credited * p["price_biochar"],
        margin_t=margin_t,
        margin_acre=credited * margin_t,
        margin_pct=margin_t / p["price_biochar"],
        co2e_per_t_biochar=co2e_per_t_biochar,
        biochar_t_acre=biochar_acre,
        pv=pv_factor(p["delay_biochar"], r),
        farmer_income_acre_inr=float("nan"),  # paid as a feedstock price inside delivery cost
    )

    # ERW: rock spread on farmland, developer bears the delivery cost
    credited = p["removal_erw"] * (1 - p["ded_erw"])
    margin_t = p["price_erw"] - p["cost_erw"]
    out["erw"] = dict(
        credited_t_acre=credited,
        revenue_acre=credited * p["price_erw"],
        margin_t=margin_t,
        margin_acre=credited * margin_t,
        margin_pct=margin_t / p["price_erw"],
        pv=pv_factor(p["delay_erw"], r),
        farmer_income_acre_inr=float("nan"),
    )

    # Nature-based: revenue shared with the farmer, developer pays MRV per acre
    for k in ("arr", "soil"):
        credited = p[f"removal_{k}"] * (1 - p[f"ded_{k}"])
        revenue = credited * p[f"price_{k}"]
        farmer = revenue * p["farmer_share"]
        dev = revenue - farmer - p["mrv_acre"]
        out[k] = dict(
            credited_t_acre=credited,
            revenue_acre=revenue,
            margin_t=dev / credited,
            margin_acre=dev,
            margin_pct=dev / revenue,
            pv=pv_factor(p[f"delay_{k}"], r),
            farmer_income_acre_inr=farmer * fx,
            farmer_income_acre_usd=farmer,
        )

    for k in PATHWAYS:
        o = out[k]
        o["pv_margin_acre"] = o["margin_acre"] * o["pv"]
        o["value_lost_to_wait"] = 1 - o["pv"]
    return out


def dose_check(p: dict[str, float]) -> dict[str, float]:
    """How a pot-trial dose compares with what one field's own stalks can supply."""
    soil_t_ha = p["depth"] * 10_000 * p["bd"]
    dose_t_ha = p["lab_dose"] * soil_t_ha
    supply_t_ha = p["stalk_ha"] * p["yield_biochar"]
    return dict(
        soil_t_ha=soil_t_ha,
        dose_t_ha=dose_t_ha,
        supply_t_ha_yr=supply_t_ha,
        years_of_own_stalk=dose_t_ha / supply_t_ha,
        dose_tco2e_ha=dose_t_ha * p["carbon_biochar"] * CO2_PER_C * p["perm_biochar"],
    )


def delay_cost(p: dict[str, float]) -> dict[str, float]:
    """Value of each AFOLU credit lost to India's slower registration (CEEW timelines)."""
    r = p["r"]
    india_median, roa_median = 796 / 365, 514 / 365
    india_q3, roa_q3 = 1689 / 365, 623 / 365
    return dict(
        pv_india_median=pv_factor(india_median, r),
        pv_roa_median=pv_factor(roa_median, r),
        pv_india_q3=pv_factor(india_q3, r),
        pv_roa_q3=pv_factor(roa_q3, r),
        loss_median=1 - pv_factor(india_median, r) / pv_factor(roa_median, r),
        loss_q3=1 - pv_factor(india_q3, r) / pv_factor(roa_q3, r),
    )


def breakeven_price_biochar(p: dict[str, float]) -> float:
    return p["cost_biochar"]


if __name__ == "__main__":
    import json

    inp = load_inputs()
    base = scenario(inp)
    print(json.dumps(evaluate(base), indent=2, default=float))
    print(json.dumps(dose_check(base), indent=2))
    print(json.dumps(delay_cost(base), indent=2))

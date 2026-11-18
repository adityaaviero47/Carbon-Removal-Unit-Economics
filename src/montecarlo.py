"""Uncertainty analysis: Monte Carlo over the (low, base, high) ranges and one-way tornado swings."""
from __future__ import annotations

import numpy as np

from model import PATHWAYS, evaluate, scenario

METRICS = ["margin_t", "margin_acre", "farmer_income_acre_inr", "revenue_acre"]


def draw(inputs: dict[str, dict], n: int, seed: int) -> dict[str, np.ndarray]:
    """Independent triangular draws (mode = base). Fixed inputs stay constant."""
    rng = np.random.default_rng(seed)
    d = {}
    for k, v in inputs.items():
        lo, mo, hi = v["low"], v["base"], v["high"]
        d[k] = np.full(n, mo) if hi == lo else rng.triangular(lo, mo, hi, n)
    return d


def run(inputs: dict[str, dict], n: int = 20_000, seed: int = 7) -> dict[str, dict]:
    d = draw(inputs, n, seed)
    res = evaluate(d)  # evaluate() is vectorised: numpy arrays pass straight through
    summary = {}
    for k in PATHWAYS:
        o = res[k]
        s = {
            "p_margin_positive": float(np.mean(o["margin_acre"] > 0)),
            "margin_t_p10_p50_p90": [float(x) for x in np.percentile(o["margin_t"], [10, 50, 90])],
            "margin_acre_p10_p50_p90": [float(x) for x in np.percentile(o["margin_acre"], [10, 50, 90])],
        }
        if k in ("arr", "soil"):
            s["farmer_inr_acre_p10_p50_p90"] = [
                float(x) for x in np.percentile(o["farmer_income_acre_inr"], [10, 50, 90])
            ]
        summary[k] = s
    return summary


def tornado(inputs: dict[str, dict], pathway: str, metric: str = "margin_acre") -> list[dict]:
    """Swing one input at a time from low to high, all others at base."""
    base = scenario(inputs)
    base_val = evaluate(base)[pathway][metric]
    rows = []
    for k, v in inputs.items():
        if v["low"] == v["high"]:
            continue
        vals = []
        for which in ("low", "high"):
            p = dict(base)
            p[k] = v[which]
            vals.append(evaluate(p)[pathway][metric])
        if abs(vals[1] - vals[0]) < 1e-12:
            continue
        rows.append(dict(input=k, label=v["parameter"], low=vals[0], high=vals[1],
                         swing=abs(vals[1] - vals[0]), base=base_val))
    return sorted(rows, key=lambda r: -r["swing"])

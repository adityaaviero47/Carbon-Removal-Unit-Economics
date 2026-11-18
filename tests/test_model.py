import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from model import delay_cost, dose_check, evaluate, load_inputs, pv_factor, scenario  # noqa: E402
from montecarlo import run, tornado  # noqa: E402

INP = load_inputs()
BASE = scenario(INP)


def test_inputs_are_ordered_and_sourced():
    for k, v in INP.items():
        assert v["low"] <= v["base"] <= v["high"], k
        if v["basis"] in ("sourced", "mixed"):
            assert v["source"], k


def test_biochar_carbon_chain():
    o = evaluate(BASE)["biochar"]
    assert math.isclose(o["co2e_per_t_biochar"], 0.70 * 44 / 12 * 0.85, rel_tol=1e-12)
    stalk_acre = 1.7 / 2.47105
    assert math.isclose(o["credited_t_acre"], stalk_acre * 0.25 * o["co2e_per_t_biochar"], rel_tol=1e-12)
    assert math.isclose(o["margin_t"], 150 - 143)


def test_nature_based_split_adds_up():
    for k in ("arr", "soil"):
        o = evaluate(BASE)[k]
        farmer_usd = o["farmer_income_acre_usd"]
        assert math.isclose(o["revenue_acre"], farmer_usd + o["margin_acre"] + BASE["mrv_acre"], rel_tol=1e-12)


def test_pv_factor():
    assert pv_factor(0, 0.12) == 1.0
    assert math.isclose(pv_factor(1, 0.12), 1 / 1.12)
    d = delay_cost(BASE)
    assert 0 < d["loss_median"] < d["loss_q3"] < 1


def test_dose_check():
    d = dose_check(BASE)
    assert math.isclose(d["dose_t_ha"], 0.02 * 0.15 * 10_000 * 1.4)
    assert d["years_of_own_stalk"] > 50


def test_monte_carlo_reproducible_and_vectorised():
    a, b = run(INP, n=2000, seed=1), run(INP, n=2000, seed=1)
    assert a == b
    for k in a:
        assert 0 <= a[k]["p_margin_positive"] <= 1
    v = evaluate({k: np.full(3, x) for k, x in BASE.items()})
    assert np.allclose(v["erw"]["margin_acre"], evaluate(BASE)["erw"]["margin_acre"])


def test_tornado_sorted():
    t = tornado(INP, "biochar")
    assert [r["swing"] for r in t] == sorted([r["swing"] for r in t], reverse=True)

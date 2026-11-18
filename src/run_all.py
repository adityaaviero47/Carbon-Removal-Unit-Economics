"""Runs the full analysis: base case, Monte Carlo, tornado, charts, Excel model, results tables."""
from __future__ import annotations

import csv
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from model import LABELS, PATHWAYS, ROOT, delay_cost, dose_check, evaluate, load_inputs, scenario  # noqa: E402
from montecarlo import run, tornado  # noqa: E402

RES, CH = ROOT / "results", ROOT / "charts"
COL = {"biochar": "#1F4E3D", "erw": "#7A6A53", "arr": "#5B8C3A", "soil": "#C08A2B"}


def r2(x):
    return None if x != x else round(float(x), 4)  # NaN -> None


def main() -> None:
    RES.mkdir(exist_ok=True)
    CH.mkdir(exist_ok=True)
    inp = load_inputs()
    base = scenario(inp)
    ev = evaluate(base)
    summary = {
        "base_case": {k: {m: r2(v) for m, v in ev[k].items()} for k in PATHWAYS},
        "dose_check": {k: r2(v) for k, v in dose_check(base).items()},
        "registration_delay": {k: r2(v) for k, v in delay_cost(base).items()},
        "monte_carlo": run(inp),
        "tornado": {k: tornado(inp, k)[:6] for k in ("biochar", "soil")},
    }
    (RES / "summary.json").write_text(json.dumps(summary, indent=2))

    with open(RES / "pathway_comparison.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pathway", "credited_tco2e_per_acre_yr", "price_usd_t", "revenue_usd_acre", "farmer_inr_acre",
                    "developer_margin_usd_acre", "developer_margin_usd_t", "years_to_first_issuance",
                    "pv_margin_usd_acre", "p_margin_positive"])
        for k in PATHWAYS:
            o = ev[k]
            w.writerow([LABELS[k], round(o["credited_t_acre"], 3), base[f"price_{k}"], round(o["revenue_acre"], 2),
                        "" if o["farmer_income_acre_inr"] != o["farmer_income_acre_inr"] else round(o["farmer_income_acre_inr"]),
                        round(o["margin_acre"], 2), round(o["margin_t"], 2), base[f"delay_{k}"],
                        round(o["pv_margin_acre"], 2), summary["monte_carlo"][k]["p_margin_positive"]])

    # Chart 1: revenue vs developer margin per acre
    fig, ax = plt.subplots(figsize=(8, 4.2))
    xs = range(len(PATHWAYS))
    ax.bar([x - 0.2 for x in xs], [ev[k]["revenue_acre"] for k in PATHWAYS], 0.4, color="#BFD3C1", label="Credit revenue")
    ax.bar([x + 0.2 for x in xs], [ev[k]["margin_acre"] for k in PATHWAYS], 0.4,
           color=[COL[k] for k in PATHWAYS], label="Developer margin")
    for x, k in zip(xs, PATHWAYS):
        ax.text(x + 0.2, ev[k]["margin_acre"] + 8, f"${ev[k]['margin_acre']:.0f}", ha="center", fontsize=9)
        ax.text(x - 0.2, ev[k]["revenue_acre"] + 8, f"${ev[k]['revenue_acre']:.0f}", ha="center", fontsize=9)
    ax.set_xticks(list(xs), [LABELS[k] for k in PATHWAYS], fontsize=9)
    ax.set_ylabel("USD per acre per year (base case)")
    ax.set_title("Revenue and developer margin per acre", loc="left", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(CH / "revenue_margin_per_acre.png", dpi=160)
    plt.close(fig)

    # Chart 2: tornado for biochar margin per acre
    t = tornado(inp, "biochar")[:6][::-1]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    b0 = t[0]["base"]
    for i, row in enumerate(t):
        lo, hi = sorted((row["low"], row["high"]))
        ax.barh(i, hi - lo, left=lo, color="#1F4E3D")
    lo_all = min(min(r["low"], r["high"]) for r in t); hi_all = max(max(r["low"], r["high"]) for r in t)
    pad = 0.08 * (hi_all - lo_all)
    ax.set_xlim(min(lo_all, 0) - pad, hi_all + pad)
    ax.axvline(b0, color="#999", lw=1)
    ax.axvline(0, color="#C0392B", lw=1, ls="--")
    ax.set_yticks(range(len(t)), [r["label"] for r in t], fontsize=9)
    ax.set_xlabel("Biochar developer margin, USD per acre per year (each input swung low to high)")
    ax.set_title("What moves biochar margin most", loc="left", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(CH / "biochar_tornado.png", dpi=160)
    plt.close(fig)

    # Chart 3: registration delay
    d = summary["registration_delay"]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    labs = ["India\nmedian", "Rest of Asia\nmedian", "India\n75th pct", "Rest of Asia\n75th pct"]
    vals = [d["pv_india_median"], d["pv_roa_median"], d["pv_india_q3"], d["pv_roa_q3"]]
    ax.bar(labs, vals, color=["#C08A2B", "#BFD3C1", "#C08A2B", "#BFD3C1"])
    for i, v in enumerate(vals):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Value today of USD 1 of first credit")
    ax.set_title("AFOLU registration delay erodes credit value (12% discount rate)", loc="left", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(CH / "registration_delay.png", dpi=160)
    plt.close(fig)

    from build_excel import build

    build(ROOT / "model" / "Carbon_Removal_Unit_Economics.xlsx")
    print(json.dumps({k: summary[k] for k in ("dose_check", "registration_delay", "monte_carlo")}, indent=1))


if __name__ == "__main__":
    main()

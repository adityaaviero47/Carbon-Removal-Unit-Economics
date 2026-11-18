"""Builds model/Carbon_Removal_Unit_Economics.xlsx: a live Excel model with formulas.

Every calculation cell is an Excel formula on named input cells, so a user can type an
override next to any input and the whole workbook updates. Monte Carlo results are
written as values (computed in Python) and labelled as such.
"""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.defined_name import DefinedName

from model import ROOT, load_inputs

FONT = "Arial"
BLUE = Font(name=FONT, color="0000FF")
BOLD = Font(name=FONT, bold=True)
HEAD = Font(name=FONT, bold=True, color="FFFFFF")
HFILL = PatternFill("solid", fgColor="1F4E3D")
YFILL = PatternFill("solid", fgColor="FFFF00")
NORM = Font(name=FONT)
GREEN = Font(name=FONT, color="008000")
THIN = Border(bottom=Side(style="thin", color="BBBBBB"))


def header(ws, row, values, widths=None):
    for j, v in enumerate(values, 1):
        c = ws.cell(row=row, column=j, value=v)
        c.font, c.fill = HEAD, HFILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[chr(64 + j)].width = w


def name(wb, nm, ref):
    wb.defined_names[nm] = DefinedName(nm, attr_text=ref)


def build(out: Path) -> None:
    inp = load_inputs()
    wb = Workbook()

    # ---- Read Me
    ws = wb.active
    ws.title = "Read Me"
    lines = [
        ("Carbon Removal Unit Economics: Biochar vs ERW vs Agroforestry vs Regen-Ag Soil Carbon", BOLD),
        ("Per-acre and per-tonne economics of four carbon removal pathways for Indian smallholder projects.", NORM),
        ("", NORM),
        ("How to use", BOLD),
        ("1. Inputs sheet: blue numbers are sourced or assumed inputs (low / base / high).", NORM),
        ("2. Type a value in the yellow Override column to test a scenario; Active = Override if filled, else Base.", NORM),
        ("3. Unit Economics, Dose Check and Registration Delay recalculate from the Active column.", NORM),
        ("4. Uncertainty sheet holds Monte Carlo results computed in Python (src/montecarlo.py); they do not recalculate.", NORM),
        ("", NORM),
        ("Colour code: blue = input, black = formula, green = link to another sheet, yellow = cell you may edit.", NORM),
        ("All results are model outputs on public data and stated assumptions, not observed project results.", NORM),
        ("ARR and soil margins are before tree planting and practice-change costs, which are not modelled.", NORM),
    ]
    for i, (t, f) in enumerate(lines, 1):
        ws.cell(row=i, column=1, value=t).font = f
    ws.column_dimensions["A"].width = 120

    # ---- Inputs
    ws = wb.create_sheet("Inputs")
    header(ws, 1, ["ID", "Pathway", "Input", "Unit", "Low", "Base", "High", "Override", "Active", "Basis", "Source"],
           [16, 10, 40, 24, 9, 9, 9, 10, 10, 11, 90])
    ws.freeze_panes = "A2"
    for i, (k, v) in enumerate(inp.items(), 2):
        ws.cell(row=i, column=1, value=k).font = NORM
        ws.cell(row=i, column=2, value=v["pathway"]).font = NORM
        ws.cell(row=i, column=3, value=v["parameter"]).font = NORM
        ws.cell(row=i, column=4, value=v["unit"]).font = NORM
        for j, s in zip((5, 6, 7), ("low", "base", "high")):
            c = ws.cell(row=i, column=j, value=v[s])
            c.font = BLUE
        ws.cell(row=i, column=8).fill = YFILL
        c = ws.cell(row=i, column=9, value=f'=IF(ISBLANK(H{i}),F{i},H{i})')
        c.font = NORM
        ws.cell(row=i, column=10, value=v["basis"]).font = NORM
        src = v["source"] + (f" | {v['url']}" if v["url"] else "")
        ws.cell(row=i, column=11, value=src).font = NORM
        fmt = "0.0%" if v["unit"].startswith("fraction") or v["unit"] == "per year" else "#,##0.00"
        for j in (5, 6, 7, 8, 9):
            ws.cell(row=i, column=j).number_format = fmt
        name(wb, f"in_{k}", f"Inputs!$I${i}")
    n_in = len(inp) + 1

    # ---- Unit Economics
    ws = wb.create_sheet("Unit Economics")
    header(ws, 1, ["Metric", "Biochar (cotton stalk)", "Enhanced rock weathering", "Agroforestry (ARR)",
                   "Regen-ag soil carbon", "Note"], [46, 20, 20, 20, 20, 70])
    acre = "2.47105"
    rows = [
        ("Credited tCO2e per acre per year",
         f"=in_stalk_ha/{acre}*in_yield_biochar*in_carbon_biochar*44/12*in_perm_biochar",
         "=in_removal_erw*(1-in_ded_erw)", "=in_removal_arr*(1-in_ded_arr)", "=in_removal_soil*(1-in_ded_soil)",
         "Biochar: own-field cotton stalk -> biochar -> durable carbon; others: removal after deductions", "0.00"),
        ("Credit price (USD/t)", "=in_price_biochar", "=in_price_erw", "=in_price_arr", "=in_price_soil", "", "$#,##0.00"),
        ("Credit revenue per acre (USD)", "=B2*B3", "=C2*C3", "=D2*D3", "=E2*E3", "", "$#,##0.00"),
        ("Farmer share of revenue", None, None, "=in_farmer_share", "=in_farmer_share",
         "Biochar and ERW: farmer paid inside delivery cost (feedstock or land access)", "0.0%"),
        ("Farmer income per acre (USD)", None, None, "=D4*D5", "=E4*E5", "", "$#,##0.00"),
        ("Farmer income per acre (INR)", None, None, "=D6*in_fx", "=E6*in_fx", "", "#,##0"),
        ("Delivery or MRV cost per acre (USD)", "=B2*in_cost_biochar", "=C2*in_cost_erw", "=in_mrv_acre", "=in_mrv_acre",
         "Biochar/ERW: supplier breakeven per tonne x tonnes; ARR/soil: MRV only", "$#,##0.00"),
        ("Developer margin per acre (USD)", "=B4-B8", "=C4-C8", "=D4-D6-D8", "=E4-E6-E8",
         "ARR/soil: before planting and practice-change costs", "$#,##0.00;($#,##0.00);-"),
        ("Developer margin per tonne (USD)", "=B9/B2", "=C9/C2", "=D9/D2", "=E9/E2", "", "$#,##0.00;($#,##0.00);-"),
        ("Margin as % of revenue", "=B9/B4", "=C9/C4", "=D9/D4", "=E9/E4", "", "0.0%;(0.0%);-"),
        ("Years to first issuance", "=in_delay_biochar", "=in_delay_erw", "=in_delay_arr", "=in_delay_soil", "", "0.00"),
        ("PV factor of first credit (discount rate)", "=(1+in_r)^-B12", "=(1+in_r)^-C12", "=(1+in_r)^-D12",
         "=(1+in_r)^-E12", "Value today of 1 USD of credit revenue that arrives after the delay", "0.000"),
        ("Present-value margin per acre (USD)", "=B9*B13", "=C9*C13", "=D9*D13", "=E9*E13", "", "$#,##0.00;($#,##0.00);-"),
        ("MRV share of developer's revenue", None, None, "=D8/(D4-D6)", "=E8/(E4-E6)",
         "How much of the developer's share MRV eats", "0.0%"),
    ]
    for i, (lab, b, c, d, e, note, fmt) in enumerate(rows, 2):
        ws.cell(row=i, column=1, value=lab).font = NORM
        for j, f in zip((2, 3, 4, 5), (b, c, d, e)):
            cell = ws.cell(row=i, column=j, value=f if f is not None else "n/a")
            cell.font = NORM
            cell.number_format = fmt
            cell.border = THIN
        ws.cell(row=i, column=6, value=note).font = NORM

    # ---- Dose check
    ws = wb.create_sheet("Dose Check")
    header(ws, 1, ["Step", "Value", "Unit", "Formula logic"], [52, 14, 18, 70])
    dose = [
        ("Topsoil mass in the plough layer", "=in_depth*10000*in_bd", "t per ha", "depth x 10,000 m2 x bulk density"),
        ("Biochar needed for the 2% pot-trial dose", "=in_lab_dose*B2", "t per ha", "2% w/w of the plough layer (own study)"),
        ("Biochar one hectare's own stalks make per year", "=in_stalk_ha*in_yield_biochar", "t per ha per year", "stalk x yield"),
        ("Years of own stalk needed for one 2% dose", "=B3/B4", "years", "dose / annual supply"),
        ("Durable tCO2e locked in one 2% dose", "=B3*in_carbon_biochar*44/12*in_perm_biochar", "tCO2e per ha", "carbon x 44/12 x durable share"),
        ("Dose one year of own stalk supports", "=B4/B2", "fraction w/w", "annual supply / topsoil mass"),
    ]
    for i, (a, f, u, logic) in enumerate(dose, 2):
        ws.cell(row=i, column=1, value=a).font = NORM
        c = ws.cell(row=i, column=2, value=f)
        c.font = NORM
        c.number_format = "0.000%" if u == "fraction w/w" else "#,##0.0"
        ws.cell(row=i, column=3, value=u).font = NORM
        ws.cell(row=i, column=4, value=logic).font = NORM

    # ---- Registration delay
    ws = wb.create_sheet("Registration Delay")
    header(ws, 1, ["Benchmark (CEEW, Verra AFOLU registration)", "Days", "Years", "PV factor", "Note"], [48, 10, 10, 12, 60])
    delay = [("India, median", 796), ("Rest of Asia, median", 514), ("India, 75th percentile", 1689), ("Rest of Asia, 75th percentile", 623)]
    for i, (lab, days) in enumerate(delay, 2):
        ws.cell(row=i, column=1, value=lab).font = NORM
        ws.cell(row=i, column=2, value=days).font = BLUE
        ws.cell(row=i, column=3, value=f"=B{i}/365").number_format = "0.00"
        ws.cell(row=i, column=4, value=f"=(1+in_r)^-C{i}").number_format = "0.000"
    ws.cell(row=7, column=1, value="Credit value lost vs rest of Asia, median").font = BOLD
    ws.cell(row=7, column=4, value="=1-D2/D3").number_format = "0.0%"
    ws.cell(row=8, column=1, value="Credit value lost vs rest of Asia, 75th percentile").font = BOLD
    ws.cell(row=8, column=4, value="=1-D4/D5").number_format = "0.0%"
    ws.cell(row=2, column=5, value="Source: CEEW VCM annexure, Table 7 (median and Q3 project duration to registration)").font = NORM
    ws.cell(row=3, column=5, value="https://www.ceew.in/sites/default/files/vcm-annexure.pdf").font = NORM

    # ---- Uncertainty (values from Python)
    ws = wb.create_sheet("Uncertainty")
    mc = json.loads((ROOT / "results" / "summary.json").read_text())["monte_carlo"]
    ws.cell(row=1, column=1, value="Monte Carlo: 20,000 draws, independent triangular (low, base, high), seed 7. "
                                    "Values computed in Python (src/montecarlo.py); they do not recalculate here.").font = BOLD
    header(ws, 3, ["Pathway", "P(margin > 0)", "Margin/t P10", "P50", "P90", "Margin/acre P10", "P50", "P90",
                   "Farmer INR/acre P10", "P50", "P90"], [26, 13, 13, 10, 10, 15, 10, 10, 18, 10, 10])
    labels = {"biochar": "Biochar (cotton stalk)", "erw": "Enhanced rock weathering", "arr": "Agroforestry (ARR)", "soil": "Regen-ag soil carbon"}
    for i, k in enumerate(["biochar", "erw", "arr", "soil"], 4):
        s = mc[k]
        vals = [labels[k], s["p_margin_positive"], *s["margin_t_p10_p50_p90"], *s["margin_acre_p10_p50_p90"],
                *(s.get("farmer_inr_acre_p10_p50_p90") or ["n/a"] * 3)]
        for j, v in enumerate(vals, 1):
            c = ws.cell(row=i, column=j, value=v)
            c.font = NORM
            c.number_format = "0.0%" if j == 2 else ("#,##0" if j >= 9 else "$#,##0.00;($#,##0.00)")

    # ---- Sources
    ws = wb.create_sheet("Sources")
    header(ws, 1, ["Input", "Source"], [40, 140])
    for i, (k, v) in enumerate(inp.items(), 2):
        ws.cell(row=i, column=1, value=v["parameter"] + f" ({v['pathway']})").font = NORM
        ws.cell(row=i, column=2, value=v["source"] + (f" | {v['url']}" if v["url"] else " | assumption")).font = NORM

    ws = wb["Inputs"]
    ws["H1"].comment = Comment("Type a value here to override Base for this input.", "model")
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"wrote {out} ({n_in - 1} inputs)")


if __name__ == "__main__":
    build(ROOT / "model" / "Carbon_Removal_Unit_Economics.xlsx")

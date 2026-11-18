"""Checks the recalculated Excel model against the Python model (run after LibreOffice recalc)."""
import json, sys
from openpyxl import load_workbook
from model import ROOT, PATHWAYS, evaluate, dose_check, delay_cost, load_inputs, scenario

wb = load_workbook(ROOT / "model" / "Carbon_Removal_Unit_Economics.xlsx", data_only=True)
p = scenario(load_inputs()); ev = evaluate(p); ws = wb["Unit Economics"]
rows = {2: "credited_t_acre", 4: "revenue_acre", 9: "margin_acre", 10: "margin_t", 13: "pv"}
bad = 0
for r, m in rows.items():
    for col, k in zip("BCDE", PATHWAYS):
        x, y = ws[f"{col}{r}"].value, ev[k][m]
        if x is None or abs(x - y) > 1e-6 * max(1, abs(y)):
            print("MISMATCH", r, k, m, x, y); bad += 1
for col, k in zip("DE", ["arr", "soil"]):
    if abs(ws[f"{col}7"].value - ev[k]["farmer_income_acre_inr"]) > 1e-6: bad += 1; print("farmer", k)
d = dose_check(p); wd = wb["Dose Check"]
for r, m in {2: "soil_t_ha", 3: "dose_t_ha", 4: "supply_t_ha_yr", 5: "years_of_own_stalk", 6: "dose_tco2e_ha"}.items():
    if abs(wd[f"B{r}"].value - d[m]) > 1e-6 * max(1, d[m]): bad += 1; print("dose", m)
dl = delay_cost(p); wr = wb["Registration Delay"]
if abs(wr["D7"].value - dl["loss_median"]) > 1e-9 or abs(wr["D8"].value - dl["loss_q3"]) > 1e-9: bad += 1; print("delay")
print("Excel matches Python" if not bad else f"{bad} mismatches"); sys.exit(bad > 0)

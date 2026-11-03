import math
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Column Base Plate Design Agent", page_icon="🏗️", layout="wide")
st.title("🏗️ Column Base Plate Design Agent")
st.caption("MVP v0.1 • BS EN 1993-1-8 effective-area method based on your uploaded workbook")

st.warning(
    "Engineering design assistant, not an approved design certificate. This MVP reproduces the calculation "
    "logic and scope stated in the supplied spreadsheet. It covers axial compression and shear only. "
    "It does NOT design for moment, uplift, holding-down bolts/anchors, concrete breakout, reinforcement, "
    "pedestal/foundation stability, fatigue, or seismic actions. A qualified structural engineer must verify "
    "the governing code edition, National Annex, assumptions, input data and all results before construction."
)

DEFAULTS = {
    "N_Ed": 1000.0, "V_Ed": 1000.0, "h": 1000.0, "b": 1000.0, "t_f": 78.0,
    "P_col": 1940.0, "A_col": 36000.0, "h_p": 800.0, "b_p": 800.0, "t_p": 90.0,
    "f_yp": 235.0, "f_ck": 30.0, "alpha_cc": 0.85, "gamma_c": 1.5,
    "alpha": 1.5, "beta_j": 2/3, "gamma_M0": 1.0, "f_u": 410.0,
    "beta_w": 0.85, "gamma_M2": 1.25, "s": 8.0, "l": 150.0,
    "n_w": 2, "t_g": 40.0, "f_grout": 30.0, "d_f": 500.0, "e_min": 250.0
}
LABELS = {
    "N_Ed":("Design axial compression, N_Ed","kN"),
    "V_Ed":("Design shear, V_Ed","kN"),
    "h":("Column overall depth, h","mm"),
    "b":("Column flange width, b","mm"),
    "t_f":("Column flange thickness, t_f","mm"),
    "P_col":("Column perimeter, P_col","mm"),
    "A_col":("Column cross-sectional area, A_col","mm²"),
    "h_p":("Base plate length, h_p","mm"),
    "b_p":("Base plate width, b_p","mm"),
    "t_p":("Provided plate thickness, t_p","mm"),
    "f_yp":("Plate yield strength, f_yp","N/mm²"),
    "f_ck":("Concrete cylinder strength, f_ck","N/mm²"),
    "alpha_cc":("Concrete coefficient, α_cc","-"),
    "gamma_c":("Concrete partial factor, γ_c","-"),
    "alpha":("Foundation diffusion coefficient, α","-"),
    "beta_j":("Joint coefficient, β_j","-"),
    "gamma_M0":("Steel resistance partial factor, γ_M0","-"),
    "f_u":("Ultimate strength of weaker welded part, f_u","N/mm²"),
    "beta_w":("Weld correlation factor, β_w","-"),
    "gamma_M2":("Weld partial factor, γ_M2","-"),
    "s":("Fillet weld leg size, s","mm"),
    "l":("Length of each weld segment, l","mm"),
    "n_w":("Number of effective weld segments, n_w","-"),
    "t_g":("Grout thickness, t_g","mm"),
    "f_grout":("Grout compressive strength, f_grout","N/mm²"),
    "d_f":("Foundation depth below plate, d_f","mm"),
    "e_min":("Minimum plate-to-foundation edge distance, e_min","mm"),
}

def safe_sqrt(x):
    return math.sqrt(x) if x >= 0 else None

def calculate(x):
    errors = []
    for k,v in x.items():
        if not isinstance(v,(int,float)) or not math.isfinite(v):
            errors.append(f"{k} must be a finite number.")
        elif k not in ["alpha_cc","beta_j","beta_w"] and v < 0:
            errors.append(f"{k} cannot be negative.")
    for k in ["h","b","h_p","b_p","t_p","f_yp","f_ck","gamma_c","gamma_M0","f_u","beta_w","gamma_M2","s","l","n_w"]:
        if x[k] <= 0: errors.append(f"{k} must be greater than zero.")
    if errors:
        return None, errors

    N = x["N_Ed"] * 1000.0
    V = x["V_Ed"]
    f_cd = x["alpha_cc"] * x["f_ck"] / x["gamma_c"]
    f_jd = x["beta_j"] * x["alpha"] * f_cd
    A_p = x["h_p"] * x["b_p"]
    A_req = N / f_jd if f_jd > 0 else float("inf")
    area_util = A_req / A_p if A_p > 0 else float("inf")
    c_no_disc = x["P_col"]**2 - 16.0*(x["A_col"] - A_req)
    c_no = (-x["P_col"] + safe_sqrt(c_no_disc))/8.0 if c_no_disc >= 0 else None
    c_max = (x["h"] - 2*x["t_f"])/2.0
    overlap = (c_no is None) or (c_no >= c_max)
    if not overlap:
        c = c_no
        A_eff = 4*c*c + x["P_col"]*c + x["A_col"]
    else:
        disc = (x["h"]+x["b"])**2 - 4.0*(x["h"]*x["b"] - A_req)
        c = (-(x["h"]+x["b"]) + safe_sqrt(disc))/4.0 if disc >= 0 else None
        A_eff = None
        if c is not None:
            A_eff = (x["h"]+2*c)*(x["b"]+2*c)
    if c is None:
        errors.append("Effective projection calculation has no real solution. Review A_req, P_col, A_col, h and b.")
        return None, errors
    h_eff = x["h"] + 2*c
    b_eff = x["b"] + 2*c
    if A_eff is None:
        errors.append("Effective area could not be calculated.")
        return None, errors

    check1 = A_p >= A_req
    check2 = h_eff <= x["h_p"] and b_eff <= x["b_p"] and A_eff >= A_req
    t_min = c * math.sqrt(3.0*f_jd*x["gamma_M0"]/x["f_yp"])
    check3 = x["t_p"] >= t_min
    throat = 0.7*x["s"]
    f_vwd = (x["f_u"]/math.sqrt(3.0))/(x["beta_w"]*x["gamma_M2"])
    weld_per_length = throat*f_vwd
    weld_length = x["n_w"]*(x["l"]-2*x["s"])
    weld_resistance = weld_per_length*weld_length/1000.0
    check4 = weld_length > 0 and weld_resistance >= V
    required_grout = 0.2*f_cd if x["t_g"] <= 50 else f_cd
    if x["t_g"] <= 50:
        grout_check = x["f_grout"] >= required_grout and x["t_g"] < 0.2*x["h_p"] and x["t_g"] < 0.2*x["b_p"]
    else:
        grout_check = x["f_grout"] >= required_grout
    req_depth = 0.5*max(x["h_p"],x["b_p"])
    req_edge = 0.25*max(x["h_p"],x["b_p"])
    foundation_check = x["d_f"] >= req_depth and x["e_min"] >= req_edge
    overall = all([check1,check2,check3,check4,grout_check,foundation_check])
    res = {
        "f_cd":f_cd,"f_jd":f_jd,"A_p":A_p,"A_req":A_req,"area_util":area_util,
        "c_no":c_no,"c_max":c_max,"overlap":overlap,"c":c,"h_eff":h_eff,"b_eff":b_eff,
        "A_eff":A_eff,"t_min":t_min,"throat":throat,"f_vwd":f_vwd,
        "weld_per_length":weld_per_length,"weld_length":weld_length,
        "weld_resistance":weld_resistance,"weld_util":V/weld_resistance if weld_resistance>0 else float("inf"),
        "required_grout":required_grout,"req_depth":req_depth,"req_edge":req_edge,
        "check1":check1,"check2":check2,"check3":check3,"check4":check4,
        "grout_check":grout_check,"foundation_check":foundation_check,"overall":overall
    }
    return res, errors

st.sidebar.header("Design inputs")
st.sidebar.caption("Defaults are copied from the uploaded workbook. Confirm or replace them with project-specific values.")
x={}
groups = {
    "Loads": ["N_Ed","V_Ed"],
    "Column geometry": ["h","b","t_f","P_col","A_col"],
    "Base plate": ["h_p","b_p","t_p","f_yp"],
    "Concrete / bearing": ["f_ck","alpha_cc","gamma_c","alpha","beta_j"],
    "Steel / weld": ["gamma_M0","f_u","beta_w","gamma_M2","s","l","n_w"],
    "Grout / foundation": ["t_g","f_grout","d_f","e_min"]
}
for group, keys in groups.items():
    with st.sidebar.expander(group, expanded=(group=="Loads")):
        for key in keys:
            label,unit=LABELS[key]
            x[key]=st.number_input(f"{label} ({unit})", value=float(DEFAULTS[key]), step=1.0 if unit in ["mm","kN","N/mm²"] else 0.05, format="%.4f", key=key)

st.subheader("Design basis")
st.write("BS EN 1993-1-8 effective-area method, following the formulas and assumptions in the uploaded **COLUMN BASE PLATE DESIGN.xlsx** workbook.")
st.write("Scope: axial compression + shear. The workbook's effective-area, plate-thickness, weld, grout and foundation-geometry checks are reproduced.")

if st.button("Run column base plate design checks", type="primary", use_container_width=True):
    result, errors = calculate(x)
    if errors:
        for err in errors: st.error(err)
    else:
        st.session_state["base_plate_inputs"] = x
        st.session_state["base_plate_results"] = result

if "base_plate_results" in st.session_state:
    x=st.session_state["base_plate_inputs"]
    r=st.session_state["base_plate_results"]
    st.subheader("Design summary")
    if r["overall"]: st.success("OVERALL STATUS: PASS — all implemented checks passed.")
    else: st.error("OVERALL STATUS: FAIL — one or more implemented checks failed.")
    cards = [
        ("Required bearing area",f'{r["A_req"]:,.1f} mm²'),
        ("Provided plate area",f'{r["A_p"]:,.1f} mm²'),
        ("Adopted projection c",f'{r["c"]:.2f} mm'),
        ("Minimum plate thickness",f'{r["t_min"]:.2f} mm'),
        ("Total weld resistance",f'{r["weld_resistance"]:.2f} kN'),
    ]
    cols=st.columns(len(cards))
    for col,(label,value) in zip(cols,cards): col.metric(label,value)

    checks = [
        ("Check 1 — Plate area",r["check1"],f'Provided area {r["A_p"]:,.1f} mm² ≥ required area {r["A_req"]:,.1f} mm².'),
        ("Check 2 — Effective area and plate fit",r["check2"],f'Effective area {r["A_eff"]:,.1f} mm²; required {r["A_req"]:,.1f} mm²; effective dimensions {r["h_eff"]:.2f} × {r["b_eff"]:.2f} mm; plate {x["h_p"]:.2f} × {x["b_p"]:.2f} mm.'),
        ("Check 3 — Plate thickness",r["check3"],f'Provided thickness {x["t_p"]:.2f} mm ≥ required {r["t_min"]:.2f} mm.'),
        ("Check 4 — Weld resistance",r["check4"],f'Weld resistance {r["weld_resistance"]:.2f} kN ≥ design shear {x["V_Ed"]:.2f} kN; effective length {r["weld_length"]:.2f} mm.'),
        ("Assumption — Grout / βj",r["grout_check"],f'Required grout strength {r["required_grout"]:.2f} N/mm²; provided {x["f_grout"]:.2f} N/mm².'),
        ("Assumption — Foundation geometry",r["foundation_check"],f'Required depth ≥ {r["req_depth"]:.2f} mm; provided {x["d_f"]:.2f} mm. Required edge distance ≥ {r["req_edge"]:.2f} mm; provided {x["e_min"]:.2f} mm.')
    ]
    st.subheader("Point-by-point design checklist")
    check_rows=[]
    for name,passed,detail in checks:
        status="PASS" if passed else "FAIL"
        check_rows.append({"Design check":name,"Status":status,"Calculation / finding":detail})
        with st.expander(f"{'✅' if passed else '❌'} {name} — {status}", expanded=not passed):
            st.write(detail)
    check_df=pd.DataFrame(check_rows)
    st.dataframe(check_df,use_container_width=True,hide_index=True)

    st.subheader("Calculation details")
    details=[
        ("Concrete design strength, f_cd",r["f_cd"],"N/mm²"),
        ("Design bearing strength, f_jd",r["f_jd"],"N/mm²"),
        ("Required bearing area, A_req",r["A_req"],"mm²"),
        ("Provided plate area, A_p",r["A_p"],"mm²"),
        ("Area utilization, A_req/A_p",r["area_util"],"ratio"),
        ("No-overlap projection candidate",r["c_no"] if r["c_no"] is not None else float("nan"),"mm"),
        ("Maximum no-overlap projection",r["c_max"],"mm"),
        ("Overlap method selected", "Yes" if r["overlap"] else "No",""),
        ("Adopted effective projection, c",r["c"],"mm"),
        ("Effective dimensions",f'{r["h_eff"]:.3f} × {r["b_eff"]:.3f}',"mm"),
        ("Effective area, A_eff",r["A_eff"],"mm²"),
        ("Minimum plate thickness",r["t_min"],"mm"),
        ("Weld throat, a = 0.7s",r["throat"],"mm"),
        ("Weld design shear strength, f_vw,d",r["f_vwd"],"N/mm²"),
        ("Weld resistance per unit length",r["weld_per_length"],"N/mm"),
        ("Total effective weld length",r["weld_length"],"mm"),
        ("Total weld resistance",r["weld_resistance"],"kN"),
        ("Weld utilization, V_Ed / F_w,Rd",r["weld_util"],"ratio"),
        ("Required grout strength",r["required_grout"],"N/mm²"),
        ("Required foundation depth",r["req_depth"],"mm"),
        ("Required edge distance",r["req_edge"],"mm"),
    ]
    detail_df=pd.DataFrame(details,columns=["Parameter","Value","Unit"])
    st.dataframe(detail_df,use_container_width=True,hide_index=True)

    report_lines=[
        "COLUMN BASE PLATE DESIGN REPORT",
        "="*55,
        f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}",
        "Design basis: BS EN 1993-1-8 effective-area method, based on supplied workbook.",
        "Scope: axial compression + shear only.",
        "",
        "INPUTS"
    ]
    for key,val in x.items():
        label,unit=LABELS[key]
        report_lines.append(f"{label}: {val:g} {unit}")
    report_lines += ["","DESIGN CHECKLIST"]
    for name,passed,detail in checks:
        report_lines += [f"[{'PASS' if passed else 'FAIL'}] {name}",f"  {detail}"]
    report_lines += ["","CALCULATION RESULTS"]
    for name,val,unit in details:
        report_lines.append(f"{name}: {val} {unit}".strip())
    report_lines += ["",f"OVERALL STATUS: {'PASS' if r['overall'] else 'FAIL'}","","LIMITATIONS",
        "This report covers only the calculation scope implemented from the supplied workbook.",
        "Not included: moment, uplift, anchor/holding-down bolt design, concrete breakout, reinforcement,",
        "foundation/pedestal stability, fatigue, seismic effects, or full connection detailing.",
        "Independent checking by a qualified structural engineer is required before construction use."]
    report="\n".join(report_lines)
    st.subheader("Download design report")
    st.download_button("Download checklist report (.txt)",report.encode("utf-8"),"column_base_plate_design_report.txt","text/plain")
    st.download_button("Download design checks (.csv)",check_df.to_csv(index=False).encode("utf-8"),"column_base_plate_checks.csv","text/csv")
    st.download_button("Download calculation details (.csv)",detail_df.to_csv(index=False).encode("utf-8"),"column_base_plate_calculations.csv","text/csv")

with st.expander("Workbook method and engineering limitations"):
    st.markdown("""
    **Calculation method reproduced from the uploaded workbook**
    - `f_cd = α_cc × f_ck / γ_c`
    - `f_jd = β_j × α × f_cd`
    - `A_req = N_Ed / f_jd`; `A_p = h_p × b_p`
    - Effective projection and area use the workbook's no-overlap / overlap equations.
    - `t_p,min = c × √(3 × f_jd × γ_M0 / f_yp)`
    - Weld throat `a = 0.7s`; weld resistance follows the workbook's `f_u`, `β_w`, `γ_M2`, and effective-length method.
    - Grout and foundation geometry checks follow the workbook assumptions.

    **Important:** The uploaded workbook's worked-example notes and its default input cells are not identical. The app uses the numeric defaults from the workbook's `Base Plate Design` input cells. Replace them with the correct project values. Verify the formulas and applicability against the original source lecture, BS EN 1993-1-8, National Annex and project specifications.
    """)
st.caption("MVP v0.1 • Spreadsheet-based calculation logic • Not a substitute for independent engineering verification")

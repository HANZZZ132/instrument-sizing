from __future__ import annotations

import json
import math
from datetime import datetime

import pandas as pd
import streamlit as st

import AGA3
import aga8_detail

from psv_engine.gas_relief import calculate_gas_relief_area
from psv_engine.liquid_relief import calculate_liquid_relief_area
from psv_engine.two_phase import calculate_omega_flashing, calculate_two_phase_area
from psv_engine.fire_scenarios import calculate_fire_wetted_load
from psv_engine.thermal_expansion import calculate_thermal_expansion_load
from psv_engine.advanced_sizing import calculate_napier_steam_area
from psv_engine.piping import calculate_inlet_pressure_drop, check_inlet_rule, check_outlet_rule
from psv_engine.unit_converter import (
    barg_to_psia, kg_h_to_lb_h, c_to_rankine, m3_h_to_gpm, m3_kg_to_ft3_lb,
)

APP_TITLE = "Instrument Sizing"
APP_VERSION = "Web 1.0.1"

COMPONENTS = [
    "C1 (Methane)", "N2 (Nitrogen)", "CO2", "C2 (Ethane)", "C3 (Propane)",
    "H2O", "H2S", "H2", "CO", "O2", "iC4", "nC4", "iC5", "nC5",
    "C6", "C7", "C8", "C9", "C10", "He", "Ar",
]
GULF_COAST = [96.5222, 0.2595, 0.5956, 1.8186, 0.4596, 0, 0, 0, 0, 0,
              0.0977, 0.1007, 0.0473, 0.0324, 0.0664, 0, 0, 0, 0, 0, 0]
AMARILLO = [90.6724, 3.1284, 0.4676, 4.5279, 0.8280, 0, 0, 0, 0, 0,
            0.1037, 0.1563, 0.0321, 0.0443, 0.0393, 0, 0, 0, 0, 0, 0]

st.set_page_config(page_title=APP_TITLE, page_icon="📐", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
<style>
    .block-container {padding-top: 1.35rem; padding-bottom: 3rem; max-width: 1500px;}
    [data-testid="stSidebar"] {border-right: 1px solid #D7DEE8;}
    .brand {background: linear-gradient(135deg,#0B1F33,#163B62); color:white; padding:1.2rem 1.35rem; border-radius:16px; margin-bottom:1rem;}
    .brand h1 {font-size:1.65rem; margin:0 0 .15rem 0; color:white;}
    .brand p {margin:0; opacity:.82; font-size:.88rem;}
    .hero {background:linear-gradient(135deg,#0B1F33 0%,#1769E0 100%); color:white; padding:2.2rem 2.4rem; border-radius:22px; margin-bottom:1.3rem; box-shadow:0 10px 28px rgba(11,31,51,.15)}
    .hero h1 {font-size:2.5rem; margin:0; color:white;}
    .hero .desc {opacity:.82; max-width:850px; margin-top:1rem;}
    .module-card {background:white; border:1px solid #D7DEE8; border-radius:16px; padding:1.15rem 1.2rem; min-height:165px; box-shadow:0 3px 12px rgba(15,23,42,.04)}
    .module-card h3 {margin:.15rem 0 .55rem 0; font-size:1.12rem;}
    .module-card p {color:#667085; font-size:.91rem;}
    .section-title {font-size:1.55rem; font-weight:750; color:#0B1F33; margin-bottom:.1rem}
    .section-sub {color:#667085; margin-bottom:1rem}
    div[data-testid="stMetric"] {background:white; border:1px solid #D7DEE8; padding:.75rem 1rem; border-radius:14px;}
    div[data-testid="stForm"] {background:white; border:1px solid #D7DEE8; border-radius:16px; padding:1rem 1rem .4rem 1rem;}
    .status-ok {padding:.7rem 1rem; border-radius:10px; background:#EAF7F1; border:1px solid #79C8A7; color:#075E45;}
    .status-warn {padding:.7rem 1rem; border-radius:10px; background:#FFF7E8; border:1px solid #F3C66B; color:#7A4C00;}
    .footnote {color:#667085; font-size:.82rem; margin-top:1.4rem;}
</style>
""",
    unsafe_allow_html=True,
)


def _default(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


def _fmt(v, digits=6):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "YES" if v else "NO"
    if isinstance(v, (int, float)):
        if v == 0:
            return "0"
        if abs(v) >= 1e6 or abs(v) < 1e-4:
            return f"{v:.6e}"
        return f"{v:,.{digits}f}".rstrip("0").rstrip(".")
    return str(v)


def aga3_core(v, d_orifice_ref, downstream=False):
    AGA3.set_units("US")
    T_r = AGA3.T_r
    d = AGA3.thermal_expansion(v["alpha_orifice"], d_orifice_ref, T_r, v["T_f"])
    D = AGA3.thermal_expansion(v["alpha_pipe"], v["D_pipe"], T_r, v["T_f"])
    if d <= 0 or D <= 0 or d >= D:
        raise ValueError("Orifice bore at flowing temperature must be smaller than meter tube ID.")
    beta = AGA3.diameter_ratio(d, D)
    Ev = AGA3.velocity_factor(beta)
    c0, c1, c2, c3, c4 = AGA3.discharge_constants(D, beta)
    Pf = AGA3.upstream_pressure(v["P_f"], v["dP"]) if downstream else v["P_f"]
    Y = AGA3.expansion_factor(beta, v["dP"], Pf, v["k"]) if v["k"] > 0 else 1.0
    FI = AGA3.iteration_flow_factor(d, D, v["dP"], Ev, v["mu"], v["rho_f"], Y)
    Cd, bound = AGA3.discharge_coefficient(c0, c1, c2, c3, c4, FI)
    qv = AGA3.base_flow(Cd, d, v["dP"], Ev, v["rho_b"], v["rho_f"], Y)
    return {"d_ref": d_orifice_ref, "d": d, "D": D, "beta": beta, "Ev": Ev, "Pf": Pf,
            "Y": Y, "FI": FI, "Cd": Cd, "bound": bound, "qv": qv, "mmscfd": qv * 0.000024}


def solve_orifice_reference(v, target_qv, downstream=False):
    if target_qv <= 0:
        raise ValueError("Target base flow must be greater than zero.")
    Dref = v["D_pipe"]
    lo, hi = max(Dref * 0.001, 1e-5), Dref * 0.99
    r_lo, r_hi = aga3_core(v, lo, downstream), aga3_core(v, hi, downstream)
    if not (r_lo["qv"] <= target_qv <= r_hi["qv"]):
        raise ValueError(
            "Target flow is outside the bore search range "
            f"({r_lo['mmscfd']:.6g}–{r_hi['mmscfd']:.6g} MMSCFD for this case)."
        )
    best = r_lo
    for _ in range(90):
        mid = (lo + hi) / 2
        best = aga3_core(v, mid, downstream)
        err = best["qv"] - target_qv
        if abs(err) <= max(abs(target_qv) * 1e-8, 1e-6):
            break
        if err < 0:
            lo = mid
        else:
            hi = mid
    return best


def page_header(title, subtitle):
    st.markdown(f'<div class="section-title">{title}</div><div class="section-sub">{subtitle}</div>', unsafe_allow_html=True)


def goto(page):
    st.session_state["nav_request"] = page
    st.rerun()


# Handle requests from welcome-page buttons before rendering sidebar navigation.
if "nav_request" in st.session_state:
    st.session_state["page"] = st.session_state.pop("nav_request")

PAGES = ["Welcome", "AGA 3 — Orifice Flow", "AGA 8 — Gas Properties", "Control Valve Sizing", "PSV Engineering", "About / Method"]
with st.sidebar:
    st.markdown(f'<div class="brand"><h1>{APP_TITLE}</h1><p>{APP_VERSION}</p></div>', unsafe_allow_html=True)
    page = st.radio("Navigation", PAGES, key="page", label_visibility="collapsed")
    st.divider()
    st.caption("Engineering calculation aid. Final design and vendor selection should be checked against the applicable project standards and certified data.")


if page == "Welcome":
    st.markdown(
        f'<div class="hero"><h1>INSTRUMENT SIZING</h1>'
        '<div class="desc">A browser-based engineering calculator for gas metering, gas properties, control valves, and pressure safety valves. Use it from Windows, macOS, tablet, or phone after deployment.</div></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "AGA 3", "Orifice gas flow or inverse sizing of the required orifice bore.", "AGA 3 — Orifice Flow"),
        (c2, "AGA 8 DETAIL", "Compressibility factor, flowing/base density, MW and Fpv from gas composition.", "AGA 8 — Gas Properties"),
        (c3, "Control Valve", "Liquid, gas and steam Cv/Kv sizing with representative valve series.", "Control Valve Sizing"),
        (c4, "PSV Engineering", "Gas, steam, liquid, two-phase, fire, thermal and piping checks.", "PSV Engineering"),
    ]
    for col, title, desc, target in cards:
        with col:
            st.markdown(f'<div class="module-card"><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)
            if st.button(f"Open {title}", key=f"go_{target}", use_container_width=True):
                goto(target)
    st.info("Tip: AGA 8 results can be transferred directly into AGA 3 and the gas Control Valve calculator during the same browser session.")


elif page == "AGA 3 — Orifice Flow":
    page_header("AGA 3 — Orifice Flow", "Calculate base flow from a known bore, or solve the reference orifice diameter for a target base flow.")
    for k, v in {
        "a3_T_f": 83.469, "a3_P_f": 522.043, "a3_dP": 3.528, "a3_d_orifice": 6.8657,
        "a3_alpha_orifice": 0.0000167, "a3_D_pipe": 11.375, "a3_alpha_pipe": 0.0000112,
        "a3_k": 1.3198, "a3_mu": 0.013520, "a3_rho_f": 1.566, "a3_rho_b": 0.4488,
        "a3_target": 13.841712,
    }.items(): _default(k, v)

    mode = st.segmented_control("Calculation mode", ["Flow Rate", "Orifice Diameter"], default="Flow Rate", key="a3_mode")
    left, right = st.columns([1.1, .9])
    with left:
        with st.form("aga3_form"):
            a, b, c = st.columns(3)
            T_f = a.number_input("Flowing temperature (°F)", key="a3_T_f", format="%.6f")
            P_f = b.number_input("Flowing pressure (psia)", key="a3_P_f", min_value=0.000001, format="%.6f")
            dP = c.number_input("Differential pressure (inH₂O)", key="a3_dP", min_value=0.000001, format="%.6f")
            a, b = st.columns(2)
            D_pipe = a.number_input("Meter tube ID @ reference (in)", key="a3_D_pipe", min_value=0.001, format="%.6f")
            d_orifice = b.number_input("Orifice bore @ reference (in)", key="a3_d_orifice", min_value=0.0001, format="%.6f", disabled=mode != "Flow Rate")
            a, b = st.columns(2)
            alpha_o = a.number_input("Orifice thermal expansion (in/in-°F)", key="a3_alpha_orifice", format="%.8f")
            alpha_p = b.number_input("Pipe thermal expansion (in/in-°F)", key="a3_alpha_pipe", format="%.8f")
            a, b, c, d = st.columns(4)
            k = a.number_input("k = Cp/Cv", key="a3_k", min_value=0.0, format="%.6f")
            mu = b.number_input("Viscosity (cP)", key="a3_mu", min_value=0.000001, format="%.6f")
            rho_f = c.number_input("Flowing density (lbm/ft³)", key="a3_rho_f", min_value=0.000001, format="%.8f")
            rho_b = d.number_input("Base density (lbm/ft³)", key="a3_rho_b", min_value=0.000001, format="%.8f")
            downstream = st.checkbox("Pressure input is downstream tap", value=False)
            target = st.number_input("Target base flow (MMSCFD)", key="a3_target", min_value=0.000001, format="%.6f", disabled=mode != "Orifice Diameter")
            submitted = st.form_submit_button("Calculate AGA 3", type="primary", use_container_width=True)
        if st.button("Use latest AGA 8 T/P + densities", use_container_width=True):
            r8 = st.session_state.get("aga8_last")
            if not r8:
                st.warning("Calculate AGA 8 first.")
            else:
                st.session_state["a3_T_f"] = st.session_state.get("a8_T", 65.0)
                st.session_state["a3_P_f"] = st.session_state.get("a8_P", 750.5)
                st.session_state["a3_rho_f"] = r8["flowing"]["density_lb_ft3"]
                st.session_state["a3_rho_b"] = r8["base"]["density_lb_ft3"]
                st.rerun()

    if submitted:
        try:
            vals = {"T_f": T_f, "P_f": P_f, "dP": dP, "D_pipe": D_pipe, "alpha_orifice": alpha_o,
                    "alpha_pipe": alpha_p, "k": k, "mu": mu, "rho_f": rho_f, "rho_b": rho_b}
            if mode == "Flow Rate":
                r = aga3_core(vals, d_orifice, downstream)
            else:
                r = solve_orifice_reference(vals, target / 0.000024, downstream)
                st.session_state["a3_d_orifice"] = r["d_ref"]
            st.session_state["aga3_last"] = r
        except Exception as e:
            st.error(f"Calculation error: {e}")

    with right:
        r = st.session_state.get("aga3_last")
        if r:
            st.metric("Base Flow", f"{r['mmscfd']:.6f} MMSCFD")
            m1, m2, m3 = st.columns(3)
            m1.metric("Orifice Bore", f"{r['d_ref']:.6f} in")
            m2.metric("β Ratio", f"{r['beta']:.6f}")
            m3.metric("Cd", f"{r['Cd']:.6f}")
            df = pd.DataFrame([
                ["Bore at flowing T", r["d"], "in"], ["Tube ID at flowing T", r["D"], "in"],
                ["Velocity approach factor Ev", r["Ev"], "—"], ["Expansion factor Y", r["Y"], "—"],
                ["Iteration flow factor FI", r["FI"], "—"], ["Base volumetric flow", r["qv"], "ft³/hr"],
                ["Flowing pressure used", r["Pf"], "psia"],
            ], columns=["Parameter", "Value", "Unit"])
            st.dataframe(df, hide_index=True, use_container_width=True)
            if r["bound"]:
                st.warning("Discharge coefficient correlation is outside its certainty flag.")
            else:
                st.success("Correlation bounds flag: OK")
        else:
            st.info("Enter the case and press **Calculate AGA 3**.")


elif page == "AGA 8 — Gas Properties":
    page_header("AGA 8 DETAIL — Gas Properties", "Calculate Z-factor and density from a 21-component gas composition, then transfer the result to other calculators.")
    for k, v in {"a8_T": 65.0, "a8_P": 750.5, "a8_Tb": 60.0, "a8_Pb": 14.73}.items(): _default(k, v)
    _default("a8_comp", GULF_COAST.copy())

    top1, top2 = st.columns([.85, 1.15])
    with top1:
        with st.form("aga8_conditions"):
            a, b = st.columns(2)
            T = a.number_input("Flowing temperature (°F)", key="a8_T", format="%.4f")
            P = b.number_input("Flowing pressure (psia abs)", key="a8_P", min_value=0.000001, format="%.4f")
            Tb = a.number_input("Base temperature (°F)", key="a8_Tb", format="%.4f")
            Pb = b.number_input("Base pressure (psia abs)", key="a8_Pb", min_value=0.000001, format="%.4f")
            calc8 = st.form_submit_button("Calculate AGA 8", type="primary", use_container_width=True)
        c1, c2, c3 = st.columns(3)
        if c1.button("Gulf Coast", use_container_width=True):
            st.session_state["a8_comp"] = GULF_COAST.copy(); st.rerun()
        if c2.button("Amarillo", use_container_width=True):
            st.session_state["a8_comp"] = AMARILLO.copy(); st.rerun()
        if c3.button("Normalize", use_container_width=True):
            vals = st.session_state["a8_comp"]
            s = sum(vals)
            if s > 0: st.session_state["a8_comp"] = [x * 100.0/s for x in vals]
            st.rerun()

    with top2:
        comp_df = pd.DataFrame({"Component": COMPONENTS, "Mole %": st.session_state["a8_comp"]})
        edited = st.data_editor(
            comp_df, hide_index=True, use_container_width=True, height=430,
            disabled=["Component"], num_rows="fixed",
            column_config={"Mole %": st.column_config.NumberColumn(format="%.6f", min_value=0.0)}, key="a8_editor"
        )
        st.session_state["a8_comp"] = [float(x) for x in edited["Mole %"].fillna(0.0).tolist()]
        total = sum(st.session_state["a8_comp"])
        st.caption(f"Composition total: **{total:.6f}%** · {sum(1 for x in st.session_state['a8_comp'] if x > 0)} active components. The DETAIL engine normalizes internally.")

    if calc8:
        try:
            r = aga8_detail.calculate_us(st.session_state["a8_comp"], T, P, Tb, Pb)
            st.session_state["aga8_last"] = r
        except Exception as e:
            st.error(f"AGA 8 calculation error: {e}")

    r = st.session_state.get("aga8_last")
    if r:
        f, b = r["flowing"], r["base"]
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Z Flowing", f"{f['Z']:.8f}")
        m2.metric("Z Base", f"{b['Z']:.8f}")
        m3.metric("ρ Flowing", f"{f['density_lb_ft3']:.6f} lb/ft³")
        m4.metric("MW", f"{r['molar_mass_g_mol']:.5f}")
        m5.metric("Fpv", f"{r['Fpv']:.7f}")
        detail = pd.DataFrame([
            ["Flowing density", f["density_kg_m3"], "kg/m³"], ["Base density", b["density_kg_m3"], "kg/m³"],
            ["Base density", b["density_lb_ft3"], "lbm/ft³"], ["Molar density flowing", f["molar_density_mol_L"], "mol/L"],
            ["Molar density base", b["molar_density_mol_L"], "mol/L"], ["Ideal gas specific gravity", r["specific_gravity_ideal"], "—"],
            ["Pressure closure check", f["pressure_check_kPa"], "kPa"],
        ], columns=["Property", "Value", "Unit"])
        st.dataframe(detail, hide_index=True, use_container_width=True)
        c1, c2 = st.columns(2)
        if c1.button("Send T/P + densities to AGA 3", type="primary", use_container_width=True):
            st.session_state["a3_T_f"] = st.session_state["a8_T"]
            st.session_state["a3_P_f"] = st.session_state["a8_P"]
            st.session_state["a3_rho_f"] = f["density_lb_ft3"]
            st.session_state["a3_rho_b"] = b["density_lb_ft3"]
            st.success("Transferred. Open AGA 3 from the sidebar.")
        if c2.button("Send gas properties to Control Valve", use_container_width=True):
            st.session_state["cv_gas_temp"] = (f["temperature_K"] - 273.15)
            st.session_state["cv_gas_mw"] = r["molar_mass_g_mol"]
            st.session_state["cv_gas_z"] = f["Z"]
            st.success("Transferred. Open Control Valve Sizing from the sidebar.")


elif page == "Control Valve Sizing":
    page_header("Control Valve Sizing", "IEC/ISA-based liquid, gas and steam sizing using the included calculation engine and representative vendor valve series.")
    try:
        from control_valve_engine.valve_sizing import (
            LiquidSizingInput, GasSizingInput, SteamSizingInput,
            size_liquid_valve, size_gas_valve, size_steam_valve,
        )
        from control_valve_engine.vendor_catalog import get_vendor_options, get_vendor_definition
    except Exception as e:
        st.error(f"Control Valve engine could not load: {e}. Ensure requirements.txt was installed during deployment.")
        st.stop()

    options = get_vendor_options()
    labels = {key: f"{get_vendor_definition(key).vendor} — {get_vendor_definition(key).style}" for key in options}
    service = st.segmented_control("Service", ["Liquid", "Gas", "Steam"], default="Liquid")
    vendor_key = st.selectbox("Representative valve series", options, format_func=lambda k: labels[k])
    vd = get_vendor_definition(vendor_key)
    st.caption(f"Representative coefficients: FL={vd.fl}, Fd={vd.fd}, xT={vd.xt}. Final vendor sizing should use certified valve-specific data.")

    if service == "Liquid":
        with st.form("cv_liquid"):
            a,b,c = st.columns(3)
            q=a.number_input("Flow (m³/h)", 0.0001, value=25.0); p1=b.number_input("P1 (bara)", 0.0001, value=8.0); p2=c.number_input("P2 (bara)", 0.0001, value=5.0)
            a,b,c = st.columns(3)
            rho=a.number_input("Density (kg/m³)", 0.001, value=998.0); pv=b.number_input("Vapor pressure (bara)", 0.0, value=0.03); pc=c.number_input("Critical pressure (bara)", 0.001, value=220.64)
            a,b,c = st.columns(3)
            mu=a.number_input("Viscosity (Pa·s)", 0.0000001, value=0.00089, format="%.7f"); d1=b.number_input("Inlet pipe ID (mm, 0=auto)", 0.0, value=0.0); d2=c.number_input("Outlet pipe ID (mm, 0=auto)",0.0,value=0.0)
            submit=st.form_submit_button("Calculate Control Valve", type="primary", use_container_width=True)
        if submit:
            try:
                data=LiquidSizingInput(q,p1,p2,rho,pv,pc,mu,fl=vd.fl or .85,fd=vd.fd or 1.0,pipe_inlet_diameter_mm=d1 or None,pipe_outlet_diameter_mm=d2 or None)
                st.session_state["cv_last"]=size_liquid_valve(data,valve_series=list(vd.sizes),valve_meta={"vendor":vd.vendor,"style":vd.style})
            except Exception as e: st.error(str(e))
    elif service == "Gas":
        _default("cv_gas_temp",20.0); _default("cv_gas_mw",18.0); _default("cv_gas_z",0.98)
        with st.form("cv_gas"):
            a,b,c = st.columns(3)
            q=a.number_input("Normal flow (Nm³/h)",0.0001,value=800.0); p1=b.number_input("P1 (bara)",0.0001,value=8.0); p2=c.number_input("P2 (bara)",0.0001,value=6.0)
            a,b,c = st.columns(3)
            temp=a.number_input("Temperature (°C)",key="cv_gas_temp"); mw=b.number_input("Molecular weight",0.001,key="cv_gas_mw"); z=c.number_input("Z-factor",0.001,key="cv_gas_z")
            a,b,c = st.columns(3)
            kr=a.number_input("k = Cp/Cv",0.1,value=1.28); mu=b.number_input("Viscosity (Pa·s)",0.00000001,value=1.1e-5,format="%.8f"); d1=c.number_input("Inlet pipe ID (mm, 0=auto)",0.0,value=0.0)
            d2=st.number_input("Outlet pipe ID (mm, 0=auto)",0.0,value=0.0)
            submit=st.form_submit_button("Calculate Control Valve", type="primary", use_container_width=True)
        if submit:
            try:
                data=GasSizingInput(q,p1,p2,temp,mw,kr,mu,z=z,fl=vd.fl or .85,fd=vd.fd or 1.0,xt=vd.xt or .69,pipe_inlet_diameter_mm=d1 or None,pipe_outlet_diameter_mm=d2 or None)
                st.session_state["cv_last"]=size_gas_valve(data,valve_series=list(vd.sizes),valve_meta={"vendor":vd.vendor,"style":vd.style})
            except Exception as e: st.error(str(e))
    else:
        with st.form("cv_steam"):
            a,b,c=st.columns(3)
            q=a.number_input("Steam flow (kg/h)",0.0001,value=2500.0); p1=b.number_input("P1 (bara)",0.0001,value=12.0); p2=c.number_input("P2 (bara)",0.0001,value=8.0)
            a,b,c=st.columns(3)
            temp=a.number_input("Temperature (°C)",value=220.0); kr=b.number_input("k = Cp/Cv",0.1,value=1.30); z=c.number_input("Z-factor",0.001,value=1.0)
            a,b=st.columns(2); d1=a.number_input("Inlet pipe ID (mm, 0=auto)",0.0,value=0.0); d2=b.number_input("Outlet pipe ID (mm, 0=auto)",0.0,value=0.0)
            submit=st.form_submit_button("Calculate Control Valve", type="primary", use_container_width=True)
        if submit:
            try:
                data=SteamSizingInput(q,p1,p2,temp,specific_heat_ratio=kr,z=z,fl=vd.fl or .85,fd=vd.fd or 1.0,xt=vd.xt or .69,pipe_inlet_diameter_mm=d1 or None,pipe_outlet_diameter_mm=d2 or None)
                st.session_state["cv_last"]=size_steam_valve(data,valve_series=list(vd.sizes),valve_meta={"vendor":vd.vendor,"style":vd.style})
            except Exception as e: st.error(str(e))

    r=st.session_state.get("cv_last")
    if r:
        m1,m2,m3,m4=st.columns(4)
        m1.metric("Required Cv",_fmt(r.required_cv,4)); m2.metric("Required Kv",_fmt(r.required_kv,4)); m3.metric("Selected Valve",f"DN {r.valve_dn_mm} ({r.valve_inch})"); m4.metric("Rated Cv",_fmt(r.rated_cv,3))
        st.success("Choked flow: YES" if r.is_choked else "Choked flow: NO")
        rows=[["ΔP",r.delta_p_bar,"bar"],["Noise estimate",r.get("noise_db"),"dB(A)"],["Actuator thrust estimate",r.get("actuator_thrust_n"),"N"],["Valve Reynolds",r.get("reynolds_valve"),"—"]]
        if r.get("expansion_factor_y") is not None: rows.append(["Expansion factor Y",r.get("expansion_factor_y"),"—"])
        if r.get("flow_regime") is not None: rows.append(["Flow regime",r.get("flow_regime"),"—"])
        st.dataframe(pd.DataFrame(rows,columns=["Parameter","Value","Unit"]),hide_index=True,use_container_width=True)
        if r.warning: st.warning(r.warning)


elif page == "PSV Engineering":
    page_header("PSV Engineering", "API-style sizing tools for common relief services. Add calculated cases to the Scenario Register to compare the governing required area.")
    _default("psv_scenarios", [])
    service = st.selectbox("Calculation service", ["Gas / Vapor", "Steam", "Liquid", "Two-Phase", "External Fire — Wetted Vessel", "Thermal Expansion", "Piping Check"])
    psv_result = None
    case_name = ""

    if service == "Gas / Vapor":
        with st.form("psv_gas"):
            case_name=st.text_input("Scenario name",value="Blocked Outlet — Gas")
            a,b,c=st.columns(3); W=a.number_input("Required relief rate (kg/h)",0.001,value=15000.0); setb=b.number_input("Set pressure (barg)",0.001,value=25.0); bp=c.number_input("Back pressure (barg)",0.0,value=1.5)
            a,b,c=st.columns(3); op=a.number_input("Overpressure (%)",0.0,value=10.0); temp=b.number_input("Relieving temperature (°C)",value=45.0); z=c.number_input("Z",0.001,value=.92)
            a,b,c=st.columns(3); mw=a.number_input("MW",0.001,value=16.04); k=b.number_input("k",0.1,value=1.31); n=c.number_input("Parallel valves",1,20,value=1,step=1)
            a,b,c=st.columns(3); kd=a.number_input("Kd",0.001,1.0,value=.975); kb=b.number_input("Kb",0.001,1.2,value=1.0); kc=c.number_input("Kc",0.001,1.2,value=1.0)
            calc=st.form_submit_button("Calculate PSV",type="primary",use_container_width=True)
        if calc:
            try:
                p1=barg_to_psia(setb*(1+op/100)); p2=barg_to_psia(bp)
                psv_result=calculate_gas_relief_area(kg_h_to_lb_h(W),p1,p2,c_to_rankine(temp),z,mw,k,kd,kb,kc,int(n))
            except Exception as e: st.error(str(e))
    elif service == "Steam":
        with st.form("psv_steam"):
            case_name=st.text_input("Scenario name",value="Steam Relief")
            a,b,c=st.columns(3); W=a.number_input("Steam rate (kg/h)",0.001,value=15000.0); setb=b.number_input("Set pressure (barg)",0.001,value=25.0); bp=c.number_input("Back pressure (barg)",0.0,value=1.5)
            a,b,c=st.columns(3); op=a.number_input("Overpressure (%)",0.0,value=10.0); temp=b.number_input("Temperature (°C)",value=300.0); n=c.number_input("Parallel valves",1,20,value=1,step=1)
            a,b,c=st.columns(3); kd=a.number_input("Kd",0.001,1.0,value=.975); kb=b.number_input("Kb",0.001,1.2,value=1.0); kc=c.number_input("Kc",0.001,1.2,value=1.0)
            calc=st.form_submit_button("Calculate PSV",type="primary",use_container_width=True)
        if calc:
            try:
                p1=barg_to_psia(setb*(1+op/100)); p2=barg_to_psia(bp)
                psv_result=calculate_napier_steam_area(kg_h_to_lb_h(W),p1,p2,c_to_rankine(temp),kd,kb,kc,int(n))
            except Exception as e: st.error(str(e))
    elif service == "Liquid":
        with st.form("psv_liquid"):
            case_name=st.text_input("Scenario name",value="Blocked Outlet — Liquid")
            a,b,c=st.columns(3); q=a.number_input("Relief flow (m³/h)",0.0001,value=100.0); setb=b.number_input("Set pressure (barg)",0.001,value=25.0); bp=c.number_input("Back pressure (barg)",0.0,value=1.5)
            a,b,c=st.columns(3); op=a.number_input("Overpressure (%)",0.0,value=10.0); sg=b.number_input("Specific gravity",0.001,value=.8); mu=c.number_input("Viscosity (cP)",0.0001,value=1.0)
            a,b,c=st.columns(3); kd=a.number_input("Kd",0.001,1.0,value=.65); kc=b.number_input("Kc",0.001,1.2,value=1.0); n=c.number_input("Parallel valves",1,20,value=1,step=1)
            vtype=st.selectbox("Valve type",["conventional","balanced_bellows","pilot"])
            calc=st.form_submit_button("Calculate PSV",type="primary",use_container_width=True)
        if calc:
            try:
                p1=barg_to_psia(setb*(1+op/100)); p2=barg_to_psia(bp)
                psv_result=calculate_liquid_relief_area(m3_h_to_gpm(q),p1,p2,sg,mu,kd=kd,kc=kc,num_valves=int(n),overpressure_pct=op,valve_type=vtype,set_pressure_psig=setb*14.5037738)
            except Exception as e: st.error(str(e))
    elif service == "Two-Phase":
        with st.form("psv_tp"):
            case_name=st.text_input("Scenario name",value="Two-Phase Relief")
            a,b,c=st.columns(3); W=a.number_input("Relief rate (kg/h)",0.001,value=50000.0); setb=b.number_input("Relieving pressure (barg)",0.001,value=27.5); bp=c.number_input("Back pressure (barg)",0.0,value=1.5)
            a,b,c=st.columns(3); v0=a.number_input("v0 specific volume (m³/kg)",0.0000001,value=.01,format="%.7f"); v9=b.number_input("v9 specific volume (m³/kg)",0.0000001,value=.011,format="%.7f"); n=c.number_input("Parallel valves",1,20,value=1,step=1)
            a,b,c=st.columns(3); kd=a.number_input("Kd",0.001,1.0,value=.85); kb=b.number_input("Kb",0.001,1.2,value=1.0); kc=c.number_input("Kc",0.001,1.2,value=1.0)
            calc=st.form_submit_button("Calculate PSV",type="primary",use_container_width=True)
        if calc:
            try:
                omega=calculate_omega_flashing(m3_kg_to_ft3_lb(v0),m3_kg_to_ft3_lb(v9))
                psv_result=calculate_two_phase_area(kg_h_to_lb_h(W),barg_to_psia(setb),barg_to_psia(bp),m3_kg_to_ft3_lb(v0),omega,kd,kb,kc,int(n)); psv_result["Omega"]=omega
            except Exception as e: st.error(str(e))
    elif service == "External Fire — Wetted Vessel":
        with st.form("psv_fire"):
            case_name=st.text_input("Scenario name",value="External Fire")
            a,b,c=st.columns(3); area=a.number_input("Wetted area (ft²)",0.001,value=1000.0); F=b.number_input("Environmental factor F",0.001,value=1.0); hvap=c.number_input("Latent heat (BTU/lb)",0.001,value=150.0)
            drainage=st.checkbox("Adequate drainage / firefighting",value=True)
            calc=st.form_submit_button("Calculate Relief Load",type="primary",use_container_width=True)
        if calc:
            try:
                w,qh=calculate_fire_wetted_load(area,F,hvap,drainage)
                psv_result={"Relief_Load_lb_h":w,"Heat_Input_BTU_h":qh}
            except Exception as e: st.error(str(e))
    elif service == "Thermal Expansion":
        with st.form("psv_thermal"):
            case_name=st.text_input("Scenario name",value="Blocked-in Thermal Expansion")
            a,b,c,d=st.columns(4); beta=a.number_input("Expansion coefficient (1/°F)",0.0000001,value=.0005,format="%.7f"); heat=b.number_input("Heat transfer (BTU/h)",0.001,value=170000.0); sg=c.number_input("Specific gravity",0.001,value=.8); cp=d.number_input("Specific heat (BTU/lb-°F)",0.001,value=.5)
            calc=st.form_submit_button("Calculate Relief Load",type="primary",use_container_width=True)
        if calc:
            try: psv_result={"Relief_Load_lb_h":calculate_thermal_expansion_load(beta,heat,sg,cp)}
            except Exception as e: st.error(str(e))
    else:
        with st.form("psv_pipe"):
            case_name="Piping Check"
            a,b,c=st.columns(3); q=a.number_input("Liquid flow (gpm)",0.0,value=100.0); rho=b.number_input("Density (lb/ft³)",0.001,value=50.0); mu=c.number_input("Viscosity (cP)",0.0001,value=1.0)
            a,b,c=st.columns(3); dia=a.number_input("Pipe ID (in)",0.001,value=3.0); length=b.number_input("Straight length (ft)",0.0,value=20.0); setpsig=c.number_input("PSV set pressure (psig)",0.001,value=100.0)
            a,b,c=st.columns(3); e90=a.number_input("90° elbows",0,20,value=2,step=1); e45=b.number_input("45° elbows",0,20,value=0,step=1); gates=c.number_input("Gate valves",0,20,value=1,step=1)
            calc=st.form_submit_button("Calculate Piping Check",type="primary",use_container_width=True)
        if calc:
            try:
                rr=calculate_inlet_pressure_drop(q,rho,mu,dia,length,int(e90),int(e45),int(gates)); passed,pct=check_inlet_rule(rr["delta_p_psi"],setpsig)
                psv_result={**rr,"Inlet_Rule_Pass":passed,"Inlet_Drop_Pct":pct}
            except Exception as e: st.error(str(e))

    if psv_result is not None:
        st.session_state["psv_last"]={"name":case_name,"service":service,"result":psv_result}
    last=st.session_state.get("psv_last")
    if last:
        st.subheader(f"Latest Result — {last['name']}")
        r=last["result"]
        area=r.get("Required_Area_sqin",r.get("Required_Area_Final_sqin"))
        letter=r.get("Selected_Orifice_Letter")
        cols=st.columns(4)
        if area is not None: cols[0].metric("Required Area",f"{area:.5f} in²")
        if letter is not None: cols[1].metric("API Orifice",str(letter))
        if r.get("Selected_Orifice_Area_sqin") is not None: cols[2].metric("Selected Area",f"{r['Selected_Orifice_Area_sqin']:.4f} in²")
        if r.get("Orifice_Loading_Pct") is not None: cols[3].metric("Loading",f"{r['Orifice_Loading_Pct']:.1f}%")
        st.dataframe(pd.DataFrame([[k,_fmt(v)] for k,v in r.items()],columns=["Parameter","Value"]),hide_index=True,use_container_width=True)
        if area is not None:
            if st.button("Add latest case to Scenario Register",type="primary"):
                st.session_state["psv_scenarios"].append({"Scenario":last["name"],"Service":last["service"],"Required Area (in²)":float(area),"Orifice":letter or "—"})
                st.success("Scenario added.")

    if st.session_state["psv_scenarios"]:
        st.subheader("Scenario Register")
        df=pd.DataFrame(st.session_state["psv_scenarios"])
        st.dataframe(df,hide_index=True,use_container_width=True)
        gov=max(st.session_state["psv_scenarios"],key=lambda x:x["Required Area (in²)"])
        st.success(f"Governing case: **{gov['Scenario']}** — {gov['Required Area (in²)']:.5f} in² — API orifice {gov['Orifice']}")
        st.download_button("Download Scenario Register CSV",df.to_csv(index=False).encode(),"psv_scenario_register.csv","text/csv")
        if st.button("Clear Scenario Register"): st.session_state["psv_scenarios"]=[]; st.rerun()


else:
    page_header("About / Method", "Application scope, calculation engines, and deployment notes.")
    st.markdown(f"""
### {APP_TITLE}
**{APP_VERSION}**  

This web edition wraps the same Python calculation engines used in the Windows edition into a responsive Streamlit interface.

**Included modules:**
- AGA 3 orifice-flow calculation and inverse bore sizing.
- AGA 8 DETAIL gas-property calculation with 21-component composition.
- Control Valve sizing for liquid, gas and steam services.
- PSV sizing and relief-load utilities for gas/vapor, steam, liquid, two-phase, fire, thermal expansion and piping checks.

### Engineering use
This application is intended as an engineering calculation aid. Confirm final designs against the applicable code edition, project basis, vendor-certified coefficients/capacities, material limits, piping configuration and process data.

### Session behavior
Browser-session values are kept in Streamlit session state. They are not a substitute for a project database. Use the download functions for records you need to retain.
""")
    project_snapshot={
        "generated_at":datetime.now().isoformat(timespec="seconds"),
        "app":APP_TITLE,"version":APP_VERSION,
        "aga3_last":st.session_state.get("aga3_last"),
        "aga8_last":st.session_state.get("aga8_last"),
        "psv_scenarios":st.session_state.get("psv_scenarios",[]),
    }
    st.download_button("Download current calculation snapshot (JSON)",json.dumps(project_snapshot,indent=2,default=str),"instrument_sizing_snapshot.json","application/json")

st.markdown(f'<div class="footnote">{APP_TITLE} · {APP_VERSION}</div>', unsafe_allow_html=True)

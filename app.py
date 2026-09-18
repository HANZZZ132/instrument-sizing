from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import AGA3
import aga7_engine
import aga8_detail
import electrical_engine as electrical

from psv_engine.gas_relief import calculate_gas_relief_area
from psv_engine.liquid_relief import calculate_liquid_relief_area
from psv_engine.two_phase import calculate_omega_flashing, calculate_two_phase_area
from psv_engine.fire_scenarios import calculate_fire_wetted_load, ENV_FACTORS
from psv_engine.thermal_expansion import calculate_thermal_expansion_load
from psv_engine.advanced_sizing import calculate_napier_steam_area
from psv_engine.piping import calculate_inlet_pressure_drop, check_inlet_rule, check_outlet_rule
from psv_engine.unit_converter import (
    barg_to_psia, barg_to_psig, kg_h_to_lb_h, c_to_rankine, m3_h_to_gpm, gpm_to_m3_h, m3_kg_to_ft3_lb,
)

APP_TITLE = "Instrument Sizing"
APP_VERSION = "Web 1.4.3 · AGA 7 Calculate"
BASE_DIR = Path(__file__).resolve().parent
INSTRUMENT_HERO_IMAGE = BASE_DIR / "assets" / "instrument_workspace_hero.png"
ELECTRICAL_HERO_IMAGE = BASE_DIR / "assets" / "electrical_workspace_hero.png"

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
    :root {
        --is-radius-lg: 22px;
        --is-radius-md: 16px;
        --is-shadow: 0 18px 45px rgba(15, 23, 42, .10);
        --is-border: color-mix(in srgb, var(--text-color) 14%, transparent);
        --is-muted: color-mix(in srgb, var(--text-color) 68%, transparent);
        --is-soft: color-mix(in srgb, var(--secondary-background-color) 88%, var(--primary-color) 12%);
    }

    /* App shell */
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 8% 0%, color-mix(in srgb, var(--primary-color) 16%, transparent), transparent 28rem),
            radial-gradient(circle at 100% 18%, rgba(0, 190, 255, .08), transparent 30rem),
            var(--background-color);
    }
    [data-testid="stHeader"] {background: transparent;}
    .block-container {padding-top: 1.1rem; padding-bottom: 4rem; max-width: 1480px;}

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #07182a 0%, #0a223a 55%, #071727 100%);
        border-right: 1px solid rgba(148, 163, 184, .18);
    }
    [data-testid="stSidebar"] * {color: #e7f0fa;}
    [data-testid="stSidebar"] [role="radiogroup"] label {
        padding: .55rem .65rem;
        border-radius: 12px;
        margin: .12rem 0;
        transition: all .18s ease;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255,255,255,.07);
        transform: translateX(2px);
    }
    .brand {
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, #0d3155 0%, #125dc1 62%, #12a4d9 100%);
        color:white;
        padding:1.25rem 1.15rem;
        border-radius:18px;
        margin:.35rem 0 1rem 0;
        box-shadow: 0 16px 34px rgba(0, 85, 170, .26);
    }
    .brand:after {
        content:""; position:absolute; width:120px; height:120px; border-radius:50%;
        right:-48px; top:-52px; background:rgba(255,255,255,.10);
    }
    .brand .eyebrow {font-size:.69rem; letter-spacing:.16em; font-weight:800; opacity:.72; text-transform:uppercase;}
    .brand h1 {font-size:1.42rem; margin:.18rem 0 .18rem 0; color:white; letter-spacing:.02em;}
    .brand p {margin:0; opacity:.78; font-size:.80rem;}

    /* Header / hero */
    .hero {
        position:relative; overflow:hidden;
        background: linear-gradient(130deg,#071a2d 0%,#0d3f73 42%,#1769e0 78%,#00a7d8 115%);
        color:white;
        padding:2.45rem 2.5rem;
        border-radius:28px;
        margin:.2rem 0 1.25rem 0;
        box-shadow:0 24px 55px rgba(0,73,155,.22);
        border:1px solid rgba(255,255,255,.10);
    }
    .hero:before, .hero:after {content:""; position:absolute; border-radius:999px; background:rgba(255,255,255,.08);}
    .hero:before {width:320px;height:320px;right:-100px;top:-180px;}
    .hero:after {width:200px;height:200px;right:140px;bottom:-150px;}
    .hero-kicker {display:inline-flex;align-items:center;gap:.45rem;padding:.38rem .72rem;border:1px solid rgba(255,255,255,.23);border-radius:999px;background:rgba(255,255,255,.08);font-size:.76rem;font-weight:750;letter-spacing:.08em;text-transform:uppercase;}
    .hero h1 {font-size:clamp(2.25rem,5vw,4rem);line-height:.96;margin:.85rem 0 .4rem 0;color:white;letter-spacing:-.035em;}
    .hero .desc {opacity:.84; max-width:880px; margin-top:.85rem; font-size:1.03rem; line-height:1.65;}
    .hero-chips {display:flex;gap:.55rem;flex-wrap:wrap;margin-top:1.25rem;}
    .hero-chip {padding:.42rem .72rem;border-radius:999px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.15);font-size:.78rem;font-weight:650;}

    /* Page section headers */
    .page-head {
        display:flex; align-items:flex-start; gap:.95rem;
        padding:1.15rem 1.25rem;
        margin:.2rem 0 1.1rem 0;
        background: color-mix(in srgb, var(--secondary-background-color) 91%, transparent);
        border:1px solid var(--is-border);
        border-radius:18px;
        box-shadow:0 8px 28px rgba(15,23,42,.05);
        backdrop-filter: blur(10px);
    }
    .page-icon {width:44px;height:44px;display:grid;place-items:center;border-radius:13px;background:linear-gradient(135deg,#1769e0,#00a7d8);box-shadow:0 8px 18px rgba(23,105,224,.24);font-size:1.2rem;flex:0 0 auto;}
    .section-title {font-size:1.55rem;font-weight:800;color:var(--text-color);margin:0;letter-spacing:-.02em;}
    .section-sub {color:var(--is-muted);margin:.2rem 0 0 0;line-height:1.5;font-size:.92rem;}

    /* Welcome module cards */
    .module-card {
        position:relative; overflow:hidden;
        background: color-mix(in srgb, var(--secondary-background-color) 95%, transparent);
        border:1px solid var(--is-border);
        border-radius:20px;
        padding:1.25rem 1.2rem 1.15rem;
        min-height:190px;
        box-shadow:0 10px 28px rgba(15,23,42,.06);
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }
    .module-card:hover {transform:translateY(-3px);box-shadow:0 18px 38px rgba(15,23,42,.11);border-color:color-mix(in srgb,var(--primary-color) 42%,transparent);}
    .module-card .mod-icon {width:44px;height:44px;display:grid;place-items:center;border-radius:13px;background:linear-gradient(135deg,#1769e0,#00a7d8);color:white;font-size:1.25rem;margin-bottom:.9rem;box-shadow:0 9px 19px rgba(23,105,224,.23);}
    .module-card h3 {margin:.15rem 0 .5rem 0;font-size:1.1rem;color:var(--text-color);}
    .module-card p {color:var(--is-muted);font-size:.88rem;line-height:1.48;margin:0;}
    .module-card .mod-tag {display:inline-block;margin-top:.8rem;padding:.25rem .5rem;border-radius:8px;background:var(--is-soft);font-size:.70rem;font-weight:700;color:var(--text-color);}

    .workflow {
        display:grid;grid-template-columns:repeat(4,1fr);gap:.7rem;
        background:color-mix(in srgb,var(--secondary-background-color) 93%,transparent);
        border:1px solid var(--is-border);border-radius:18px;padding:.9rem;margin:1.1rem 0;
    }
    .workflow-item {padding:.55rem .65rem;border-radius:12px;background:color-mix(in srgb,var(--background-color) 55%,transparent);}
    .workflow-item b {display:block;font-size:.78rem;margin-bottom:.13rem;}
    .workflow-item span {font-size:.73rem;color:var(--is-muted);}

    /* Streamlit native components */
    div[data-testid="stMetric"] {
        background: color-mix(in srgb, var(--secondary-background-color) 95%, transparent);
        border:1px solid var(--is-border);
        padding:.85rem 1rem;
        border-radius:16px;
        box-shadow:0 8px 22px rgba(15,23,42,.05);
    }
    div[data-testid="stMetric"] label {color:var(--is-muted)!important;font-weight:650!important;}
    div[data-testid="stMetricValue"] {font-weight:800;letter-spacing:-.02em;}
    div[data-testid="stForm"] {
        background: color-mix(in srgb, var(--secondary-background-color) 96%, transparent);
        border:1px solid var(--is-border);
        border-radius:18px;
        padding:1.05rem 1.05rem .55rem 1.05rem;
        box-shadow:0 10px 30px rgba(15,23,42,.05);
    }
    div[data-testid="stDataFrame"] {border:1px solid var(--is-border);border-radius:16px;overflow:hidden;}
    [data-testid="stExpander"] {border:1px solid var(--is-border)!important;border-radius:14px!important;background:color-mix(in srgb,var(--secondary-background-color) 95%,transparent)!important;}
    .stButton > button, .stFormSubmitButton > button {
        border-radius:12px!important;
        font-weight:750!important;
        min-height:2.75rem;
        transition:transform .15s ease, box-shadow .15s ease!important;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {transform:translateY(-1px);box-shadow:0 8px 18px rgba(23,105,224,.18)!important;}
    button[kind="primary"] {background:linear-gradient(135deg,#1769e0,#008fd5)!important;border:0!important;}
    [data-baseweb="tab-list"] {gap:.35rem;background:color-mix(in srgb,var(--secondary-background-color) 92%,transparent);padding:.35rem;border-radius:14px;border:1px solid var(--is-border);}
    [data-baseweb="tab"] {border-radius:10px;padding:.55rem .85rem;}
    [data-baseweb="tab"][aria-selected="true"] {background:color-mix(in srgb,var(--primary-color) 15%,transparent);}

    /* Alerts */
    .status-ok {padding:.75rem 1rem;border-radius:12px;background:rgba(18,183,106,.10);border:1px solid rgba(18,183,106,.30);color:var(--text-color);}
    .status-warn {padding:.75rem 1rem;border-radius:12px;background:rgba(247,144,9,.10);border:1px solid rgba(247,144,9,.30);color:var(--text-color);}
    .footnote {color:var(--is-muted);font-size:.80rem;margin-top:1.4rem;}
    .footer-line {margin-top:2rem;padding-top:1rem;border-top:1px solid var(--is-border);color:var(--is-muted);font-size:.76rem;text-align:center;}

    @media (max-width: 900px) {
        .block-container {padding:.65rem .7rem 3.5rem .7rem;}
        .hero {padding:1.55rem 1.25rem;border-radius:21px;}
        .hero h1 {font-size:2.35rem;}
        .hero .desc {font-size:.91rem;line-height:1.5;}
        .module-card {min-height:0;padding:1rem;}
        .workflow {grid-template-columns:1fr 1fr;}
        .page-head {padding:.9rem;border-radius:15px;}
    }
    @media (max-width: 520px) {
        .workflow {grid-template-columns:1fr;}
        .hero-chips {gap:.35rem;}
        .hero-chip {font-size:.70rem;}
        .section-title {font-size:1.28rem;}
        .page-icon {width:39px;height:39px;}
    }
</style>
""",
    unsafe_allow_html=True,
)


def _default(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


CALC_RESULT_KEYS = [
    "aga3_last", "aga3_last_mode", "aga7_range_last", "aga7_single_last", "aga8_last", "cv_last", "cv_last_service",
    "electrical_last", "electrical_candidates", "electrical_cb_i2t", "electrical_last_mode",
    "ground_conductor_last", "step_touch_last", "grid_resistance_last",
    "lightning_lps_last", "nfpa780_last", "psv_last"
]

PAGE_RESULT_KEYS = {
    "AGA 3 — Orifice Flow": ["aga3_last", "aga3_last_mode"],
    "AGA 7 — Turbine Meter": ["aga7_range_last", "aga7_single_last"],
    "AGA 8 — Gas Properties": ["aga8_last"],
    "Control Valve Sizing": ["cv_last", "cv_last_service"],
    "Electrical Sizing": [
        "electrical_last", "electrical_candidates", "electrical_cb_i2t", "electrical_last_mode",
        "ground_conductor_last", "step_touch_last", "grid_resistance_last",
        "lightning_lps_last", "nfpa780_last",
    ],
    "PSV Engineering": ["psv_last"],
}

def clear_calculation_results():
    """Manual fallback: clear all displayed outputs without deleting user inputs."""
    for _key in CALC_RESULT_KEYS:
        st.session_state.pop(_key, None)


def invalidate_current_page_results():
    """Automatically hide stale output as soon as an input on the current calculator changes."""
    _page = st.session_state.get("page")
    for _key in PAGE_RESULT_KEYS.get(_page, []):
        st.session_state.pop(_key, None)


def begin_new_result(*keys):
    """Invalidate previous output before a calculation so failed/revised cases never show stale results."""
    for _key in keys:
        st.session_state.pop(_key, None)


def _install_auto_invalidation():
    """
    Streamlit forms buffer input changes until submit, so this version uses normal
    bordered containers instead. These wrappers attach an on_change callback to
    ordinary input widgets, causing the displayed result for the active calculator
    to disappear immediately when the user edits an input.
    """
    try:
        from streamlit.delta_generator import DeltaGenerator
    except Exception:
        return

    widget_methods = (
        "number_input", "selectbox", "checkbox", "text_input", "radio",
        "segmented_control", "data_editor", "multiselect", "slider",
    )

    for _name in widget_methods:
        _original = getattr(DeltaGenerator, _name, None)
        if _original is None or getattr(_original, "_is_autoclear_wrapped", False):
            continue

        def _make_wrapper(original):
            def _wrapped(self, *args, **kwargs):
                kwargs.setdefault("on_change", invalidate_current_page_results)
                return original(self, *args, **kwargs)
            _wrapped._is_autoclear_wrapped = True
            return _wrapped

        setattr(DeltaGenerator, _name, _make_wrapper(_original))


_install_auto_invalidation()


def inject_suite_theme(active_suite: str):
    if active_suite == "Electrical":
        css = """
        <style>
            [data-testid="stAppViewContainer"] {
                background:
                    radial-gradient(circle at 15% 10%, rgba(255, 193, 7, .16), transparent 24rem),
                    radial-gradient(circle at 92% 6%, rgba(0, 229, 255, .14), transparent 26rem),
                    linear-gradient(135deg, rgba(255,193,7,.045) 0%, transparent 32%),
                    repeating-linear-gradient(135deg, rgba(255,193,7,.035) 0px, rgba(255,193,7,.035) 2px, transparent 2px, transparent 18px),
                    var(--background-color);
            }
            [data-testid="stSidebar"] {background: linear-gradient(180deg, #16120a 0%, #241a08 48%, #111820 100%);}
            .brand {background: linear-gradient(135deg, #3a2904 0%, #9a6b00 52%, #f0a500 100%); box-shadow: 0 16px 34px rgba(173, 112, 0, .28);}
            .hero {background: linear-gradient(130deg,#17120b 0%,#5b4307 40%,#e59d00 76%,#ffd54f 115%); box-shadow:0 24px 55px rgba(131,90,0,.24);}
            .page-icon, .module-card .mod-icon {background: linear-gradient(135deg,#8e6200,#f0a500); box-shadow:0 8px 18px rgba(173,112,0,.24);}
            button[kind="primary"] {background: linear-gradient(135deg,#8e6200,#f0a500)!important;}
            .suite-badge {background: linear-gradient(135deg,#fff7e1,#fff2bf); border:1px solid rgba(240,165,0,.28); color:#6e5000;}
        </style>
        """
    else:
        css = """
        <style>
            [data-testid="stAppViewContainer"] {
                background:
                    radial-gradient(circle at 8% 0%, rgba(23, 105, 224, .14), transparent 28rem),
                    radial-gradient(circle at 100% 18%, rgba(0, 190, 255, .10), transparent 30rem),
                    linear-gradient(135deg, rgba(0,167,216,.035) 0%, transparent 33%),
                    repeating-linear-gradient(135deg, rgba(23,105,224,.03) 0px, rgba(23,105,224,.03) 2px, transparent 2px, transparent 18px),
                    var(--background-color);
            }
            [data-testid="stSidebar"] {background: linear-gradient(180deg, #07182a 0%, #0a223a 55%, #071727 100%);}
            .brand {background: linear-gradient(135deg, #0d3155 0%, #125dc1 62%, #12a4d9 100%); box-shadow: 0 16px 34px rgba(0, 85, 170, .26);}
            .hero {background: linear-gradient(130deg,#071a2d 0%,#0d3f73 42%,#1769e0 78%,#00a7d8 115%); box-shadow:0 24px 55px rgba(0,73,155,.22);}
            .page-icon, .module-card .mod-icon {background: linear-gradient(135deg,#1769e0,#00a7d8); box-shadow:0 8px 18px rgba(23,105,224,.24);}
            button[kind="primary"] {background: linear-gradient(135deg,#1769e0,#008fd5)!important;}
            .suite-badge {background: linear-gradient(135deg,#e9f4ff,#def7ff); border:1px solid rgba(23,105,224,.20); color:#0b4674;}
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)


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
    icon_map = {
        "AGA 3": "◫", "AGA 8": "⬡", "Control Valve": "◉",
        "Electrical": "⚡", "PSV": "◆", "About": "i",
    }
    icon = next((v for k, v in icon_map.items() if title.startswith(k)), "▣")
    st.markdown(
        f'<div class="page-head"><div class="page-icon">{icon}</div>'
        f'<div><div class="section-title">{title}</div><div class="section-sub">{subtitle}</div></div></div>',
        unsafe_allow_html=True,
    )


def goto(page, suite=None):
    # Do not mutate a session-state key after the widget using that key
    # has already been instantiated in the current Streamlit run.
    # Queue the requested workspace/page, then apply it on the next rerun
    # before sidebar widgets are created.
    if suite is not None:
        st.session_state["suite_request"] = suite
    st.session_state["nav_request"] = page
    st.rerun()


_default("suite", "Instrument")

# Apply queued navigation requests BEFORE sidebar widgets are instantiated.
if "suite_request" in st.session_state:
    st.session_state["suite"] = st.session_state.pop("suite_request")
if "nav_request" in st.session_state:
    st.session_state["page"] = st.session_state.pop("nav_request")

INSTRUMENT_PAGES = ["Welcome", "Instrument Home", "AGA 3 — Orifice Flow", "AGA 7 — Turbine Meter", "AGA 8 — Gas Properties", "Control Valve Sizing", "PSV Engineering", "About / Method"]
ELECTRICAL_PAGES = ["Welcome", "Electrical Home", "Electrical Sizing", "About / Method"]
NAV_LABELS = {
    "Welcome": "⌂  Main Welcome",
    "Instrument Home": "🧪  Instrument Home",
    "Electrical Home": "⚡  Electrical Home",
    "AGA 3 — Orifice Flow": "◫  AGA 3 · Orifice Flow",
    "AGA 7 — Turbine Meter": "◎  AGA 7 · Turbine Meter",
    "AGA 8 — Gas Properties": "⬡  AGA 8 · Gas Properties",
    "Control Valve Sizing": "◉  Control Valve Sizing",
    "Electrical Sizing": "⚡  Electrical Sizing",
    "PSV Engineering": "◆  PSV Engineering",
    "About / Method": "ⓘ  About / Method",
}
SUITE_LABELS = {"Instrument": "🧪  Instrument", "Electrical": "⚡  Electrical"}
suite = st.session_state.get("suite", "Instrument")
PAGES = INSTRUMENT_PAGES if suite == "Instrument" else ELECTRICAL_PAGES
if st.session_state.get("page") not in PAGES:
    st.session_state["page"] = "Welcome"
with st.sidebar:
    st.markdown(
        f'<div class="brand"><div class="eyebrow">Engineering Toolkit</div><h1>{APP_TITLE}</h1><p>{APP_VERSION}</p></div>',
        unsafe_allow_html=True,
    )
    st.caption("WORKSPACE")
    suite = st.radio("Workspace", ["Instrument", "Electrical"], key="suite", label_visibility="collapsed", format_func=lambda x: SUITE_LABELS[x])
    PAGES = INSTRUMENT_PAGES if suite == "Instrument" else ELECTRICAL_PAGES
    if st.session_state.get("page") not in PAGES:
        st.session_state["page"] = "Welcome"
    st.divider()
    st.caption("NAVIGATION")
    page = st.radio("Navigation", PAGES, key="page", label_visibility="collapsed", format_func=lambda x: NAV_LABELS[x])
    st.divider()
    st.caption("↻ Results automatically disappear when calculator inputs are changed. Recalculate to show the new result.")
    st.caption("Calculation aid for engineering screening and sizing. Verify final design against project standards and certified vendor data.")

inject_suite_theme(suite)

if page == "Welcome":
    # Neutral landing page: choose the discipline first.
    st.markdown(
        '<div class="hero">'
        '<div class="hero-kicker">●  INTEGRATED ENGINEERING PLATFORM</div>'
        '<h1>ENGINEERING<br>CALCULATION HUB</h1>'
        '<div class="desc">One platform for dedicated Instrument and Electrical engineering workspaces — built for faster calculations, cleaner navigation, and focused technical workflows.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Choose your workspace")
    left_ws, right_ws = st.columns(2)

    with left_ws:
        if INSTRUMENT_HERO_IMAGE.exists():
            st.image(str(INSTRUMENT_HERO_IMAGE), use_container_width=True)
        st.markdown(
            '<div class="module-card"><div class="mod-icon">🧪</div><h3>Instrument Workspace</h3>'
            '<p>Process & instrumentation calculations for orifice metering, turbine metering, gas properties, control valves, and pressure safety valves.</p>'
            '<span class="mod-tag">AGA 3 · AGA 7 · AGA 8 · Control Valve · PSV</span></div>',
            unsafe_allow_html=True,
        )
        if st.button("Enter Instrument Workspace  →", key="enter_instrument", type="primary", use_container_width=True):
            goto("Instrument Home", suite="Instrument")

    with right_ws:
        if ELECTRICAL_HERO_IMAGE.exists():
            st.image(str(ELECTRICAL_HERO_IMAGE), use_container_width=True)
        st.markdown(
            '<div class="module-card"><div class="mod-icon">⚡</div><h3>Electrical Workspace</h3>'
            '<p>Electrical calculations for cables, voltage drop, grounding, step/touch voltage, and lightning protection.</p>'
            '<span class="mod-tag">Cable · Grounding · Lightning · Panels</span></div>',
            unsafe_allow_html=True,
        )
        if st.button("Enter Electrical Workspace  →", key="enter_electrical", use_container_width=True):
            goto("Electrical Home", suite="Electrical")

    st.info("The sidebar workspace selector can also switch disciplines. Each discipline now has its own Home page and its own navigation list.")

elif page == "Instrument Home":
    st.markdown(
        '<div class="hero">'
        '<div class="hero-kicker">●  PROCESS & INSTRUMENT ENGINEERING</div>'
        '<h1>INSTRUMENT<br>SIZING</h1>'
        '<div class="desc">Dedicated process and instrumentation workspace for orifice metering, turbine-meter conversion and screening, gas properties, control valve sizing, pressure safety valves, gauges, and PLC-oriented engineering workflows.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if INSTRUMENT_HERO_IMAGE.exists():
        st.image(str(INSTRUMENT_HERO_IMAGE), use_container_width=True)

    st.markdown("### Instrument modules")
    c1, c2, c3 = st.columns(3)
    c4, c5, _ = st.columns([1, 1, 1])
    cards = [
        (c1, "◫", "AGA 3", "Orifice gas flow and inverse bore sizing.", "Orifice Metering", "AGA 3 — Orifice Flow"),
        (c2, "◎", "AGA 7", "Turbine-meter base/line flow conversion and meter-range screening.", "Turbine Meter", "AGA 7 — Turbine Meter"),
        (c3, "⬡", "AGA 8 DETAIL", "Gas Z-factor, density, MW and Fpv.", "Gas Properties", "AGA 8 — Gas Properties"),
        (c4, "◉", "Control Valve", "Liquid, gas and steam Cv/Kv sizing.", "Valve Sizing", "Control Valve Sizing"),
        (c5, "◆", "PSV Engineering", "Relief sizing, API orifice selection and scenario checks.", "Relief Systems", "PSV Engineering"),
    ]
    for col, icon, title, desc, tag, target in cards:
        with col:
            st.markdown(
                f'<div class="module-card"><div class="mod-icon">{icon}</div><h3>{title}</h3><p>{desc}</p><span class="mod-tag">{tag}</span></div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Open {title}  →", key=f"inst_{target}", use_container_width=True):
                goto(target, suite="Instrument")

    st.success("Instrument workspace only. Electrical modules are intentionally excluded from this navigation.")

elif page == "Electrical Home":
    st.markdown(
        '<div class="hero">'
        '<div class="hero-kicker">●  ELECTRICAL ENGINEERING</div>'
        '<h1>ELECTRICAL<br>SIZING</h1>'
        '<div class="desc">Dedicated electrical workspace for cable sizing, voltage drop, grounding, step & touch voltage, ground-grid resistance, and conventional/ESE lightning protection.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if ELECTRICAL_HERO_IMAGE.exists():
        st.image(str(ELECTRICAL_HERO_IMAGE), use_container_width=True)

    st.markdown("### Electrical modules")
    st.markdown(
        '<div class="module-card"><div class="mod-icon">⚡</div><h3>Electrical Sizing</h3>'
        '<p>Cable sizing, voltage drop, grounding, step/touch voltage, earth-grid resistance, NFPA 780 rolling sphere, and NF C 17-102 ESE.</p>'
        '<span class="mod-tag">Cable · Grounding · Lightning · Panels</span></div>',
        unsafe_allow_html=True,
    )
    if st.button("Open Electrical Sizing  →", key="elec_open_sizing", type="primary", use_container_width=True):
        goto("Electrical Sizing", suite="Electrical")

    st.success("Electrical workspace only. AGA, Control Valve and PSV modules are intentionally excluded from this navigation.")

elif page == "AGA 7 — Turbine Meter":
    page_header("AGA 7 — Turbine Meter", "Convert between base and flowing volume, reproduce the project workbook workflow, and screen turbine-meter G rating against actual line flow.")

    for k, v in {
        "a7_qmax": 1283.0, "a7_qmin": 515.0,
        "a7_pmin": 1.0, "a7_pmax": 4.0,
        "a7_pb": 1.01325, "a7_patm": 1.013253,
        "a7_tf": 32.0, "a7_tb": 15.555556,
        "a7_zratio": 1.0, "a7_cont": 80.0,
        "a7_qf_single": 250.0, "a7_pg_single": 4.0,
    }.items(): _default(k, v)

    st.info("**AGA 7 Appendix B basis.** Pressure in the gas-law conversion is absolute. The project workbook is reproduced as a selectable legacy mode, while standard mode uses °C + 273.15 K.")

    mode1, mode2, mode3 = st.tabs(["Flow Range / G-Size", "Single Conversion", "Method & Source"])

    with mode1:
        left, right = st.columns([1.05, .95])
        with left:
            st.markdown("##### Base-condition demand")
            a,b = st.columns(2)
            qmin = a.number_input("Base flow minimum (Sm³/h)", min_value=0.0, key="a7_qmin", format="%.6f")
            qmax = b.number_input("Base flow maximum (Sm³/h)", min_value=0.0, key="a7_qmax", format="%.6f")
            a,b = st.columns(2)
            pmin = a.number_input("Operating pressure minimum (barg)", key="a7_pmin", format="%.6f")
            pmax = b.number_input("Operating pressure maximum (barg)", key="a7_pmax", format="%.6f")
            a,b = st.columns(2)
            tf = a.number_input("Average flowing temperature (°C)", key="a7_tf", format="%.6f")
            tb = b.number_input("Base temperature (°C)", key="a7_tb", format="%.6f")
            a,b,c = st.columns(3)
            pb = a.number_input("Base pressure Pb (bar abs)", min_value=0.000001, key="a7_pb", format="%.6f")
            patm = b.number_input("Atmospheric pressure Pa (bar abs)", min_value=0.000001, key="a7_patm", format="%.6f")
            zratio = c.number_input("Zf / Zb", min_value=0.000001, key="a7_zratio", format="%.8f")

            if st.button("Use latest AGA 8 Zf/Zb", key="a7_use_a8", use_container_width=True):
                r8 = st.session_state.get("aga8_last")
                if r8:
                    begin_new_result("aga7_range_last", "aga7_single_last")
                    st.session_state["a7_zratio"] = r8["flowing"]["Z"] / r8["base"]["Z"]
                    st.success("Zf/Zb transferred from the latest AGA 8 calculation.")
                    st.rerun()
                else:
                    st.warning("No AGA 8 result is available yet.")

            basis = st.radio(
                "Flow-range pairing",
                ["Project paired conditions", "Conservative envelope"],
                horizontal=True,
                key="a7_pairing",
                help="Project paired: Qmin@Pmin and Qmax@Pmax. Conservative envelope: Qmin@Pmax and Qmax@Pmin.",
            )
            legacy = st.checkbox("Legacy Excel match: use 273.0 instead of 273.15 for °C → K", value=False, key="a7_legacy_range")
            continuous_pct = st.slider("Continuous-use target (% of screening Qmax)", min_value=50, max_value=100, value=int(st.session_state["a7_cont"]), step=5, key="a7_cont_slider")

            calculate_range = st.button(
                "Calculate Flow Range / G-Size",
                key="a7_calculate_range",
                type="primary",
                use_container_width=True,
            )

            if calculate_range:
                begin_new_result("aga7_range_last")
                try:
                    rr = aga7_engine.calculate_flow_range(
                        qmin, qmax, pmin, pmax,
                        base_pressure_bar_abs=pb,
                        flowing_temp_c=tf, base_temp_c=tb,
                        zf_over_zb=zratio, atmospheric_bar_abs=patm,
                        pairing="conservative" if basis == "Conservative envelope" else "paired",
                        legacy_excel_temperature_offset=legacy,
                    )
                    rec = aga7_engine.recommend_g_rating(rr["Actual_Max_m3_h"], continuous_pct/100.0)
                    flange = aga7_engine.workbook_flange_screening(pmax)
                    st.session_state["aga7_range_last"] = {
                        "rr": rr,
                        "rec": rec,
                        "flange": flange,
                        "continuous_pct": continuous_pct,
                        "legacy": legacy,
                    }
                except Exception as e:
                    st.error(str(e))

        with right:
            result = st.session_state.get("aga7_range_last")
            if result is None:
                st.info("Masukkan / ubah input di kiri, lalu klik **Calculate Flow Range / G-Size** untuk menampilkan hasil.")
            else:
                rr = result["rr"]
                rec = result["rec"]
                flange = result["flange"]
                saved_continuous_pct = result["continuous_pct"]
                m1,m2,m3 = st.columns(3)
                m1.metric("Actual line flow min", f"{rr['Actual_Min_m3_h']:.3f} m³/h")
                m2.metric("Actual line flow max", f"{rr['Actual_Max_m3_h']:.3f} m³/h")
                m3.metric("Actual rangeability", f"{rr['Actual_Rangeability']:.2f}:1")
                st.markdown("##### Turbine meter screening")
                a,b,c = st.columns(3)
                a.metric("Minimum by nominal Qmax", str(rec["Minimum_By_Qmax"]))
                b.metric("Recommended continuous", str(rec["Recommended_Continuous"]))
                util = rec["Recommended_Utilization_pct"]
                c.metric("Recommended utilization", "—" if util is None else f"{util:.1f}%")
                st.caption(rr["Pairing_Basis"])
                st.warning("AGA 7 does **not** prescribe the G-rating table used here. Final selection must be checked against the selected manufacturer's operating flow range at the actual pressure, density, calibration basis, pressure loss and service conditions.")
                with st.expander("Project workbook flange screening (not final ASME rating)"):
                    st.write(f"**{flange}**")
                    st.caption("This reproduces the workbook's simple pressure threshold screening only. Verify material, temperature, flange standard and vendor MAOP separately.")

                table = pd.DataFrame(aga7_engine.g_rating_table(saved_continuous_pct/100.0))
                st.dataframe(table, hide_index=True, use_container_width=True)

        if legacy:
            st.caption("Legacy Excel regression: with Qmin=515 Sm³/h @ 1 barg and Qmax=1283 Sm³/h @ 4 barg, T=32°C, Tb=15.555556°C, Pb=1.01325 bar abs and Zf/Zb=1, the project paired results are approximately 273.966 and 274.091 m³/h.")

    with mode2:
        st.markdown("##### Single base / line-flow conversion")
        direction = st.segmented_control("Conversion direction", ["Base → Flowing", "Flowing → Base"], default="Base → Flowing", key="a7_direction")
        a,b,c = st.columns(3)
        if direction == "Base → Flowing":
            qsingle = a.number_input("Base flow Qb (Sm³/h)", min_value=0.0, value=float(st.session_state["a7_qmax"]), key="a7_single_qb")
        else:
            qsingle = a.number_input("Flowing/line flow Qf (m³/h)", min_value=0.0, key="a7_qf_single")
        pgsingle = b.number_input("Flowing pressure Pg (barg)", key="a7_pg_single")
        legacy2 = c.checkbox("Legacy Excel 273.0 K offset", value=False, key="a7_legacy_single")
        a,b,c,d,e = st.columns(5)
        tf2 = a.number_input("Tf (°C)", key="a7_tf_single", value=float(st.session_state["a7_tf"]))
        tb2 = b.number_input("Tb (°C)", key="a7_tb_single", value=float(st.session_state["a7_tb"]))
        pb2 = c.number_input("Pb (bar abs)", min_value=0.000001, key="a7_pb_single", value=float(st.session_state["a7_pb"]))
        pa2 = d.number_input("Pa (bar abs)", min_value=0.000001, key="a7_pa_single", value=float(st.session_state["a7_patm"]))
        zr2 = e.number_input("Zf/Zb", min_value=0.000001, key="a7_zr_single", value=float(st.session_state["a7_zratio"]), format="%.8f")

        calculate_single = st.button(
            "Calculate Conversion",
            key="a7_calculate_single",
            type="primary",
            use_container_width=True,
        )
        if calculate_single:
            begin_new_result("aga7_single_last")
            try:
                if direction == "Base → Flowing":
                    sr = aga7_engine.flowing_rate_from_base(qsingle, pgsingle, pb2, tf2, tb2, zr2, pa2, legacy2)
                    result_label = "Flowing / line flow Qf"
                    result_value = f"{sr['Q_flowing_m3_h']:.6f} m³/h"
                else:
                    sr = aga7_engine.base_rate_from_flowing(qsingle, pgsingle, pb2, tf2, tb2, zr2, pa2, legacy2)
                    result_label = "Base flow Qb"
                    result_value = f"{sr['Q_base_sm3_h']:.6f} Sm³/h"
                st.session_state["aga7_single_last"] = {
                    "sr": sr,
                    "label": result_label,
                    "value": result_value,
                }
            except Exception as e:
                st.error(str(e))

        single_result = st.session_state.get("aga7_single_last")
        if single_result is None:
            st.info("Ubah input bila perlu, lalu klik **Calculate Conversion**.")
        else:
            st.metric(single_result["label"], single_result["value"])
            st.dataframe(pd.DataFrame([[k,v] for k,v in single_result["sr"].items()], columns=["Parameter","Value"]), hide_index=True, use_container_width=True)

    with mode3:
        st.markdown("##### AGA Report No. 7 basis")
        st.markdown(r"""
The module uses the Appendix B gas-law relationship between flowing and base conditions:

**Qb = Qf × (Pf/Pb) × (Tb/Tf) × (Zb/Zf)**

and its inverse:

**Qf = Qb × (Pb/Pf) × (Tf/Tb) × (Zf/Zb)**

where pressure and temperature are **absolute**. The operating gauge pressure is converted to absolute pressure using **Pf = Pg + Pa**.

The project workbook workflow is retained as a selectable legacy mode, but its G-size recommendation logic is not copied as a standard rule because the workbook contains inconsistent/corrupted selection cells. Final turbine-meter range must be verified against manufacturer data.
""")
        st.markdown("##### Project Excel source")
        st.code("Cari Meter Turbin(2).xlsx  |  password supplied by user during analysis  |  source not redistributed", language="text")
        st.caption("The password is not stored in the application package.")

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
        with st.container(border=True):
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
            submitted = st.button("Calculate AGA 3", type="primary", use_container_width=True)
        if st.button("Use latest AGA 8 T/P + densities", use_container_width=True):
            r8 = st.session_state.get("aga8_last")
            if not r8:
                st.warning("Calculate AGA 8 first.")
            else:
                begin_new_result("aga3_last", "aga3_last_mode")
                st.session_state["a3_T_f"] = st.session_state.get("a8_T", 65.0)
                st.session_state["a3_P_f"] = st.session_state.get("a8_P", 750.5)
                st.session_state["a3_rho_f"] = r8["flowing"]["density_lb_ft3"]
                st.session_state["a3_rho_b"] = r8["base"]["density_lb_ft3"]
                st.rerun()

    if submitted:
        begin_new_result("aga3_last", "aga3_last_mode")
        try:
            vals = {"T_f": T_f, "P_f": P_f, "dP": dP, "D_pipe": D_pipe, "alpha_orifice": alpha_o,
                    "alpha_pipe": alpha_p, "k": k, "mu": mu, "rho_f": rho_f, "rho_b": rho_b}
            if mode == "Flow Rate":
                r = aga3_core(vals, d_orifice, downstream)
            else:
                r = solve_orifice_reference(vals, target / 0.000024, downstream)
                st.session_state["a3_d_orifice"] = r["d_ref"]
            st.session_state["aga3_last"] = r
            st.session_state["aga3_last_mode"] = mode
        except Exception as e:
            st.error(f"Calculation error: {e}")

    with right:
        r = st.session_state.get("aga3_last") if st.session_state.get("aga3_last_mode") == mode else None
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
        with st.container(border=True):
            a, b = st.columns(2)
            T = a.number_input("Flowing temperature (°F)", key="a8_T", format="%.4f")
            P = b.number_input("Flowing pressure (psia abs)", key="a8_P", min_value=0.000001, format="%.4f")
            Tb = a.number_input("Base temperature (°F)", key="a8_Tb", format="%.4f")
            Pb = b.number_input("Base pressure (psia abs)", key="a8_Pb", min_value=0.000001, format="%.4f")
            calc8 = st.button("Calculate AGA 8", type="primary", use_container_width=True)
        c1, c2, c3 = st.columns(3)
        if c1.button("Gulf Coast", use_container_width=True):
            begin_new_result("aga8_last")
            st.session_state["a8_comp"] = GULF_COAST.copy(); st.rerun()
        if c2.button("Amarillo", use_container_width=True):
            begin_new_result("aga8_last")
            st.session_state["a8_comp"] = AMARILLO.copy(); st.rerun()
        if c3.button("Normalize", use_container_width=True):
            begin_new_result("aga8_last")
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
        begin_new_result("aga8_last")
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
            begin_new_result("aga3_last", "aga3_last_mode")
            st.session_state["a3_T_f"] = st.session_state["a8_T"]
            st.session_state["a3_P_f"] = st.session_state["a8_P"]
            st.session_state["a3_rho_f"] = f["density_lb_ft3"]
            st.session_state["a3_rho_b"] = b["density_lb_ft3"]
            st.success("Transferred. Open AGA 3 from the sidebar.")
        if c2.button("Send gas properties to Control Valve", use_container_width=True):
            begin_new_result("cv_last", "cv_last_service")
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
        with st.container(border=True):
            a,b,c = st.columns(3)
            q=a.number_input("Flow (m³/h)", 0.0001, value=25.0); p1=b.number_input("P1 (bara)", 0.0001, value=8.0); p2=c.number_input("P2 (bara)", 0.0001, value=5.0)
            a,b,c = st.columns(3)
            rho=a.number_input("Density (kg/m³)", 0.001, value=998.0); pv=b.number_input("Vapor pressure (bara)", 0.0, value=0.03); pc=c.number_input("Critical pressure (bara)", 0.001, value=220.64)
            a,b,c = st.columns(3)
            mu=a.number_input("Viscosity (Pa·s)", 0.0000001, value=0.00089, format="%.7f"); d1=b.number_input("Inlet pipe ID (mm, 0=auto)", 0.0, value=0.0); d2=c.number_input("Outlet pipe ID (mm, 0=auto)",0.0,value=0.0)
            submit=st.button("Calculate Control Valve", type="primary", use_container_width=True)
        if submit:
            begin_new_result("cv_last", "cv_last_service")
            try:
                data=LiquidSizingInput(q,p1,p2,rho,pv,pc,mu,fl=vd.fl or .85,fd=vd.fd or 1.0,pipe_inlet_diameter_mm=d1 or None,pipe_outlet_diameter_mm=d2 or None)
                st.session_state["cv_last"]=size_liquid_valve(data,valve_series=list(vd.sizes),valve_meta={"vendor":vd.vendor,"style":vd.style})
                st.session_state["cv_last_service"] = service
            except Exception as e: st.error(str(e))
    elif service == "Gas":
        _default("cv_gas_temp",20.0); _default("cv_gas_mw",18.0); _default("cv_gas_z",0.98)
        with st.container(border=True):
            a,b,c = st.columns(3)
            q=a.number_input("Normal flow (Nm³/h)",0.0001,value=800.0); p1=b.number_input("P1 (bara)",0.0001,value=8.0); p2=c.number_input("P2 (bara)",0.0001,value=6.0)
            a,b,c = st.columns(3)
            temp=a.number_input("Temperature (°C)",key="cv_gas_temp"); mw=b.number_input("Molecular weight",0.001,key="cv_gas_mw"); z=c.number_input("Z-factor",0.001,key="cv_gas_z")
            a,b,c = st.columns(3)
            kr=a.number_input("k = Cp/Cv",0.1,value=1.28); mu=b.number_input("Viscosity (Pa·s)",0.00000001,value=1.1e-5,format="%.8f"); d1=c.number_input("Inlet pipe ID (mm, 0=auto)",0.0,value=0.0)
            d2=st.number_input("Outlet pipe ID (mm, 0=auto)",0.0,value=0.0)
            submit=st.button("Calculate Control Valve", type="primary", use_container_width=True)
        if submit:
            begin_new_result("cv_last", "cv_last_service")
            try:
                data=GasSizingInput(q,p1,p2,temp,mw,kr,mu,z=z,fl=vd.fl or .85,fd=vd.fd or 1.0,xt=vd.xt or .69,pipe_inlet_diameter_mm=d1 or None,pipe_outlet_diameter_mm=d2 or None)
                st.session_state["cv_last"]=size_gas_valve(data,valve_series=list(vd.sizes),valve_meta={"vendor":vd.vendor,"style":vd.style})
                st.session_state["cv_last_service"] = service
            except Exception as e: st.error(str(e))
    else:
        with st.container(border=True):
            a,b,c=st.columns(3)
            q=a.number_input("Steam flow (kg/h)",0.0001,value=2500.0); p1=b.number_input("P1 (bara)",0.0001,value=12.0); p2=c.number_input("P2 (bara)",0.0001,value=8.0)
            a,b,c=st.columns(3)
            temp=a.number_input("Temperature (°C)",value=220.0); kr=b.number_input("k = Cp/Cv",0.1,value=1.30); z=c.number_input("Z-factor",0.001,value=1.0)
            a,b=st.columns(2); d1=a.number_input("Inlet pipe ID (mm, 0=auto)",0.0,value=0.0); d2=b.number_input("Outlet pipe ID (mm, 0=auto)",0.0,value=0.0)
            submit=st.button("Calculate Control Valve", type="primary", use_container_width=True)
        if submit:
            begin_new_result("cv_last", "cv_last_service")
            try:
                data=SteamSizingInput(q,p1,p2,temp,specific_heat_ratio=kr,z=z,fl=vd.fl or .85,fd=vd.fd or 1.0,xt=vd.xt or .69,pipe_inlet_diameter_mm=d1 or None,pipe_outlet_diameter_mm=d2 or None)
                st.session_state["cv_last"]=size_steam_valve(data,valve_series=list(vd.sizes),valve_meta={"vendor":vd.vendor,"style":vd.style})
                st.session_state["cv_last_service"] = service
            except Exception as e: st.error(str(e))

    r=st.session_state.get("cv_last") if st.session_state.get("cv_last_service") == service else None
    if r:
        m1,m2,m3,m4=st.columns(4)
        m1.metric("Required Cv",_fmt(r.required_cv,4)); m2.metric("Required Kv",_fmt(r.required_kv,4)); m3.metric("Selected Valve",f"DN {r.valve_dn_mm} ({r.valve_inch})"); m4.metric("Rated Cv",_fmt(r.rated_cv,3))
        st.success("Choked flow: YES" if r.is_choked else "Choked flow: NO")
        rows=[["ΔP",r.delta_p_bar,"bar"],["Noise estimate",r.get("noise_db"),"dB(A)"],["Actuator thrust estimate",r.get("actuator_thrust_n"),"N"],["Valve Reynolds",r.get("reynolds_valve"),"—"]]
        if r.get("expansion_factor_y") is not None: rows.append(["Expansion factor Y",r.get("expansion_factor_y"),"—"])
        if r.get("flow_regime") is not None: rows.append(["Flow regime",r.get("flow_regime"),"—"])
        st.dataframe(pd.DataFrame(rows,columns=["Parameter","Value","Unit"]),hide_index=True,use_container_width=True)
        if r.warning: st.warning(r.warning)



elif page == "Electrical Sizing":
    page_header("Electrical Sizing", "Cable sizing, voltage drop, IEEE 80 grounding, conventional NFPA 780 rolling-sphere screening, lightning earthing, and NF C 17-102 ESE screening.")
    st.caption("Source basis: Lampiran C — Cable Sizing / Voltage Drop; Lampiran 2 — grounding and App-1C LPS earthing; NFPA 780 (2000) — traditional rolling-sphere screening; NF C 17-102:2011 — ESE protection radius and installation screening.")

    etab1, etab2, etab3, etab4, etab5, etab6, etab7 = st.tabs([
        "⚡ Cable Sizing", "⏚ Ground Conductor", "⚠ Step & Touch", "▦ Grid Resistance", "⚡ Lightning Earthing", "⛈ NFPA 780 Rolling Sphere", "⚡ ESE — NF C 17-102"
    ])

    with etab1:
        st.markdown("#### Cable Sizing & Voltage Drop")
        mode = st.segmented_control("Mode", ["Auto Select", "Check Selected Cable"], default="Auto Select", key="elec_cable_mode")
        c0, c1, c2 = st.columns(3)
        voltage = c0.selectbox("Nominal voltage", [400.0, 230.0, 220.0, 6600.0, 20000.0], format_func=lambda x: f"{x/1000:g} kV" if x >= 1000 else f"{x:g} V", key="elec_voltage")
        default_sys = "DC" if voltage == 220 else ("1-Phase AC" if voltage == 230 else "3-Phase AC")
        system = c1.selectbox("System", ["3-Phase AC", "1-Phase AC", "DC"], index=["3-Phase AC","1-Phase AC","DC"].index(default_sys), key="elec_system")
        load_type = c2.selectbox("Load type", ["Feeder", "Motor"], disabled=(system == "DC"), key="elec_load_type")
        if system == "DC":
            load_type = "Feeder"

        if voltage > 1000:
            inst_options = ["Above Ground / In Air", "Direct Buried", "Buried Ducts", "Buried Direct @20°C"]
            cores = 3
        else:
            inst_options = ["Above Ground / In Tray", "In Ducts", "Direct Buried", "Buried Ducts"]
            default_core = 4 if system == "3-Phase AC" else 2
            cores = st.selectbox("Cable cores", [1,2,3,4], index=[1,2,3,4].index(default_core), key="elec_cores")
        installation = st.selectbox("Installation method", inst_options, key="elec_install")

        with st.container(border=True):
            a,b,c,d = st.columns(4)
            load_kw = a.number_input("Load rating (kW)", min_value=0.001, value=37.0 if load_type == "Motor" else 360.0, format="%.3f")
            pf = b.number_input("Power factor", min_value=0.01, max_value=1.0, value=0.89 if load_type == "Motor" else (1.0 if system == "DC" else 0.80), format="%.3f", disabled=(system == "DC"))
            if system == "DC": pf = 1.0
            eff = c.number_input("Efficiency", min_value=0.01, max_value=1.0, value=0.94 if load_type == "Motor" else 1.0, format="%.3f")
            length_m = d.number_input("Cable length (m)", min_value=0.0, value=160.0 if load_type == "Motor" else 35.0, format="%.2f")
            a,b,c,d = st.columns(4)
            derating = a.number_input("Total derating factor K", min_value=0.01, max_value=1.5, value=0.66 if voltage <= 1000 else 0.63, format="%.3f")
            max_vd = b.number_input("Max steady-state VD (%)", min_value=0.01, value=5.0 if voltage <= 1000 else 1.0, format="%.2f")
            k_factor = c.number_input("Short-circuit k factor", min_value=1.0, value=143.0, format="%.1f")
            max_parallel = d.number_input("Max parallel runs", min_value=1, max_value=12, value=6, step=1)

            if load_type == "Motor":
                a,b,c = st.columns(3)
                start_mult = a.number_input("Starting current multiplier", min_value=1.0, value=7.0, format="%.2f")
                start_pf = b.number_input("Starting power factor", min_value=0.01, max_value=1.0, value=0.30, format="%.3f")
                max_start_vd = c.number_input("Max starting VD (%)", min_value=0.01, value=20.0, format="%.2f")
            else:
                start_mult, start_pf, max_start_vd = 7.0, 0.30, 20.0

            use_sc = st.checkbox("Check minimum conductor area for short-circuit duty", value=False)
            if use_sc:
                a,b = st.columns(2)
                fault_ka = a.number_input("Fault current (kA rms)", min_value=0.001, value=25.0, format="%.3f")
                clear_s = b.number_input("Fault clearing time (s)", min_value=0.001, value=1.0 if voltage <= 1000 else 0.1, format="%.3f")
            else:
                fault_ka, clear_s = None, None

            cb_i2t = st.number_input("CB let-through energy I²t (A²s, optional; 0 = skip)", min_value=0.0, value=0.0, format="%.0f")

            manual_size = manual_n = None
            if mode == "Check Selected Cable":
                sizes = electrical.cable_sizes(voltage, cores if voltage <= 1000 else 3, installation)
                if not sizes:
                    st.warning("No cable rows are available for this combination in the uploaded cable data table.")
                    manual_size = 0.0
                else:
                    a,b = st.columns(2)
                    manual_size = a.selectbox("Selected conductor size (mm²)", sizes, index=min(len(sizes)-1, max(0, len(sizes)//2)))
                    manual_n = b.number_input("Parallel cable runs", min_value=1, max_value=12, value=1, step=1)

            calc_electrical = st.button("Calculate Electrical", type="primary", use_container_width=True)

        if calc_electrical:
            begin_new_result("electrical_last", "electrical_candidates", "electrical_cb_i2t", "electrical_last_mode")
            try:
                common = dict(
                    voltage=voltage, load_kw=load_kw, pf=pf, efficiency=eff, length_m=length_m,
                    derating=derating, cores=cores if voltage <= 1000 else 3, installation=installation,
                    system=system, load_type=load_type, max_vd_pct=max_vd, max_start_vd_pct=max_start_vd,
                    start_multiplier=start_mult, start_pf=start_pf, fault_current_ka=fault_ka,
                    clearing_time_s=clear_s, k_factor=k_factor,
                )
                if mode == "Auto Select":
                    candidates = electrical.recommend_cables(**common, max_parallel=int(max_parallel))
                    st.session_state["electrical_candidates"] = candidates
                    st.session_state["electrical_last"] = candidates[0].to_dict() if candidates else None
                else:
                    r = electrical.evaluate_cable(**common, size_mm2=float(manual_size), parallel_runs=int(manual_n))
                    st.session_state["electrical_candidates"] = [r]
                    st.session_state["electrical_last"] = r.to_dict()
                st.session_state["electrical_cb_i2t"] = cb_i2t
                st.session_state["electrical_last_mode"] = mode
            except Exception as e:
                st.error(f"Electrical calculation error: {e}")

        last = st.session_state.get("electrical_last") if st.session_state.get("electrical_last_mode") == mode else None
        candidates = st.session_state.get("electrical_candidates", []) if st.session_state.get("electrical_last_mode") == mode else []
        if last:
            st.markdown("#### Calculation Result")
            a,b,c,d = st.columns(4)
            a.metric("Full Load Current", f"{last['full_load_current_a']:.2f} A")
            b.metric("Selected Cable", f"{last['parallel_runs']} × {last['cores']}C × {last['size_mm2']:g} mm²")
            c.metric("Derated Ampacity", f"{last['derated_ampacity_a']:.1f} A")
            d.metric("Voltage Drop", f"{last['voltage_drop_pct']:.2f}%")
            checks = {
                "Ampacity": last["ampacity_ok"], "Steady-state VD": last["vd_ok"],
                "Starting VD": last["start_vd_ok"], "Short-circuit area": last["sc_area_ok"],
            }
            check_text = " · ".join([f"{'✓' if ok else '✕'} {name}" for name,ok in checks.items()])
            if last["overall_ok"]:
                st.success(f"Overall cable check: ACCEPTABLE · {check_text}")
            else:
                st.error(f"Overall cable check: NOT ACCEPTABLE · {check_text}")
            details = [
                ["Base ampacity", last["base_ampacity_a"], "A"],
                ["R @ 90°C", last["resistance_ohm_km"], "Ω/km"],
                ["X @ 50 Hz", last["reactance_ohm_km"], "Ω/km"],
                ["Voltage drop", last["voltage_drop_v"], "V"],
                ["Cable thermal withstand S²k²", last["cable_i2t_a2s"], "A²s"],
            ]
            if last.get("min_sc_area_mm2") is not None:
                details.append(["Minimum SC area", last["min_sc_area_mm2"], "mm²"])
            if last.get("start_current_a") is not None:
                details.extend([["Motor starting current", last["start_current_a"], "A"], ["Starting voltage drop", last["start_voltage_drop_pct"], "%"]])
            cb_val = st.session_state.get("electrical_cb_i2t", 0.0)
            if cb_val:
                details.append(["CB let-through I²t", cb_val, "A²s"])
                details.append(["CB I²t ≤ Cable S²k²", "ACCEPTABLE" if cb_val <= last["cable_i2t_a2s"] else "NOT ACCEPTABLE", "—"])
            st.dataframe(pd.DataFrame(details, columns=["Parameter","Value","Unit"]), hide_index=True, use_container_width=True)

            if mode == "Auto Select" and candidates:
                st.markdown("##### Acceptable alternatives")
                rows=[]
                for r in candidates[:12]:
                    rows.append({
                        "Runs":r.parallel_runs,"Cores":r.cores,"Size (mm²)":r.size_mm2,"Ampacity (A)":round(r.derated_ampacity_a,1),
                        "VD (%)":round(r.voltage_drop_pct,3),"Start VD (%)":None if r.start_voltage_drop_pct is None else round(r.start_voltage_drop_pct,3),
                        "Total Cu area (mm²)":r.parallel_runs*r.size_mm2,
                    })
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        elif calc_electrical:
            st.warning("No cable combination in the uploaded database met all selected criteria. Increase maximum parallel runs, relax criteria only if justified, or review cable/installation data.")

        with st.expander("Calculation basis from the uploaded cable workbook"):
            st.markdown("""
- Full-load current follows the sample sheets: √3 denominator for 3-phase AC, V·pf·η for 1-phase AC, and V·η for DC.
- Steady-state voltage drop follows the workbook expressions using cable R/X and cable length; 3-phase uses √3 and 1-phase/DC uses 2.
- Motor starting check uses the workbook defaults **Ist = 7 × IFL** and **starting pf = 0.30**, both editable above.
- Cable ampacity, AC resistance and reactance are taken from the **SUMI LV/MV cable data** tables embedded in the uploaded workbook.
- Cable thermal withstand is shown as **S²k²**. Optional fault-current input also calculates **Smin = I√t/k**.
""")

    with etab2:
        st.markdown("#### Main Ground Conductor Sizing — IEEE 80")
        with st.container(border=True):
            a,b,c,d = st.columns(4)
            ig = a.number_input("Symmetrical earth fault current (kA)", min_value=0.001, value=27.5)
            tm = b.number_input("Material fusing temperature Tm (°C)", value=1084.0)
            ta = c.number_input("Ambient temperature Ta (°C)", value=35.0)
            tc = d.number_input("Fault duration tc (s)", min_value=0.001, value=0.8)
            a,b,c,d = st.columns(4)
            alpha = a.number_input("αr (1/°C)", min_value=0.000001, value=0.00381, format="%.6f")
            rho_r = b.number_input("ρr (µΩ·cm)", min_value=0.0001, value=1.78)
            k0 = c.number_input("K0 (°C)", value=242.0)
            tcap = d.number_input("TCAP (J/cm³·°C)", min_value=0.001, value=3.42)
            gc_calc = st.button("Calculate Ground Conductor", type="primary", use_container_width=True)
        if gc_calc:
            begin_new_result("ground_conductor_last")
            try:
                req = electrical.ground_conductor_area_ieee80(ig, tm, ta, alpha, rho_r, k0, tc, tcap)
                selected = electrical.nearest_standard_size(req)
                st.session_state["ground_conductor_last"] = {"required_mm2":req,"selected_mm2":selected}
            except Exception as e: st.error(str(e))
        gc = st.session_state.get("ground_conductor_last")
        if gc:
            a,b = st.columns(2)
            a.metric("Required Cross-Section", f"{gc['required_mm2']:.2f} mm²")
            b.metric("Nearest Standard Size", f"{gc['selected_mm2']:.0f} mm²")
            st.success("Workbook regression case: 27.5 kA / 0.8 s returns ≈ 87.53 mm² → 95 mm².")

    with etab3:
        st.markdown("#### Maximum Allowable Step & Touch Voltage")
        with st.container(border=True):
            a,b,c = st.columns(3)
            rho = a.number_input("Soil resistivity ρ (Ω·m)", min_value=0.001, value=48.0)
            rhos = b.number_input("Surface layer resistivity ρs (Ω·m)", min_value=0.001, value=1000.0)
            hs = c.number_input("Surface layer thickness hs (m)", min_value=0.0, value=0.10, format="%.3f")
            a,b = st.columns(2)
            ts = a.number_input("Fault clearing time ts (s)", min_value=0.001, value=0.8)
            rb = b.number_input("Human body resistance RB (Ω)", min_value=1.0, value=1000.0)
            st_calc = st.button("Calculate Step & Touch", type="primary", use_container_width=True)
        if st_calc:
            begin_new_result("step_touch_last")
            try: st.session_state["step_touch_last"] = electrical.allowable_step_touch(rho,rhos,hs,ts,rb)
            except Exception as e: st.error(str(e))
        sr = st.session_state.get("step_touch_last")
        if sr:
            a,b,c = st.columns(3)
            a.metric("Surface Derating Cs", f"{sr['Cs']:.6f}")
            b.metric("Touch 50 kg", f"{sr['Etouch50_V']:.1f} V")
            c.metric("Touch 70 kg", f"{sr['Etouch70_V']:.1f} V")
            a,b = st.columns(2)
            a.metric("Step 50 kg", f"{sr['Estep50_V']:.1f} V")
            b.metric("Step 70 kg", f"{sr['Estep70_V']:.1f} V")
            st.dataframe(pd.DataFrame([
                ["Body current 50 kg",sr['Ib50_A'],"A"],["Body current 70 kg",sr['Ib70_A'],"A"],
                ["Etouch 50 kg",sr['Etouch50_V'],"V"],["Etouch 70 kg",sr['Etouch70_V'],"V"],
                ["Estep 50 kg",sr['Estep50_V'],"V"],["Estep 70 kg",sr['Estep70_V'],"V"],
            ],columns=["Parameter","Value","Unit"]),hide_index=True,use_container_width=True)
            st.info("The uploaded workbook has an inconsistent cell reference in its 50-kg touch-voltage cell. This program uses the same consistent IEEE 80 expression IB × (RB + 1.5·Cs·ρs) for both 50-kg and 70-kg cases rather than reproducing that single spreadsheet reference anomaly.")

    with etab4:
        st.markdown("#### Ground Grid + Earth Rod Resistance")
        with st.container(border=True):
            a,b,c,d = st.columns(4)
            rho_g = a.number_input("Grid-layer soil ρ (Ω·m)", min_value=0.001, value=6.71)
            rho_rod = b.number_input("Rod-layer soil ρ (Ω·m)", min_value=0.001, value=144.47)
            x = c.number_input("Grid length x (m)", min_value=0.001, value=85.0)
            y = d.number_input("Grid width y (m)", min_value=0.001, value=75.0)
            a,b,c,d = st.columns(4)
            lc = a.number_input("Total grid conductor LC (m)", min_value=0.001, value=320.0)
            h = b.number_input("Burial depth h (m)", min_value=0.001, value=0.8)
            dc = c.number_input("Grid conductor diameter (m)", min_value=0.000001, value=0.014, format="%.4f")
            nr = d.number_input("Number of earth rods", min_value=1, value=37, step=1)
            a,b,c,d = st.columns(4)
            lr = a.number_input("Rod length LR (m)", min_value=0.001, value=3.0)
            dr = b.number_input("Rod diameter (m)", min_value=0.000001, value=0.019, format="%.4f")
            k1 = c.number_input("K1", value=1.374705882352941, format="%.9f")
            k2 = d.number_input("K2", value=5.632352941176471, format="%.9f")
            grid_calc = st.button("Calculate Grid Resistance", type="primary", use_container_width=True)
        if grid_calc:
            begin_new_result("grid_resistance_last")
            try:
                st.session_state["grid_resistance_last"] = electrical.grid_resistance_rectangular(
                    rho_g,rho_rod,x,y,lc,h,dc,lr,dr,int(nr),k1,k2
                )
            except Exception as e: st.error(str(e))
        gr = st.session_state.get("grid_resistance_last")
        if gr:
            a,b,c,d = st.columns(4)
            a.metric("Grid R1", f"{gr['R1_ohm']:.5f} Ω")
            b.metric("Rods R2", f"{gr['R2_ohm']:.5f} Ω")
            c.metric("Mutual R12", f"{gr['R12_ohm']:.5f} Ω")
            d.metric("Total Rg", f"{gr['Rg_ohm']:.5f} Ω")
            if gr["Acceptable_lt_5_ohm"]: st.success("Grounding resistance < 5 Ω: ACCEPTABLE for the workbook criterion.")
            else: st.error("Grounding resistance ≥ 5 Ω: NOT ACCEPTABLE for the workbook criterion.")
            st.caption("Default regression case reproduces the uploaded WTIP calculation at approximately Rg = 0.05716 Ω.")

    with etab5:
        st.markdown("#### Lightning Protection Earthing — App-1C LPS")
        st.caption("This calculator reproduces the Lightning Protection Earthing Resistance worksheet in Lampiran 2. It is an earthing-resistance calculation, not a lightning-risk or protection-radius/rolling-sphere study.")
        with st.container(border=True):
            a,b,c,d = st.columns(4)
            rho_lps_grid = a.number_input("Grid-layer soil ρ (Ω·m)", min_value=0.001, value=24.29, key="lps_rho_grid")
            rho_lps_rod = b.number_input("Rod-layer soil ρ (Ω·m)", min_value=0.001, value=24.40, key="lps_rho_rod")
            spacing = c.number_input("Triangle side / rod spacing (m)", min_value=0.001, value=6.0, key="lps_spacing")
            lc_lps = d.number_input("Total grid conductor LC (m)", min_value=0.001, value=18.0, key="lps_lc")
            a,b,c,d = st.columns(4)
            h_lps = a.number_input("Burial depth h (m)", min_value=0.001, value=0.8, key="lps_h")
            dc_lps = b.number_input("Grid conductor diameter (m)", min_value=0.000001, value=0.018, format="%.4f", key="lps_dc")
            lr_lps = c.number_input("Earth rod length LR (m)", min_value=0.001, value=3.0, key="lps_lr")
            dr_lps = d.number_input("Earth rod diameter (m)", min_value=0.000001, value=0.016, format="%.4f", key="lps_dr")
            a,b,c,d = st.columns(4)
            nr_lps = a.number_input("Number of earth rods", min_value=1, value=3, step=1, key="lps_nr")
            k1_lps = b.number_input("K1", value=1.37, format="%.6f", key="lps_k1")
            k2_lps = c.number_input("K2", value=5.65, format="%.6f", key="lps_k2")
            req_lps = d.number_input("Maximum allowable Rg (Ω)", min_value=0.001, value=10.0, key="lps_req")
            lps_calc = st.button("Calculate Lightning Earthing", type="primary", use_container_width=True)
        if lps_calc:
            begin_new_result("lightning_lps_last")
            try:
                st.session_state["lightning_lps_last"] = electrical.lightning_lps_earthing(
                    rho_lps_grid, rho_lps_rod, spacing, lc_lps, h_lps, dc_lps,
                    lr_lps, dr_lps, int(nr_lps), k1_lps, k2_lps, req_lps
                )
            except Exception as e:
                st.error(str(e))
        lpsr = st.session_state.get("lightning_lps_last")
        if lpsr:
            a,b,c,d = st.columns(4)
            a.metric("Grid R1", f"{lpsr['R1_ohm']:.5f} Ω")
            b.metric("Rods R2", f"{lpsr['R2_ohm']:.5f} Ω")
            c.metric("Mutual R12", f"{lpsr['R12_ohm']:.5f} Ω")
            d.metric("Total Rg", f"{lpsr['Rg_ohm']:.5f} Ω")
            if lpsr["Acceptable"]:
                st.success(f"Lightning-protection earthing resistance < {lpsr['Requirement_ohm']:.2f} Ω: ACCEPTABLE")
            else:
                st.error(f"Lightning-protection earthing resistance ≥ {lpsr['Requirement_ohm']:.2f} Ω: NOT ACCEPTABLE")
            st.dataframe(pd.DataFrame([
                ["Triangle area", lpsr["Triangle_Area_m2"], "m²"],
                ["Equivalent a'", lpsr["a_prime_m"], "m"],
                ["Earth rod count", lpsr["Rod_Count"], "—"],
                ["Rod spacing", lpsr["Rod_Spacing_m"], "m"],
            ], columns=["Parameter","Value","Unit"]), hide_index=True, use_container_width=True)
            st.info("Regression case from Lampiran 2, App-1C LPS: 3 rods × 3 m in a 6 m triangular arrangement gives Rg ≈ 2.33215 Ω, with the worksheet requirement < 10 Ω.")
        with st.expander("Calculation basis from Lampiran 2 — App-1C LPS"):
            st.markdown("""
- The worksheet title is **Appendix 1C — Lightning Protection Earthing Resistance**.
- The default layout uses **3 vertical earth rods**, each **3 m** long, arranged as an equilateral triangle with **6 m spacing**.
- The worksheet calculates **R1** (grid conductor resistance), **R2** (earth-rod resistance), **R12** (mutual resistance), then **Rg = (R1·R2 − R12²) / (R1 + R2 − 2R12)**.
- The worksheet acceptance criterion is **Rg < 10 Ω**.
- The workbook note refers to **NFC 17-102 Type A.2** earthing arrangement.
- Protection-radius calculation is handled separately in the **ESE Protection** tab using the uploaded NF C 17-102:2011 standard.
""")

    with etab6:
        st.markdown("#### Conventional Lightning Protection — NFPA 780 (2000) Rolling Sphere")
        st.caption("Traditional LPS screening only. The uploaded NFPA 780 edition uses a 150 ft (46 m) rolling sphere and explicitly excludes Early Streamer Emission (ESE) systems from its scope.")
        with st.container(border=True):
            a,b,c = st.columns(3)
            h1 = a.number_input("Higher roof / strike-termination height h1 (m)", min_value=0.01, value=15.0, step=0.5, key="nfpa_h1")
            h2 = b.number_input("Lower protected plane height h2 (m)", min_value=0.0, value=0.0, step=0.5, key="nfpa_h2")
            req_d = c.number_input("Required horizontal protected distance (m, 0 = none)", min_value=0.0, value=20.0, step=0.5, key="nfpa_req_d")
            nfpa_calc = st.button("Calculate NFPA 780 Rolling Sphere", type="primary", use_container_width=True)
        if nfpa_calc:
            begin_new_result("nfpa780_last")
            try:
                if hasattr(electrical, "nfpa780_rolling_sphere_2000"):
                    nr = electrical.nfpa780_rolling_sphere_2000(h1, h2)
                else:
                    # Compatibility fallback if the deployed repository still
                    # contains an older electrical_engine.py during update.
                    import math
                    FT_PER_M = 3.280839895013123
                    M_PER_FT = 1.0 / FT_PER_M
                    h1_m, h2_m = float(h1), float(h2)
                    if h1_m <= 0:
                        raise ValueError("Higher strike-termination / roof height must be > 0 m.")
                    if h2_m < 0 or h2_m >= h1_m:
                        raise ValueError("Lower protected height h2 must be >= 0 and below h1.")
                    R_ft = 150.0
                    h1_ft, h2_ft = h1_m * FT_PER_M, h2_m * FT_PER_M
                    if (h1_ft - h2_ft) > R_ft + 1e-9:
                        raise ValueError("Height difference h1-h2 must be 150 ft (46 m) or less for this NFPA 780 geometry.")
                    radicand = h1_ft * (2.0 * R_ft - h1_ft) - h2_ft * (2.0 * R_ft - h2_ft)
                    if radicand < -1e-9:
                        raise ValueError("Rolling-sphere geometry produced a negative radicand; review the heights.")
                    d_ft = math.sqrt(max(radicand, 0.0))
                    nr = {
                        "Method": "NFPA 780 (2000) §3.7.3 Rolling Sphere",
                        "Sphere_Radius_ft": R_ft,
                        "Sphere_Radius_m": R_ft * M_PER_FT,
                        "Higher_Height_h1_m": h1_m,
                        "Lower_Protected_Height_h2_m": h2_m,
                        "Height_Difference_m": h1_m - h2_m,
                        "Horizontal_Protected_Distance_m": d_ft * M_PER_FT,
                        "Horizontal_Protected_Distance_ft": d_ft,
                        "High_Rise_Additional_Analysis": bool(h1_ft > R_ft),
                        "Note": "Higher point exceeds 150 ft (46 m); perform the full NFPA 780 high-rise zone-of-protection analysis." if h1_ft > R_ft else "",
                        "ESE_In_Scope": False,
                    }
                nr["Required_Distance_m"] = None if req_d <= 0 else req_d
                nr["Coverage_OK"] = None if req_d <= 0 else nr["Horizontal_Protected_Distance_m"] >= req_d
                nr["Coverage_Margin_m"] = None if req_d <= 0 else nr["Horizontal_Protected_Distance_m"] - req_d
                st.session_state["nfpa780_last"] = nr
            except Exception as e:
                st.error(str(e))
        nr = st.session_state.get("nfpa780_last")
        if nr:
            a,b,c,d = st.columns(4)
            a.metric("Rolling-sphere radius", f"{nr['Sphere_Radius_m']:.2f} m")
            b.metric("Horizontal protected distance", f"{nr['Horizontal_Protected_Distance_m']:.2f} m")
            c.metric("h1", f"{nr['Higher_Height_h1_m']:.2f} m")
            d.metric("h2", f"{nr['Lower_Protected_Height_h2_m']:.2f} m")
            if nr.get("Coverage_OK") is not None:
                if nr["Coverage_OK"]:
                    st.success(f"Required horizontal distance is covered. Margin = {nr['Coverage_Margin_m']:.2f} m.")
                else:
                    st.error(f"Required horizontal distance is NOT covered. Shortfall = {abs(nr['Coverage_Margin_m']):.2f} m.")
            if nr["High_Rise_Additional_Analysis"]:
                st.warning(nr["Note"])
            st.dataframe(pd.DataFrame([
                ["Method", nr["Method"], "—"],
                ["Sphere radius", nr["Sphere_Radius_ft"], "ft"],
                ["Height difference", nr["Height_Difference_m"], "m"],
                ["Horizontal protected distance", nr["Horizontal_Protected_Distance_ft"], "ft"],
                ["ESE covered by this method?", "No", "—"],
            ], columns=["Parameter","Value","Unit"]), hide_index=True, use_container_width=True)
        with st.expander("NFPA 780 (2000) basis and scope"):
            st.markdown("""
- The uploaded NFPA 780 edition uses a **150 ft (46 m)** rolling sphere for the traditional zone-of-protection method.
- The equation implemented is the §3.7.3.4 horizontal-distance relationship, evaluated in feet exactly as published and converted back to metres.
- The simple equation requires **h1 − h2 ≤ 150 ft (46 m)**.
- Structures / points above the basic 150 ft geometry need the additional high-rise limitations and full layout analysis described by the standard.
- **ESE is not an NFPA 780 method in this uploaded edition**. Use the separate **ESE — NF C 17-102** tab for ESE screening.
- A complete NFPA 780 design also requires strike termination placement, conductors, bonding, grounding, surge protection, inspection and maintenance checks; this tab is geometry screening only.
""")

    with etab7:
        st.markdown("#### Early Streamer Emission (ESE) — Project Excel Aligned")
        st.caption("The project mode follows the uploaded workbook sheet **PENGANGKAL PETIR**. Both ESE calculators below now recalculate live whenever an input changes, so an old result cannot remain on screen after you edit the inputs.")

        project_tab, standard_tab = st.tabs(["Project Excel Method", "NF C 17-102 Standard Mode"])

        with project_tab:
            st.markdown("##### 1 · Lightning risk / protection level")
            st.caption("Live mode — change any value and the results below update immediately.")

            a,b,c,d = st.columns(4)
            x_a = a.number_input("Panjang area, a (m)", min_value=0.01, value=120.0, step=1.0, key="xls_ese_a")
            x_b = b.number_input("Lebar area, b (m)", min_value=0.01, value=110.0, step=1.0, key="xls_ese_b")
            x_H = c.number_input("Tinggi penangkal petir (m)", min_value=0.01, value=25.0, step=0.5, key="xls_ese_H")
            x_Td = d.number_input("Tingkat Hari Guruh, Td", min_value=0.01, value=127.0, step=1.0, key="xls_ese_Td")

            a,b,c,d,e = st.columns(5)
            x_c1 = a.number_input("C1 · lingkungan", min_value=0.01, value=0.5, step=0.1, key="xls_ese_c1")
            x_c2 = b.number_input("C2", min_value=0.01, value=2.0, step=0.5, key="xls_ese_c2")
            x_c3 = c.number_input("C3", min_value=0.01, value=4.0, step=0.5, key="xls_ese_c3")
            x_c4 = d.number_input("C4", min_value=0.01, value=1.0, step=0.5, key="xls_ese_c4")
            x_c5 = e.number_input("C5", min_value=0.01, value=5.0, step=0.5, key="xls_ese_c5")

            st.markdown("##### 2 · ESE protection radius")
            a,b,c,d = st.columns(4)
            x_hb = a.number_input("Tinggi bangunan tertinggi (m)", min_value=0.0, value=12.5, step=0.5, key="xls_ese_hb")
            x_v = b.number_input("Kecepatan tracer, V (m/s)", min_value=1.0, value=1000000.0, step=10000.0, format="%.0f", key="xls_ese_v")
            x_dt_us = c.number_input("Tambahan waktu spark ΔT (µs)", min_value=0.0, value=67.0, step=1.0, key="xls_ese_dt")
            x_off = d.number_input("Allowance selisih tinggi (m)", value=0.5, step=0.1, key="xls_ese_off")

            try:
                xr = electrical.ese_project_excel_method(
                    area_length_m=x_a, area_width_m=x_b,
                    lightning_rod_height_m=x_H, thunder_days_td=x_Td,
                    c1_environment=x_c1, c2_building=x_c2, c3_building=x_c3,
                    c4_building=x_c4, c5_building=x_c5,
                    highest_building_height_m=x_hb,
                    tracer_speed_m_s=x_v, delta_t_s=x_dt_us*1e-6,
                    height_offset_m=x_off,
                )
            except Exception as e:
                xr = None
                st.error(str(e))

            if xr:
                m1,m2,m3,m4 = st.columns(4)
                m1.metric("Protection Level", xr["Protection_Level"])
                m2.metric("Efficiency", f"{xr['Efficiency']*100:.4f}%")
                m3.metric("Radius Proteksi Rp", f"{xr['Rp_m']:.2f} m")
                m4.metric("ΔL", f"{xr['DeltaL_m']:.2f} m")

                st.dataframe(pd.DataFrame([
                    ["Panjang area, a", xr["Area_Length_a_m"], "m"],
                    ["Lebar area, b", xr["Area_Width_b_m"], "m"],
                    ["Tinggi penangkal petir", xr["Lightning_Rod_Height_m"], "m"],
                    ["Tingkat Hari Guruh, Td", xr["Thunder_Days_Td"], "—"],
                    ["C1 · lingkungan", xr["C1_Environment"], "—"],
                    ["C2", xr["C2"], "—"],
                    ["C3", xr["C3"], "—"],
                    ["C4", xr["C4"], "—"],
                    ["C5", xr["C5"], "—"],
                    ["Total koefisien C2×C3×C4×C5", xr["Total_Coefficient_C2xC3xC4xC5"], "—"],
                    ["Intensitas sambaran menuju tanah, Ng", xr["Ng_per_km2_year"], "km²/year"],
                    ["Luas area yang diproteksi, Ae", xr["Protected_Area_Ae_m2"], "m²"],
                    ["Level proteksi petir, Nd", xr["Nd_strikes_per_year"], "lightning strikes/year"],
                    ["Kebutuhan penangkal petir, Nc", xr["Nc"], "—"],
                    ["Efisiensi penangkal petir", xr["Efficiency"], "—"],
                    ["Tingkat proteksi", xr["Protection_Level"], "Level"],
                    ["Tinggi bangunan tertinggi", xr["Highest_Building_Height_m"], "m"],
                    ["Allowance selisih tinggi", xr["Height_Offset_m"], "m"],
                    ["Selisih tinggi, h", xr["Height_Difference_h_m"], "m"],
                    ["Level area, D", xr["Level_Area_D_m"], "m"],
                    ["Kecepatan tracer, V", xr["Tracer_Speed_m_s"], "m/s"],
                    ["Tambahan waktu spark, ΔT", xr["DeltaT_s"], "s"],
                    ["Tambahan jarak, ΔL", xr["DeltaL_m"], "m"],
                    ["Radius proteksi, Rp", xr["Rp_m"], "m"],
                ], columns=["Parameter","Value","Unit"]), hide_index=True, use_container_width=True)

                if xr.get("Workbook_Display_Match"):
                    st.success("Default workbook case: Ng ≈ 17.90, Ae = 65,362.50 m², Nd ≈ 0.585, Level I, ΔL = 67 m, Rp ≈ 86.72 m.")
                else:
                    st.info("Calculated from the CURRENT input values shown above.")

            with st.expander("Project Excel calculation basis"):
                st.markdown(r"""
- **Total coefficient** = C2 × C3 × C4 × C5
- **Ng** = 0.04 × Td^1.26
- **Ae** = a×b + 6H(a+b) + 9×3.14×H²
- **Nd** = Ng × Ae × C1 × 10⁻⁶
- **Nc** = 1.5×10⁻³ / Total coefficient
- **Efficiency** = 1 − Nc/Nd
- Protection-level mapping used by the program: **I ≥ 0.98**, **II ≥ 0.95**, **III ≥ 0.90**, otherwise **IV**.
- **h** = lightning-rod height − highest-building height + allowance.
- **D** = 20 / 30 / 45 / 60 m for Levels I / II / III / IV.
- **ΔL** = V × ΔT.
- **Rp** = √[h(2D−h) + ΔL(2D+ΔL)].

The uploaded workbook's default case uses **ΔT = 67 µs**. This project-workbook reproduction remains separate from the NF C 17-102 standard-mode calculator.
""")

        with standard_tab:
            st.markdown("##### NF C 17-102:2011 standard-mode screening")
            st.caption("Live mode — use the certified ΔT value from the selected ESEAT test report. This calculation is separate from the project Excel reproduction.")

            a,b,c,d = st.columns(4)
            ese_level = a.selectbox("Protection level", ["I", "II", "III", "IV"], index=0, key="ese_level")
            ese_dt = b.number_input("ESE efficiency ΔT (µs)", min_value=0.0, max_value=60.0, value=60.0, step=1.0, key="ese_dt")
            ese_h = c.number_input("ESE tip height h above protected plane (m)", min_value=2.0, value=5.0, step=0.5, key="ese_h")
            ese_required = d.number_input("Required coverage radius (m, 0 = none)", min_value=0.0, value=50.0, step=1.0, key="ese_required")

            a,b,c,d = st.columns(4)
            ese_system = a.selectbox("ESE system", ["Non-isolated", "Isolated"], key="ese_system")
            ese_count = b.number_input("Number of ESEATs", min_value=1, value=1, step=1, key="ese_count")
            building_h = c.number_input("Building height (m, optional)", min_value=0.0, value=20.0, step=1.0, key="ese_building_h")
            tip_elev = d.number_input("ESE tip elevation above ground (m, optional)", min_value=0.0, value=25.0, step=1.0, key="ese_tip_elev")
            level_ipp = st.checkbox("Apply special Level I++ radius reduction (40% reduction from Level-I radius)", value=False, key="ese_ipp")

            try:
                er = electrical.ese_protection_radius_nfc17102(
                    protection_level=ese_level,
                    ese_efficiency_us=ese_dt,
                    height_over_protected_plane_m=ese_h,
                    required_radius_m=None if ese_required <= 0 else ese_required,
                    building_height_m=None if building_h <= 0 else building_h,
                    ese_tip_elevation_m=None if tip_elev <= 0 else tip_elev,
                    system_type=ese_system,
                    ese_count=int(ese_count),
                    apply_level_i_plus_plus=level_ipp,
                )
            except Exception as e:
                er = None
                st.error(str(e))

            if er:
                a,b,c,d = st.columns(4)
                a.metric("Protection Radius Rp", f"{er['Rp_m']:.2f} m")
                b.metric("Reference Radius r", f"{er['r_m']:.0f} m")
                c.metric("Δ", f"{er['Delta_m']:.1f} m")
                d.metric("Circular Coverage Area", f"{er['Protected_Circular_Area_m2']:.0f} m²")
                if er["Coverage_OK"] is not None:
                    if er["Coverage_OK"]:
                        st.success(f"Required radius {er['Required_Radius_m']:.2f} m is covered. Margin = {er['Coverage_Margin_m']:.2f} m.")
                    else:
                        st.error(f"Required radius {er['Required_Radius_m']:.2f} m is NOT covered. Shortfall = {abs(er['Coverage_Margin_m']):.2f} m.")
                if er["High_Rise_Additional_Protection_Required"]:
                    st.warning("High-rise rule triggered; perform the additional project-specific protection checks required by the standard.")
                st.info(er["Downconductor_Guidance"])


elif page == "PSV Engineering":
    page_header("PSV Engineering", "API-style sizing tools for common relief services. Add calculated cases to the Scenario Register to compare the governing required area.")
    _default("psv_scenarios", [])
    service = st.selectbox("Calculation service", ["Gas / Vapor", "Steam", "Liquid", "Two-Phase", "External Fire — Wetted Vessel", "Thermal Expansion", "Piping Check"])
    psv_result = None
    case_name = ""

    if service == "Gas / Vapor":
        with st.container(border=True):
            case_name=st.text_input("Scenario name",value="Blocked Outlet — Gas")
            a,b,c=st.columns(3); W=a.number_input("Required relief rate (kg/h)",0.001,value=15000.0); setb=b.number_input("Set pressure (barg)",0.001,value=25.0); bp=c.number_input("Back pressure (barg)",0.0,value=1.5)
            a,b,c=st.columns(3); op=a.number_input("Overpressure (%)",0.0,value=10.0); temp=b.number_input("Relieving temperature (°C)",value=45.0); z=c.number_input("Z",0.001,value=.92)
            a,b,c=st.columns(3); mw=a.number_input("MW",0.001,value=16.04); k=b.number_input("k",0.1,value=1.31); n=c.number_input("Parallel valves",1,20,value=1,step=1)
            vtype=st.selectbox("Valve type",["conventional","balanced_bellows","pilot"], key="psv_gas_vtype")
            a,b,c=st.columns(3); kd=a.number_input("Kd",0.001,1.0,value=.975); kb=b.number_input("Kb (balanced bellows / manufacturer; ignored for conventional & pilot direct method)",0.001,1.0,value=1.0); kc=c.number_input("Kc",0.001,1.2,value=1.0)
            calc=st.button("Calculate PSV",type="primary",use_container_width=True)
        if calc:
            begin_new_result("psv_last")
            try:
                p1=barg_to_psia(setb*(1+op/100)); p2=barg_to_psia(bp)
                psv_result=calculate_gas_relief_area(kg_h_to_lb_h(W),p1,p2,c_to_rankine(temp),z,mw,k,kd,kb,kc,int(n),valve_type=vtype)
            except Exception as e: st.error(str(e))
    elif service == "Steam":
        with st.container(border=True):
            case_name=st.text_input("Scenario name",value="Steam Relief")
            a,b,c=st.columns(3); W=a.number_input("Steam rate (kg/h)",0.001,value=15000.0); setb=b.number_input("Set pressure (barg)",0.001,value=25.0); bp=c.number_input("Back pressure (barg)",0.0,value=1.5)
            a,b,c=st.columns(3); op=a.number_input("Overpressure (%)",0.0,value=10.0); temp=b.number_input("Temperature (°C)",value=300.0); n=c.number_input("Parallel valves",1,20,value=1,step=1)
            a,b,c=st.columns(3); kd=a.number_input("Kd",0.001,1.0,value=.975); kb=b.number_input("Kb",0.001,1.2,value=1.0); kc=c.number_input("Kc",0.001,1.2,value=1.0)
            calc=st.button("Calculate PSV",type="primary",use_container_width=True)
        if calc:
            begin_new_result("psv_last")
            try:
                p1=barg_to_psia(setb*(1+op/100)); p2=barg_to_psia(bp)
                psv_result=calculate_napier_steam_area(kg_h_to_lb_h(W),p1,p2,c_to_rankine(temp),kd,kb,kc,int(n))
            except Exception as e: st.error(str(e))
    elif service == "Liquid":
        with st.container(border=True):
            case_name=st.text_input("Scenario name",value="Blocked Outlet — Liquid")
            a,b,c=st.columns(3); q=a.number_input("Relief flow (m³/h)",0.0001,value=100.0); setb=b.number_input("Set pressure (barg)",0.001,value=25.0); bp=c.number_input("Back pressure (barg)",0.0,value=1.5)
            a,b,c=st.columns(3); op=a.number_input("Overpressure (%)",0.0,value=10.0); sg=b.number_input("Specific gravity",0.001,value=.8); visc_unit=c.selectbox("Viscosity unit",["cP","SSU"], key="psv_liq_visc_unit")
            a,b,c=st.columns(3); mu=a.number_input(f"Viscosity ({visc_unit})",0.0001,value=1.0 if visc_unit=="cP" else 2000.0); kd=b.number_input("Kd",0.001,1.0,value=.65); kc=c.number_input("Kc",0.001,1.2,value=1.0)
            a,b=st.columns(2); n=a.number_input("Parallel valves",1,20,value=1,step=1); vtype=b.selectbox("Valve type",["conventional","balanced_bellows","pilot"], key="psv_liq_vtype")
            calc=st.button("Calculate PSV",type="primary",use_container_width=True)
        if calc:
            begin_new_result("psv_last")
            try:
                # API 520 liquid Eq. 32/33 uses gauge pressure (psig), not absolute pressure.
                p1=barg_to_psig(setb*(1+op/100)); p2=barg_to_psig(bp)
                psv_result=calculate_liquid_relief_area(m3_h_to_gpm(q),p1,p2,sg,mu,kd=kd,kc=kc,num_valves=int(n),overpressure_pct=op,valve_type=vtype,set_pressure_psig=barg_to_psig(setb),viscosity_unit=visc_unit)
            except Exception as e: st.error(str(e))
    elif service == "Two-Phase":
        with st.container(border=True):
            case_name=st.text_input("Scenario name",value="Two-Phase Relief")
            a,b,c=st.columns(3); W=a.number_input("Relief rate (kg/h)",0.001,value=50000.0); setb=b.number_input("Relieving pressure (barg)",0.001,value=27.5); bp=c.number_input("Back pressure (barg)",0.0,value=1.5)
            a,b,c=st.columns(3); v0=a.number_input("v0 specific volume (m³/kg)",0.0000001,value=.01,format="%.7f"); v9=b.number_input("v9 specific volume (m³/kg)",0.0000001,value=.011,format="%.7f"); n=c.number_input("Parallel valves",1,20,value=1,step=1)
            a,b,c=st.columns(3); kd=a.number_input("Kd",0.001,1.0,value=.85); kb=b.number_input("Kb",0.001,1.2,value=1.0); kc=c.number_input("Kc",0.001,1.2,value=1.0)
            calc=st.button("Calculate PSV",type="primary",use_container_width=True)
        if calc:
            begin_new_result("psv_last")
            try:
                omega=calculate_omega_flashing(m3_kg_to_ft3_lb(v0),m3_kg_to_ft3_lb(v9))
                psv_result=calculate_two_phase_area(kg_h_to_lb_h(W),barg_to_psia(setb),barg_to_psia(bp),m3_kg_to_ft3_lb(v0),omega,kd,kb,kc,int(n)); psv_result["Omega"]=omega
            except Exception as e: st.error(str(e))
    elif service == "External Fire — Wetted Vessel":
        env_choice=st.selectbox("API 521 Table 5 environment-factor preset", list(ENV_FACTORS.keys()) + ["Custom / project-specific"], key="fire_env_choice")
        preset_f = ENV_FACTORS.get(env_choice, 1.0)
        with st.container(border=True):
            case_name=st.text_input("Scenario name",value="External Fire")
            a,b,c=st.columns(3); area=a.number_input("Wetted area (ft²)",0.001,value=1000.0); F=b.number_input("Environmental factor F",0.0,1.0,value=float(preset_f)); hvap=c.number_input("Latent heat (BTU/lb)",0.001,value=150.0)
            drainage=st.checkbox("Adequate drainage / prompt firefighting",value=True)
            calc=st.button("Calculate Relief Load",type="primary",use_container_width=True)
        st.caption("API 521 Table 5: water application facilities on a bare vessel and depressuring/emptying facilities are listed as F = 1.0 with footnote conditions; they are not automatically credited as F = 0.3 in this version.")
        if calc:
            begin_new_result("psv_last")
            try:
                w,qh=calculate_fire_wetted_load(area,F,hvap,drainage)
                psv_result={"Relief_Load_lb_h":w,"Heat_Input_BTU_h":qh}
            except Exception as e: st.error(str(e))
    elif service == "Thermal Expansion":
        with st.container(border=True):
            case_name=st.text_input("Scenario name",value="Blocked-in Thermal Expansion")
            a,b,c,d=st.columns(4); beta=a.number_input("Expansion coefficient (1/°F)",0.0000001,value=.0005,format="%.7f"); heat=b.number_input("Heat transfer (BTU/h)",0.001,value=170000.0); sg=c.number_input("Specific gravity",0.001,value=.8); cp=d.number_input("Specific heat (BTU/lb-°F)",0.001,value=.5)
            calc=st.button("Calculate Relief Load",type="primary",use_container_width=True)
        if calc:
            begin_new_result("psv_last")
            try:
                q_gpm=calculate_thermal_expansion_load(beta,heat,sg,cp)
                psv_result={"Relief_Flow_gpm":q_gpm,"Relief_Flow_m3_h":gpm_to_m3_h(q_gpm),"Method":"API 521 thermal expansion — volumetric relief flow"}
            except Exception as e: st.error(str(e))
    else:
        with st.container(border=True):
            case_name="Piping Check"
            a,b,c=st.columns(3); q=a.number_input("Liquid flow (gpm)",0.0,value=100.0); rho=b.number_input("Density (lb/ft³)",0.001,value=50.0); mu=c.number_input("Viscosity (cP)",0.0001,value=1.0)
            a,b,c=st.columns(3); dia=a.number_input("Pipe ID (in)",0.001,value=3.0); length=b.number_input("Straight length (ft)",0.0,value=20.0); setpsig=c.number_input("PSV set pressure (psig)",0.001,value=100.0)
            a,b,c=st.columns(3); e90=a.number_input("90° elbows",0,20,value=2,step=1); e45=b.number_input("45° elbows",0,20,value=0,step=1); gates=c.number_input("Gate valves",0,20,value=1,step=1)
            calc=st.button("Calculate Piping Check",type="primary",use_container_width=True)
        if calc:
            begin_new_result("psv_last")
            try:
                rr=calculate_inlet_pressure_drop(q,rho,mu,dia,length,int(e90),int(e45),int(gates)); passed,pct=check_inlet_rule(rr["delta_p_psi"],setpsig)
                psv_result={**rr,"Inlet_Rule_Pass":passed,"Inlet_Drop_Pct":pct}
            except Exception as e: st.error(str(e))

    if psv_result is not None:
        st.session_state["psv_last"]={"name":case_name,"service":service,"result":psv_result}
    last=st.session_state.get("psv_last")
    if last and last.get("service") != service:
        last = None
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
    st.info("v1.4.1: previous calculation outputs are invalidated before every new sizing run, so a revised or failed case cannot keep showing the old result.")
    st.markdown(f"""
### {APP_TITLE}
**{APP_VERSION}**  

This web edition wraps the same Python calculation engines used in the Windows edition into a responsive Streamlit interface.

**Included modules:**
- AGA 3 orifice-flow calculation and inverse bore sizing.
- AGA 8 DETAIL gas-property calculation with 21-component composition.
- Control Valve sizing for liquid, gas and steam services.
- Electrical cable sizing, voltage drop, grounding conductor, permissible step/touch voltage, and grid resistance.
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
        "electrical_last":st.session_state.get("electrical_last"),
        "psv_scenarios":st.session_state.get("psv_scenarios",[]),
    }
    st.download_button("Download current calculation snapshot (JSON)",json.dumps(project_snapshot,indent=2,default=str),"instrument_sizing_snapshot.json","application/json")

st.markdown(f'<div class="footnote">{APP_TITLE} · {APP_VERSION}</div>', unsafe_allow_html=True)


st.markdown(f'<div class="footer-line">{APP_TITLE} · {APP_VERSION} · Engineering Calculation Aid</div>', unsafe_allow_html=True)

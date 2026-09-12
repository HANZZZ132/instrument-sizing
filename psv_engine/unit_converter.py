# unit_converter.py
from .constants import (
    PSIA_PER_BAR, ATMOSPHERIC_PSIA, KG_TO_LB, M3H_TO_GPM, M3KG_TO_FT3LB,
    SQFT_PER_M2, KCALH_TO_BTUH, KW_TO_BTUH, KCAL_KG_TO_BTU_LB,
    KJ_KGK_TO_BTU_LBF, SECONDS_PER_HOUR, CUBIC_FEET_PER_M3,
    R_PER_BARA, STANDARD_TEMP_RANKINE, NORMAL_TEMP_RANKINE,
    STANDARD_PRESSURE_PSIA, RANKINE_OFFSET, FAHRENHEIT_RATIO, FAHRENHEIT_OFFSET,
    LBFT3_PER_KGM3, KPA_PER_PSIA,
)

# Aliases for units.py compatibility
ATM_PSIA = ATMOSPHERIC_PSIA
PSI_PER_BAR = PSIA_PER_BAR
R_PSIA_FT3_LBMOL_R = R_PER_BARA

def barg_to_psia(barg, atm_psia=None):
    if atm_psia is None:
        atm_psia = ATMOSPHERIC_PSIA
    return (barg * PSIA_PER_BAR) + atm_psia

def bara_to_psia(bara):
    return bara * PSIA_PER_BAR

def psia_to_barg(psia, atm_psia=None):
    if atm_psia is None:
        atm_psia = ATMOSPHERIC_PSIA
    return (psia - atm_psia) / PSIA_PER_BAR

def psia_to_bara(psia):
    return psia / PSIA_PER_BAR

def bara_to_barg(bara):
    return bara - ATMOSPHERIC_PSIA / PSIA_PER_BAR

def barg_to_psig(barg):
    return barg * PSIA_PER_BAR

def psig_to_barg(psig):
    return psig / PSIA_PER_BAR

def kg_h_to_lb_h(kg_h):
    return kg_h * KG_TO_LB

def lb_h_to_kg_h(lb_h):
    return lb_h / KG_TO_LB

def kg_s_to_lb_h(kg_s):
    return kg_s * SECONDS_PER_HOUR * KG_TO_LB

def m3_h_to_gpm(m3_h):
    return m3_h * M3H_TO_GPM

def gpm_to_m3_h(gpm):
    return gpm / M3H_TO_GPM

def c_to_rankine(c):
    return (c * FAHRENHEIT_RATIO) + RANKINE_OFFSET

def c_to_f(c):
    return (c * FAHRENHEIT_RATIO) + FAHRENHEIT_OFFSET

def f_to_rankine(f):
    return f + RANKINE_OFFSET - FAHRENHEIT_OFFSET

def f_to_c(f):
    return (f - FAHRENHEIT_OFFSET) / FAHRENHEIT_RATIO

def m3_kg_to_ft3_lb(m3_kg):
    return m3_kg * M3KG_TO_FT3LB

def kg_m3_to_lb_ft3(kg_m3):
    return kg_m3 * LBFT3_PER_KGM3

def kcal_h_to_btu_h(kcal_h):
    return kcal_h * KCALH_TO_BTUH

def kw_to_btu_h(kw):
    return kw * KW_TO_BTUH

def m2_to_sqft(m2):
    return m2 * SQFT_PER_M2

def sqft_to_m2(sqft):
    return sqft / SQFT_PER_M2

def kcal_kg_to_btu_lb(kcal_kg):
    return kcal_kg * KCAL_KG_TO_BTU_LB

def kj_kgK_to_btu_lbF(kj_kgK):
    return kj_kgK * KJ_KGK_TO_BTU_LBF

def kpa_to_psia(kpa):
    return kpa * KPA_PER_PSIA

def psia_to_kpa(psia):
    return psia / KPA_PER_PSIA

# --- Gas Volumetric to Mass Flow Converters ---

def actual_m3_h_to_lb_h(m3_h, p_psia, t_rankine, mw, z):
    """Convert actual m3/h at relieving conditions to mass flow lb/h."""
    rho_lb_ft3 = (p_psia * mw) / (z * R_PER_BARA * t_rankine)
    ft3_h = m3_h * CUBIC_FEET_PER_M3
    return ft3_h * rho_lb_ft3

def sm3_h_to_lb_h(sm3_h, mw):
    """Convert Standard m3/h (60F, 14.696 psia) to mass flow lb/h."""
    rho_std_lb_ft3 = (STANDARD_PRESSURE_PSIA * mw) / (1.0 * R_PER_BARA * STANDARD_TEMP_RANKINE)
    ft3_h = sm3_h * CUBIC_FEET_PER_M3
    return ft3_h * rho_std_lb_ft3

def nm3_h_to_lb_h(nm3_h, mw):
    """Convert Normal m3/h (0C, 1.01325 bar) to mass flow lb/h."""
    rho_norm_lb_ft3 = (STANDARD_PRESSURE_PSIA * mw) / (1.0 * R_PER_BARA * NORMAL_TEMP_RANKINE)
    ft3_h = nm3_h * CUBIC_FEET_PER_M3
    return ft3_h * rho_norm_lb_ft3


def rankine_to_c(t_rankine):
    return (t_rankine - RANKINE_OFFSET) / FAHRENHEIT_RATIO


def ft3_lb_to_m3_kg(v_ft3_lb):
    return v_ft3_lb / M3KG_TO_FT3LB


def btu_lb_to_kcal_kg(h_btu_lb):
    return h_btu_lb / KCAL_KG_TO_BTU_LB


def btu_h_to_kw(q_btu_h):
    return q_btu_h / KW_TO_BTUH


def btu_h_to_kcal_h(q_btu_h):
    return q_btu_h / KCALH_TO_BTUH


def sqin_to_mm2(a_sqin):
    return a_sqin * 645.16


def rankine_to_f(t_rankine):
    return t_rankine - 459.67


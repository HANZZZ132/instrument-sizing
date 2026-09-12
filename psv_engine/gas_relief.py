import math
from .valve_selection import select_orifice
from .validation import validate_gas_inputs
from .constants import (
    GAS_FORMULA_CONSTANT, GAS_SUBCRITICAL_CONSTANT, GAS_DEFAULT_C_COEFF, K_NEAR_ONE_THRESHOLD,
)


def calculate_c_coefficient(k):
    if k <= 0:
        return GAS_DEFAULT_C_COEFF
    if abs(k - 1.0) < K_NEAR_ONE_THRESHOLD:
        return GAS_DEFAULT_C_COEFF

    return GAS_FORMULA_CONSTANT * math.sqrt(k * ((2.0 / (k + 1.0)) ** ((k + 1.0) / (k - 1.0))))


def calculate_f2_coefficient(k, r):
    """
    Calculate F2 coefficient for subcritical gas flow.
    r = P2 / P1 (Back pressure / Relieving pressure)
    """
    if r >= 1.0 or r <= 0.0:
        return 0.0

    if abs(k - 1.0) < K_NEAR_ONE_THRESHOLD:
        inner = (- (r ** 2.0) * math.log(r)) / (1.0 - r)
        return math.sqrt(max(inner, 0.0))

    term1 = k / (k - 1.0)
    term2 = r ** (2.0 / k)
    term3 = (1.0 - (r ** ((k - 1.0) / k))) / (1.0 - r)

    return math.sqrt(max(term1 * term2 * term3, 0.0))



def calculate_gas_relief_area(w_lb_h, p1_psia, p2_psia, t_rankine, z, mw, k, kd=0.975, kb=1.0, kc=1.0, num_valves=1):
    """
    Calculate required area for gas/vapor relief using API 520 formulation.
    Determines whether flow is critical or subcritical automatically.

    Parameters:
    w_lb_h: Mass flow rate in lb/h
    p1_psia: Relieving pressure in psia
    p2_psia: Total back pressure in psia
    t_rankine: Relieving temperature in Rankine
    z: Compressibility factor
    mw: Molecular weight
    k: Ratio of specific heats (Cp/Cv)
    kd: Discharge coefficient (default 0.975 for gas)
    kb: Back pressure correction factor (default 1.0)
    kc: Combination correction factor for rupture disks (default 1.0)
    """
    validate_gas_inputs(w_lb_h, p1_psia, p2_psia, t_rankine, z, mw, k, kd)
    if num_valves < 1:
        raise ValueError("num_valves must be >= 1")

    p_cf = p1_psia * ((2.0 / (k + 1.0)) ** (k / (k - 1.0)))

    flow_type = "CRITICAL" if p2_psia <= p_cf else "SUBCRITICAL"

    if flow_type == "CRITICAL":
        c = calculate_c_coefficient(k)
        term_sqrt = math.sqrt((z * t_rankine) / mw)
        a_req = (w_lb_h / (c * kd * p1_psia * kb * kc)) * term_sqrt
        f2 = None
    else:
        r = p2_psia / p1_psia
        f2 = calculate_f2_coefficient(k, r)
        if f2 <= 0:
            raise ValueError("Subcritical flow calculation failed: F2 coefficient is zero or negative.")
        c = None
        # API 520 subcritical equation: Kb does NOT appear (back pressure is
        # already accounted for by F2). Including Kb here would be non-standard.
        term_sqrt = math.sqrt((z * t_rankine) / (mw * p1_psia * (p1_psia - p2_psia)))
        a_req = (w_lb_h / (GAS_SUBCRITICAL_CONSTANT * f2 * kd * kc)) * term_sqrt

    a_req_per_valve = a_req / num_valves
    letter, selected_area = select_orifice(a_req_per_valve)
    loading_pct = (a_req_per_valve / selected_area * 100.0
                   if isinstance(selected_area, (int, float)) else None)

    return {
        'Flow_Type': flow_type,
        'Critical_Pressure_psia': p_cf,
        'C_Coefficient': c,
        'F2_Coefficient': f2,
        'Required_Area_sqin': a_req_per_valve,
        'Selected_Orifice_Letter': letter,
        'Selected_Orifice_Area_sqin': selected_area,
        'Orifice_Loading_Pct': loading_pct,
        'Kd': kd,
        'Kb': kb,
        'Kc': kc,
        'Num_Valves': num_valves
    }

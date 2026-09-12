"""
Pilot-operated pressure relief valve sizing (API 520 Part I Section 7).

Pilot-operated valves have distinct Kd values:
- Gas/Vapor: Kd = 0.99
- Liquid: Kd = 0.80
- Two-phase: Kd = 0.85

Also, pilot valves can operate closer to set pressure and
have lower blowdown (typically 3-5% vs 7-15% for conventional).
"""
import math
from typing import Dict, Optional, Union
from .valve_selection import select_orifice
from .kb_coefficient import get_kb
from .constants import (
    LIQUID_FORMULA_CONSTANT, GAS_SUBCRITICAL_CONSTANT, ATMOSPHERIC_PSIA,
)


# API 520 Table 13 — Pilot-operated discharge coefficients
KD_GAS = 0.99
KD_LIQUID = 0.80
KD_TWO_PHASE = 0.85


def calculate_pilot_gas_area(
    w_lb_h: float,
    p1_psia: float,
    p2_psia: float,
    t_rankine: float,
    z: float,
    mw: float,
    k: float,
    kc: float = 1.0,
    kb: Optional[float] = None,
    set_pressure_psig: Optional[float] = None,
    num_valves: int = 1,
    overpressure_pct: float = 10.0,
) -> Dict[str, Union[float, str]]:
    """
    Calculate required orifice area for a pilot-operated gas relief valve.
    
    Uses Kd = 0.99 per API 520 Section 7.
    """
    from .gas_relief import calculate_c_coefficient, calculate_f2_coefficient

    p_cf = p1_psia * ((2.0 / (k + 1.0)) ** (k / (k - 1.0)))
    flow_type = "CRITICAL" if p2_psia <= p_cf else "SUBCRITICAL"

    if kb is None:
        if set_pressure_psig:
            sp = set_pressure_psig
        else:
            p1_gauge = max(p1_psia - ATMOSPHERIC_PSIA, 0.0)
            sp = p1_gauge / (1.0 + overpressure_pct / 100.0)
        kb = get_kb(p2_psia, sp, "conventional", overpressure_pct)

    if flow_type == "CRITICAL":
        c = calculate_c_coefficient(k)
        term_sqrt = math.sqrt((z * t_rankine) / mw)
        a_req = (w_lb_h / (c * KD_GAS * p1_psia * kb * kc)) * term_sqrt
    else:
        r = p2_psia / p1_psia
        f2 = calculate_f2_coefficient(k, r)
        term_sqrt = math.sqrt((z * t_rankine) / (mw * p1_psia * (p1_psia - p2_psia)))
        a_req = (w_lb_h / (GAS_SUBCRITICAL_CONSTANT * f2 * KD_GAS * kb * kc)) * term_sqrt

    a_req_per_valve = a_req / num_valves
    letter, selected_area = select_orifice(a_req_per_valve)

    return {
        'Flow_Type': flow_type,
        'Kd': KD_GAS,
        'Required_Area_sqin': a_req_per_valve,
        'Selected_Orifice_Letter': letter,
        'Selected_Orifice_Area_sqin': selected_area,
        'Num_Valves': num_valves,
    }


def calculate_pilot_liquid_area(
    q_gpm: float,
    p1_psia: float,
    p2_psia: float,
    g: float,
    mu_cp: float,
    kw: float = 1.0,
    num_valves: int = 1,
) -> Dict[str, Union[float, str]]:
    """
    Calculate required orifice area for a pilot-operated liquid relief valve.
    
    Uses Kd = 0.80 per API 520 Section 7.
    """
    from .liquid_relief import calculate_reynolds, calculate_kv, select_orifice as _select

    delta_p = p1_psia - p2_psia
    if delta_p <= 0:
        raise ValueError("Relieving pressure must be greater than back pressure.")

    a_req_no_visc = (q_gpm / (LIQUID_FORMULA_CONSTANT * KD_LIQUID * kw * 1.0)) * math.sqrt(g / delta_p)
    a_req_no_visc_per_valve = a_req_no_visc / num_valves

    letter, selected_area = _select(a_req_no_visc_per_valve)

    if isinstance(selected_area, float):
        re = calculate_reynolds(q_gpm / num_valves, g, mu_cp, selected_area)
        kv = calculate_kv(re)
        a_req_final = (q_gpm / (LIQUID_FORMULA_CONSTANT * KD_LIQUID * kw * kv)) * math.sqrt(g / delta_p)
        a_req_final_per_valve = a_req_final / num_valves
        final_letter, final_selected_area = _select(a_req_final_per_valve)

        for _ in range(3):
            if isinstance(final_selected_area, float):
                re = calculate_reynolds(q_gpm / num_valves, g, mu_cp, final_selected_area)
                kv = calculate_kv(re)
                a_req_final = (q_gpm / (LIQUID_FORMULA_CONSTANT * KD_LIQUID * kw * kv)) * math.sqrt(g / delta_p)
                a_req_final_per_valve = a_req_final / num_valves
                new_letter, new_selected_area = _select(a_req_final_per_valve)
                if new_letter == final_letter:
                    break
                final_letter, final_selected_area = new_letter, new_selected_area
    else:
        kv = 1.0
        re = float('inf')
        a_req_final = a_req_no_visc
        a_req_final_per_valve = a_req_no_visc_per_valve
        final_letter = letter
        final_selected_area = selected_area

    return {
        'Kd': KD_LIQUID,
        'Reynolds_Number': re,
        'Kv': kv,
        'Required_Area_sqin': a_req_final_per_valve,
        'Selected_Orifice_Letter': final_letter,
        'Selected_Orifice_Area_sqin': final_selected_area,
        'Num_Valves': num_valves,
    }


__all__ = [
    "calculate_pilot_gas_area",
    "calculate_pilot_liquid_area",
    "KD_GAS",
    "KD_LIQUID",
    "KD_TWO_PHASE",
]
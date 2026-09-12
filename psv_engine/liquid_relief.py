import math
from .valve_selection import select_orifice
from .validation import validate_liquid_inputs
from .constants import (
    LIQUID_FORMULA_CONSTANT, REYNOLDS_CONSTANT,
    KV_A, KV_B, KV_C, ATMOSPHERIC_PSIA,
)

# API 520 Part I Figure 38 — Capacity correction factor due to overpressure Kp
KP_CURVE = [
    (0.0, 0.60),
    (2.5, 0.62),
    (5.0, 0.70),
    (7.5, 0.85),
    (10.0, 1.00),
    (15.0, 1.06),
    (20.0, 1.11),
    (25.0, 1.15),
]

# API 520 Part I Figure 37 — Capacity correction factor due to back pressure Kw (balanced bellows)
KW_BALANCED_BELLOWS_LIQUID = [
    (0.0, 1.00),
    (15.0, 1.00),
    (20.0, 0.97),
    (25.0, 0.94),
    (30.0, 0.89),
    (35.0, 0.84),
    (40.0, 0.78),
    (45.0, 0.72),
    (50.0, 0.65),
]


def _interpolate_points(val: float, points: list) -> float:
    """Linear interpolation between points [(x0, y0), (x1, y1), ...]."""
    if val <= points[0][0]:
        return points[0][1]
    if val >= points[-1][0]:
        return points[-1][1]
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        if x1 <= val <= x2:
            return y1 + ((val - x1) / (x2 - x1)) * (y2 - y1)
    return points[-1][1]


def calculate_kp(overpressure_pct: float) -> float:
    """
    API 520 Part I Figure 38 — Capacity correction factor for overpressure Kp.
    Kp = 1.0 at 10% overpressure (certified rating point).
    """
    if overpressure_pct is None:
        return 1.0
    return _interpolate_points(max(overpressure_pct, 0.0), KP_CURVE)


def calculate_kw_liquid(back_pressure_pct: float, valve_type: str = "conventional") -> float:
    """
    API 520 Part I Figure 37 — Back pressure correction factor Kw for liquids.
    For conventional and pilot valves, Kw = 1.0.
    For balanced bellows valves, Kw is 1.0 up to 15% BP, then decreases.
    """
    if valve_type != "balanced_bellows":
        return 1.0
    return _interpolate_points(max(back_pressure_pct, 0.0), KW_BALANCED_BELLOWS_LIQUID)


def calculate_reynolds(q_gpm, g, mu_cp, area_sq_in):
    if area_sq_in <= 0 or mu_cp <= 0:
        return float('inf')
    return (REYNOLDS_CONSTANT * q_gpm * g) / (mu_cp * math.sqrt(area_sq_in))


def calculate_kv(re):
    """API 520 Part I (9th/10th ed.) Eq. (34): Kv = (0.9935 + 2.878/Re^0.5 + 342.75/Re^1.5)^-1."""
    if re <= 0 or math.isinf(re):
        return 1.0
    kv = 1.0 / (KV_A + KV_B / re ** 0.5 + KV_C / re ** 1.5)
    return min(kv, 1.0)


def calculate_liquid_relief_area(
    q_gpm,
    p1_psia,
    p2_psia,
    g,
    mu_cp,
    kd=0.65,
    kw=None,
    kc=1.0,
    num_valves=1,
    kp=None,
    overpressure_pct=10.0,
    valve_type="conventional",
    set_pressure_psig=None,
    atm_psia=ATMOSPHERIC_PSIA,
):
    """
    API 520 Part I Section 5.8 — Liquid relief valve sizing.

    Uses Reynolds-number-dependent iterative sizing with Kv viscosity
    correction factor and Kp overpressure correction factor.
    Returns required area, selected orifice, Re, Kv, Kp, and Kw.
    """
    if kp is None:
        kp = calculate_kp(overpressure_pct)

    if kw is None:
        if valve_type == "balanced_bellows":
            if set_pressure_psig is not None and set_pressure_psig > 0:
                sp = set_pressure_psig
            else:
                p1_gauge = max(p1_psia - atm_psia, 0.0)
                sp = p1_gauge / (1.0 + overpressure_pct / 100.0) if overpressure_pct > -100 else 1.0
            bp_gauge = max(p2_psia - atm_psia, 0.0)
            bp_pct = (bp_gauge / sp * 100.0) if sp > 0 else 0.0
            kw = calculate_kw_liquid(bp_pct, valve_type)
        else:
            kw = 1.0

    validate_liquid_inputs(q_gpm, p1_psia, p2_psia, g, mu_cp, kd, kw, kp)
    if num_valves < 1:
        raise ValueError("num_valves must be >= 1")

    delta_p = p1_psia - p2_psia

    a_req_no_visc = (q_gpm / (LIQUID_FORMULA_CONSTANT * kd * kw * kc * kp)) * math.sqrt(g / delta_p)
    a_req_no_visc_per_valve = a_req_no_visc / num_valves

    letter, selected_area = select_orifice(a_req_no_visc_per_valve)

    re = calculate_reynolds(q_gpm / num_valves, g, mu_cp, selected_area)
    kv = calculate_kv(re)
    a_req_final = (q_gpm / (LIQUID_FORMULA_CONSTANT * kd * kw * kc * kv * kp)) * math.sqrt(g / delta_p)
    a_req_final_per_valve = a_req_final / num_valves
    final_letter, final_selected_area = select_orifice(a_req_final_per_valve)

    prev_letter = final_letter
    for iteration in range(10):
        re = calculate_reynolds(q_gpm / num_valves, g, mu_cp, final_selected_area)
        kv = calculate_kv(re)
        a_req_final = (q_gpm / (LIQUID_FORMULA_CONSTANT * kd * kw * kc * kv * kp)) * math.sqrt(g / delta_p)
        a_req_final_per_valve = a_req_final / num_valves
        new_letter, new_selected_area = select_orifice(a_req_final_per_valve)
        if new_letter == prev_letter:
            final_letter, final_selected_area = new_letter, new_selected_area
            break
        prev_letter = new_letter
        final_letter, final_selected_area = new_letter, new_selected_area

    loading_pct = (a_req_final_per_valve / final_selected_area * 100.0
                   if isinstance(final_selected_area, (int, float)) else None)

    return {
        'Required_Area_No_Visc_sqin': a_req_no_visc_per_valve,
        'Reynolds_Number': re,
        'Kv': kv,
        'Kp': kp,
        'Kw': kw,
        'Overpressure_Pct': overpressure_pct,
        'Required_Area_Final_sqin': a_req_final_per_valve,
        'Selected_Orifice_Letter': final_letter,
        'Selected_Orifice_Area_sqin': final_selected_area,
        'Orifice_Loading_Pct': loading_pct,
        'Kd': kd,
        'Kc': kc,
        'Num_Valves': num_valves,
        'Valve_Type': valve_type,
    }


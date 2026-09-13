import math
from .valve_selection import select_orifice
from .validation import validate_liquid_inputs
from .constants import LIQUID_FORMULA_CONSTANT

# API 520 Part I, 10th ed., Figure 32 — preliminary Kw curve for balanced
# spring-loaded PRVs in liquid service.  The standard notes that the curve may
# be used when the manufacturer is not known; manufacturer data governs final
# sizing. Values are a screening interpolation of the published curve, with the
# 20 % point anchored to API 520 Example 5 (Kw = 0.97).
KW_BALANCED_BELLOWS_LIQUID = [
    (0.0, 1.00),
    (15.0, 1.00),
    (20.0, 0.97),
    (25.0, 0.925),
    (30.0, 0.875),
    (35.0, 0.825),
    (40.0, 0.775),
    (45.0, 0.725),
    (50.0, 0.675),
]

# API 520 Part I, 10th ed., Figure 39 is for NONCERTIFIED liquid PRVs.  It is
# intentionally not applied in the certified-liquid sizing routine below.
_KP_NONCERTIFIED_SCREENING = [
    (10.0, 0.60), (15.0, 0.80), (20.0, 0.93), (25.0, 1.00),
    (30.0, 1.04), (40.0, 1.08), (50.0, 1.10),
]


def _interpolate_points(val: float, points: list[tuple[float, float]]) -> float:
    if val <= points[0][0]:
        return points[0][1]
    if val >= points[-1][0]:
        return points[-1][1]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if x1 <= val <= x2:
            return y1 + ((val - x1) / (x2 - x1)) * (y2 - y1)
    return points[-1][1]


def calculate_kp_noncertified(overpressure_pct: float) -> float:
    """Screening interpolation of API 520 Figure 39 for noncertified liquid PRVs."""
    return _interpolate_points(max(float(overpressure_pct), 0.0), _KP_NONCERTIFIED_SCREENING)


# Backward-compatible alias. It is NOT used by calculate_liquid_relief_area().
def calculate_kp(overpressure_pct: float) -> float:
    return calculate_kp_noncertified(overpressure_pct)


def calculate_kw_liquid(back_pressure_pct: float, valve_type: str = "conventional") -> float:
    """Preliminary API 520 Figure 32 Kw for balanced spring-loaded liquid PRVs."""
    vt = str(valve_type).strip().lower()
    if vt not in {"balanced_bellows", "balanced", "balanced bellows"}:
        return 1.0
    bp = max(float(back_pressure_pct), 0.0)
    if bp > 50.0:
        raise ValueError(
            "API 520 Figure 32 screening curve is limited to backpressure up to 50% of set pressure; "
            "use manufacturer data for this case."
        )
    return _interpolate_points(bp, KW_BALANCED_BELLOWS_LIQUID)


def calculate_reynolds(q_gpm, g, viscosity, area_sq_in, viscosity_unit="cP"):
    """API 520 Part I, 10th ed., Eq. (35) or Eq. (36), USC units."""
    if area_sq_in <= 0 or viscosity <= 0:
        return float("inf")
    unit = str(viscosity_unit).strip().lower()
    if unit in {"cp", "centipoise", "centipoises"}:
        # Eq. (35): Re = Q(2800*G_l)/(mu*sqrt(Aselected))
        return (float(q_gpm) * (2800.0 * float(g))) / (float(viscosity) * math.sqrt(float(area_sq_in)))
    if unit in {"ssu", "sus", "saybolt", "saybolt universal seconds"}:
        # Eq. (36): Re = 12,700 Q / (U sqrt(Aselected))
        if viscosity < 100.0:
            raise ValueError("API 520 Eq. (36) is not recommended for viscosity below 100 SSU.")
        return (12700.0 * float(q_gpm)) / (float(viscosity) * math.sqrt(float(area_sq_in)))
    raise ValueError("viscosity_unit must be 'cP' or 'SSU'.")


def calculate_kv(re):
    """API 520 Part I, 10th ed., Eq. (34): Kv = (170/Re + 1)^(-0.5), valid for Re >= 80."""
    if re <= 0 or math.isinf(re):
        return 1.0
    if re < 80.0:
        raise ValueError(
            f"Calculated Reynolds number Re={re:.1f} is below the API 520 Eq. (34) applicability limit Re >= 80."
        )
    return min((170.0 / re + 1.0) ** -0.5, 1.0)


def calculate_liquid_relief_area(
    q_gpm,
    p1_psig,
    p2_psig,
    g,
    viscosity,
    kd=0.65,
    kw=None,
    kc=1.0,
    num_valves=1,
    kp=None,
    overpressure_pct=10.0,
    valve_type="conventional",
    set_pressure_psig=None,
    atm_psia=None,
    viscosity_unit="cP",
):
    """API 520 Part I, 10th ed., Section 5.8 certified liquid PRV sizing.

    Pressure inputs are GAUGE pressures in psig, as required by API 520
    Equations (32)/(33).  Kp is retained only for backward API compatibility
    with older callers but is deliberately NOT applied: Kp belongs to the
    noncertified-liquid procedure in Section 5.9 / Figure 39.
    """
    if num_valves < 1:
        raise ValueError("num_valves must be >= 1")
    if set_pressure_psig is None:
        if overpressure_pct <= -100.0:
            raise ValueError("Invalid overpressure percentage.")
        set_pressure_psig = float(p1_psig) / (1.0 + float(overpressure_pct) / 100.0)

    vt = str(valve_type).strip().lower()
    if kw is None:
        if vt in {"balanced_bellows", "balanced", "balanced bellows"}:
            bp_pct = (float(p2_psig) / float(set_pressure_psig) * 100.0) if set_pressure_psig > 0 else 0.0
            kw = calculate_kw_liquid(bp_pct, "balanced_bellows")
        else:
            kw = 1.0

    # Kp intentionally fixed to 1.0 for Section 5.8 certified PRV sizing.
    validate_liquid_inputs(q_gpm, p1_psig, p2_psig, g, viscosity, kd, kw, 1.0)
    delta_p = float(p1_psig) - float(p2_psig)
    q_per_valve = float(q_gpm) / int(num_valves)

    # Step 1 — Eq. (32) with Kv = 1.0, then select the next API 526 orifice.
    ar = (q_per_valve / (LIQUID_FORMULA_CONSTANT * kd * kw * kc)) * math.sqrt(float(g) / delta_p)
    selected_letter, selected_area = select_orifice(ar)
    if selected_letter == "Multiple Valves Required":
        return {
            "Required_Area_No_Visc_sqin": ar,
            "Required_Area_Final_sqin": ar,
            "Selected_Orifice_Letter": selected_letter,
            "Selected_Orifice_Area_sqin": selected_area,
            "Kv": None,
            "Reynolds_Number": None,
            "Kw": kw,
            "Kp": 1.0,
            "Kp_Applied": False,
            "Kd": kd,
            "Kc": kc,
            "Num_Valves": num_valves,
            "Valve_Type": valve_type,
            "Viscosity_Unit": viscosity_unit,
        }

    unit = str(viscosity_unit).strip().lower()
    # API 520 permits Kv=1 for <=100 cP. For SSU, calculate Re via Eq. (36).
    if unit in {"cp", "centipoise", "centipoises"} and float(viscosity) <= 100.0:
        re = calculate_reynolds(q_per_valve, g, viscosity, selected_area, viscosity_unit)
        kv = 1.0
        final_area = ar
        final_letter, final_selected_area = selected_letter, selected_area
        iterations = 0
    else:
        final_letter, final_selected_area = selected_letter, selected_area
        iterations = 0
        for iterations in range(1, 12):
            re = calculate_reynolds(q_per_valve, g, viscosity, final_selected_area, viscosity_unit)
            kv = calculate_kv(re)
            final_area = ar / kv
            new_letter, new_area = select_orifice(final_area)
            if new_letter == final_letter:
                final_selected_area = new_area
                break
            final_letter, final_selected_area = new_letter, new_area
        else:
            raise RuntimeError("Liquid viscosity iteration did not converge within 11 iterations.")

    loading_pct = final_area / final_selected_area * 100.0 if isinstance(final_selected_area, (int, float)) else None
    bp_pct = float(p2_psig) / float(set_pressure_psig) * 100.0 if set_pressure_psig > 0 else None

    return {
        "Required_Area_No_Visc_sqin": ar,
        "Reynolds_Number": re,
        "Kv": kv,
        "Kw": kw,
        "Kp": 1.0,
        "Kp_Applied": False,
        "Overpressure_Pct": overpressure_pct,
        "Backpressure_Pct_of_Set": bp_pct,
        "Required_Area_Final_sqin": final_area,
        "Selected_Orifice_Letter": final_letter,
        "Selected_Orifice_Area_sqin": final_selected_area,
        "Orifice_Loading_Pct": loading_pct,
        "Kd": kd,
        "Kc": kc,
        "Num_Valves": num_valves,
        "Valve_Type": valve_type,
        "Viscosity": viscosity,
        "Viscosity_Unit": viscosity_unit,
        "Iteration_Count": iterations,
        "Pressure_Basis": "Gauge pressure (psig) per API 520 Eq. 32/33",
        "Method": "API 520 Part I Section 5.8 — certified liquid PRV",
    }

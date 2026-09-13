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
    """API 520 Eq. (22) coefficient F2 for subcritical gas/vapor flow."""
    if r >= 1.0 or r <= 0.0:
        return 0.0
    if abs(k - 1.0) < K_NEAR_ONE_THRESHOLD:
        inner = (-(r ** 2.0) * math.log(r)) / (1.0 - r)
        return math.sqrt(max(inner, 0.0))
    term1 = k / (k - 1.0)
    term2 = r ** (2.0 / k)
    term3 = (1.0 - (r ** ((k - 1.0) / k))) / (1.0 - r)
    return math.sqrt(max(term1 * term2 * term3, 0.0))


def calculate_gas_relief_area(
    w_lb_h,
    p1_psia,
    p2_psia,
    t_rankine,
    z,
    mw,
    k,
    kd=0.975,
    kb=1.0,
    kc=1.0,
    num_valves=1,
    valve_type="conventional",
):
    """API 520 Part I gas/vapor preliminary PRV sizing.

    P1 and P2 are absolute pressures.  Conventional and pilot-operated valves
    use the direct subcritical equations when P2/P1 exceeds the critical ratio.
    Balanced spring-loaded PRVs use the critical-flow equation with Kb even
    when the downstream condition is subcritical, per API 520 §5.6.4.3.
    """
    validate_gas_inputs(w_lb_h, p1_psia, p2_psia, t_rankine, z, mw, k, kd)
    if num_valves < 1:
        raise ValueError("num_valves must be >= 1")

    vt = str(valve_type).strip().lower().replace("-", "_").replace(" ", "_")
    if vt in {"balanced", "balanced_bellows", "balanced_spring_loaded"}:
        vt = "balanced_bellows"
    elif vt in {"pilot", "pilot_operated", "pilotoperated"}:
        vt = "pilot"
    elif vt in {"conventional", "spring_loaded", "conventional_spring_loaded"}:
        vt = "conventional"
    else:
        raise ValueError("valve_type must be conventional, balanced_bellows, or pilot.")

    if vt != "balanced_bellows":
        kb_effective = 1.0
    else:
        if kb <= 0 or kb > 1.0:
            raise ValueError("Balanced-bellows Kb must be > 0 and <= 1.0 for preliminary sizing.")
        kb_effective = float(kb)

    p_cf = p1_psia * ((2.0 / (k + 1.0)) ** (k / (k - 1.0)))
    physical_flow_type = "CRITICAL" if p2_psia <= p_cf else "SUBCRITICAL"

    c = None
    f2 = None
    if physical_flow_type == "CRITICAL":
        c = calculate_c_coefficient(k)
        term_sqrt = math.sqrt((z * t_rankine) / mw)
        a_req = (w_lb_h / (c * kd * p1_psia * kb_effective * kc)) * term_sqrt
        sizing_method = "API 520 critical-flow equation"
    elif vt == "balanced_bellows":
        # API 520 §5.6.4.3: balanced PRVs should still be sized with the
        # critical-flow equations and Kb supplied by the manufacturer.
        c = calculate_c_coefficient(k)
        term_sqrt = math.sqrt((z * t_rankine) / mw)
        a_req = (w_lb_h / (c * kd * p1_psia * kb_effective * kc)) * term_sqrt
        sizing_method = "API 520 §5.6.4.3 balanced PRV: critical equation + Kb for subcritical condition"
    else:
        r = p2_psia / p1_psia
        f2 = calculate_f2_coefficient(k, r)
        if f2 <= 0:
            raise ValueError("Subcritical flow calculation failed: F2 coefficient is zero or negative.")
        # API 520 Eq. (16): backpressure is explicitly present in the equation;
        # Kb is not used in the direct subcritical formulation.
        term_sqrt = math.sqrt((z * t_rankine) / (mw * p1_psia * (p1_psia - p2_psia)))
        a_req = (w_lb_h / (GAS_SUBCRITICAL_CONSTANT * f2 * kd * kc)) * term_sqrt
        sizing_method = "API 520 direct subcritical equation (conventional/pilot)"

    a_req_per_valve = a_req / num_valves
    letter, selected_area = select_orifice(a_req_per_valve)
    loading_pct = (
        a_req_per_valve / selected_area * 100.0
        if isinstance(selected_area, (int, float)) else None
    )

    notes = []
    if vt == "balanced_bellows":
        notes.append("Use manufacturer Kb for final sizing; API Figure 31 is preliminary guidance only.")
        if physical_flow_type == "SUBCRITICAL" and abs(kb_effective - 1.0) < 1e-12:
            notes.append("Subcritical balanced-bellows case is currently using Kb=1.0; enter the applicable manufacturer/Figure-31 screening factor before relying on the area.")
    elif kb != 1.0:
        notes.append("Input Kb was ignored because conventional/pilot direct equations do not apply Kb in this implementation.")

    return {
        "Flow_Type": physical_flow_type,
        "Critical_Pressure_psia": p_cf,
        "C_Coefficient": c,
        "F2_Coefficient": f2,
        "Required_Area_sqin": a_req_per_valve,
        "Selected_Orifice_Letter": letter,
        "Selected_Orifice_Area_sqin": selected_area,
        "Orifice_Loading_Pct": loading_pct,
        "Kd": kd,
        "Kb_Input": kb,
        "Kb_Applied": kb_effective,
        "Kc": kc,
        "Num_Valves": num_valves,
        "Valve_Type": vt,
        "Sizing_Method": sizing_method,
        "Notes": " ".join(notes),
    }

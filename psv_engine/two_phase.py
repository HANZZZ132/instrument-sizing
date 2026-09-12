import math
from .valve_selection import select_orifice
from .validation import validate_two_phase_inputs
from .constants import (
    OMEGA_MULTIPLIER, TWO_PHASE_CRITICAL_CONSTANT, TWO_PHASE_AREA_CONSTANT,
)


def calculate_omega_flashing(v0, v9):
    if v0 <= 0:
        raise ValueError("Specific volume at inlet (v0) must be positive.")
    return OMEGA_MULTIPLIER * ((v9 / v0) - 1.0)


def calculate_critical_pressure_ratio(omega):
    """
    API 520 Part I 10th Ed. (2020) Annex C, Eq. (C.15) — Critical pressure
    ratio (ηc) for two-phase flow. Single unified correlation for all ω > 0.
    """
    if omega <= 0:
        return 1.0

    base = 1.0 + (1.0446 - 0.0093431 * math.sqrt(omega)) * omega ** (-0.56261)
    power = -0.70356 + 0.014685 * math.log(omega)
    return base ** power


def calculate_two_phase_area(w_lb_h, p0_psia, p_back_psia, v0_ft3_lb, omega, kd=0.85, kb=1.0, kc=1.0, num_valves=1):
    """
    Calculate required area for two-phase flow (Omega method) using API 520.

    w_lb_h: Mass flow rate in lb/h
    p0_psia: Stagnation relieving pressure in psia
    p_back_psia: Back pressure in psia
    v0_ft3_lb: Specific volume at inlet in ft3/lb
    omega: Compressibility parameter
    """
    validate_two_phase_inputs(w_lb_h, p0_psia, p_back_psia, v0_ft3_lb, omega, kd)
    if num_valves < 1:
        raise ValueError("num_valves must be >= 1")

    eta_c = calculate_critical_pressure_ratio(omega)
    p_critical_psia = eta_c * p0_psia

    flow_type = "CRITICAL" if p_back_psia <= p_critical_psia else "SUBCRITICAL"

    if flow_type == "CRITICAL":
        g_flux = TWO_PHASE_CRITICAL_CONSTANT * eta_c * math.sqrt(p0_psia / (v0_ft3_lb * omega))
    else:
        eta = p_back_psia / p0_psia
        # API 520 Annex C subcritical mass flux (no 1/sqrt(omega) factor here).
        term_sqrt1 = math.sqrt(p0_psia / v0_ft3_lb)

        inner = -2.0 * (omega * math.log(eta) + (omega - 1.0) * (1.0 - eta))
        if inner < 0:
            raise ValueError(
                f"Subcritical two-phase flow calculation failed: negative discriminant "
                f"(omega={omega:.3f}, eta={eta:.3f}). The back pressure may be too close to "
                f"the relieving pressure or the omega parameter may be invalid."
            )

        term_sqrt2 = math.sqrt(inner)
        denominator = (omega / eta) + 1.0 - omega
        if denominator <= 0:
            raise ValueError("Subcritical two-phase flow calculation failed: denominator is zero or negative.")

        g_flux = (TWO_PHASE_CRITICAL_CONSTANT * term_sqrt1 * term_sqrt2) / denominator

    if g_flux <= 0:
        raise ValueError("Mass flux calculation resulted in zero or negative value.")

    a_req = w_lb_h / (TWO_PHASE_AREA_CONSTANT * g_flux * kd * kb * kc)

    a_req_per_valve = a_req / num_valves

    letter, selected_area = select_orifice(a_req_per_valve)
    loading_pct = (a_req_per_valve / selected_area * 100.0
                   if isinstance(selected_area, (int, float)) else None)

    return {
        'Omega': omega,
        'Critical_Pressure_Ratio_hc': eta_c,
        'Critical_Pressure_psia': p_critical_psia,
        'Flow_Type': flow_type,
        'Mass_Flux_G_lb_s_ft2': g_flux,
        'Required_Area_sqin': a_req_per_valve,
        'Selected_Orifice_Letter': letter,
        'Selected_Orifice_Area_sqin': selected_area,
        'Orifice_Loading_Pct': loading_pct,
        'Kd': kd,
        'Num_Valves': num_valves
    }

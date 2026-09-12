import math
from .constants import (
    KD_MIN, KD_MAX, KW_MIN, KW_MAX, KP_MIN, KP_MAX, Z_MIN, Z_MAX, K_MIN, K_MAX, F_FACTOR_MIN, F_FACTOR_MAX,
)

class ValidationError(Exception):
    pass

def validate_positive(value, name):
    if value <= 0:
        raise ValidationError(f"{name} must be positive (got {value})")
    return value

def validate_non_negative(value, name):
    if value < 0:
        raise ValidationError(f"{name} must be non-negative (got {value})")
    return value

def validate_range(value, name, min_val, max_val):
    if value < min_val or value > max_val:
        raise ValidationError(f"{name} must be between {min_val} and {max_val} (got {value})")
    return value

def validate_liquid_inputs(q_gpm, p1_psia, p2_psia, g, mu_cp, kd=0.65, kw=1.0, kp=1.0):
    validate_positive(q_gpm, "Flow Rate (Q)")
    validate_positive(p1_psia, "Relieving Pressure (P1)")
    validate_positive(p2_psia, "Back Pressure (P2)")
    validate_positive(g, "Specific Gravity (G)")
    validate_positive(mu_cp, "Viscosity")
    validate_range(kd, "Discharge Coefficient (Kd)", KD_MIN, KD_MAX)
    validate_range(kw, "Back Pressure Factor (Kw)", KW_MIN, KW_MAX)
    validate_range(kp, "Overpressure Factor (Kp)", KP_MIN, KP_MAX)
    if p2_psia >= p1_psia:
        raise ValidationError(f"Back Pressure (P2={p2_psia:.2f}) must be less than Relieving Pressure (P1={p1_psia:.2f})")


def validate_gas_inputs(w_lb_h, p1_psia, p2_psia, t_rankine, z, mw, k, kd=0.975):
    validate_positive(w_lb_h, "Mass Flow Rate (W)")
    validate_positive(p1_psia, "Relieving Pressure (P1)")
    validate_non_negative(p2_psia, "Back Pressure (P2)")
    validate_positive(t_rankine, "Temperature (Rankine)")
    validate_range(z, "Compressibility (Z)", Z_MIN, Z_MAX)
    validate_positive(mw, "Molecular Weight (MW)")
    validate_range(k, "Specific Heat Ratio (k)", K_MIN, K_MAX)
    validate_range(kd, "Discharge Coefficient (Kd)", KD_MIN, KD_MAX)
    if p2_psia >= p1_psia:
        raise ValidationError(f"Back Pressure (P2={p2_psia:.2f}) must be less than Relieving Pressure (P1={p1_psia:.2f})")

def validate_two_phase_inputs(w_lb_h, p0_psia, p_back_psia, v0_ft3_lb, omega, kd=0.85):
    validate_positive(w_lb_h, "Mass Flow Rate (W)")
    validate_positive(p0_psia, "Relieving Pressure (P0)")
    validate_non_negative(p_back_psia, "Back Pressure")
    validate_positive(v0_ft3_lb, "Specific Volume at Inlet (v0)")
    validate_positive(omega, "Omega Parameter")
    validate_range(kd, "Discharge Coefficient (Kd)", KD_MIN, KD_MAX)
    if p_back_psia >= p0_psia:
        raise ValidationError(f"Back Pressure ({p_back_psia:.2f}) must be less than Relieving Pressure ({p0_psia:.2f})")

def validate_fire_wetted_inputs(a_wetted_sqft, f_factor, heat_of_vap_btu_lb):
    validate_positive(a_wetted_sqft, "Wetted Area")
    validate_range(f_factor, "Environment Factor (F)", F_FACTOR_MIN, F_FACTOR_MAX)
    validate_positive(heat_of_vap_btu_lb, "Heat of Vaporization")

def validate_fire_unwetted_inputs(a_exposed_sqft, p1_psia, t_gas_rankine, t_wall_rankine, k):
    validate_positive(a_exposed_sqft, "Exposed Area")
    validate_positive(p1_psia, "Relieving Pressure (P1)")
    validate_positive(t_gas_rankine, "Gas Temperature (Rankine)")
    validate_positive(t_wall_rankine, "Wall Temperature (Rankine)")
    validate_range(k, "Specific Heat Ratio (k)", K_MIN, K_MAX)
    if t_wall_rankine <= t_gas_rankine:
        raise ValidationError(f"Wall Temperature ({t_wall_rankine:.1f}R) must be greater than Gas Temperature ({t_gas_rankine:.1f}R)")

def validate_thermal_inputs(b_expansion_coeff, h_heat_transfer_btu_h, g_specific_gravity, c_specific_heat):
    validate_positive(b_expansion_coeff, "Expansion Coefficient (B)")
    validate_positive(h_heat_transfer_btu_h, "Heat Transfer Rate (H)")
    validate_positive(g_specific_gravity, "Specific Gravity (G)")
    validate_positive(c_specific_heat, "Specific Heat (C)")

def validate_blowby_inputs(assumed_flow_kg_h, nominal_cv, calculated_cv_at_blowby):
    validate_positive(assumed_flow_kg_h, "Assumed Flow Rate")
    validate_positive(nominal_cv, "Nominal Cv")
    validate_positive(calculated_cv_at_blowby, "Calculated Cv at Blow-by")

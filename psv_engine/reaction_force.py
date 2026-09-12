"""
Reaction force estimation for pressure relief devices.

API 520 Part II provides the standard method for estimating the reaction
force on a relief valve discharging gas/vapor to atmosphere (or into a
line). The simplified USCS form is:

    F = (W / 68) * sqrt(k * T / M) + (P2 - Pa) * Ae

where
    F   reaction force [lbf]
    W   mass flow rate [lb/h]
    k   specific heat ratio at relieving conditions [-]
    T   relieving temperature [degR]
    M   molecular weight [lb/lbmol]
    P2  pressure at valve outlet [psia]
    Pa  atmospheric (or downstream) pressure [psia]
    Ae  effective outlet flow area [in2]

For liquid service the momentum term is small and usually neglected; the
force is dominated by the pressure term only.
"""
import math
from .constants import ATMOSPHERIC_PSIA

# API 520 Part II momentum constant (USCS).
REACTION_MOMENTUM_CONSTANT = 68.0


def calculate_gas_reaction_force(
    w_lb_h,
    k,
    t_rankine,
    mw,
    outlet_pressure_psia,
    outlet_area_sqin,
    atmospheric_psia=ATMOSPHERIC_PSIA,
):
    """
    Estimate the reaction force [lbf] for a gas/vapor relief valve venting
    to atmosphere, per API 520 Part II.

    Parameters
    ----------
    w_lb_h : Mass flow rate (lb/h)
    k : Specific heat ratio (Cp/Cv)
    t_rankine : Relieving temperature (degR)
    mw : Molecular weight (lb/lbmol)
    outlet_pressure_psia : Pressure at the valve outlet (psia)
    outlet_area_sqin : Effective outlet area (in2)
    atmospheric_psia : Downstream/atmospheric pressure (psia)
    """
    if w_lb_h <= 0:
        raise ValueError("Mass flow rate must be positive.")
    if k <= 0 or mw <= 0:
        raise ValueError("k and MW must be positive.")
    if t_rankine <= 0:
        raise ValueError("Temperature must be positive.")

    momentum_term = (w_lb_h / REACTION_MOMENTUM_CONSTANT) * math.sqrt(k * t_rankine / mw)
    pressure_term = (outlet_pressure_psia - atmospheric_psia) * outlet_area_sqin
    if pressure_term < 0:
        pressure_term = 0.0

    total_force = momentum_term + pressure_term
    return {
        'Total_Reaction_Force_lbf': total_force,
        'Momentum_Term_lbf': momentum_term,
        'Pressure_Term_lbf': pressure_term,
    }


def calculate_liquid_reaction_force(
    q_gpm,
    fluid_density_lb_ft3,
    outlet_area_sqin,
    discharge_velocity_fps=None,
):
    """
    Estimate the reaction force [lbf] for a liquid relief valve (momentum term).

    F = rho * Q * v / gc

    Parameters
    ----------
    q_gpm : Volumetric flow (US gpm)
    fluid_density_lb_ft3 : Fluid density (lb/ft3)
    outlet_area_sqin : Effective outlet area (in2)
    discharge_velocity_fps : Discharge velocity (ft/s). If None, computed
        from the volumetric flow and outlet area.
    """
    if q_gpm <= 0:
        raise ValueError("Flow rate must be positive.")
    if fluid_density_lb_ft3 <= 0 or outlet_area_sqin <= 0:
        raise ValueError("Density and outlet area must be positive.")

    q_ft3_s = q_gpm / (7.48052 * 60.0)
    outlet_area_ft2 = outlet_area_sqin / 144.0
    if discharge_velocity_fps is None:
        discharge_velocity_fps = q_ft3_s / outlet_area_ft2 if outlet_area_ft2 > 0 else 0.0

    mass_flow_lb_s = q_ft3_s * fluid_density_lb_ft3
    force = mass_flow_lb_s * discharge_velocity_fps / 32.174
    return {
        'Total_Reaction_Force_lbf': force,
        'Discharge_Velocity_fps': discharge_velocity_fps,
    }
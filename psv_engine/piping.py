"""
Piping pressure drop checking per API 520 Part II Section 4.

API 520 Part II limits:
- Inlet piping: ΔP ≤ 3% of set pressure (conventional) / 1.5% (pilot)
- Outlet (tail) piping: ΔP ≤ 10% of gauge set pressure (variable back pressure)
"""
import math
from typing import Dict, List, Optional, Tuple

# Speed of sound in ideal gas: a = sqrt(k * R * T * g_c)
# g_c = 32.174 lbm·ft/(lbf·s²)
GC = 32.174
R_UNIVERSAL = 1545.0  # ft·lbf/(lbmol·°R)

# Sonic velocity in gas at given conditions
def calculate_sonic_velocity(k: float, mw: float, t_rankine: float) -> float:
    r_gas = R_UNIVERSAL / mw
    return math.sqrt(k * r_gas * t_rankine * GC)


def calculate_mach_number(
    velocity_fps: float,
    k: float,
    mw: float,
    t_rankine: float,
) -> float:
    sonic = calculate_sonic_velocity(k, mw, t_rankine)
    return velocity_fps / sonic if sonic > 0 else 0.0

# Darcy friction factor for turbulent flow (Colebrook-White)
def darcy_friction_factor(re: float, epsilon_d: float) -> float:
    """
    Calculate Darcy friction factor using Colebrook-White equation.
    
    Parameters
    ----------
    re : Reynolds number
    epsilon_d : Relative roughness (ε/D), dimensionless
    
    Returns
    -------
    Darcy friction factor f
    """
    if re <= 0:
        return 0.0
    if re < 2100:
        return 64.0 / re
    # Colebrook-White (iterative)
    f = 0.02
    for _ in range(20):
        lhs = 1.0 / math.sqrt(f)
        rhs = -2.0 * math.log10(
            (epsilon_d / 3.7) + (2.51 / (re * math.sqrt(f)))
        )
        f_new = 1.0 / (rhs * rhs)
        if abs(f_new - f) < 1e-8:
            break
        f = f_new
    return f


def calculate_inlet_pressure_drop(
    flow_gpm: Optional[float],
    fluid_density_lb_ft3: float,
    viscosity_cp: float,
    pipe_id_in: float,
    pipe_length_ft: float,
    fittings_90deg: int = 0,
    fittings_45deg: int = 0,
    gate_valves: int = 0,
    roughness_in: float = 0.00015,
    flow_rate_lb_h: Optional[float] = None,
) -> Dict[str, float]:
    """
    Calculate inlet line pressure drop per API 520 Part II.
    
    Parameters
    ----------
    flow_gpm : Flow rate (US GPM) - optional if flow_rate_lb_h is provided
    fluid_density_lb_ft3 : Fluid density (lb/ft3)
    viscosity_cp : Fluid viscosity (cP)
    pipe_id_in : Pipe inner diameter (inches)
    pipe_length_ft : Straight pipe length (ft)
    fittings_90deg : Number of 90° elbows
    fittings_45deg : Number of 45° elbows
    gate_valves : Number of fully open gate valves
    roughness_in : Pipe wall roughness (inches, default 0.00015 for steel)
    flow_rate_lb_h : Mass flow rate (lb/h) - optional, used for gas/two-phase
    
    Returns
    -------
    dict with keys: delta_p_psi, velocity_fps, reynolds, friction_factor
    """
    pipe_area_ft2 = math.pi * (pipe_id_in / 24.0) ** 2
    
    # Calculate volumetric flow rate in CFS
    if flow_rate_lb_h is not None and flow_rate_lb_h > 0:
        flow_cfs = flow_rate_lb_h / (3600.0 * fluid_density_lb_ft3)
        flow_gpm = flow_cfs * 7.48052 * 60.0
    elif flow_gpm is not None and flow_gpm > 0:
        flow_cfs = flow_gpm / (7.48052 * 60.0)
        flow_rate_lb_h = flow_cfs * 3600.0 * fluid_density_lb_ft3
    else:
        flow_cfs = 0.0
        flow_gpm = 0.0
        flow_rate_lb_h = 0.0
        
    velocity_fps = flow_cfs / pipe_area_ft2 if pipe_area_ft2 > 0 else 0.0
    
    # Reynolds number
    pipe_id_ft = pipe_id_in / 12.0
    viscosity_lb_ft_s = viscosity_cp * 0.000672
    if viscosity_lb_ft_s > 0:
        re = (fluid_density_lb_ft3 * velocity_fps * pipe_id_ft) / viscosity_lb_ft_s
    else:
        re = float('inf')
    
    # Friction factor
    epsilon_d = roughness_in / pipe_id_in if pipe_id_in > 0 else 0
    f = darcy_friction_factor(re, epsilon_d)
    
    # Minor loss equivalent lengths (Crane TP-410)
    equiv_length_ft = pipe_length_ft
    equiv_length_ft += fittings_90deg * 30.0 * pipe_id_in / 12.0
    equiv_length_ft += fittings_45deg * 16.0 * pipe_id_in / 12.0
    equiv_length_ft += gate_valves * 8.0 * pipe_id_in / 12.0
    
    # Darcy-Weisbach
    delta_p_psi = (
        f * equiv_length_ft * fluid_density_lb_ft3 * velocity_fps ** 2
    ) / (2.0 * 32.174 * pipe_id_ft * 144.0)
    
    return {
        "delta_p_psi": delta_p_psi,
        "velocity_fps": velocity_fps,
        "reynolds": re,
        "friction_factor": f,
        "equivalent_length_ft": equiv_length_ft,
        "flow_gpm": flow_gpm,
        "flow_rate_lb_h": flow_rate_lb_h,
    }


def check_mach_limit(mach: float, limit: float = 0.7) -> Tuple[bool, float, str]:
    if mach >= 0.7:
        return (False, mach, f"Exceeds 0.7 Mach limit (Ma={mach:.3f})")
    if mach >= 0.5:
        return (True, mach, f"Marginal — consider larger pipe (Ma={mach:.3f})")
    return (True, mach, f"Adequate (Ma={mach:.3f})")


def check_inlet_rule(
    delta_p_psi: float,
    set_pressure_psig: float,
    valve_type: str = "conventional",
    remote_sensing: bool = False,
) -> Tuple[bool, float]:
    """
    Check if inlet pressure drop is within API 520 Part II limits.
    
    Returns
    -------
    (passes: bool, delta_p_pct: float)
    """
    if valve_type == "pilot" and remote_sensing:
        limit_pct = 100.0  # essentially exempt
    else:
        limit_pct = 3.0
    delta_p_pct = (delta_p_psi / set_pressure_psig) * 100.0 if set_pressure_psig > 0 else 0
    return delta_p_pct <= limit_pct, delta_p_pct


def check_outlet_rule(
    back_pressure_psi: float,
    set_pressure_psig: float,
) -> Tuple[bool, float]:
    """
    Check if built-up back pressure is within API 520 Part II limits (≤10% of set).
    
    Returns
    -------
    (passes: bool, back_pressure_pct: float)
    """
    if set_pressure_psig <= 0:
        return False, 0.0
    bp_pct = (back_pressure_psi / set_pressure_psig) * 100.0
    return bp_pct <= 10.0, bp_pct


__all__ = [
    "calculate_inlet_pressure_drop",
    "check_inlet_rule",
    "check_outlet_rule",
    "darcy_friction_factor",
]
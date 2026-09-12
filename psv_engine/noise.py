"""
Venting noise estimation for pressure relief valves.

Methodology per API 521 §5.8.10 (Pressure-relieving and Depressuring Systems)
and Lighthill's acoustic power theory for sonic atmospheric jets:

    P_ac = eta_a * (0.5 * W * a^2)
    I = P_ac / (4 * pi * r^2)
    L_p(r) = 10 * log10( I / I_ref )

where
    W      mass flow rate [kg/s]
    a      speed of sound at relieving conditions [m/s]
    eta_a  acoustic efficiency factor (typically ~10^-4 for turbulent jets)
    r      distance from the vent [m]
    I_ref  reference sound intensity 10^-12 W/m^2
"""
import math

from .constants import ACOUSTIC_EFFICIENCY_BASE

GC = 32.174
# Universal gas constant in ft.lbf/(lbmol.degR)
R_UNIVERSAL = 1545.0
FT_TO_M = 0.3048
LB_TO_KG = 0.45359237
I_REF = 1e-12
REF_SPEED_SOUND_M_S = 340.0


def calculate_sonic_velocity_fps(k, mw, t_rankine):
    """Speed of sound [ft/s] for an ideal gas at relieving conditions."""
    r_gas = R_UNIVERSAL / mw  # ft.lbf/(lbm.degR)
    return math.sqrt(k * r_gas * t_rankine * GC)


def calculate_noise_level(w_lb_h, k, mw, t_rankine, distance_ft, num_valves=1, acoustic_efficiency=None):
    """
    Estimate the sound pressure level [dB] at `distance_ft` from an
    atmospheric relief valve vent per API 521.

    Parameters
    ----------
    w_lb_h : Total mass flow rate (lb/h)
    k : Specific heat ratio (Cp/Cv)
    mw : Molecular weight (lb/lbmol)
    t_rankine : Relieving temperature (degR)
    distance_ft : Distance from the vent (ft)
    num_valves : Number of parallel valves sharing the flow
    acoustic_efficiency : Optional acoustic conversion efficiency factor eta_a.
                          If None, calculated via API 521 / Lighthill correlation.
    """
    if w_lb_h <= 0:
        raise ValueError("Mass flow rate must be positive.")
    if distance_ft <= 0:
        raise ValueError("Distance must be positive.")
    if k <= 0 or mw <= 0 or t_rankine <= 0:
        raise ValueError("k, MW and temperature must be positive.")

    a_ft_s = calculate_sonic_velocity_fps(k, mw, t_rankine)
    a_m_s = a_ft_s * FT_TO_M

    w_lb_s = (w_lb_h / 3600.0) / max(num_valves, 1)
    w_kg_s = w_lb_s * LB_TO_KG

    # Kinetic power of the jet in Watts
    p_mech_watts = 0.5 * w_kg_s * (a_m_s ** 2)

    # API 521 §5.8.10 / Lighthill acoustic efficiency (eta_a ~ 10^-4 * (a / a_ref)^5)
    if acoustic_efficiency is not None:
        eta_a = acoustic_efficiency
    else:
        mach_ratio = a_m_s / REF_SPEED_SOUND_M_S
        eta_a = ACOUSTIC_EFFICIENCY_BASE * (mach_ratio ** 5)
        eta_a = max(min(eta_a, 0.01), 1e-6)

    p_acoustic_watts = eta_a * p_mech_watts

    r_m = distance_ft * FT_TO_M
    intensity = p_acoustic_watts / (4.0 * math.pi * r_m ** 2)
    if intensity <= 0:
        raise ValueError("Computed sound intensity is not positive.")

    spl_db = 10.0 * math.log10(intensity / I_REF)
    return {
        'Sound_Pressure_Level_dB': spl_db,
        'Sonic_Velocity_fps': a_ft_s,
        'Distance_ft': distance_ft,
        'Flow_per_Valve_lb_h': (w_lb_h / max(num_valves, 1)),
        'Acoustic_Power_Watts': p_acoustic_watts,
        'Acoustic_Efficiency': eta_a,
    }
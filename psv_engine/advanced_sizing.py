import math
from typing import Dict, Any, Union, Optional
from .valve_selection import select_orifice

# -----------------------------------------------------------------------------
# Bilinear Interpolation for Superheat Correction Factor Ksh (psvpy)
# -----------------------------------------------------------------------------

# Temperature grid in °C
KSH_T_C = [
    93.33333333,
    148.8888889,
    204.4444444,
    260.0,
    315.5555556,
    371.1111111,
    426.6666667,
    482.2222222,
    537.7777778,
    565.5555556
]

# Pressure grid in kPa absolute
KSH_P_KPA = [
    137.8951817,
    344.7379543,
    689.4759087,
    1034.213863,
    1378.951817,
    1723.689772,
    2068.427726,
    2413.16568,
    2757.903635,
    3102.641589,
    3447.379543,
    3792.117498,
    4136.855452,
    4826.331361,
    5515.807269,
    6205.283178,
    6894.759087,
    7584.234995,
    8273.710904,
    8963.186813,
    9652.662721,
    10342.13863,
    12065.8284,
    13789.51817,
    17236.89772,
    20684.27726
]

# 2D Table: rows are pressure (KSH_P_KPA), columns are temperature (KSH_T_C)
KSH_TABLE = [
    [1.0, 0.99455814, 0.987, 0.93, 0.882, 0.841, 0.805, 0.774, 0.745, 0.732],
    [1.0, 0.997925224, 0.987, 0.93, 0.882, 0.841, 0.805, 0.774, 0.745, 0.732],
    [1.0, 1.0, 0.998, 0.935, 0.885, 0.843, 0.807, 0.775, 0.746, 0.733],
    [1.0, 1.0, 0.984, 0.94, 0.888, 0.846, 0.808, 0.776, 0.747, 0.733],
    [1.0, 1.0, 0.979, 0.945, 0.892, 0.848, 0.81, 0.777, 0.748, 0.734],
    [1.0, 1.0, 1.0, 0.951, 0.895, 0.85, 0.812, 0.778, 0.749, 0.735],
    [1.0, 1.0, 1.0, 0.957, 0.898, 0.852, 0.813, 0.78, 0.75, 0.736],
    [1.0, 1.0, 1.0, 0.963, 0.902, 0.854, 0.815, 0.781, 0.75, 0.736],
    [1.0, 1.0, 1.0, 0.963, 0.906, 0.857, 0.816, 0.782, 0.751, 0.737],
    [1.0, 1.0, 1.0, 0.961, 0.909, 0.859, 0.818, 0.783, 0.752, 0.738],
    [1.0, 1.0, 1.0, 0.961, 0.914, 0.862, 0.82, 0.784, 0.753, 0.739],
    [1.0, 1.0, 1.0, 0.962, 0.918, 0.864, 0.822, 0.785, 0.754, 0.74],
    [1.0, 1.0, 1.0, 0.964, 0.922, 0.867, 0.823, 0.787, 0.755, 0.74],
    [1.0, 1.0, 1.0, 1.0, 0.931, 0.872, 0.827, 0.789, 0.757, 0.742],
    [1.0, 1.0, 1.0, 1.0, 0.942, 0.878, 0.83, 0.792, 0.759, 0.744],
    [1.0, 1.0, 1.0, 1.0, 0.953, 0.883, 0.834, 0.794, 0.76, 0.745],
    [1.0, 1.0, 1.0, 1.0, 0.959, 0.89, 0.838, 0.797, 0.762, 0.747],
    [1.0, 1.0, 1.0, 1.0, 0.962, 0.896, 0.842, 0.8, 0.764, 0.749],
    [1.0, 1.0, 1.0, 1.0, 0.966, 0.903, 0.846, 0.802, 0.766, 0.75],
    [1.0, 1.0, 1.0, 1.0, 0.973, 0.91, 0.85, 0.805, 0.768, 0.752],
    [1.0, 1.0, 1.0, 1.0, 0.982, 0.918, 0.854, 0.808, 0.77, 0.754],
    [1.0, 1.0, 1.0, 1.0, 0.993, 0.926, 0.859, 0.811, 0.772, 0.755],
    [1.0, 1.0, 1.0, 1.0, 1.0, 0.94, 0.862, 0.81, 0.77, 0.752],
    [1.0, 1.0, 1.0, 1.0, 1.0, 0.952, 0.861, 0.805, 0.762, 0.744],
    [1.0, 1.0, 1.0, 1.0, 1.0, 0.951, 0.852, 0.787, 0.74, 0.721],
    [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.831, 0.753, 0.704, 0.684]
]


def find_interval(grid: list, val: float) -> tuple:
    """Find the bounding index interval and fraction for a 1D grid."""
    if val <= grid[0]:
        return 0, 1, 0.0
    if val >= grid[-1]:
        n = len(grid)
        return n - 2, n - 1, 1.0
    for i in range(len(grid) - 1):
        if grid[i] <= val <= grid[i + 1]:
            frac = (val - grid[i]) / (grid[i + 1] - grid[i])
            return i, i + 1, frac
    return 0, 1, 0.0


def bilinear_interpolate(x_grid: list, y_grid: list, z_table: list, x: float, y: float) -> float:
    """Perform bilinear interpolation on a 2D grid."""
    x_idx0, x_idx1, x_frac = find_interval(x_grid, x)
    y_idx0, y_idx1, y_frac = find_interval(y_grid, y)

    z00 = z_table[y_idx0][x_idx0]
    z01 = z_table[y_idx0][x_idx1]
    z10 = z_table[y_idx1][x_idx0]
    z11 = z_table[y_idx1][x_idx1]

    # Interpolate temperature (x) first
    z_y0 = z00 + x_frac * (z01 - z00)
    z_y1 = z10 + x_frac * (z11 - z10)

    # Interpolate pressure (y)
    return z_y0 + y_frac * (z_y1 - z_y0)


def get_water_sat_temp_f(p1_psia: float) -> float:
    """Return saturation temperature of water in °F for a given pressure in psia."""
    try:
        import CoolProp.CoolProp as CP
        p_pa = p1_psia * 6894.757
        t_k = CP.PropsSI('T', 'P', p_pa, 'Q', 0, 'Water')
        return (t_k - 273.15) * 1.8 + 32.0
    except Exception:
        # Fallback to water saturation temperature correlation from psvpy
        p_kpa = p1_psia * 6.894757
        if p_kpa <= 0:
            p_kpa = 101.325
        lnP = math.log(p_kpa)
        tA = 0.00379302
        tB = -0.000220828
        tC = -0.000425693
        invT = tA + tB * lnP + tC / lnP
        t_c = (1.0 / invT) - 273.15
        return t_c * 1.8 + 32.0


def get_ksh(p1_psia: float, t_f: Optional[float]) -> float:
    """Calculate steam superheat correction factor Ksh based on temperature and pressure."""
    if t_f is None:
        return 1.0
    
    t_sat_f = get_water_sat_temp_f(p1_psia)
    if t_f <= t_sat_f + 0.01:
        return 1.0  # Saturated or subcooled steam
    
    # Convert to metric for table lookup
    t_c = (t_f - 32.0) / 1.8
    p_kpa = p1_psia * 6.894757
    
    ksh = bilinear_interpolate(KSH_T_C, KSH_P_KPA, KSH_TABLE, t_c, p_kpa)
    return max(min(ksh, 1.0), 0.1)


# -----------------------------------------------------------------------------
# Napier Steam Sizing Module (psvpy)
# -----------------------------------------------------------------------------

def calculate_napier_steam_area(
    w_lb_h: float,
    p1_psia: float,
    p2_psia: float,
    t_rankine: Optional[float] = None,
    kd: float = 0.975,
    kb: float = 1.0,
    kc: float = 1.0,
    num_valves: int = 1,
) -> Dict[str, Any]:
    """
    Calculate required relief area for steam using the Napier formula (API 520 Section 5.6).
    
    Parameters:
    w_lb_h: Required mass flow rate (lb/h)
    p1_psia: Relieving pressure (psia, set pressure + overpressure + atmospheric)
    p2_psia: Total backpressure (psia)
    t_rankine: Upstream temperature (Rankine)
    kd: Effective discharge coefficient (typically 0.975 for steam)
    kb: Backpressure correction factor
    kc: Combination correction factor for rupture disk (typically 1.0)
    num_valves: Number of parallel valves
    """
    # High pressure correction factor Kn (API 520: valid for 1500 < P1 <= 3200 psia)
    if p1_psia > 1500.0:
        kn = (0.1906 * p1_psia - 1000.0) / (0.2292 * p1_psia - 1061.0)
    else:
        kn = 1.0
    
    # Superheat correction factor Ksh
    t_f = None
    if t_rankine is not None:
        t_f = t_rankine - 459.67
    ksh = get_ksh(p1_psia, t_f)
    
    # Napier constant: 51.5 in standard API 520, but psvpy uses 51.45.
    # We will use 51.5 to be strictly compliant with API 520.
    cnapier = 51.5
    
    # Required area in sq.in per valve
    # W = 51.5 * A * P1 * Kd * Kb * Kc * Kn * Ksh
    # A_req = W / (51.5 * P1 * Kd * Kb * Kc * Kn * Ksh)
    denominator = cnapier * p1_psia * kd * kb * kc * kn * ksh
    if denominator <= 0:
        raise ValueError("Invalid parameters resulting in zero or negative denominator.")
        
    a_req = w_lb_h / denominator
    a_req_per_valve = a_req / num_valves
    
    letter, selected_area = select_orifice(a_req_per_valve)
    
    # Metric conversion: 1 sq.in = 645.16 mm²
    a_req_mm2 = a_req_per_valve * 645.16
    selected_area_mm2 = selected_area * 645.16
    
    # Critical pressure ratio for saturated steam (k ~= 1.3).
    k_steam = 1.3
    p_critical_ratio = (2.0 / (k_steam + 1.0)) ** (k_steam / (k_steam - 1.0))

    return {
        'Required_Area_sqin': a_req_per_valve,
        'Required_Area_mm2': a_req_mm2,
        'Selected_Orifice_Letter': letter,
        'Selected_Orifice_Area_sqin': selected_area,
        'Selected_Orifice_Area_mm2': selected_area_mm2,
        'Kn': kn,
        'Ksh': ksh,
        'Kb': kb,
        'Kc': kc,
        'Num_Valves': num_valves,
        'Flow_Type': "CRITICAL" if p2_psia <= p_critical_ratio * p1_psia else "SUBCRITICAL",
    }


# -----------------------------------------------------------------------------
# Subcooled Flashing Liquid Two-Phase Relief Module (PolyKin)
# -----------------------------------------------------------------------------

def area_relief_2phase_subcooled(
    q_l_min: float,
    p1_bara: float,
    p2_bara: float,
    ps_bara: float,
    rho1_kg_m3: float,
    rho9_kg_m3: float,
    kd: float = 0.65,
    kb: float = 1.0,
    kc: float = 1.0,
    kv: float = 1.0,
    num_valves: int = 1,
) -> Dict[str, Any]:
    """
    Calculate the required discharge area of a relief device for subcooled liquid flow 
    which flashes inside the nozzle, using the API 520 Section C.2.3 Omega method.
    
    Parameters:
    q_l_min: Relieving volume flow rate (L/min)
    p1_bara: Upstream relieving pressure, absolute (bara)
    p2_bara: Downstream backpressure, absolute (bara)
    ps_bara: Saturation (bubble) pressure at upstream relieving temperature (bara)
    rho1_kg_m3: Liquid density at upstream relieving conditions (kg/m³)
    rho9_kg_m3: Overall density evaluated at 90% of the saturation pressure Ps (kg/m³)
    kd: Discharge coefficient (0.65 for subcooled liquid, 0.85 for saturated liquid)
    kb: Backpressure correction factor
    kc: Combination correction factor
    kv: Viscosity correction factor
    num_valves: Number of parallel valves
    """
    # Convert pressures from bar to Pa
    P1 = p1_bara * 1e5
    P2 = p2_bara * 1e5
    Ps = ps_bara * 1e5

    # Omega parameter for saturated liquid
    ws = 9.0 * (rho1_kg_m3 / rho9_kg_m3 - 1.0)
    ws = max(ws, 0.01)

    # Transition saturation pressure ratio
    eta_st = 2.0 * ws / (1.0 + 2.0 * ws)

    # Ratios
    eta_s = Ps / P1
    eta_a = P2 / P1
    high_subcooling = eta_s < eta_st

    if high_subcooling:
        critical_flow = P2 <= Ps
        P = Ps if critical_flow else P2
        pcf_bara = Ps / 1e5
        # Mass flux [kg/(s.m²)]
        # PolyKin uses: G = 1.414 * sqrt(rho1 * (P1 - P))
        # Note: 1.414 is sqrt(2). We will use math.sqrt(2.0) for precision.
        G = math.sqrt(2.0 * rho1_kg_m3 * (P1 - P))
    else:
        # Low subcooling
        if eta_s > eta_st:
            # Safe guard to avoid division by zero or negative sqrt
            denom = 2.0 * ws - 1.0
            if abs(denom) < 1e-10:
                denom = 1e-10 if denom >= 0 else -1e-10
            
            term_val = 1.0 - (1.0 / eta_s) * (denom / (2.0 * ws))
            term_val = max(term_val, 0.0)
            
            eta_c_ = eta_s * (2.0 * ws / denom) * (1.0 - math.sqrt(term_val))
            eta_c = eta_c_
        else:
            eta_c = eta_s

        pcf_bara = P1 * eta_c / 1e5
        critical_flow = P2 <= (P1 * eta_c)
        eta = eta_c if critical_flow else eta_a
        
        # Guard log from negative values or zero
        log_ratio = eta_s / eta
        if log_ratio <= 0:
            log_ratio = 1e-10
            
        term_flux = 2.0 * (1.0 - eta_s) + 2.0 * (ws * eta_s * math.log(log_ratio) - (ws - 1.0) * (eta_s - eta))
        term_flux = max(term_flux, 0.0)
        
        denom_G = ws * (eta_s / eta - 1.0) + 1.0
        if denom_G <= 0:
            denom_G = 1e-10
            
        G = math.sqrt(term_flux) * math.sqrt(P1 * rho1_kg_m3) / denom_G

    # Required area in mm² (equation from PolyKin)
    # A = 16.67 * Q * rho1 / (Kd * Kb * Kc * Kv * G)
    a_req_mm2 = 16.67 * q_l_min * rho1_kg_m3 / (kd * kb * kc * kv * G)
    a_req_mm2_per_valve = a_req_mm2 / num_valves
    
    # Convert to sq.in to select orifice
    # 1 sq.in = 645.16 mm²
    a_req_sqin_per_valve = a_req_mm2_per_valve / 645.16
    letter, selected_area = select_orifice(a_req_sqin_per_valve)
    
    return {
        'Required_Area_mm2': a_req_mm2_per_valve,
        'Required_Area_sqin': a_req_sqin_per_valve,
        'Selected_Orifice_Letter': letter,
        'Selected_Orifice_Area_sqin': selected_area,
        'Selected_Orifice_Area_mm2': selected_area * 645.16,
        'Critical_Pressure_bara': pcf_bara,
        'Critical_Flow': critical_flow,
        'Omega_s': ws,
        'Transition_Ratio': eta_st,
        'Mass_Flux_G_kg_s_m2': G,
        'Flow_Type': "CRITICAL" if critical_flow else "SUBCRITICAL",
        'High_Subcooling': high_subcooling,
        'Kb': kb,
        'Kc': kc,
        'Kv': kv,
        'Num_Valves': num_valves,
    }

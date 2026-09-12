"""Minimal steam-property adapter used by the control-valve core.

IAPWS is optional. If it is unavailable or the state cannot be solved, the
sizing core falls back to its ideal-gas steam estimate rather than preventing
the application from starting.
"""
try:
    from iapws import IAPWS97
    _HAS_IAPWS = True
except Exception:
    IAPWS97 = None
    _HAS_IAPWS = False


def get_steam_properties_iapws(pressure_bar_a: float, temperature_c: float):
    if not _HAS_IAPWS:
        return None
    try:
        steam = IAPWS97(P=float(pressure_bar_a) / 10.0, T=float(temperature_c) + 273.15)
        return {
            "density_kg_m3": float(steam.rho),
            "viscosity_pa_s": float(steam.mu),
            "cp_kj_kgk": float(steam.cp),
            "cv_kj_kgk": float(steam.cv),
            "specific_heat_ratio": float(steam.cp_cv),
            "z": float(steam.Z),
            "enthalpy_kj_kg": float(steam.h),
            "entropy_kj_kgk": float(steam.s),
            "thermal_conductivity_w_mk": float(steam.k),
            "phase": str(steam.phase),
        }
    except Exception:
        return None

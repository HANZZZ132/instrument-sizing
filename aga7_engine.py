"""AGA Report No. 7 turbine-meter calculation helpers.

Core volumetric conversion follows Appendix B of AGA Report No. 7:
    Qb = Qf * (Pf/Pb) * (Tb/Tf) * (Zb/Zf)
therefore
    Qf = Qb * (Pb/Pf) * (Tf/Tb) * (Zf/Zb)

Pressures are absolute in the equation. This module accepts flowing gauge pressure
in barg and adds atmospheric pressure to obtain Pf.

G-rating recommendation is a screening aid only. AGA 7 requires the manufacturer
to provide the operating flow range at the applicable pressures; G-rating designations
and Qmax values should therefore be checked against the selected meter/vendor data.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

ATM_BAR_DEFAULT = 1.01325

# Common G-rating / nominal maximum flow screening table in m3/h.
# This is deliberately labelled as screening data, not an AGA 7 requirement.
G_RATING_QMAX_M3H = [
    ("G40", 65.0),
    ("G65", 100.0),
    ("G100", 160.0),
    ("G160", 250.0),
    ("G250", 400.0),
    ("G400", 650.0),
    ("G650", 1000.0),
    ("G1000", 1600.0),
    ("G1600", 2500.0),
    ("G2500", 4000.0),
    ("G4000", 6500.0),
    ("G6500", 10000.0),
]


def _temp_abs_c(temp_c: float, legacy_excel: bool = False) -> float:
    offset = 273.0 if legacy_excel else 273.15
    t = float(temp_c) + offset
    if t <= 0:
        raise ValueError("Absolute temperature must be greater than zero.")
    return t


def flowing_pressure_bar_abs(flowing_pressure_barg: float, atmospheric_bar_abs: float = ATM_BAR_DEFAULT) -> float:
    p = float(flowing_pressure_barg) + float(atmospheric_bar_abs)
    if p <= 0:
        raise ValueError("Flowing absolute pressure must be greater than zero.")
    return p


def flowing_rate_from_base(
    q_base_sm3_h: float,
    flowing_pressure_barg: float,
    base_pressure_bar_abs: float = ATM_BAR_DEFAULT,
    flowing_temp_c: float = 32.0,
    base_temp_c: float = 15.555556,
    zf_over_zb: float = 1.0,
    atmospheric_bar_abs: float = ATM_BAR_DEFAULT,
    legacy_excel_temperature_offset: bool = False,
) -> Dict[str, float]:
    """Convert base volumetric flow Qb to flowing/line volumetric flow Qf."""
    qb = float(q_base_sm3_h)
    if qb < 0:
        raise ValueError("Base flow must be non-negative.")
    pb = float(base_pressure_bar_abs)
    if pb <= 0:
        raise ValueError("Base pressure must be greater than zero absolute.")
    zr = float(zf_over_zb)
    if zr <= 0:
        raise ValueError("Zf/Zb must be greater than zero.")

    pf = flowing_pressure_bar_abs(flowing_pressure_barg, atmospheric_bar_abs)
    tf = _temp_abs_c(flowing_temp_c, legacy_excel_temperature_offset)
    tb = _temp_abs_c(base_temp_c, legacy_excel_temperature_offset)
    pressure_multiplier_inverse = pb / pf
    temperature_multiplier_inverse = tf / tb
    qf = qb * pressure_multiplier_inverse * temperature_multiplier_inverse * zr
    return {
        "Q_base_sm3_h": qb,
        "Q_flowing_m3_h": qf,
        "P_flowing_bar_abs": pf,
        "P_base_bar_abs": pb,
        "T_flowing_K": tf,
        "T_base_K": tb,
        "Zf_over_Zb": zr,
        "Pb_over_Pf": pressure_multiplier_inverse,
        "Tf_over_Tb": temperature_multiplier_inverse,
        "Legacy_Excel_273": bool(legacy_excel_temperature_offset),
    }


def base_rate_from_flowing(
    q_flowing_m3_h: float,
    flowing_pressure_barg: float,
    base_pressure_bar_abs: float = ATM_BAR_DEFAULT,
    flowing_temp_c: float = 32.0,
    base_temp_c: float = 15.555556,
    zf_over_zb: float = 1.0,
    atmospheric_bar_abs: float = ATM_BAR_DEFAULT,
    legacy_excel_temperature_offset: bool = False,
) -> Dict[str, float]:
    """Convert flowing/line volumetric flow Qf to base volumetric flow Qb."""
    qf = float(q_flowing_m3_h)
    if qf < 0:
        raise ValueError("Flowing flow must be non-negative.")
    pb = float(base_pressure_bar_abs)
    if pb <= 0:
        raise ValueError("Base pressure must be greater than zero absolute.")
    zr = float(zf_over_zb)
    if zr <= 0:
        raise ValueError("Zf/Zb must be greater than zero.")

    pf = flowing_pressure_bar_abs(flowing_pressure_barg, atmospheric_bar_abs)
    tf = _temp_abs_c(flowing_temp_c, legacy_excel_temperature_offset)
    tb = _temp_abs_c(base_temp_c, legacy_excel_temperature_offset)
    qb = qf * (pf / pb) * (tb / tf) * (1.0 / zr)
    return {
        "Q_flowing_m3_h": qf,
        "Q_base_sm3_h": qb,
        "P_flowing_bar_abs": pf,
        "P_base_bar_abs": pb,
        "T_flowing_K": tf,
        "T_base_K": tb,
        "Zf_over_Zb": zr,
        "Pf_over_Pb": pf / pb,
        "Tb_over_Tf": tb / tf,
        "Legacy_Excel_273": bool(legacy_excel_temperature_offset),
    }


def calculate_flow_range(
    q_base_min_sm3_h: float,
    q_base_max_sm3_h: float,
    p_min_barg: float,
    p_max_barg: float,
    base_pressure_bar_abs: float = ATM_BAR_DEFAULT,
    flowing_temp_c: float = 32.0,
    base_temp_c: float = 15.555556,
    zf_over_zb: float = 1.0,
    atmospheric_bar_abs: float = ATM_BAR_DEFAULT,
    pairing: str = "paired",
    legacy_excel_temperature_offset: bool = False,
) -> Dict[str, object]:
    """Calculate turbine-meter line flow range.

    pairing='paired': Qb_min at Pmin and Qb_max at Pmax, mirroring the clean
    version of the supplied project workbook.

    pairing='conservative': minimum line flow uses Qb_min at Pmax and maximum
    line flow uses Qb_max at Pmin, giving the broadest line-flow envelope.
    """
    qmin = float(q_base_min_sm3_h)
    qmax = float(q_base_max_sm3_h)
    pmin = float(p_min_barg)
    pmax = float(p_max_barg)
    if qmin < 0 or qmax < 0 or qmax < qmin:
        raise ValueError("Require 0 <= Qbase min <= Qbase max.")
    if pmax < pmin:
        raise ValueError("Pmax must be greater than or equal to Pmin.")

    if pairing == "conservative":
        low = flowing_rate_from_base(qmin, pmax, base_pressure_bar_abs, flowing_temp_c, base_temp_c,
                                     zf_over_zb, atmospheric_bar_abs, legacy_excel_temperature_offset)
        high = flowing_rate_from_base(qmax, pmin, base_pressure_bar_abs, flowing_temp_c, base_temp_c,
                                      zf_over_zb, atmospheric_bar_abs, legacy_excel_temperature_offset)
        basis = "Conservative envelope: Qbase min @ Pmax, Qbase max @ Pmin"
    else:
        low = flowing_rate_from_base(qmin, pmin, base_pressure_bar_abs, flowing_temp_c, base_temp_c,
                                     zf_over_zb, atmospheric_bar_abs, legacy_excel_temperature_offset)
        high = flowing_rate_from_base(qmax, pmax, base_pressure_bar_abs, flowing_temp_c, base_temp_c,
                                      zf_over_zb, atmospheric_bar_abs, legacy_excel_temperature_offset)
        basis = "Paired project conditions: Qbase min @ Pmin, Qbase max @ Pmax"

    vals = sorted([low["Q_flowing_m3_h"], high["Q_flowing_m3_h"]])
    actual_min, actual_max = vals[0], vals[1]
    return {
        "Pairing_Basis": basis,
        "Low_Case": low,
        "High_Case": high,
        "Actual_Min_m3_h": actual_min,
        "Actual_Max_m3_h": actual_max,
        "Actual_Rangeability": (actual_max / actual_min) if actual_min > 0 else math.inf,
    }


def g_rating_table(continuous_fraction: float = 0.80) -> List[Dict[str, float]]:
    f = float(continuous_fraction)
    if not (0 < f <= 1):
        raise ValueError("Continuous utilization fraction must be > 0 and <= 1.")
    return [
        {"G_Rating": g, "Typical_Qmax_m3_h": q, "Continuous_Target_m3_h": q * f}
        for g, q in G_RATING_QMAX_M3H
    ]


def recommend_g_rating(required_line_flow_m3_h: float, continuous_fraction: float = 0.80) -> Dict[str, object]:
    """Return screening G-rating based on typical nominal Qmax values.

    This is not an AGA 7-mandated selection table. Final meter selection must use the
    manufacturer operating range at the actual service pressure/density.
    """
    q = float(required_line_flow_m3_h)
    if q < 0:
        raise ValueError("Required line flow must be non-negative.")
    f = float(continuous_fraction)
    if not (0 < f <= 1):
        raise ValueError("Continuous utilization fraction must be > 0 and <= 1.")

    absolute = next(((g, qm) for g, qm in G_RATING_QMAX_M3H if q <= qm), None)
    continuous = next(((g, qm) for g, qm in G_RATING_QMAX_M3H if q <= qm * f), None)
    return {
        "Required_Line_Flow_m3_h": q,
        "Continuous_Target_Fraction": f,
        "Minimum_By_Qmax": absolute[0] if absolute else "Above G6500 table",
        "Minimum_By_Qmax_Qmax_m3_h": absolute[1] if absolute else None,
        "Recommended_Continuous": continuous[0] if continuous else "Above G6500 table",
        "Recommended_Qmax_m3_h": continuous[1] if continuous else None,
        "Recommended_Utilization_pct": (100.0 * q / continuous[1]) if continuous else None,
        "Final_Verification": "Verify vendor/manufacturer operating flow range at actual pressure, density, calibration basis and service conditions.",
    }


def workbook_flange_screening(pmax_barg: float) -> str:
    """Replicate the supplied workbook's flange-class screening only.

    Not an AGA 7 or final ASME B16.5 pressure-temperature rating calculation.
    """
    p = float(pmax_barg)
    if p <= 19.3:
        return "Class 150 (workbook screening)"
    if p <= 50.6:
        return "Class 300 (workbook screening)"
    if p <= 100.12:
        return "Class 600 (workbook screening)"
    return "Outside workbook screening — verify flange/material rating"


def self_test() -> Dict[str, bool]:
    # Supplied workbook legacy-273 regression values.
    a = flowing_rate_from_base(515, 1, 1.01325, 32, 15.555556, 1.0, 1.013253, True)
    b = flowing_rate_from_base(1283, 4, 1.01325, 32, 15.555556, 1.0, 1.013253, True)
    excel_match = abs(a["Q_flowing_m3_h"] - 273.96550549538443) < 1e-9 and abs(b["Q_flowing_m3_h"] - 274.09053899459616) < 1e-9

    # AGA-7 round trip with 273.15 K offset.
    c = flowing_rate_from_base(1000, 5, 1.01325, 30, 15, 0.985)
    d = base_rate_from_flowing(c["Q_flowing_m3_h"], 5, 1.01325, 30, 15, 0.985)
    round_trip = abs(d["Q_base_sm3_h"] - 1000) < 1e-9
    g = recommend_g_rating(380, 0.80)
    screening = g["Recommended_Continuous"] == "G400"
    return {"excel_legacy_match": excel_match, "aga7_round_trip": round_trip, "g_screening": screening}

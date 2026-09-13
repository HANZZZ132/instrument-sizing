"""Electrical calculation helpers derived from the uploaded cable-sizing and grounding workbooks.

The functions are intentionally dependency-light so they can be used by Streamlit and the
Windows edition.  Cable data below is transcribed from the SUMI LV/MV tables contained in
"Lampiran C_Cable Sizing (1).xlsx".  Grounding equations follow the cells in "Lampiran 2.xlsx".
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Cable data from uploaded workbook
# tuple layout: size_mm2, ampacity_1, ampacity_2, ampacity_3, ampacity_4, R90, X
# LV ampacity columns: In Tray (40 C), In Ducts (20 C), Direct Buried, Buried Ducts
# ---------------------------------------------------------------------------
_LV_RAW = {
    1: [
        (2.5,29,28,35,33,None,None),(4,40,37,46,43,None,None),(6,53,48,58,53,None,None),(10,74,66,77,71,None,None),
        (16,101,88,100,91,1.47,0.1264),(25,135,117,129,116,0.927,0.119),(35,169,144,155,139,0.668,0.1123),
        (50,207,175,183,164,0.494,0.1109),(70,268,222,225,203,0.342,0.1052),(95,328,269,270,239,0.247,0.0995),
        (120,383,312,306,271,0.196,0.0996),(150,444,342,343,306,0.159,0.0975),(185,510,384,387,343,0.128,0.0958),
        (240,607,450,448,395,0.0978,0.0926),(300,703,514,502,446,0.0788,0.0903),
    ],
    2: [
        (2.5,36,30,35,33,9.45,0.0959),(4,49,40,46,43,5.88,0.0906),(6,63,51,58,53,3.93,0.085),(10,86,69,77,71,2.33,0.0807),
        (16,115,91,100,91,1.47,0.0781),(25,149,119,129,116,0.927,0.0779),(35,185,146,155,139,0.669,0.0753),
        (50,225,175,183,164,0.494,0.0747),(70,289,221,225,203,0.342,0.0734),(95,352,265,270,239,0.247,0.0711),
        (120,410,305,306,271,0.196,0.0708),(150,473,334,343,306,0.160,0.0712),(185,542,384,387,343,0.128,0.0720),
        (240,641,459,448,395,0.0987,0.0711),(300,741,532,502,446,0.0798,0.0704),
    ],
    3: [
        (2.5,32,26,30,28,9.45,0.0959),(4,42,35,39,36,5.88,0.0906),(6,54,44,49,44,3.93,0.085),(10,75,60,65,58,2.33,0.0807),
        (16,100,80,84,75,1.47,0.0781),(25,127,105,107,96,0.927,0.0779),(35,158,128,129,115,0.669,0.0753),
        (50,192,154,153,135,0.494,0.0747),(70,246,194,188,167,0.342,0.0734),(95,298,233,226,197,0.247,0.0711),
        (120,346,268,257,223,0.196,0.0708),(150,399,300,287,251,0.160,0.0712),(185,456,340,324,281,0.128,0.0720),
        (240,538,398,375,324,0.0987,0.0711),(300,621,455,419,365,0.0798,0.0704),
    ],
    4: [
        (2.5,32,26,30,28,9.45,0.1031),(4,42,35,39,36,5.88,0.0979),(6,54,44,49,44,3.93,0.0923),(10,75,60,65,58,2.33,0.0880),
        (16,100,80,84,75,1.47,0.0853),(25,127,105,107,96,0.927,0.0852),(35,158,128,129,115,0.669,0.0826),
        (50,192,154,153,135,0.494,0.0820),(70,246,194,188,167,0.342,0.0806),(95,298,233,226,197,0.247,0.0783),
        (120,346,268,257,223,0.196,0.0781),(150,399,300,287,251,0.160,0.0785),(185,456,340,324,281,0.128,0.0793),
        (240,538,398,375,324,0.0987,0.0784),(300,621,455,419,365,0.0798,0.0776),
    ],
}

# MV tuple: size, In Air, Direct Buried, Buried Ducts, Buried Direct@20C, R90, X
_MV_20KV = [
    (35,172,153,135,154,0.668,0.128),(50,205,153,135,181,0.494,0.123),(70,253,188,167,220,0.342,0.116),
    (95,307,226,197,263,0.247,0.109),(120,352,257,223,298,0.196,0.106),(150,397,287,251,332,0.159,0.103),
    (185,453,324,281,374,0.128,0.0991),(240,529,375,324,431,0.0978,0.0953),(300,599,419,365,482,0.0788,0.0920),
]
_MV_66KV = [
    (25,143,153,135,129,0.927,0.121),(35,172,153,135,154,0.668,0.114),(50,205,188,167,181,0.494,0.109),
    (70,253,226,197,220,0.342,0.103),(95,307,257,223,263,0.247,0.0977),(120,352,287,251,298,0.196,0.0947),
    (150,397,324,281,332,0.159,0.0920),(185,453,375,324,374,0.128,0.0892),(240,529,419,365,431,0.0980,0.0862),
    (300,599,375,324,482,0.0791,0.0836),
]


@dataclass
class CableOption:
    voltage: float
    phase: str
    load_type: str
    cores: int
    size_mm2: float
    parallel_runs: int
    base_ampacity_a: float
    derated_ampacity_a: float
    full_load_current_a: float
    voltage_drop_v: float
    voltage_drop_pct: float
    start_current_a: Optional[float]
    start_voltage_drop_pct: Optional[float]
    resistance_ohm_km: float
    reactance_ohm_km: float
    min_sc_area_mm2: Optional[float]
    cable_i2t_a2s: float
    ampacity_ok: bool
    vd_ok: bool
    start_vd_ok: bool
    sc_area_ok: bool
    overall_ok: bool

    def to_dict(self):
        return asdict(self)


def system_kind(voltage: float, system: str) -> str:
    if system != "Auto":
        return system
    if voltage >= 1000:
        return "3-Phase AC"
    if abs(voltage - 230) < 10:
        return "1-Phase AC"
    if abs(voltage - 220) < 10:
        return "DC"
    return "3-Phase AC"


def full_load_current(load_kw: float, voltage: float, pf: float = 1.0, efficiency: float = 1.0, system: str = "3-Phase AC") -> float:
    if load_kw < 0 or voltage <= 0 or efficiency <= 0 or pf <= 0:
        raise ValueError("Load, voltage, power factor and efficiency must be positive.")
    p_w = load_kw * 1000.0
    if system == "3-Phase AC":
        return p_w / (math.sqrt(3.0) * voltage * pf * efficiency)
    if system == "1-Phase AC":
        return p_w / (voltage * pf * efficiency)
    if system == "DC":
        return p_w / (voltage * efficiency)
    raise ValueError(f"Unsupported system: {system}")


def _vd(current_a: float, voltage: float, pf: float, length_m: float, r: float, x: float, n: int, system: str) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("Parallel runs must be at least 1.")
    sinphi = 0.0 if system == "DC" else math.sqrt(max(0.0, 1.0 - pf * pf))
    z_term = r if system == "DC" else (r * pf + x * sinphi)
    factor = math.sqrt(3.0) if system == "3-Phase AC" else 2.0
    drop_v = factor * (current_a / n) * z_term * length_m / 1000.0
    return drop_v, drop_v / voltage * 100.0


def _database(voltage: float, cores: int, installation: str) -> List[dict]:
    rows: List[dict] = []
    if voltage > 1000:
        raw = _MV_20KV if voltage >= 10000 else _MV_66KV
        idx_map = {"Above Ground / In Air": 1, "Direct Buried": 2, "Buried Ducts": 3, "Buried Direct @20°C": 4}
        idx = idx_map.get(installation, 1)
        for row in raw:
            size, a_air, a_db, a_bd, a_20, r90, x = row
            amps = [a_air, a_db, a_bd, a_20][idx-1]
            rows.append({"size": size, "ampacity": amps, "r": r90, "x": x, "cores": 3})
        return rows

    raw = _LV_RAW.get(int(cores), [])
    idx_map = {"Above Ground / In Tray": 1, "In Ducts": 2, "Direct Buried": 3, "Buried Ducts": 4}
    idx = idx_map.get(installation, 1)
    for row in raw:
        size, a1, a2, a3, a4, r90, x = row
        if r90 is None or x is None:
            continue
        amps = [a1, a2, a3, a4][idx-1]
        rows.append({"size": size, "ampacity": amps, "r": r90, "x": x, "cores": int(cores)})
    return rows


def evaluate_cable(
    *, voltage: float, load_kw: float, pf: float, efficiency: float, length_m: float,
    derating: float, cores: int, size_mm2: float, parallel_runs: int, installation: str,
    system: str = "Auto", load_type: str = "Feeder", max_vd_pct: float = 5.0,
    max_start_vd_pct: float = 20.0, start_multiplier: float = 7.0, start_pf: float = 0.3,
    fault_current_ka: Optional[float] = None, clearing_time_s: Optional[float] = None,
    k_factor: float = 143.0,
) -> CableOption:
    sys = system_kind(voltage, system)
    rows = _database(voltage, cores, installation)
    match = next((r for r in rows if abs(r["size"] - size_mm2) < 1e-9), None)
    if match is None:
        raise ValueError("Selected cable size/core/installation combination is not available in the uploaded cable data table.")
    ifl = full_load_current(load_kw, voltage, pf, efficiency, sys)
    iz = match["ampacity"] * derating * parallel_runs
    vd_v, vd_pct = _vd(ifl, voltage, pf, length_m, match["r"], match["x"], parallel_runs, sys)
    start_i = start_vd_pct = None
    start_ok = True
    if load_type == "Motor" and sys != "DC":
        start_i = ifl * start_multiplier
        _, start_vd_pct = _vd(start_i, voltage, start_pf, length_m, match["r"], match["x"], parallel_runs, sys)
        start_ok = start_vd_pct <= max_start_vd_pct
    min_sc_area = None
    sc_ok = True
    if fault_current_ka is not None and clearing_time_s is not None and fault_current_ka > 0 and clearing_time_s > 0:
        min_sc_area = fault_current_ka * 1000.0 * math.sqrt(clearing_time_s) / k_factor
        sc_ok = size_mm2 >= min_sc_area
    cable_i2t = (size_mm2 * k_factor) ** 2
    amp_ok = iz >= ifl
    vd_ok = vd_pct <= max_vd_pct
    return CableOption(
        voltage=voltage, phase=sys, load_type=load_type, cores=int(cores), size_mm2=size_mm2,
        parallel_runs=int(parallel_runs), base_ampacity_a=match["ampacity"], derated_ampacity_a=iz,
        full_load_current_a=ifl, voltage_drop_v=vd_v, voltage_drop_pct=vd_pct,
        start_current_a=start_i, start_voltage_drop_pct=start_vd_pct,
        resistance_ohm_km=match["r"], reactance_ohm_km=match["x"], min_sc_area_mm2=min_sc_area,
        cable_i2t_a2s=cable_i2t, ampacity_ok=amp_ok, vd_ok=vd_ok, start_vd_ok=start_ok, sc_area_ok=sc_ok,
        overall_ok=(amp_ok and vd_ok and start_ok and sc_ok),
    )


def recommend_cables(
    *, voltage: float, load_kw: float, pf: float, efficiency: float, length_m: float,
    derating: float, cores: int, installation: str, system: str = "Auto", load_type: str = "Feeder",
    max_vd_pct: float = 5.0, max_start_vd_pct: float = 20.0, start_multiplier: float = 7.0,
    start_pf: float = 0.3, fault_current_ka: Optional[float] = None,
    clearing_time_s: Optional[float] = None, k_factor: float = 143.0, max_parallel: int = 6,
) -> List[CableOption]:
    rows = _database(voltage, cores, installation)
    candidates: List[CableOption] = []
    for n in range(1, max_parallel + 1):
        for r in rows:
            opt = evaluate_cable(
                voltage=voltage, load_kw=load_kw, pf=pf, efficiency=efficiency, length_m=length_m,
                derating=derating, cores=cores if voltage <= 1000 else 3, size_mm2=r["size"], parallel_runs=n,
                installation=installation, system=system, load_type=load_type, max_vd_pct=max_vd_pct,
                max_start_vd_pct=max_start_vd_pct, start_multiplier=start_multiplier, start_pf=start_pf,
                fault_current_ka=fault_current_ka, clearing_time_s=clearing_time_s, k_factor=k_factor,
            )
            if opt.overall_ok:
                candidates.append(opt)
    candidates.sort(key=lambda x: (x.parallel_runs, x.size_mm2, x.size_mm2 * x.parallel_runs))
    return candidates


def cable_sizes(voltage: float, cores: int, installation: str) -> List[float]:
    return [r["size"] for r in _database(voltage, cores, installation)]


# ---------------------------------------------------------------------------
# Grounding calculations from uploaded "Lampiran 2.xlsx"
# ---------------------------------------------------------------------------
def ground_conductor_area_ieee80(
    fault_current_ka: float = 27.5, melting_temp_c: float = 1084.0,
    ambient_temp_c: float = 35.0, alpha_r: float = 0.00381,
    resistivity_microohm_cm: float = 1.78, k0_c: float = 242.0,
    fault_duration_s: float = 0.8, tcap_j_cm3_c: float = 3.42,
) -> float:
    if fault_current_ka <= 0 or fault_duration_s <= 0 or alpha_r <= 0 or resistivity_microohm_cm <= 0:
        raise ValueError("Fault current, duration, alpha and conductor resistivity must be positive.")
    log_term = math.log((k0_c + melting_temp_c) / (k0_c + ambient_temp_c))
    denom = math.sqrt(((tcap_j_cm3_c / 10000.0) / (fault_duration_s * alpha_r * resistivity_microohm_cm)) * log_term)
    return fault_current_ka / denom


def nearest_standard_size(required_mm2: float, sizes=None) -> float:
    if sizes is None:
        sizes = [16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 500, 630]
    for s in sizes:
        if s >= required_mm2:
            return float(s)
    return float(sizes[-1])


def allowable_step_touch(
    soil_resistivity_ohm_m: float = 48.0, surface_resistivity_ohm_m: float = 1000.0,
    surface_thickness_m: float = 0.1, clearing_time_s: float = 0.8,
    body_resistance_ohm: float = 1000.0,
) -> Dict[str, float]:
    if surface_thickness_m < 0 or clearing_time_s <= 0 or surface_resistivity_ohm_m <= 0:
        raise ValueError("Invalid surface layer or clearing-time input.")
    cs = 1.0 - (0.09 * (1.0 - soil_resistivity_ohm_m / surface_resistivity_ohm_m) / (2.0 * surface_thickness_m + 0.09))
    ib50 = 0.116 / math.sqrt(clearing_time_s)
    ib70 = 0.157 / math.sqrt(clearing_time_s)
    touch50 = ib50 * (body_resistance_ohm + 1.5 * cs * surface_resistivity_ohm_m)
    touch70 = ib70 * (body_resistance_ohm + 1.5 * cs * surface_resistivity_ohm_m)
    step50 = ib50 * (body_resistance_ohm + 6.0 * cs * surface_resistivity_ohm_m)
    step70 = ib70 * (body_resistance_ohm + 6.0 * cs * surface_resistivity_ohm_m)
    return {"Cs": cs, "Ib50_A": ib50, "Ib70_A": ib70, "Etouch50_V": touch50, "Etouch70_V": touch70,
            "Estep50_V": step50, "Estep70_V": step70}


def grid_resistance_rectangular(
    rho_grid_ohm_m: float, rho_rod_ohm_m: float, grid_length_m: float, grid_width_m: float,
    total_grid_conductor_m: float, burial_depth_m: float, conductor_diameter_m: float,
    rod_length_m: float, rod_diameter_m: float, rod_count: int, k1: float, k2: float,
) -> Dict[str, float]:
    """Rectangular grid + rods calculation matching the worksheet R1/R2/R12/Rg equations."""
    if min(rho_grid_ohm_m, rho_rod_ohm_m, grid_length_m, grid_width_m, total_grid_conductor_m,
           burial_depth_m, conductor_diameter_m, rod_length_m, rod_diameter_m) <= 0 or rod_count <= 0:
        raise ValueError("All grid/rod dimensions, resistivities and rod count must be positive.")
    area = grid_length_m * grid_width_m
    # Source sheet defines 2a = conductor diameter, then a' = sqrt((a/2)*(2h)) = sqrt((2a/2)*h).
    # With conductor_diameter = 2a this reduces to sqrt((diameter/2)*2h).
    a_prime = math.sqrt((conductor_diameter_m / 2.0) * (2.0 * burial_depth_m))
    r1 = (rho_grid_ohm_m / (math.pi * total_grid_conductor_m)) * (
        math.log((2.0 * total_grid_conductor_m) / a_prime) +
        (k1 * total_grid_conductor_m / math.sqrt(area)) - k2
    )
    n = float(rod_count)
    r2 = (rho_rod_ohm_m / (2.0 * n * math.pi * rod_length_m)) * (
        math.log((4.0 * rod_length_m) / (rod_diameter_m / 2.0)) - 1.0 +
        (2.0 * k1 * rod_length_m / math.sqrt(area)) * ((math.sqrt(n) - 1.0) ** 2)
    )
    r12 = (rho_grid_ohm_m / (math.pi * total_grid_conductor_m)) * (
        math.log((2.0 * total_grid_conductor_m) / rod_length_m) +
        k1 * (total_grid_conductor_m / math.sqrt(area)) - k2 + 1.0
    )
    denom = r1 + r2 - 2.0 * r12
    rg = (r1 * r2 - r12 ** 2) / denom if abs(denom) > 1e-12 else float("inf")
    return {"Area_m2": area, "a_prime_m": a_prime, "R1_ohm": r1, "R2_ohm": r2, "R12_ohm": r12, "Rg_ohm": rg,
            "Acceptable_lt_5_ohm": rg < 5.0}


def lightning_lps_earthing(
    rho_grid_ohm_m: float = 24.29,
    rho_rod_ohm_m: float = 24.4,
    triangle_side_m: float = 6.0,
    total_grid_conductor_m: float = 18.0,
    burial_depth_m: float = 0.8,
    conductor_diameter_m: float = 0.018,
    rod_length_m: float = 3.0,
    rod_diameter_m: float = 0.016,
    rod_count: int = 3,
    k1: float = 1.37,
    k2: float = 5.65,
    requirement_ohm: float = 10.0,
) -> Dict[str, float]:
    """Lightning-protection earthing resistance from Lampiran 2, App-1C LPS.

    The worksheet models a Type A.2 arrangement with three vertical rods in an
    equilateral-triangle arrangement.  The equations below reproduce the worksheet
    R1, R2, mutual R12 and total Rg calculation.
    """
    vals = [rho_grid_ohm_m, rho_rod_ohm_m, triangle_side_m, total_grid_conductor_m,
            burial_depth_m, conductor_diameter_m, rod_length_m, rod_diameter_m,
            k1, k2, requirement_ohm]
    if any(v <= 0 for v in vals) or rod_count <= 0:
        raise ValueError("All dimensions, resistivities, coefficients, requirement and rod count must be positive.")

    area = (triangle_side_m ** 2 / 4.0) * math.sqrt(3.0)
    a_prime = math.sqrt((conductor_diameter_m / 2.0) * (2.0 * burial_depth_m))
    r1 = (rho_grid_ohm_m / (math.pi * total_grid_conductor_m)) * (
        math.log((2.0 * total_grid_conductor_m) / a_prime) +
        k1 * (total_grid_conductor_m / math.sqrt(area)) - k2
    )
    n = float(rod_count)
    r2 = (rho_rod_ohm_m / (2.0 * n * math.pi * rod_length_m)) * (
        math.log((4.0 * rod_length_m) / (rod_diameter_m / 2.0)) - 1.0 +
        2.0 * k1 * (rod_length_m / math.sqrt(area)) * ((math.sqrt(n) - 1.0) ** 2)
    )
    # App-1C LPS uses the deeper/rod-layer resistivity in the mutual term.
    r12 = (rho_rod_ohm_m / (math.pi * total_grid_conductor_m)) * (
        math.log((2.0 * total_grid_conductor_m) / rod_length_m) +
        k1 * (total_grid_conductor_m / math.sqrt(area)) - k2 + 1.0
    )
    denom = r1 + r2 - 2.0 * r12
    rg = (r1 * r2 - r12 ** 2) / denom if abs(denom) > 1e-12 else float("inf")
    return {
        "Triangle_Area_m2": area, "a_prime_m": a_prime,
        "R1_ohm": r1, "R2_ohm": r2, "R12_ohm": r12, "Rg_ohm": rg,
        "Requirement_ohm": requirement_ohm,
        "Acceptable": rg < requirement_ohm,
        "Rod_Spacing_m": triangle_side_m, "Rod_Count": rod_count,
    }


# Minimal regression checks copied from the uploaded calculation samples.
def self_test() -> Dict[str, bool]:
    # 400 VAC feeder sample: 360 kW, pf .8, 4C 185, 3 runs, K=.66, L=35m
    r = evaluate_cable(voltage=400, load_kw=360, pf=.8, efficiency=1.0, length_m=35, derating=.66,
                       cores=4, size_mm2=185, parallel_runs=3, installation="Above Ground / In Tray",
                       system="3-Phase AC", max_vd_pct=5)
    cable_ok = abs(r.full_load_current_a - 649.51905) < 0.02 and abs(r.voltage_drop_v - 1.966) < 0.01
    area = ground_conductor_area_ieee80()
    conductor_ok = abs(area - 87.5295033782) < 1e-6
    st = allowable_step_touch()
    step_ok = abs(st["Cs"] - 0.7045517241) < 1e-8 and abs(st["Estep70_V"] - 917.55677) < 0.01
    lps = lightning_lps_earthing()
    lightning_ok = abs(lps["Rg_ohm"] - 2.33215259516) < 1e-8 and lps["Acceptable"]
    return {"cable_sample": cable_ok, "ground_conductor_sample": conductor_ok, "step_touch_sample": step_ok, "lightning_lps_sample": lightning_ok}

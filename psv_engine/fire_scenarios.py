from .gas_relief import calculate_c_coefficient
from .validation import validate_fire_wetted_inputs, validate_fire_unwetted_inputs
from .constants import (
    FIRE_WETTED_HEAT_CONSTANT, FIRE_WETTED_AREA_EXPONENT,
    FIRE_UNWETTED_COEFF, FIRE_UNWETTED_WALL_EXPONENT, FIRE_UNWETTED_GAS_EXPONENT,
)
import math

# API 521 (6th/7th ed.) — heat absorption rate coefficient for vessels with
# inadequate drainage / firefighting. Higher than the 21,000 value used when
# adequate drainage and prompt firefighting are available.
FIRE_WETTED_HEAT_CONSTANT_NO_DRAINAGE = 34500.0

# API 521 Table 4 — Environmental factor F (fire case).
ENV_FACTORS = {
    "Bare vessel (no insulation)": 1.0,
    "Insulated vessel (k <= 4 Btu/h/ft2/F)": 0.3,
    "Insulated vessel (k <= 2 Btu/h/ft2/F)": 0.15,
    "Insulated vessel (k <= 1 Btu/h/ft2/F)": 0.075,
    "Insulated vessel (k <= 0.5 Btu/h/ft2/F)": 0.0375,
    "Water spray (sprinkler)": 0.3,
    "Depressuring and emptying facility": 0.3,
    "Underground storage": 0.0,
}


def get_env_factor(name):
    """Return the API 521 environmental factor F for a given equipment description."""
    return ENV_FACTORS.get(name, 1.0)


def calculate_heat_absorption(a_wetted_sqft, f_factor=1.0, adequate_drainage=True):
    """API 521 — Fire heat absorption rate Q [Btu/h] for a wetted vessel."""
    coefficient = (
        FIRE_WETTED_HEAT_CONSTANT if adequate_drainage
        else FIRE_WETTED_HEAT_CONSTANT_NO_DRAINAGE
    )
    return coefficient * f_factor * (a_wetted_sqft ** FIRE_WETTED_AREA_EXPONENT)


def calculate_fire_wetted_load(a_wetted_sqft, f_factor, heat_of_vap_btu_lb, adequate_drainage=True):
    """API 521 Section 4.4.13 — Fire wetted relief load (eq. 17-18)."""
    validate_fire_wetted_inputs(a_wetted_sqft, f_factor, heat_of_vap_btu_lb)

    q_btu_h = calculate_heat_absorption(a_wetted_sqft, f_factor, adequate_drainage)
    w_lb_h = q_btu_h / heat_of_vap_btu_lb

    return w_lb_h, q_btu_h


def calculate_fire_unwetted_area(a_exposed_sqft, p1_psia, t_gas_rankine, t_wall_rankine, k, kd=0.975):
    validate_fire_unwetted_inputs(a_exposed_sqft, p1_psia, t_gas_rankine, t_wall_rankine, k)

    c = calculate_c_coefficient(k)

    temp_term = ((t_wall_rankine - t_gas_rankine) ** FIRE_UNWETTED_WALL_EXPONENT) / (t_gas_rankine ** FIRE_UNWETTED_GAS_EXPONENT)
    f_prime = (FIRE_UNWETTED_COEFF / (c * kd)) * temp_term

    a_req = (f_prime * a_exposed_sqft) / math.sqrt(p1_psia)

    return a_req, f_prime

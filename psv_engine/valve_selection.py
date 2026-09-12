import math

# API 520 Standard Effective Orifice Areas (sq. inch)
API_ORIFICE_AREAS = {
    'D': 0.110,
    'E': 0.196,
    'F': 0.307,
    'G': 0.503,
    'H': 0.785,
    'J': 1.287,
    'K': 1.838,
    'L': 2.853,
    'M': 3.60,
    'N': 4.34,
    'P': 6.38,
    'Q': 11.05,
    'R': 16.0,
    'T': 26.0
}

def select_orifice(required_area_sq_in):
    """
    Selects the next largest standard API orifice area.
    Raises ValueError if input is NaN, inf, or negative.
    """
    if not isinstance(required_area_sq_in, (int, float)):
        raise ValueError(f"Required area must be a number (got {type(required_area_sq_in).__name__})")
    if math.isnan(required_area_sq_in) or math.isinf(required_area_sq_in):
        raise ValueError(f"Required area is invalid: {required_area_sq_in}")
    if required_area_sq_in < 0:
        raise ValueError(f"Required area must be non-negative (got {required_area_sq_in})")

    selected_letter = None
    selected_area = None
    
    for letter, area in API_ORIFICE_AREAS.items():
        if area >= required_area_sq_in:
            selected_letter = letter
            selected_area = area
            break
            
    if selected_letter is None:
        return 'Multiple Valves Required', required_area_sq_in
        
    return selected_letter, selected_area

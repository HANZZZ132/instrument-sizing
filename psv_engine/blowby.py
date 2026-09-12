from .validation import validate_blowby_inputs

def calculate_blowby_flowrate(assumed_flow_kg_h, nominal_cv, calculated_cv_at_blowby):
    """
    Calculate blow-by flowrate based on linear control valve characteristics.
    The blow-by flowrate is proportional to the ratio of the nominal (100% open) Cv
    to the calculated Cv at blow-by conditions for an assumed flowrate.

    assumed_flow_kg_h: Estimated flowrate at blow-by conditions (kg/h)
    nominal_cv: Selected nominal Cv of the control valve (e.g. at 100% opening)
    calculated_cv_at_blowby: Calculated Cv for the assumed flowrate

    Returns:
    blowby_flowrate in kg/h
    """
    validate_blowby_inputs(assumed_flow_kg_h, nominal_cv, calculated_cv_at_blowby)

    blowby_flowrate = assumed_flow_kg_h * (nominal_cv / calculated_cv_at_blowby)
    return blowby_flowrate

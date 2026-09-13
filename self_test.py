"""Deployment + code-audit regression checks."""
import AGA3, aga8_detail, electrical_engine
from psv_engine.gas_relief import calculate_gas_relief_area
from psv_engine.liquid_relief import calculate_liquid_relief_area
from psv_engine.unit_converter import barg_to_psia, kg_h_to_lb_h, c_to_rankine

# AGA 3 regression case
AGA3.set_units("US")
Tf=83.469; Pf=522.043; dp=3.528; d0=6.8657; ao=0.0000167; D0=11.375; ap=0.0000112
d=AGA3.thermal_expansion(ao,d0,AGA3.T_r,Tf); D=AGA3.thermal_expansion(ap,D0,AGA3.T_r,Tf)
b=AGA3.diameter_ratio(d,D); Ev=AGA3.velocity_factor(b); c=AGA3.discharge_constants(D,b)
Y=AGA3.expansion_factor(b,dp,Pf,1.3198); FI=AGA3.iteration_flow_factor(d,D,dp,Ev,0.013520,1.566,Y)
Cd,_=AGA3.discharge_coefficient(*c,FI); q=AGA3.base_flow(Cd,d,dp,Ev,0.4488,1.566,Y)
assert abs(q*0.000024-13.841712)<0.001

# AGA 8 DETAIL regression case
G=[96.5222,0.2595,0.5956,1.8186,0.4596,0,0,0,0,0,0.0977,0.1007,0.0473,0.0324,0.0664,0,0,0,0,0,0]
r=aga8_detail.calculate_us(G,60,600)
assert abs(r['flowing']['Z']-0.914141)<2e-6

# API 520 Example 3-style subcritical gas/vapor case.
# The standard example uses rounded F2=0.86; direct equation evaluation here
# gives F2≈0.8549, hence area≈6.59 in² while retaining the same Q orifice.
g=calculate_gas_relief_area(53500,97.2,77.2,627,0.90,51,1.11,kd=0.975,kc=1.0,valve_type="conventional")
assert g['Flow_Type']=='SUBCRITICAL'
assert 6.50 < g['Required_Area_sqin'] < 6.66
assert g['Selected_Orifice_Letter']=='Q'

# API 520 Example 5 liquid case using the example's 2000 SSU viscosity.
l=calculate_liquid_relief_area(
    1800, 275, 50, 0.90, 2000,
    kd=0.65, kc=1.0, overpressure_pct=10,
    valve_type="balanced_bellows", set_pressure_psig=250,
    viscosity_unit="SSU",
)
assert abs(l['Required_Area_No_Visc_sqin']-4.752) < 0.01
assert abs(l['Reynolds_Number']-4525) < 5
assert abs(l['Kv']-0.982) < 0.002
assert abs(l['Required_Area_Final_sqin']-4.84) < 0.02
assert l['Selected_Orifice_Letter']=='P'

# Electrical + lightning regressions
e = electrical_engine.self_test()
assert all(e.values()), e

print(f"AGA3: {q*0.000024:.6f} MMSCFD")
print(f"AGA8 Z: {r['flowing']['Z']:.9f}")
print(f"API520 gas example area: {g['Required_Area_sqin']:.4f} in2 -> {g['Selected_Orifice_Letter']}")
print(f"API520 liquid example area: {l['Required_Area_Final_sqin']:.4f} in2 -> {l['Selected_Orifice_Letter']}")
print(f"Electrical: {e}")
print("CORE SELF TEST PASS — AGA3 + AGA8 + API520 PSV + ELECTRICAL/LIGHTNING")

"""Small engine smoke test for deployment."""
import AGA3, aga8_detail
from psv_engine.gas_relief import calculate_gas_relief_area
from psv_engine.unit_converter import barg_to_psia, kg_h_to_lb_h, c_to_rankine

AGA3.set_units("US")
Tf=83.469; Pf=522.043; dp=3.528; d0=6.8657; ao=0.0000167; D0=11.375; ap=0.0000112
d=AGA3.thermal_expansion(ao,d0,AGA3.T_r,Tf); D=AGA3.thermal_expansion(ap,D0,AGA3.T_r,Tf)
b=AGA3.diameter_ratio(d,D); Ev=AGA3.velocity_factor(b); c=AGA3.discharge_constants(D,b)
Y=AGA3.expansion_factor(b,dp,Pf,1.3198); FI=AGA3.iteration_flow_factor(d,D,dp,Ev,0.013520,1.566,Y)
Cd,_=AGA3.discharge_coefficient(*c,FI); q=AGA3.base_flow(Cd,d,dp,Ev,0.4488,1.566,Y)
assert abs(q*0.000024-13.841712)<0.001

G=[96.5222,0.2595,0.5956,1.8186,0.4596,0,0,0,0,0,0.0977,0.1007,0.0473,0.0324,0.0664,0,0,0,0,0,0]
r=aga8_detail.calculate_us(G,60,600)
assert abs(r['flowing']['Z']-0.914141)<2e-6

g=calculate_gas_relief_area(kg_h_to_lb_h(15000),barg_to_psia(27.5),barg_to_psia(1.5),c_to_rankine(45),.92,16.04,1.31)
assert g['Required_Area_sqin']>0
print(f"AGA3: {q*0.000024:.6f} MMSCFD")
print(f"AGA8 Z: {r['flowing']['Z']:.9f}")
print(f"PSV gas orifice: {g['Selected_Orifice_Letter']}")
print("CORE SELF TEST PASS")

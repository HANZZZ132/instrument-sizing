"""AGA8 DETAIL EOS core for Instrument Sizing.

Pure-Python implementation of the pressure/density/compressibility portion of
AGA Report No. 8 DETAIL, using the public NIST reference formulation and
constants. Internal units: T [K], P [kPa], D [mol/L].
"""
from __future__ import annotations
import math

R = 8.31451  # kPa*L/(mol*K) == J/(mol*K)
N = 21
NT = 58
EPS = 1e-15

# Modern/NIST component order
COMPONENTS = [
    "Methane", "Nitrogen", "Carbon dioxide", "Ethane", "Propane",
    "Isobutane", "n-Butane", "Isopentane", "n-Pentane", "Hexane",
    "Heptane", "Octane", "Nonane", "Decane", "Hydrogen", "Oxygen",
    "Carbon monoxide", "Water", "Hydrogen sulfide", "Helium", "Argon",
]
MW = [16.043,28.0135,44.01,30.07,44.097,58.123,58.123,72.15,72.15,
      86.177,100.204,114.231,128.258,142.285,2.0159,31.9988,28.01,
      18.0153,34.082,4.0026,39.948]

# Equation coefficients, n=1..58 (dummy 0 prepended)
an = [0.0,
 0.1538326,1.341953,-2.998583,-0.04831228,0.3757965,-1.589575,-0.05358847,
 0.88659463,-0.71023704,-1.471722,1.32185035,-0.78665925,2.29129e-9,
 0.1576724,-0.4363864,-0.04408159,-0.003433888,0.03205905,0.02487355,
 0.07332279,-0.001600573,0.6424706,-0.4162601,-0.06689957,0.2791795,
 -0.6966051,-0.002860589,-0.008098836,3.150547,0.007224479,-0.7057529,
 0.5349792,-0.07931491,-1.418465,-5.99905e-17,0.1058402,0.03431729,
 -0.007022847,0.02495587,0.04296818,0.7465453,-0.2919613,7.294616,
 -9.936757,-0.005399808,-0.2432567,0.04987016,0.003733797,1.874951,
 0.002168144,-0.6587164,0.000205518,0.009776195,-0.02048708,0.01557322,
 0.006862415,-0.001226752,0.002850908]

bn = [0] + [1]*18 + [2]*9 + [3]*10 + [4]*7 + [5]*5 + [6]*2 + [7]*2 + [8]*3 + [9]*2
assert len(bn)==59
kn = [0]*59
for i,v in {13:3,14:2,15:2,16:2,17:4,18:4,21:2,22:2,23:2,24:4,25:4,26:4,27:4,
            29:1,30:1,31:2,32:2,33:3,34:3,35:4,36:4,37:4,40:2,41:2,42:2,43:4,44:4,
            46:2,47:2,48:4,49:4,51:2,53:2,54:1,55:2,56:2,57:2,58:2}.items(): kn[i]=v
un_vals = [0,0.5,1,3.5,-0.5,4.5,0.5,7.5,9.5,6,12,12.5,-6,2,3,2,2,11,-0.5,0.5,
           0,4,6,21,23,22,-1,-0.5,7,-1,6,4,1,9,-13,21,8,-0.5,0,2,7,9,22,23,1,9,3,8,23,1.5,5,-0.5,4,7,3,0,1,0]
un=[0.0]+un_vals

fn=[0]*59; gn=[0]*59; qn=[0]*59; sn=[0]*59; wn=[0]*59
for i in [13,27,30,35]: fn[i]=1
for i in [5,6,25,29,32,33,34,51,54,56]: gn[i]=1
for i in [7,16,26,28,37,42,47,49,52,58]: qn[i]=1
for i in [8,9]: sn[i]=1
for i in [10,11,12]: wn[i]=1

Ei=[151.3183,99.73778,241.9606,244.1667,298.1183,324.0689,337.6389,365.5999,
    370.6823,402.636293,427.72263,450.325022,470.840891,489.558373,26.95794,
    122.7667,105.5348,514.0156,296.355,2.610111,119.6299]
Ki=[0.4619255,0.4479153,0.4557489,0.5279209,0.583749,0.6406937,0.6341423,
    0.6738577,0.6798307,0.7175118,0.7525189,0.784955,0.8152731,0.8437826,
    0.3514916,0.4186954,0.4533894,0.3825868,0.4618263,0.3589888,0.4216551]
Gi=[0.0,0.027815,0.189065,0.0793,0.141239,0.256692,0.281835,0.332267,0.366911,
    0.289731,0.337542,0.383381,0.427354,0.469659,0.034369,0.021,0.038953,
    0.3325,0.0885,0.0,0.0]
Qi=[0.0]*21; Qi[2]=0.69; Qi[17]=1.06775; Qi[18]=0.633276
Fi=[0.0]*21; Fi[14]=1.0
Si=[0.0]*21; Si[17]=1.5822; Si[18]=0.39
Wi=[0.0]*21; Wi[17]=1.0

def _matrix(): return [[1.0]*N for _ in range(N)]
Eij=_matrix(); Uij=_matrix(); Kij=_matrix(); Gij=_matrix()
def _set(m, pairs):
    for i,j,v in pairs:
        i-=1; j-=1; m[i][j]=m[j][i]=v

_set(Eij,[
(1,2,.97164),(1,3,.960644),(1,5,.994635),(1,6,1.01953),(1,7,.989844),(1,8,1.00235),(1,9,.999268),(1,10,1.107274),(1,11,.88088),(1,12,.880973),(1,13,.881067),(1,14,.881161),(1,15,1.17052),(1,17,.990126),(1,18,.708218),(1,19,.931484),
(2,3,1.02274),(2,4,.97012),(2,5,.945939),(2,6,.946914),(2,7,.973384),(2,8,.95934),(2,9,.94552),(2,15,1.08632),(2,16,1.021),(2,17,1.00571),(2,18,.746954),(2,19,.902271),
(3,4,.925053),(3,5,.960237),(3,6,.906849),(3,7,.897362),(3,8,.726255),(3,9,.859764),(3,10,.855134),(3,11,.831229),(3,12,.80831),(3,13,.786323),(3,14,.765171),(3,15,1.28179),(3,17,1.5),(3,18,.849408),(3,19,.955052),
(4,5,1.02256),(4,7,1.01306),(4,9,1.00532),(4,15,1.16446),(4,18,.693168),(4,19,.946871),(5,7,1.0049),(5,15,1.034787),(6,15,1.3),(7,15,1.3),
(10,19,1.008692),(11,19,1.010126),(12,19,1.011501),(13,19,1.012821),(14,19,1.014089),(15,17,1.1)])
_set(Uij,[
(1,2,.886106),(1,3,.963827),(1,5,.990877),(1,7,.992291),(1,9,1.00367),(1,10,1.302576),(1,11,1.191904),(1,12,1.205769),(1,13,1.219634),(1,14,1.233498),(1,15,1.15639),(1,19,.736833),
(2,3,.835058),(2,4,.816431),(2,5,.915502),(2,7,.993556),(2,15,.408838),(2,19,.993476),
(3,4,.96987),(3,10,1.066638),(3,11,1.077634),(3,12,1.088178),(3,13,1.098291),(3,14,1.108021),(3,17,.9),(3,19,1.04529),
(4,5,1.065173),(4,6,1.25),(4,7,1.25),(4,8,1.25),(4,9,1.25),(4,15,1.61666),(4,19,.971926),
(10,19,1.028973),(11,19,1.033754),(12,19,1.038338),(13,19,1.042735),(14,19,1.046966)])
_set(Kij,[
(1,2,1.00363),(1,3,.995933),(1,5,1.007619),(1,7,.997596),(1,9,1.002529),(1,10,.982962),(1,11,.983565),(1,12,.982707),(1,13,.981849),(1,14,.980991),(1,15,1.02326),(1,19,1.00008),
(2,3,.982361),(2,4,1.00796),(2,15,1.03227),(2,19,.942596),(3,4,1.00851),(3,10,.910183),(3,11,.895362),(3,12,.881152),(3,13,.86752),(3,14,.854406),(3,19,1.00779),(4,5,.986893),(4,15,1.02034),(4,19,.999969),
(10,19,.96813),(11,19,.96287),(12,19,.957828),(13,19,.952441),(14,19,.948338)])
_set(Gij,[(1,3,.807653),(1,15,1.95731),(2,3,.982746),(3,4,.370296),(3,18,1.67309)])

Ki25=[v**2.5 for v in Ki]
Ei25=[v**2.5 for v in Ei]
# precomputed binary virial contribution coefficients
Bsnij2=[[[0.0]*19 for _ in range(N)] for __ in range(N)]
Kij5=[[0.0]*N for _ in range(N)]; Uij5=[[0.0]*N for _ in range(N)]; Gij5=[[0.0]*N for _ in range(N)]
for i in range(N):
    for j in range(i,N):
        for n in range(1,19):
            b=1.0
            if gn[n]: b=Gij[i][j]*(Gi[i]+Gi[j])/2.0
            if qn[n]: b*=Qi[i]*Qi[j]
            if fn[n]: b*=Fi[i]*Fi[j]
            if sn[n]: b*=Si[i]*Si[j]
            if wn[n]: b*=Wi[i]*Wi[j]
            Bsnij2[i][j][n]=an[n]*(Eij[i][j]*math.sqrt(Ei[i]*Ei[j]))**un[n]*(Ki[i]*Ki[j])**1.5*b
        Kij5[i][j]=(Kij[i][j]**5-1.0)*Ki25[i]*Ki25[j]
        Uij5[i][j]=(Uij[i][j]**5-1.0)*Ei25[i]*Ei25[j]
        Gij5[i][j]=(Gij[i][j]-1.0)*(Gi[i]+Gi[j])/2.0

class DetailMixture:
    def __init__(self, x):
        x=[float(v) for v in x]
        if len(x)!=N: raise ValueError("AGA8 composition must contain 21 components")
        if any(v<0 for v in x): raise ValueError("Negative mole fractions are not allowed")
        s=sum(x)
        if s<=0: raise ValueError("Composition total must be greater than zero")
        self.x=[v/s for v in x]
        self.mm=sum(self.x[i]*MW[i] for i in range(N))
        self.Bs=[0.0]*19
        K3=U=G=Q=F=0.0
        for i in range(N):
            xi=self.x[i]
            if xi<=0: continue
            xi2=xi*xi
            K3+=xi*Ki25[i]; U+=xi*Ei25[i]; G+=xi*Gi[i]; Q+=xi*Qi[i]; F+=xi2*Fi[i]
            for n in range(1,19): self.Bs[n]+=xi2*Bsnij2[i][i][n]
        K3=K3*K3; U=U*U
        for i in range(N-1):
            if self.x[i]<=0: continue
            for j in range(i+1,N):
                if self.x[j]<=0: continue
                xij=2*self.x[i]*self.x[j]
                K3+=xij*Kij5[i][j]; U+=xij*Uij5[i][j]; G+=xij*Gij5[i][j]
                for n in range(1,19): self.Bs[n]+=xij*Bsnij2[i][j][n]
        self.K3=K3**0.6; U=U**0.2; Q2=Q*Q
        self.Csn=[0.0]*59
        for n in range(13,59):
            c=an[n]*(U**un[n])
            if gn[n]: c*=G
            if qn[n]: c*=Q2
            if fn[n]: c*=F
            self.Csn[n]=c

    def alphar(self,T,D,need_d2=True):
        Dred=self.K3*D
        Dkn=[1.0]*10
        for n in range(1,10): Dkn[n]=Dred*Dkn[n-1]
        Exp=[1.0]*5
        for n in range(1,5): Exp[n]=math.exp(-Dkn[n])
        ar01=ar02=0.0
        RT=R*T
        for n in range(1,59):
            tun=T**(-un[n])
            sumb=0.0; sum0=0.0
            if n<=18:
                sm=self.Bs[n]*D
                if n>=13: sm-=self.Csn[n]*Dred
                sumb=sm*tun
            if n>=13:
                sum0=self.Csn[n]*Dkn[bn[n]]*tun*Exp[kn[n]]
                bkd=bn[n]-kn[n]*Dkn[kn[n]]
                ckd=kn[n]*kn[n]*Dkn[kn[n]]
                cd1=bkd
                cd2=bkd*(bkd-1.0)-ckd
            else:
                cd1=cd2=0.0
            s1=sum0*cd1+sumb
            s2=sum0*cd2
            ar01+=RT*s1
            ar02+=RT*s2
        return ar01, ar02

    def pressure(self,T,D):
        ar01,ar02=self.alphar(T,D)
        Z=1.0+ar01/(R*T)
        P=D*R*T*Z
        dpdD=R*T+2.0*ar01+ar02
        return P,Z,dpdD

    def density(self,T,P):
        if T<=0 or P<0: raise ValueError("Invalid absolute temperature or pressure")
        if abs(P)<EPS: return 0.0
        D=P/(R*T)
        plog=math.log(P); vlog=-math.log(D)
        for _ in range(20):
            if vlog < -7 or vlog > 100: break
            D=math.exp(-vlog)
            P2,Z,dpdD=self.pressure(T,D)
            if dpdD<EPS or P2<EPS:
                vlog+=0.1
            else:
                dpdlv=-D*dpdD
                vdiff=(math.log(P2)-plog)*P2/dpdlv
                vlog-=vdiff
                if abs(vdiff)<1e-7: return math.exp(-vlog)
        raise ArithmeticError("AGA8 DETAIL density calculation failed to converge")

    def state(self,T,P):
        D=self.density(T,P)
        P2,Z,_=self.pressure(T,D)
        rho=D*self.mm  # kg/m3 because mol/L*g/mol = g/L
        return {"temperature_K":T,"pressure_kPa":P,"pressure_check_kPa":P2,
                "molar_density_mol_L":D,"Z":Z,"molar_mass_g_mol":self.mm,
                "density_kg_m3":rho,"density_lb_ft3":rho*0.0624279605761}

# UI's legacy component order -> modern/NIST order (0-based indices)
# UI: C1,N2,CO2,C2,C3,H2O,H2S,H2,CO,O2,iC4,nC4,iC5,nC5,C6,C7,C8,C9,C10,He,Ar
_UI_TO_NIST=[0,1,2,3,4,17,18,14,16,15,5,6,7,8,9,10,11,12,13,19,20]

def ui_to_nist(composition):
    if len(composition)!=21: raise ValueError("Composition must contain 21 components")
    out=[0.0]*21
    for ui_i,nist_i in enumerate(_UI_TO_NIST): out[nist_i]=float(composition[ui_i])
    s=sum(out)
    if s<=0: raise ValueError("Composition total must be greater than zero")
    return [v/s for v in out]

def calculate_us(composition, temperature_F, pressure_psia, base_temperature_F=60.0, base_pressure_psia=14.73):
    x=ui_to_nist(composition)
    mix=DetailMixture(x)
    TK=(float(temperature_F)-32.0)*5.0/9.0+273.15
    TbK=(float(base_temperature_F)-32.0)*5.0/9.0+273.15
    Pk=float(pressure_psia)*6.894757293168
    Pbk=float(base_pressure_psia)*6.894757293168
    flow=mix.state(TK,Pk); base=mix.state(TbK,Pbk)
    return {"flowing":flow,"base":base,"molar_mass_g_mol":mix.mm,
            "specific_gravity_ideal":mix.mm/28.9625,
            "Fpv":math.sqrt(base["Z"]/flow["Z"]),
            "normalized_nist_mole_fractions":x}

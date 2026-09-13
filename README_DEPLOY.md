# Instrument Sizing — Web Edition


This package is ready to run locally with Streamlit and to deploy to Streamlit Community Cloud.

## Run locally on Windows

Open Command Prompt inside this folder and run:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

The browser should open automatically. If not, open the Local URL printed by Streamlit.

## Deploy online with Streamlit Community Cloud

1. Create a GitHub repository, for example `instrument-sizing`.
2. Upload **all files and folders in this package** to the repository root.
3. Commit and push them to the `main` branch.
4. Sign in to Streamlit Community Cloud with GitHub.
5. Create a new app and choose your repository.
6. Set the main file path to `app.py`.
7. Deploy.

After deployment you will receive a public HTTPS address such as:

`https://your-app-name.streamlit.app`

If the app is private/internal, make the repository/private-app access settings match your intended audience rather than publishing process data openly.

## Recommended repository layout

```text
instrument-sizing/
├── app.py
├── AGA3.py
├── aga8_detail.py
├── electrical_engine.py
├── requirements.txt
├── .python-version
├── .streamlit/
│   └── config.toml
├── control_valve_engine/
└── psv_engine/
```

## Calculation modules

- AGA 3: known orifice bore → base flow, or target base flow → required reference bore.
- AGA 8 DETAIL: 21-component composition → Z, density, MW, SG, Fpv.
- Control Valve: liquid, gas, steam sizing.
- Electrical: LV/MV cable sizing & voltage drop, ground conductor sizing, allowable step/touch voltage, and rectangular grid/rod resistance.
- PSV Engineering: gas/vapor, steam, liquid, two-phase, fire, thermal expansion and piping checks.

## Local core test

Before deployment you can run:

```bat
python self_test.py
```

Control-valve calculations additionally depend on the packages installed from `requirements.txt`.

## Important

This is an engineering calculation aid. Final engineering decisions should be checked against the applicable standard/code edition, project design basis, vendor-certified data, and independent engineering review.


## UI update v1.2.0
Modern responsive engineering dashboard plus a new **Electrical Sizing** workspace derived from the uploaded cable-sizing and grounding Excel workbooks. No author byline is displayed.


## v1.2.6 navigation fix
Fixed StreamlitWidgetAlreadyInstantiatedError when switching workspace from Welcome buttons. Replace `app.py`; keep the `assets/` folder from v1.2.5+.

### v1.2.7 Electrical / Lightning update
Electrical now includes a dedicated **ESE Protection** tab based on the user-supplied **NF C 17-102:2011** standard. It calculates ESE protection radius Rp from protection level, ESEAT ΔT, and installation height, plus coverage, high-rise, and down-conductor screening flags.

## v1.2.8 — Code Audited update

Replace the previous application files with this package, especially:

- `app.py`
- `electrical_engine.py`
- `psv_engine/` (replace the whole folder)
- `self_test.py`
- `NFPA_780_SOURCE_NOTICE.txt`
- `CODE_AUDIT.md`

Keep the existing `assets/` folder from this package so the illustrated Instrument/Electrical welcome pages remain available.

Key engineering corrections in this release:

- API 520 certified-liquid sizing uses gauge pressure, corrected viscosity `Kv`, cP/SSU Reynolds paths, and no Section-5.9 `Kp` in the Section-5.8 equation.
- Gas/vapor sizing distinguishes conventional, balanced-bellows, and pilot logic for subcritical service.
- API 521 fire environment-factor presets corrected.
- Thermal-expansion output labeled as volumetric flow.
- NFPA 780 traditional rolling-sphere calculator added separately from NF C 17-102 ESE.

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
- PSV Engineering: gas/vapor, steam, liquid, two-phase, fire, thermal expansion and piping checks.

## Local core test

Before deployment you can run:

```bat
python self_test.py
```

Control-valve calculations additionally depend on the packages installed from `requirements.txt`.

## Important

This is an engineering calculation aid. Final engineering decisions should be checked against the applicable standard/code edition, project design basis, vendor-certified data, and independent engineering review.

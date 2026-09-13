# Update GitHub / Streamlit — Web v1.2.2

For an existing deployment, replace/upload these files to the repository root:

- `app.py`
- `electrical_engine.py`

No new Python dependency is required. Commit to `main`; Streamlit Community Cloud should redeploy automatically.

New Electrical workspace structure:
- Cable Sizing & Voltage Drop
- Ground Conductor Sizing
- Step & Touch Voltage
- Ground Grid + Earth Rod Resistance
- Lightning Protection Earthing (Lampiran 2 — App-1C LPS)


## v1.2.6 navigation fix
Fixed StreamlitWidgetAlreadyInstantiatedError when switching workspace from Welcome buttons. Replace `app.py`; keep the `assets/` folder from v1.2.5+.

## v1.2.7 — ESE Protection (NF C 17-102)
Replace these files in GitHub:
- `app.py`
- `electrical_engine.py`
- `self_test.py`
- add `NF_C_17_102_SOURCE_NOTICE.txt`

Keep the existing `assets/`, `control_valve_engine/`, and `psv_engine/` folders.

## Update to v1.2.8 Code Audited

For GitHub/Streamlit, upload/replace these paths and commit to `main`:

1. `app.py`
2. `electrical_engine.py`
3. the complete `psv_engine/` folder
4. `self_test.py`
5. `NFPA_780_SOURCE_NOTICE.txt`
6. `CODE_AUDIT.md`

No new Python dependency is required beyond the current `requirements.txt`.

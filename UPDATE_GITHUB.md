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

## v1.4.0 update
Upload/replace these files together:
- `app.py`
- `aga7_engine.py` (new)
- `self_test.py`
- `AGA7_SOURCE_NOTICE.txt` (new)

For the safest update, replace the whole repository content with this package while preserving your repository settings.


## v1.4.1 — New Sizing / stale-result fix
Previous results are cleared before each new calculation submit. Failed validation no longer leaves the prior case visible. Results are also isolated across AGA 3 modes, control-valve services, cable modes, and PSV services. A sidebar **New Sizing / Clear Result** button clears outputs without deleting current input values.


## v1.4.2 — automatic stale-result invalidation
Input widgets now run outside Streamlit forms. Editing an input triggers a rerun and automatically
removes the previous displayed result for the active calculator. The user does not need to press a
Clear Result button. A new result appears only after Calculate is pressed again. Live calculators
(such as AGA 7 / ESE modes where applicable) continue to recalculate from current inputs.

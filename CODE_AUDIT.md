# Instrument Sizing Web v1.2.8 — Code Audit Notes

This version corrects and separates calculations against the editions supplied by the user.

## PSV / pressure relief

### API 520 Part I, 10th Edition (2020)
- Gas/vapor: critical/subcritical determination retained.
- Balanced spring-loaded gas PRVs in subcritical conditions now use the critical-flow equation with `Kb`, consistent with §5.6.4.3. Manufacturer `Kb` remains required for final sizing.
- Conventional/pilot subcritical service uses the direct subcritical equation; `Kb` is not applied in that direct formulation.
- Liquid PRV Section 5.8 now uses **gauge pressure** in Eq. 32/33.
- Liquid viscosity correction now uses Eq. 34: `Kv=(170/Re+1)^-0.5`, valid for `Re >= 80`.
- Reynolds supports Eq. 35 (`cP`) and Eq. 36 (`SSU`).
- Certified-liquid Section 5.8 no longer applies `Kp`; `Kp` belongs to the noncertified Section 5.9 procedure.
- API 526 orifice letter selection remains D through T using the standard effective areas.

### API 521, 7th Edition (2020)
- External-fire heat input retains the 21,000 / 34,500 USC coefficients with wetted-area exponent 0.82.
- Environment-factor presets were corrected to Table 5 values from the supplied standard.
- Thermal-expansion output is now labeled as **volumetric flow** (`gpm` and `m3/h`), not `lb/h`.

## Lightning protection

### NFPA 780 (2000)
- Added a separate **traditional rolling-sphere** tab using a 150 ft (46 m) sphere.
- The ESE module is intentionally not labeled or treated as NFPA 780; the supplied NFPA 780 edition excludes ESE systems.

### NF C 17-102 (2011 supplied file)
- ESE module remains separate with protection level, `Delta T`, height and protection-radius screening.

## Control valve

The supplied ANSI/ISA-75.01.01-2012 attachment available in this chat contains only the title/preface pages, not the sizing-equation body. Therefore the control-valve engine was **not silently rewritten or declared line-by-line verified** in this audit. Existing implementation remains as-is pending a complete standard source or another user-approved basis.

## Verification tests

`self_test.py` includes:
- AGA 3 regression
- AGA 8 DETAIL regression
- API 520 Example 3-style gas/subcritical regression
- API 520 Example 5 liquid/viscosity regression
- Electrical cable/grounding regressions
- NF C 17-102 ESE radius regression
- NFPA 780 rolling-sphere regression

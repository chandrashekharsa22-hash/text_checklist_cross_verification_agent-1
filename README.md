# Column Base Plate Design Agent — MVP v0.1

This Streamlit application reproduces the main input fields, formulas and checks from the uploaded `COLUMN BASE PLATE DESIGN.xlsx` workbook.

## Included
- Design inputs for axial compression, shear, column geometry, base plate, concrete, steel, weld, grout and foundation geometry.
- Effective-area method with no-overlap / overlap branch.
- Plate area check.
- Effective area and plate-fit check.
- Minimum plate thickness check.
- Weld resistance check.
- Grout / beta-joint assumption check.
- Foundation depth and edge-distance assumption check.
- Overall PASS / FAIL status.
- Downloadable TXT checklist report and CSV calculation/check reports.

## Run locally on Windows
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy online
Upload `app.py`, `requirements.txt`, and `README.md` to the root of a GitHub repository. Deploy with Streamlit Community Cloud using branch `main` and main file path `app.py`.

## Design scope and limitations
The supplied workbook states scope as axial compression and shear only. The MVP does not design for moment, uplift, holding-down bolts/anchors, concrete breakout, pedestal reinforcement, foundation stability, fatigue or seismic actions. It is not a code-compliant approval or construction release. Verify all formulas, coefficients, National Annex requirements, material properties, weld assumptions and project inputs against the governing standards and a qualified structural engineer's independent check.

## Source workbook notes
The app's default values are copied from the `Base Plate Design` sheet input cells. The workbook's `Design Notes` sheet describes a worked example with some different values; the app intentionally does not silently substitute those values.

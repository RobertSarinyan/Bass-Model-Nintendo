# Nintendo Switch 2: Bass diffusion analysis

The innovation is [Nintendo Switch 2, featured in TIME's Best Inventions of 2025](https://time.com/collections/best-inventions-2025/7318303/nintendo-switch-2/). The historical analogue is the original Nintendo Switch platform family. Both series use **worldwide hardware sell-in in millions of units**, as a proxy for adoption; they do not count unique people or households.

Read the [final PDF](report/report.pdf) or its [Markdown source](report/report_source.md). The report includes the required two-paragraph historical comparison, sourced data, scope, Bass estimation, forecast, sensitivity analysis, and references. Numbered sections start at 1.

## Main results and interpretation

Nine historical fiscal-period observations through March 2025 give estimated p = 0.06497 per year, q = 0.46426 per year, and M = 167.29 million hardware units. The fit uses exact reporting-interval increments of the continuous Bass curve, including the 29-day launch period. Historical period-sales R-squared is 0.9277 and RMSE is 1.88 million units.

The Switch 2 forecast is a **retrospective pre-launch exercise with a May 9, 2025 numerical information cutoff**, prepared in October 2026. The base case transfers historical q and M as explicit analogue assumptions. It solves for p = 0.09450 per year so that the first 300-day period matches Nintendo's original 15 million-unit forecast. That calibration target is not independent validation. The model projects a broad peak in fiscal 2028–2029, with 27.45 million units in the year ending March 2029, and 163.28 million cumulative units by March 2035.

Later results are evaluated separately: Nintendo reported 19.86 million Switch 2 units for the year ended March 2026. The anchored forecast misses this by -4.86 million units (24.47% absolute percentage error). These later actuals never enter fitting or calibration. Lower/base/upper cases show assumption sensitivity; they are not confidence intervals. The assumed eventual market and fixed diffusion parameters remain substantial limitations.

## Reproduce the complete project

Tested with Python 3.13.5. From the repository root, create an environment if one is not already available and install the Python packages:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

On macOS/Linux, use `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`. With an activated environment, `python run_project.py` is sufficient. Dependencies are pinned in `requirements.txt`; the virtual environment is excluded from Git.

The PDF build also needs **Node.js** for the included KaTeX renderer and **Pango** native libraries for WeasyPrint. The Python packages alone do not install Pango. On Windows, an existing Pango installation can be supplied through `WEASYPRINT_DLL_DIRECTORIES`. Alternatively, run this once from the repository root to use the official portable WeasyPrint 70.0 libraries locally:

```powershell
New-Item -ItemType Directory -Force tmp, .tools/weasyprint | Out-Null
Invoke-WebRequest -Uri https://github.com/Kozea/WeasyPrint/releases/download/v70.0/weasyprint-windows-onedir.zip -OutFile tmp/weasyprint-windows-onedir.zip
Expand-Archive -LiteralPath tmp/weasyprint-windows-onedir.zip -DestinationPath .tools/weasyprint -Force
```

The builder detects that local runtime automatically. `.tools/` is ignored by Git. On macOS/Linux, install Pango using the platform's package manager, as described in [WeasyPrint's setup instructions](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html). Node.js must be on PATH, or its executable can be supplied through `NODE_BINARY`.

Once Node.js and Pango are available, run the full project:

```powershell
.\.venv\Scripts\python.exe run_project.py
```

The single command regenerates calculated CSV/JSON files, all four figures, the Markdown report, and the PDF. It then checks numerical identities, dates, units, source availability, optimization convergence, independent numerical integration of the Bass equation, forecast continuity, and report contents. It runs offline once dependencies are installed because the source documents are included. It does not download data or perform Git operations. Manual visual inspection of the PDF complements the automated checks.

**Edit `write_report.py` to change report prose**, then rerun the pipeline. It generates `report/report_source.md` from the calculated results. The Markdown is the immediate input to `build_report.py`, which can also be run separately to render manual Markdown edits; a subsequent complete pipeline run will overwrite those edits.

## Files and workflow

| File or directory | Purpose |
| --- | --- |
| `analyze_bass.py` | Prepare historical observations, estimate the historical Bass model, and run sensitivity checks. |
| `forecast_switch2.py` | Calibrate and generate Switch 2 forecast cases using pre-launch inputs only. |
| `verify_project.py` | Check scientific consistency and compare the forecast with the separately stored later actual. |
| `write_report.py` | Generate the report Markdown with calculated results and references. |
| `build_report.py` | Convert Markdown with `markdown` and `mdx_math`, typeset equations as KaTeX HTML, and render the PDF with WeasyPrint. |
| `run_project.py` | Run all stages in order. |
| `data/switch_historical_sales.csv` | Original transcribed historical observations, source IDs, and pages. |
| `data/forecast_inputs.json` | Pre-launch calibration inputs, dates, and source references. |
| `data/switch2_validation_actual.csv` | Later actual, reserved for evaluation only. |
| `data/sources.csv`, `data/sources/` | Source register and retained Nintendo documents. |
| `data/README.md` | Data definitions, provenance, timing, rounding, and generated-file dictionary. |
| Other CSV/JSON files in `data/` | Reproducible prepared data, estimates, forecasts, and checks. |
| `img/` | Four reproducible figures used in the report. |
| `report/` | Final PDF and its Markdown source. |
| `report/assets/katex/` | KaTeX 0.19.0 renderer, CSS, fonts, and MIT license, included for offline builds. |
| `.gitignore` | Excludes environments, caches, temporary renders, and local configuration. |
| `.gitattributes` | Keeps text line endings consistent, treats PDFs/images/fonts as binary, and preserves the original HTML source bytes. |

Equations use HTML font text instead of PNGs or SVG outlines. WeasyPrint embeds their fonts and Unicode mappings in a tagged PDF. The intermediate HTML is saved as `tmp/report.html` for inspection and is not submitted. The PDF checks verify visible equation text and font mappings, rather than relying on replacement-text fields. Fractions and subscripts may paste in a different order depending on the PDF viewer, so the Markdown remains the exact LaTeX source.

## Method and sources

The primary historical fit minimizes unweighted squared errors in nine reporting-interval sales observations, using differences in the continuous-time Bass cumulative curve. Calendar days are divided by 365.25. Positive p and q and M above observed cumulative sales are estimated from 27 starting points. A launch-conditioned fit and nine omitted-period fits assess sensitivity. These diagnostics share the historical sample and are not independent validation.

The interval-sales NLS formulation is supported by [Srinivasan and Mason (1986), Section 2, equation (1), p. 170](https://doi.org/10.1287/mksc.5.2.169). The report distinguishes this published method from this project's numerical settings and transfer assumptions. [Bass (1969)](https://doi.org/10.1287/mnsc.15.5.215) supplies the original diffusion framework.

The pre-launch target is from [Nintendo's May 2025 material, p. 9](https://www.nintendo.co.jp/ir/pdf/2025/250508_4e.pdf). The later outcome is from [Nintendo's May 2026 material, p. 5](https://www.nintendo.co.jp/ir/pdf/2026/260508_4e.pdf). Full source details, publication dates, and local copies are in the source register. Hardware purchases include repeat purchases and channel inventory. Pandemic conditions, supply constraints, competition, marketing, and product refreshes are not separately modeled.

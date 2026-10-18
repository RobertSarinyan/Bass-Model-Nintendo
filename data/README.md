# Data and sources

## Scope and provenance

`switch_historical_sales.csv` contains nine global fiscal-period hardware sell-in observations for the original Nintendo Switch platform family, from launch through March 31, 2025. It includes the base Switch, Switch Lite, and Switch OLED where available. Switch 2, software, accessories, revenue, active accounts, and consumer sell-through estimates are excluded.

Values were manually transcribed from the actual worldwide hardware total rows of Nintendo's financial reports. Source tables are expressed in ten thousands of units. Conversions are `sales_units = reported_sales_ten_thousands * 10000` and `sales_millions = reported_sales_ten_thousands / 100`. These are converted published values, not exact unrounded console counts. The forecast columns in the same tables were not collected.

`sources.csv` maps each source ID to its publication date, URL, local document, and one-based PDF page number (blank for HTML). Eight documents are retained in `sources/`: five reports supplying historical observations, the May 2025 Q&A, the Switch 2 launch announcement in HTML, and a May 2026 report used only for evaluation. Retrieval date: October 18, 2026. The numerical information cutoff for the retrospective pre-launch forecast is May 9, 2025. All five historical data sources were already published by May 8. The last historical period ends March 31, 2025. No post-launch Switch 2 outcomes enter the historical dataset or forecast calibration.

For N2017 through N2023, use the table headed "Consolidated sales units, number of new titles, and sales units forecast." For N2025, use "Sales Units and Sales Units Forecast." Select Nintendo Switch hardware, Total, Actual. For 2018, 2020, 2022, and 2024, use the preceding-year comparative Actual column in the following year's selected report. For 2017, the launch date is also documented on page 3 of N2017. N2025 page 11 explicitly identifies the series as sell-in and page 27 supplies the data.

## Data dictionary

| Column | Definition |
| --- | --- |
| fiscal_year_end | Calendar year of the fiscal year ending March 31; not a calendar-year sales total. |
| period_start / period_end | Inclusive bounds of Nintendo's April-to-March reporting year. |
| observation_start | Launch date for the first row; period_start for later rows. |
| is_partial_launch_period | True only for the launch period in March 2017. |
| geography | Global in every observation. |
| product_scope | Original Switch platform family; excludes Switch 2. |
| measure | Hardware sell-in, used as a proxy for adoption. |
| reported_sales_ten_thousands | Published hardware total in its original source unit. |
| sales_units / sales_millions | Unit conversions of the published sales figure. |
| reported_lifetime_units_if_available | Independently reported life-to-date hardware total in the same source table; blank when that endpoint is not in the selected source. Blank means unavailable here, not zero. |
| source_id | Key into sources.csv. |
| source_page | One-based PDF page containing the observation. |

## Timing and interpretation

The first row covers only March 3-31, 2017, when Switch was on sale for 29 days. The model uses those 29 days rather than treating the observation as a full year. In the separate launch check, those sales become the starting total for the following periods.

Ideally, adoption would count each buyer's first console purchase. These data cannot identify first-time buyers. They count hardware sold into distribution, including repeat purchases and stock held in stores. The model's market potential is therefore a number of hardware units, not unique people or households. Active-player counts measure something different and are not part of this series.

## Rounding and checks

The nine annual figures add up to 152.13 million units. Nintendo reports a lifetime total of 152.12 million at March 31, 2025 (N2025, p. 27). A 0.01 million-unit difference also appears at the 2021 and 2023 checkpoints. The annual and lifetime totals are rounded separately, so small differences are possible. Both published figures are kept as they are.

The source history includes unusual demand and supply conditions. N2021 discusses COVID-19 conditions; N2023 page 3 reports production effects from semiconductor/component shortages. These effects should be considered when evaluating a Bass fit. No missing years have been interpolated. The subsequent historical fit and diagnostics are documented in the report and generated files below.

## Forecast inputs and later evaluation

`forecast_inputs.json` stores the May 9, 2025 information cutoff, June 5 launch date (N2025LAUNCH), March 31, 2026 first-period end, Nintendo's original 15 million-unit first-period target (N2025, p. 9; N2025QA, Q1), and the 152.12 million historical lifetime-volume benchmark (N2025, p. 27). It also specifies the analyst-selected ten-period horizon. These inputs distinguish published numbers from modeling choices.

The base case assumes the original family's fitted q and M transfer to Switch 2. It solves p so that the first 300-day interval matches the published target. The lower case uses the 152.12 million observed lifetime benchmark and the smallest historical omitted-period q; the upper uses the largest omitted-period M and q. Each case recalibrates p to the same target. M is an analogue assumption about eventual hardware volume, not an independently measured Switch 2 market size. The cases are assumption checks, not probability or confidence bounds. Their annual increments need not retain lower/base/upper ordering in every period.

`switch2_validation_actual.csv` separately records the 19.86 million-unit actual for fiscal 2026 from N2026, p. 5, published May 8, 2026. Only `verify_project.py` reads that input, after the forecasts have been generated. It is never read by `forecast_switch2.py` or the historical fitting script. A separate evaluation prevents this later outcome from being used to tune the retrospective forecast. The first-period miss remains visible.

The TIME article explains the choice of Switch 2 and supplies no numbers for the forecast. The analysis was done in October 2026 using the earlier information cutoff. It reconstructs a pre-launch forecast rather than claiming the predictions were made before launch.

## Prepared data and estimated results

`switch_prepared.csv` retains the source figures and adds actual observation durations, elapsed years since launch, cumulative sums of annual observations, and discrepancies from reported lifetime totals. End dates are exclusive. Time is measured as calendar days divided by 365.25; the first interval is 29 days, not a full year.

`switch_bass_fit.csv` adds primary-model fitted interval sales, observed-minus-fitted residuals, and model cumulative endpoints. Values in these calculated columns are in millions of hardware units. `bass_estimates.json` stores parameters, diagnostics, algorithm settings, software versions, and sensitivity summaries. `switch_bass_sensitivity.csv` stores nine omitted-period refits. These files are generated by `analyze_bass.py` and preserve the raw source CSV.

All M bounds and estimates are in millions of hardware units. The primary fit uses all nine intervals. Its unweighted objective treats errors in million-unit totals equally rather than annualizing the short first interval. The launch-conditioned check fixes the observed launch total at April 1, 2017 and fits the following eight intervals. Omission diagnostics keep the same full-history market-potential floor and are sensitivity checks, not independent validation or confidence intervals.

## Generated forecast and verification files

| File | Contents |
| --- | --- |
| `switch2_forecast.csv` | Ten fiscal-period forecasts for the base case. |
| `switch2_forecast_scenarios.csv` | Thirty rows: ten periods for each of lower, base, and upper cases. |
| `forecast_results.json` | Parameter sets, transfer rules, numerical cutoff, calibration target, peak years, and terminal cumulative volumes. |
| `switch2_validation.csv` | Forecast, later actual, forecast-minus-actual error in millions, and absolute percentage error using actual as denominator. |
| `verification_results.json` | Check status, sample sizes, independent ODE-versus-formula errors, rounding discrepancy, and separate evaluation. |

Forecast CSV fields are `scenario`, `fiscal_year_end`, inclusive `period_start` and `period_end`, `duration_days`, elapsed `t_start_years` and `t_end_years`, `new_hardware_units_millions`, and `cumulative_hardware_units_millions`. The first period runs June 5, 2025–March 31, 2026; subsequent periods run April 1–March 31. Elapsed-year endpoints follow the same exclusive-end convention as the historical fit. Cumulative values are measured from Switch 2 launch. All calculated figures retain full numerical precision; report tables round independently.

Run `python run_project.py` from the repository root to rebuild the results. The original sales CSV, forecast inputs, later actual, source register, and source documents are kept unchanged. The main README explains setup. The report and figures are kept with the project. Local environments, caches, and temporary files are ignored by Git.

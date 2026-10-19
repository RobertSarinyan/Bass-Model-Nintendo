"""Prepare historical sales, fit the interval Bass model, and export results.

This script estimates the historical Switch model only, not Switch 2 adoption.
"""
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal
from itertools import product
import csv
import json
import platform

import numpy as np
import scipy
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
IMG = ROOT / 'img'
YEAR_DAYS = 365.25
LAUNCH = date(2017, 3, 3)
PLOT_STYLE = {'font.family': 'DejaVu Sans', 'font.size': 10,
              'axes.spines.top': False, 'axes.spines.right': False,
              'axes.titleweight': 'bold', 'savefig.dpi': 180}


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def cumulative(t, p, q, m, initial=0.0):
    """Bass cumulative hardware-unit proxy, in millions, t in years.

    Solves dN/dt = (p + q*N/M)*(M-N); optional known N(0).
    """
    f0 = initial / m
    e0 = (1 - f0) / (1 + (q / p) * f0)
    e = e0 * np.exp(-(p + q) * np.asarray(t))
    return m * (1 - e) / (1 + (q / p) * e)


def fit_intervals(starts, ends, y, m_floor, initial=0.0, mask=None, full_search=True):
    if mask is None:
        mask = np.ones(len(y), dtype=bool)

    def decode(z):
        return np.exp(z[0]), np.exp(z[1]), m_floor + np.exp(z[2])

    def predict(z):
        p, q, m = decode(z)
        return cumulative(ends, p, q, m, initial) - cumulative(starts, p, q, m, initial)

    def residual(z):
        return (predict(z) - y)[mask]

    # Numerical search bounds are intentionally broad; report if an optimum hits them.
    lower = np.log([1e-8, 1e-8, 1e-6])
    upper = np.log([10., 10., 100000.])
    seeds = product([0.003, 0.02, 0.10], [0.15, 0.5, 1.2], [10., 80., 300.])
    if not full_search:
        seeds = [(0.02, 0.5, 50.), (0.1, 0.15, 100.), (0.003, 1.2, 10.)]
    trials = [least_squares(residual, np.log(seed), bounds=(lower, upper),
                            x_scale='jac', max_nfev=4000,
                            ftol=1e-11, xtol=1e-11, gtol=1e-11) for seed in seeds]
    successful = [trial for trial in trials if trial.success]
    if not successful:
        raise RuntimeError('No optimization start converged.')
    best = min(successful, key=lambda result: float(result.fun @ result.fun))
    p, q, m = decode(best.x)
    predictions = predict(best.x)
    r = y[mask] - predictions[mask]
    sse = float(r @ r)
    sst = float(np.sum((y[mask] - y[mask].mean())**2))
    result = {
        'p_per_year': float(p), 'q_per_year': float(q), 'M_million_units': float(m),
        'n_fit_observations': int(mask.sum()), 'SSE_million_units_squared': sse,
        'RMSE_million_units': float(np.sqrt(np.mean(r**2))),
        'MAE_million_units': float(np.mean(np.abs(r))), 'R_squared_period_sales': 1 - sse / sst,
        'starts_attempted': len(trials), 'starts_converged': len(successful),
        'starts_within_1e_6_of_best_SSE': sum(abs(float(t.fun @ t.fun) - sse) < 1e-6 for t in successful),
        'numerical_bound_hit': bool(np.any(best.active_mask != 0)),
        'optimality': float(best.optimality),
    }
    return result, predictions


def main():
    IMG.mkdir(exist_ok=True)
    with (DATA / 'switch_historical_sales.csv').open(encoding='utf-8') as stream:
        raw = list(csv.DictReader(stream))
    with (DATA / 'sources.csv').open(encoding='utf-8') as stream:
        sources = {r['source_id']: r for r in csv.DictReader(stream)}
    assert [int(r['fiscal_year_end']) for r in raw] == list(range(2017, 2026))
    prepared = []
    total_units = 0
    previous_end = LAUNCH
    for row in raw:
        start = date.fromisoformat(row['observation_start'])
        end_exclusive = date.fromisoformat(row['period_end']) + timedelta(days=1)
        assert start == previous_end
        previous_end = end_exclusive
        units = int(row['sales_units'])
        assert units == int(row['reported_sales_ten_thousands']) * 10000
        assert Decimal(row['sales_millions']) == Decimal(units) / 1000000
        assert (DATA / sources[row['source_id']]['local_file']).exists()
        total_units += units
        reported = row['reported_lifetime_units_if_available']
        prepared.append({
            'fiscal_year_end': int(row['fiscal_year_end']),
            'observation_start': start.isoformat(), 'observation_end_exclusive': end_exclusive.isoformat(),
            'duration_days': (end_exclusive - start).days,
            't_start_years_since_launch': (start - LAUNCH).days / YEAR_DAYS,
            't_end_years_since_launch': (end_exclusive - LAUNCH).days / YEAR_DAYS,
            'sales_units': units, 'sales_millions': units / 1e6,
            'cumulative_from_annual_units': total_units,
            'cumulative_from_annual_millions': total_units / 1e6,
            'reported_lifetime_units_if_available': reported,
            'cumulative_minus_reported_units': total_units - int(reported) if reported else '',
            'source_id': row['source_id'], 'source_page': int(row['source_page']),
        })
    assert prepared[0]['duration_days'] == 29
    write_csv(DATA / 'switch_prepared.csv', prepared)
    starts = np.array([r['t_start_years_since_launch'] for r in prepared])
    ends = np.array([r['t_end_years_since_launch'] for r in prepared])
    y = np.array([r['sales_millions'] for r in prepared])
    years = np.array([r['fiscal_year_end'] for r in prepared])
    total = float(y.sum())
    primary, predicted = fit_intervals(starts, ends, y, total)
    p, q, m = [primary[key] for key in ['p_per_year', 'q_per_year', 'M_million_units']]
    assert not primary['numerical_bound_hit']
    assert abs(cumulative(0, p, q, m)) < 1e-8
    assert np.all(predicted >= 0)
    assert np.all(np.diff(cumulative(np.linspace(0, ends[-1], 500), p, q, m)) >= 0)
    assert abs(predicted.sum() - cumulative(ends[-1], p, q, m)) < 1e-8
    residual = y - predicted
    full_year = np.array([r['duration_days'] > 300 for r in prepared])
    primary['R_squared_full_year_intervals'] = float(1 - np.sum(residual[full_year]**2) /
        np.sum((y[full_year] - y[full_year].mean())**2))
    fit_rows = []
    for i, row in enumerate(prepared):
        fit_rows.append({**row, 'fitted_sales_millions': float(predicted[i]),
                         'residual_observed_minus_fitted_millions': float(residual[i]),
                         'fitted_cumulative_millions': float(cumulative(ends[i], p, q, m))})
    write_csv(DATA / 'switch_bass_fit.csv', fit_rows)

    conditioned, _ = fit_intervals(starts[1:] - ends[0], ends[1:] - ends[0],
                                           y[1:], total, initial=float(y[0]))
    sensitivity = []
    for i, year in enumerate(years):
        mask = np.ones(len(y), dtype=bool)
        mask[i] = False
        check, _ = fit_intervals(starts, ends, y, total, mask=mask, full_search=False)
        sensitivity.append({'omitted_fiscal_year_end': int(year),
                            **{k: check[k] for k in ['p_per_year', 'q_per_year', 'M_million_units',
                                                     'RMSE_million_units', 'numerical_bound_hit']}})
    write_csv(DATA / 'switch_bass_sensitivity.csv', sensitivity)
    primary['fitted_cumulative_at_last_observation_millions'] = float(cumulative(ends[-1], p, q, m))
    peak = float(np.log(q / p) / (p + q)) if q > p else 0.
    primary['instantaneous_peak_years_since_launch'] = peak
    primary['instantaneous_peak_date_approx'] = (LAUNCH + timedelta(days=peak * YEAR_DAYS)).isoformat()
    payload = {
        'model': 'Continuous-time Bass, exact reporting-interval increments, zero adoption at launch',
        'objective': 'Unweighted nonlinear least squares on period sales in millions',
        'constraints': {'p_q_min_per_year': 1e-8, 'p_q_max_per_year': 10.,
                        'M_min_millions': total + 1e-6, 'M_max_millions': total + 100000.},
        'time_convention': 'Actual calendar days / 365.25; end dates made exclusive',
        'primary': primary,
        'launch_conditioned_check': {'description': 'April 1 2017 initial condition N0=2.74 million; fit the next eight intervals',
                                     **conditioned},
        'leave_one_period_out_parameter_ranges': {
            k: [min(r[k] for r in sensitivity), max(r[k] for r in sensitivity)]
            for k in ['p_per_year', 'q_per_year', 'M_million_units']},
        'diagnostic_note': 'No sensitivity fit is an out-of-sample Switch 2 forecast; all keep the same observed-total lower bound for M.',
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'scipy': scipy.__version__, 'matplotlib': matplotlib.__version__},
    }
    (DATA / 'bass_estimates.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')

    plt.rcParams.update(PLOT_STYLE)
    blue, red = '#225b83', '#b44835'
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), layout='constrained')
    axes[0].bar(years, y, color=[red] + [blue] * 8, width=0.68)
    axes[0].set(title='Sales by reporting period', ylabel='Hardware sell-in (million units)',
                xlabel='Fiscal year ended March 31')
    axes[0].annotate('29-day launch period', (2017, y[0]), (2017.1, 7.5), fontsize=8,
                     arrowprops={'arrowstyle': '-', 'color': red})
    axes[1].plot(years, y.cumsum(), 'o-', color=blue)
    axes[1].set(title='Cumulative published annual sales', ylabel='Hardware sell-in (million units)',
                xlabel='Fiscal year ended March 31')
    for ax in axes:
        ax.set_xticks(years[::2]); ax.grid(axis='y', alpha=0.2); ax.set_axisbelow(True)
    fig.suptitle('Original Nintendo Switch family: global historical sales', fontsize=13, weight='bold')
    fig.savefig(IMG / 'historical_sales.png'); plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True, layout='constrained',
                             gridspec_kw={'height_ratios': [2, 1]})
    axes[0].plot(years, y, 'o-', color=blue, label='Observed sell-in')
    axes[0].plot(years, predicted, 's--', color=red, label='Bass fitted interval sales')
    axes[0].set(ylabel='Million hardware units', title='Bass fit using actual interval lengths')
    axes[0].legend(frameon=False, ncol=2)
    axes[1].bar(years, residual, color=[red if v > 0 else blue for v in residual], width=0.65)
    axes[1].axhline(0, color='#555555', linewidth=0.8)
    axes[1].set(ylabel='Observed - fitted\n(million units)', xlabel='Fiscal year ended March 31')
    axes[1].set_xticks(years)
    for ax in axes:
        ax.grid(axis='y', alpha=0.2); ax.set_axisbelow(True)
    fig.savefig(IMG / 'bass_fit_and_residuals.png'); plt.close(fig)
    print("Historical Bass fit: p={:.5f}, q={:.5f}, M={:.2f} million".format(p, q, m))


if __name__ == '__main__':
    main()

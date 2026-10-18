"""Build a pre-launch analogue forecast without reading later actual outcomes."""
import csv
import json
from datetime import date, timedelta

from scipy.optimize import brentq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from analyze_bass import ROOT, DATA, IMG, YEAR_DAYS, PLOT_STYLE, cumulative, write_csv


def main():
    inputs = json.loads((DATA / 'forecast_inputs.json').read_text())
    historical = json.loads((DATA / 'bass_estimates.json').read_text())
    primary = historical['primary']
    ranges = historical['leave_one_period_out_parameter_ranges']
    launch = date.fromisoformat(inputs['launch_date'])
    cutoff = date.fromisoformat(inputs['information_cutoff'])
    first_end = date.fromisoformat(inputs['first_period_end']) + timedelta(days=1)
    final_end = date.fromisoformat(inputs['final_forecast_period_end'])
    target = inputs['first_period_target_million_units']
    with (DATA / 'sources.csv').open(encoding='utf-8') as stream:
        sources = {r['source_id']: r for r in csv.DictReader(stream)}
    for source_id in [inputs['launch_source_id'], inputs['target_source_id'], inputs['lifetime_source_id']]:
        assert date.fromisoformat(sources[source_id]['publication_date']) <= cutoff
    assert cutoff < launch < first_end
    t_first = (first_end - launch).days / YEAR_DAYS
    cases = {
        'lower': (inputs['analogue_reported_lifetime_million_units'], ranges['q_per_year'][0]),
        'base': (primary['M_million_units'], primary['q_per_year']),
        'upper': (ranges['M_million_units'][1], ranges['q_per_year'][1]),
    }
    parameters = {}
    rows = []
    peak_summaries = {}
    for name, (m, q) in cases.items():
        assert m > target > 0
        p = brentq(lambda value: float(cumulative(t_first, value, q, m)) - target,
                   1e-8, 10., xtol=1e-13)
        assert abs(float(cumulative(t_first, p, q, m)) - target) < 1e-8
        parameters[name] = {'p_per_year': p, 'q_per_year': q, 'M_million_units': m}
        start = launch
        scenario_rows = []
        for year in range(first_end.year, final_end.year + 1):
            end = date(year, 4, 1)
            a, b = (start - launch).days / YEAR_DAYS, (end - launch).days / YEAR_DAYS
            n_start, n_end = float(cumulative(a, p, q, m)), float(cumulative(b, p, q, m))
            row = {'scenario': name, 'fiscal_year_end': year,
                   'period_start': start.isoformat(), 'period_end': (end - timedelta(days=1)).isoformat(),
                   'duration_days': (end - start).days, 't_start_years': a, 't_end_years': b,
                   'new_hardware_units_millions': n_end - n_start,
                   'cumulative_hardware_units_millions': n_end}
            scenario_rows.append(row)
            start = end
        rows.extend(scenario_rows)
        annual_peak = max(scenario_rows, key=lambda row: row['new_hardware_units_millions'])
        peak_summaries[name] = {'peak_fiscal_year_end': annual_peak['fiscal_year_end'],
                                'peak_period_sales_millions': annual_peak['new_hardware_units_millions'],
                                'final_cumulative_millions': scenario_rows[-1]['cumulative_hardware_units_millions']}
    write_csv(DATA / 'switch2_forecast_scenarios.csv', rows)
    baseline = [r for r in rows if r['scenario'] == 'base']
    write_csv(DATA / 'switch2_forecast.csv', baseline)
    unchanged = float(cumulative(t_first, primary['p_per_year'], primary['q_per_year'], primary['M_million_units']))
    output = {
        'information_cutoff': inputs['information_cutoff'],
        'launch_date': launch.isoformat(), 'first_period_days': (first_end - launch).days,
        'calibration_target_million_units': target,
        'parameters': parameters, 'summaries': peak_summaries,
        'unchanged_analogue_first_period_millions': unchanged,
        'first_period_is_calibrated_not_independently_predicted': True,
        'scenario_interpretation': inputs['scenario_note'],
        'market_potential_logic': {
            'established_analogue_volume_millions': inputs['analogue_reported_lifetime_million_units'],
            'base_increment_over_established_volume_millions': primary['M_million_units'] - inputs['analogue_reported_lifetime_million_units'],
            'assumption': 'Comparable long-run platform hardware volume; no claim that each earlier buyer upgrades.'},
    }
    (DATA / 'forecast_results.json').write_text(json.dumps(output, indent=2) + '\n')

    plt.rcParams.update(PLOT_STYLE)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), layout='constrained')
    colors = {'lower': '#7d8691', 'base': '#225b83', 'upper': '#ba6835'}
    for name in cases:
        selected = [r for r in rows if r['scenario'] == name]
        years = [r['fiscal_year_end'] for r in selected]
        for ax, key in zip(axes, ['new_hardware_units_millions', 'cumulative_hardware_units_millions']):
            ax.plot(years, [r[key] for r in selected], marker='o', markersize=3,
                    color=colors[name], label=name.capitalize(), linewidth=2 if name == 'base' else 1.2)
            ax.grid(axis='y', alpha=0.2)
            ax.set(xlabel='Fiscal year ended March 31', ylabel='Million hardware units')
            ax.set_xticks(years[::2])
    axes[0].set_title('Sales by reporting period')
    axes[1].set_title('Cumulative hardware adoption proxy')
    axes[1].legend(frameon=False)
    fig.suptitle('Switch 2 forecast from pre-launch information', fontweight='bold')
    fig.savefig(IMG / 'switch2_forecast.png'); plt.close(fig)
    print('Switch 2 forecast:', json.dumps(output['parameters']['base']))


if __name__ == '__main__':
    main()

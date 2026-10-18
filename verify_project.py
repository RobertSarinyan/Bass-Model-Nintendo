"""Scientific consistency and source checks; writes a separate holdout evaluation."""
import csv
import json
import re
from datetime import date, timedelta

import numpy as np
from scipy.integrate import solve_ivp
from pypdf import PdfReader
from pypdf.generic import ContentStream
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from analyze_bass import ROOT, DATA, YEAR_DAYS, PLOT_STYLE, cumulative, write_csv


def read_rows(name):
    with (DATA / name).open(encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def verify_numbers():
    historical = json.loads((DATA / 'bass_estimates.json').read_text())
    forecasts = json.loads((DATA / 'forecast_results.json').read_text())
    inputs = json.loads((DATA / 'forecast_inputs.json').read_text())
    source_rows = read_rows('sources.csv')
    sources = {r['source_id']: r for r in source_rows}
    assert len(sources) == len(source_rows), 'Duplicate source IDs'
    for source in sources.values():
        path = DATA / source['local_file']
        assert path.is_file() and path.stat().st_size > 1000, source['source_id']
        if path.suffix == '.pdf':
            assert path.read_bytes().startswith(b'%PDF'), source['source_id']
    fits = read_rows('switch_bass_fit.csv')
    raw = read_rows('switch_historical_sales.csv')
    assert len(raw) == len(fits) == 9
    assert [int(r['fiscal_year_end']) for r in raw] == list(range(2017, 2026))
    for row, fitted in zip(raw, fits):
        assert date.fromisoformat(sources[row['source_id']]['publication_date']) <= date.fromisoformat(inputs['information_cutoff'])
        assert int(row['sales_units']) == int(row['reported_sales_ten_thousands']) * 10000
        assert float(row['sales_millions']) == int(row['sales_units']) / 1e6
        for key in ['fiscal_year_end', 'source_id', 'source_page', 'sales_units']:
            assert fitted[key] == row[key], f'Raw/derived mismatch in {key}'
        assert float(fitted['sales_millions']) == float(row['sales_millions'])
    y = np.array([float(r['sales_millions']) for r in fits])
    yh = np.array([float(r['fitted_sales_millions']) for r in fits])
    assert np.isclose(np.sqrt(np.mean((y-yh)**2)), historical['primary']['RMSE_million_units'])
    assert np.isclose(1-np.sum((y-yh)**2)/np.sum((y-y.mean())**2), historical['primary']['R_squared_period_sales'])
    assert int(fits[0]['duration_days']) == 29
    assert not historical['primary']['numerical_bound_hit']
    assert historical['primary']['starts_within_1e_6_of_best_SSE'] == 27

    ode_errors = {}
    sets = {'historical': historical['primary'],
            'launch_conditioned': historical['launch_conditioned_check'], **forecasts['parameters']}
    for name, params in sets.items():
        p, q, m = [params[k] for k in ['p_per_year', 'q_per_year', 'M_million_units']]
        initial = float(raw[0]['sales_millions']) if name == 'launch_conditioned' else 0.0
        t = np.linspace(0, 10, 150)
        solution = solve_ivp(lambda _, n: (p+q*n/m)*(m-n), [0, 10], [initial],
                             t_eval=t, rtol=1e-10, atol=1e-10)
        assert solution.success
        numeric = solution.y[0]
        analytic = cumulative(t, p, q, m, initial=initial)
        assert abs(analytic[0] - initial) < 1e-8
        error = float(np.max(np.abs(numeric-analytic)))
        assert error < 1e-5
        assert np.all(np.diff(analytic) >= 0) and np.all(analytic <= m)
        ode_errors[name] = error
    rows = read_rows('switch2_forecast_scenarios.csv')
    assert len(rows) == 30
    for name in forecasts['parameters']:
        selected = [r for r in rows if r['scenario'] == name]
        assert [int(r['fiscal_year_end']) for r in selected] == list(range(2026, 2036))
        assert int(selected[0]['duration_days']) == 300
        assert abs(float(selected[0]['new_hardware_units_millions']) - inputs['first_period_target_million_units']) < 1e-8
        running = 0.0
        prior_end = None
        for row in selected:
            start, end = date.fromisoformat(row['period_start']), date.fromisoformat(row['period_end'])
            assert prior_end is None or start == prior_end + timedelta(days=1)
            prior_end = end
            assert (end-start).days+1 == int(row['duration_days'])
            running += float(row['new_hardware_units_millions'])
            assert float(row['new_hardware_units_millions']) >= 0
            assert abs(running-float(row['cumulative_hardware_units_millions'])) < 1e-8
            assert running < forecasts['parameters'][name]['M_million_units']

    # Later actuals are read here only, after forecast parameters and values exist.
    actuals = read_rows('switch2_validation_actual.csv')
    baseline = read_rows('switch2_forecast.csv')
    evaluations = []
    for actual in actuals:
        assert date.fromisoformat(actual['publication_date']) > date.fromisoformat(inputs['information_cutoff'])
        assert actual['publication_date'] == sources[actual['source_id']]['publication_date']
        predicted = next(r for r in baseline if r['fiscal_year_end'] == actual['fiscal_year_end'])
        assert actual['observation_start'] == predicted['period_start']
        assert actual['period_end'] == predicted['period_end']
        observed, forecast = float(actual['sales_millions']), float(predicted['new_hardware_units_millions'])
        evaluations.append({'fiscal_year_end': actual['fiscal_year_end'],
                            'forecast_millions': forecast, 'actual_millions': observed,
                            'forecast_minus_actual_millions': forecast-observed,
                            'absolute_percentage_error': abs(forecast-observed)/observed*100,
                            'actual_source_id': actual['source_id'], 'actual_source_page': actual['source_page'],
                            'role': 'Evaluation only; no refitting'})
    write_csv(DATA / 'switch2_validation.csv', evaluations)
    evaluation = evaluations[0]
    # The figure must look the same in a standalone check and in the full run.
    plt.rcParams.update(PLOT_STYLE)
    fig, ax = plt.subplots(figsize=(7, 3.3), layout='constrained')
    values = [evaluation['forecast_millions'], evaluation['actual_millions']]
    bars = ax.bar(['Pre-launch anchored forecast', 'Later reported actual'], values,
                  color=['#225b83', '#ba6835'], width=0.55)
    ax.bar_label(bars, labels=[f'{v:.2f}' for v in values], padding=4)
    ax.set(ylim=(0, max(values)*1.2), ylabel='Million hardware sell-in units',
           title='Fiscal year ended March 2026: separate outcome check')
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', alpha=0.2); ax.set_axisbelow(True)
    fig.savefig(ROOT / 'img/switch2_validation.png', dpi=180); plt.close(fig)
    result = {'numeric_checks': 'passed', 'historical_observations': len(raw),
              'forecast_observations': len(rows), 'local_sources': len(sources),
              'max_ODE_difference_million_units': ode_errors,
              'holdout_evaluation': evaluations,
              'rounding_difference_annual_sum_minus_reported_lifetime_units':
                  sum(int(r['sales_units']) for r in raw)-int(raw[-1]['reported_lifetime_units_if_available'])}
    (DATA / 'verification_results.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Numerical/source checks passed; later outcome evaluated separately.')
    return result


def verify_report():
    markdown = (ROOT / 'report/report_source.md').read_text(encoding='utf-8')
    headings = re.findall(r'^## (\d+)\.', markdown, re.M)
    assert headings == [str(i) for i in range(1, 8)], headings
    assert '{{' not in markdown and '<!-- BEGIN' not in markdown
    assert ';' not in markdown, 'Semicolon left in report source'
    for image in re.findall(r'!\[.*?\]\((.*?)\)', markdown):
        assert (ROOT / 'report' / image).resolve().is_file(), image
    pdf = PdfReader(ROOT / 'report/report.pdf')
    text = '\n'.join(p.extract_text() for p in pdf.pages)
    assert 'Robert Sarinyan' in pdf.pages[0].extract_text(), 'Author missing on first page'
    assert ';' not in text, 'Semicolon left in PDF text'
    for required in ['167.29', '19.86', '24.47', '2035', 'References']:
        assert required in text, required
    assert len(pdf.pages) > 1
    expected_figures = len(re.findall(r'!\[.*?\]\(.*?\)', markdown))
    # WeasyPrint shares its image resource dictionary across pages. Count unique
    # objects rather than counting that same dictionary once for every page.
    image_ids = {im.indirect_reference.idnum for p in pdf.pages for im in p.images}
    assert len(image_ids) == expected_figures, 'Unexpected raster images, possibly equations'
    assert '/StructTreeRoot' in pdf.trailer['/Root'], 'PDF reading structure missing'
    formula_fonts = set()
    for page in pdf.pages:
        for font in page['/Resources']['/Font'].values():
            name = str(font.get_object().get('/BaseFont', ''))
            if 'KaTeX' in name:
                formula_fonts.add(name)
                assert '/ToUnicode' in font.get_object(), 'Math font has no text mapping'
        for operands, operator in ContentStream(page.get_contents(), pdf).operations:
            if operator == b'BDC' and len(operands) == 2 and '/ActualText' in operands[1]:
                raise AssertionError('Old replacement-text equation spans remain')
    assert formula_fonts, 'Typeset equation fonts missing'
    # Check visible equation text, not just a substitute string embedded in PDF.
    equation_page = next(p for p in pdf.pages if '5.1 Model' in p.extract_text())
    equation_text = ''.join(equation_page.extract_text().split())
    for fragment in ['dN(t)', 'N(b)', 'N(a)', 'exp(']:
        assert fragment in equation_text, f'Math symbols missing from PDF text: {fragment}'
    assert markdown.count('$$') // 2 == 3
    assert all(len(p.extract_text().strip()) > 80 for p in pdf.pages), 'Near-empty page'
    print(f'Report checks passed: {len(pdf.pages)} pages, author, no semicolons, '
          f'{expected_figures} figures, mapped equation fonts, and expected results.')


if __name__ == '__main__':
    verify_numbers()
    verify_report()

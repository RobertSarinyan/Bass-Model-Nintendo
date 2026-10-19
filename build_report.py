from html import escape, unescape
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import markdown

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'report/report_source.md'
OUTPUT = ROOT / 'report/report.pdf'
ASSETS = ROOT / 'report/assets/katex'

CSS = '''
@page {
  size: A4;
  margin: 15mm 17mm 18mm;
  @bottom-left {
    content: "Nintendo Switch 2 | Bass diffusion analysis";
    font: 8pt Arial, sans-serif;
    color: #59636d;
  }
  @bottom-right { content: counter(page); font: 8pt Arial, sans-serif; color: #59636d; }
}
body { font: 11pt/1.32 "Times New Roman", "Liberation Serif", serif; color: #111; }
h1, h2, h3 { font-family: Arial, "Liberation Sans", sans-serif; break-after: avoid; }
h1 { font-size: 19pt; line-height: 1.2; margin: 0 0 17pt; }
h2 { font-size: 12pt; line-height: 1.3; margin: 14pt 0 10pt; }
h3 { font-size: 11pt; line-height: 1.3; margin: 12pt 0 9pt; }
h2[id^="5-"], h2[id^="6-"], h2[id^="7-"], h2#references,
h3[id^="63-"] { break-before: page; }
p { margin: 0 0 10pt; orphans: 3; widows: 3; }
table { width: 100%; border-collapse: collapse; table-layout: fixed;
        margin: 6pt 0 13pt; font-size: 9.5pt; line-height: 1.25; break-inside: avoid; }
thead { display: table-header-group; background: #edf2f6; }
th { font-weight: normal; border-bottom: 0.7pt solid #718494; }
th, td { text-align: left; padding: 5pt 6pt; vertical-align: top; }
td { border-bottom: 0.3pt solid #d3d8dd; }
th:first-child, td:first-child { width: 38%; }
th:nth-child(2), td:nth-child(2) { width: 27%; }
figure { margin: 9pt 0 15pt; break-inside: avoid; }
figure img { display: block; width: 100%; height: auto; }
figcaption { font-size: 9.5pt; line-height: 1.25; color: #465461; margin-top: 6pt; }
a { color: #245782; text-decoration: none; }
code { font: 9pt monospace; }
.equation { margin: 12pt 0 15pt; break-inside: avoid; }
.equation .katex-display { margin: 0; text-align: left; }
.equation .katex { font-size: 1.1em; }
h2#references ~ p { font-size: 9.5pt; line-height: 1.25; margin-bottom: 8pt; }
'''

KATEX_SCRIPT = '''
const fs = require('fs');
const katex = require(process.argv[1]);
const formulas = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(formulas.map(item => katex.renderToString(
  item.latex, {displayMode: item.display, output: 'html', throwOnError: true,
               strict: 'error', trust: false}
))));
'''


def typeset_math(body):
    """Replace mdx_math's script markers with already-typeset HTML."""
    pattern = re.compile(r'<script type="math/tex(?P<display>; mode=display)?">'
                         r'(?P<latex>.*?)</script>', re.S)
    matches = list(pattern.finditer(body))
    if not matches:
        return body
    node = os.environ.get('NODE_BINARY') or shutil.which('node')
    if not node:
        raise RuntimeError('Node.js is required to typeset equations with the bundled KaTeX renderer.')
    formulas = [{'latex': unescape(m['latex']), 'display': bool(m['display'])} for m in matches]
    result = subprocess.run([node, '-e', KATEX_SCRIPT, str(ASSETS / 'katex.min.js')],
                            input=json.dumps(formulas), text=True, encoding='utf-8',
                            capture_output=True, check=True)
    rendered = iter(json.loads(result.stdout))

    def replace(match):
        tag = 'div' if match['display'] else 'span'
        html = next(rendered).replace(' aria-hidden="true"', '')
        return f'<{tag} class="equation">{html}</{tag}>'

    body = re.sub(r'<p>\s*(<script type="math/tex; mode=display">.*?</script>)\s*</p>',
                  r'\1', body, flags=re.S)
    return pattern.sub(replace, body)


def make_html(source):
    body = markdown.markdown(source, extensions=['mdx_math', 'tables', 'toc', 'sane_lists'])
    body = typeset_math(body)

    def figure(match):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', match[1]))
        caption = attrs.get('alt', '')
        return f'<figure><img {match[1]}><figcaption>{caption}</figcaption></figure>'

    body = re.sub(r'<p><img\s+([^>]*?)/?>\s*</p>', figure, body)
    body = re.sub(r'(?<!["=])(https://[^\s<>]+)',
                  lambda m: f'<a href="{escape(m[0], quote=True)}">[Source]</a>', body)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Nintendo Switch 2: A Bass Model Forecast</title>
<meta name="author" content="Robert Sarinyan">
<link rel="stylesheet" href="{(ASSETS / 'katex.min.css').as_uri()}">
<style>{CSS}</style></head><body>{body}</body></html>'''


def load_weasyprint():
    """Use normal system libraries, or the optional local Windows runtime."""
    runtime = ROOT / '.tools/weasyprint/onedir/weasyprint/_internal'
    if os.name == 'nt' and runtime.is_dir() and not os.environ.get('WEASYPRINT_DLL_DIRECTORIES'):
        os.environ['WEASYPRINT_DLL_DIRECTORIES'] = str(runtime)
    try:
        from weasyprint import HTML
    except OSError as error:
        raise RuntimeError(
            'WeasyPrint requires Pango native libraries. See the README Windows setup '
            'or set WEASYPRINT_DLL_DIRECTORIES to your existing Pango DLL directory.'
        ) from error
    return HTML


def build():
    HTML = load_weasyprint()
    document = make_html(SOURCE.read_text(encoding='utf-8-sig'))
    temporary = ROOT / 'tmp'
    temporary.mkdir(exist_ok=True)
    (temporary / 'report.html').write_text(document, encoding='utf-8')
    # Build in memory first so a failed render cannot truncate the final report.
    pdf = HTML(string=document, base_url=str(SOURCE.parent)).write_pdf(
        pdf_tags=True, custom_metadata=True)
    OUTPUT.write_bytes(pdf)
    print(OUTPUT)


if __name__ == '__main__':
    build()

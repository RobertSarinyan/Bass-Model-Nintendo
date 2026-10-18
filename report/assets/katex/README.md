# KaTeX assets

Version: 0.19.0. Source: https://registry.npmjs.org/katex/-/katex-0.19.0.tgz

These files are the unmodified renderer (`katex.min.js`), stylesheet (`katex.min.css`), fonts, and license from the official KaTeX npm package. The MIT license is reproduced in `LICENSE` and also covers the included fonts as distributed by KaTeX.

`build_report.py` invokes the renderer with Node.js to turn LaTeX into HTML before WeasyPrint runs. No network requests are needed during report generation.

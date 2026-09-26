# IET Renewable Power Generation template

Layout: Wiley New Journal Design v5 (`WileyNJDv5.cls`) with the class options
Wiley's journal list gives for IET Renewable Power Generation: `Garamond2COL`
(EB Garamond, two columns) and `MPS` (numbered references).

References: the IET numbered style
(`the-institution-of-engineering-and-technology.csl`, CC BY-SA 3.0, from the
Citation Style Language repository), which the CSL repository assigns to this
journal. The journal accepts free-format submission, so the typesetter
applies the final reference style.

## Wiley class files (not bundled)

Wiley's class is "copyright by Wiley. All rights reserved" and ships with
commercial fonts, so it is not part of this package. Place these files

    WileyNJDv5.cls  NJDnatbib.sty  NJDapacite.sty  LETTERSP.STY

in one folder, found in this order:

1. `class_dir=` in `build()` / `--class-dir` on the command line
2. the `WILEY_NJD_DIR` environment variable
3. `~/.local/share/pytexMB/wiley-njd-v5/`

Get them from Wiley's NJD page
(https://authors.wiley.com/author-resources/Journal-Authors/Prepare/new-journal-design.html)
or Overleaf's "Wiley New Journal Design version 5 (NJD-v5)" template.

The class also loads the free LaTeX packages `ebgaramond`, `algorithms`, and
`algorithmicx`. Debian/Ubuntu ship them in `texlive-fonts-extra` and
`texlive-science`; alternatively install them from CTAN into `~/texmf`.

Wiley states the class targets TeX Live 2022; with this template it also
compiles under TeX Live 2023 and XeLaTeX.

# UiA PhD thesis template

The structure of the University of Agder's official doctoral thesis
template (V3, 2026): UiA front pages, then preface, acknowledgements,
abstract, and list of publications, then the table of contents and the
lists of figures and tables, then numbered chapters and the bibliography.
Each Markdown `#` heading starts a chapter, numbered automatically.

References: IEEE numbered style (`ieee.csl`, CC BY-SA 3.0, from the
Citation Style Language repository), matching the template's `ieeetr`.

Engine: pdfLaTeX, as in UiA's template (XeLaTeX via `engine=` also works
if the header allows it).

## UiA project files (not bundled)

UiA's layout lives in its `header/` files (front pages, page style, fonts,
logo), which come from your own copy of UiA's template:

1. On Overleaf, open
   [PhD Thesis Template, University of Agder (UiA) 2026](https://www.overleaf.com/latex/templates/phd-thesis-template-university-of-agder-uia-2026/gghyfkchxxzw)
   with **Open as Template**.
2. Fill in `header/information.tex` (title, author, faculty, and so on);
   the front pages are built from it.
3. **Menu > Download > Source**, and unzip the project into one folder.

pytexMB copies that whole folder into the LaTeX package, except
`thesis.tex`, `chapters/`, and `appendix/`, which the Markdown replaces. It
looks for the folder in this order:

1. `class_dir=` in `file_settings()` / `--class-dir`
2. the `UIA_THESIS_DIR` environment variable
3. `~/.local/share/pytexMB/uia-phd/`

## Front matter in the Markdown

```yaml
---
title: "Thesis title"          # used by the Word copy; the PDF uses information.tex
preface: |
  ...
acknowledgements: |
  ...
abstract: |
  ...
publications: |
  1. Paper one ...
---
```

The UiA template itself is by UiA-Universitetsbiblioteket and UiAdoc
(Adalberon, Cardenas-Cartagena, Brehmer, Slokvik Lian, Torjusen),
licensed CC BY 4.0.

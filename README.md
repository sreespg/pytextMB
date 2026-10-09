# pytexMB

Create a journal-style PDF, an editable LaTeX package, and a Word review copy
from one Markdown manuscript.

You write the paper once in Markdown: prose, tables, figure captions, and
citations. pytexMB turns it into:

- a **PDF** typeset with the journal's own LaTeX class,
- the **LaTeX package** behind it (`.tex`, class files, figures), which
  compiles on its own and can be submitted,
- a **Word copy** for co-authors and reviewers who comment in Word.

The PDF and the Word copy are both made from the same generated LaTeX, so
they always agree.

## Journal templates

| Name | Journal | Layout | References |
| --- | --- | --- | --- |
| `applied-energy` (default) | Applied Energy (Elsevier) | Elsevier CAS class, two columns | Elsevier Vancouver, numbered |
| `iet-rpg` | IET Renewable Power Generation (Wiley) | Wiley NJD v5 class, two columns, EB Garamond | IET, numbered |
| `uia-phd` | PhD thesis, University of Agder | UiA thesis template V3 (2026), `extbook`, chapters | IEEE, numbered |

The Elsevier class ships with pytexMB. Wiley's class and UiA's thesis
header files do not; see [Wiley class files](#wiley-class-files-for-iet-rpg)
and [UiA thesis files](#uia-thesis-files-for-uia-phd).

## Install

Into the virtual environment (or conda environment) of any project:

```
pip install git+https://github.com/sreespg/pytextMB.git
```

To pin a version, add a tag: `...pytextMB.git@v1.1.0`. In a
`requirements.txt` or `pyproject.toml` dependency list, write it as
`pytexMB @ git+https://github.com/sreespg/pytextMB.git@v1.1.0`.

pytexMB is pure Python (3.9+, no Python dependencies), but it drives these
programs, which must be on your `PATH`:

- [Pandoc](https://pandoc.org) 3.x
- XeLaTeX (TeX Live or MiKTeX)
- `rsvg-convert` (Debian/Ubuntu: `librsvg2-bin`), for SVG figures

For `applied-energy`, the STIX and Inconsolata fonts give the journal's
exact look (Debian/Ubuntu: `fonts-stix fonts-inconsolata`). Without them it
uses TeX Gyre Termes and Latin Modern Mono, which come with TeX Live, and
says so.

### Setting up a machine

```
pytexMB check
```

lists which programs, fonts, and template files pytexMB can find, and what
to do about anything missing:

```
ok  pandoc          pandoc 3.1.3
ok  rsvg-convert    rsvg-convert version 2.58.0
ok  xelatex         XeTeX 3.141592653-2.6-0.999995 (TeX Live 2023/Debian)
ok  applied-energy  ready
--  iet-rpg         needs the Wiley NJD v5 class: run `pytexMB install-files iet-rpg <download.zip or folder>`
```

The Wiley and UiA files cannot be shipped with pytexMB. Download them once
per machine and install them straight from the download, a `.zip` or an
unpacked folder:

```
pytexMB install-files iet-rpg ~/Downloads/wiley-njd-v5.zip
pytexMB install-files uia-phd ~/Downloads/uia-thesis.zip
```

The files may sit anywhere inside the download. They are copied to
`~/.local/share/pytexMB/`, where every build finds them, in every
environment. From Python: `pytexMB.check()` and
`pytexMB.install_files('iet-rpg', '~/Downloads/wiley-njd-v5.zip')`.

## Use

The simplest way is a short `build.py` beside the manuscript, naming what
to build:

```python
import pytexMB

pytexMB.run(
    manuscript='paper.md',         # path to the Markdown file
    template='iet-rpg',            # see `pytexMB --list-templates`, or a template folder

    # Optional
    output_dir='build',            # default: build/ beside the manuscript
    word=True,                     # also make the Word copy (default: True)
)
```

That is the whole script. It takes every command and flag the `pytexMB`
command does, with no code of yours:

```
python build.py             # PDF and Word copy, in build/iet-rpg/
python build.py -f          # rebuild even if nothing changed
python build.py pdf         # the PDF only
python build.py clean       # delete build/
python build.py -h          # every command and flag, and the script's settings
```

Relative paths start at the script's folder, so it works from any folder.
A flag wins over the script for that run (`python build.py -t applied-energy`).
`run()` accepts any setting listed under [Settings](#settings). See
[examples/minimal/build.py](examples/minimal/build.py).

### Without a script

Put the journal and the references in the manuscript's YAML header:

```yaml
template: iet-rpg             # optional; default applied-energy
bibliography: refs/library.bib  # optional; see below
```

Then build, with no settings at all:

```
cd ~/papers/review
pytexMB
```

or from Python:

```python
import pytexMB

result = pytexMB.build()             # or pytexMB.build('paper.md')
print(result.pdf, result.docx)
```

pytexMB works out everything else from the manuscript:

- **Manuscript**: `manuscript.md` in this folder or one above it, or else
  the only `.md` file here (a `README.md` is ignored).
- **References**: the header's `bibliography:` (one file or a list, relative
  to the manuscript), else `references.bib` beside it, else the only `.bib`
  file beside it. A manuscript that cites nothing needs none.
- **Figures**: the files its image lines name, in any folder.
- **Journal**: the header's `template:`, else `applied-energy`.

No folders need to be made: outputs go to `build/<template>/` beside the
manuscript.

### A step of your own after the build

A project that makes something more from the outputs, such as supplementary
material, names the command in the header instead of wrapping pytexMB in a
script:

```yaml
after-build: python scripts/build_supplementary.py
```

It runs in the manuscript's folder after every successful build, from the
command line or `pytexMB.build()`. It is told what was built through
environment variables, so it needs no arguments of its own:

| Variable | Value |
| --- | --- |
| `PYTEXMB_MANUSCRIPT` | the manuscript |
| `PYTEXMB_TEMPLATE` | the template name |
| `PYTEXMB_OUTPUT_DIR` | `build/<template>/` |
| `PYTEXMB_TEX`, `PYTEXMB_PDF`, `PYTEXMB_DOCX` | each output; empty if not built this time |

A leading `python` runs with the same Python as pytexMB. If the command
fails, the build fails. `--no-after-build` (or
`build(after_build=False)`) skips it.

### Settings

Settings override what pytexMB works out, and are only needed when the
defaults do not fit. They come in two groups. **File settings** say where
things are; **build settings** say what to make. Set them once, then build:

```python
import pytexMB

# Where things are
pytexMB.file_settings(
    input_dir='~/papers/review',     # relative paths below start here
    manuscript='paper.md',
    bibliography='refs/library.bib',
    output_dir='out',                # instead of build/ beside the manuscript
)

# What to make
pytexMB.build_settings(
    template='iet-rpg',              # journal template
    pdf=True,
    word=False,                      # no Word copy
)

result = pytexMB.build()             # builds with both groups
print(result.pdf, result.tex)
```

Any setting from either group can be changed for one call without touching
the stored ones:

```python
pytexMB.build(template='applied-energy', word=True)
```

`pytexMB.file_settings()` and `pytexMB.build_settings()` with no arguments
show the current values, and `pytexMB.reset_settings()` puts both back to
the defaults. A one-line build also works:
`pytexMB.build('paper.md', template='iet-rpg')`.

From the terminal:

```
pytexMB                          # nearest manuscript.md, PDF + Word
pytexMB pdf paper.md -t iet-rpg  # one output, another template
pytexMB -i ~/papers/review -o out
pytexMB --list-templates
pytexMB check                    # what this machine can build
pytexMB --help
```

Try it on the included example:

```
cd examples/minimal
pytexMB
```

Outputs go to a subfolder per template, named after the manuscript:
`build/applied-energy/note.pdf`, `note.docx`, and `latex/note.tex`. With
`output_dir='out'` they go to `out/applied-energy/` instead, so outputs for
different journals never overwrite each other.

### File settings

| Setting | Command line | Default |
| --- | --- | --- |
| `input_dir` | `-i` | the current folder; relative paths start here |
| `manuscript` | first argument | `manuscript.md` in the input folder or above, else the only `.md` there |
| `bibliography` | `-b` | the header's `bibliography:`, else `references.bib` or the only `.bib` beside the manuscript |
| `class_dir` | `--class-dir` | see [Wiley class files](#wiley-class-files-for-iet-rpg) |
| `output_dir` | `-o` | `build/` beside the manuscript |

### Build settings

| Setting | Command line | Default |
| --- | --- | --- |
| `template` | `-t` | the header's `template:`, else `applied-energy`; a name or a template folder |
| `pdf` | `pdf`, `docx`, `tex`, `all` | `True` |
| `word` | (same) | `True` |
| `engine` | `-e` | `xelatex` (or `$PANDOC_PDF_ENGINE`) |
| `strict` | `--strict` | `False`; `True` fails on missing citations or undefined references |
| `force` | `-f` | `False`; `True` rebuilds even if outputs are current |

`input_dir` is fixed when set, so changing folder afterwards does not move
it. Without it, relative paths start from the folder you build in.
`build(formats=['tex'])` picks outputs directly, and
`build(fresh=True)` (`rebuild` on the command line) deletes that template's
outputs first.

Only outputs whose inputs changed are rebuilt. The check uses file contents,
not dates, and covers the manuscript, references, figures, template, the
pytexMB code, and the Pandoc and LaTeX versions. Every failure raises
`pytexMB.BuildError` with a message saying what to fix. Progress goes to the
`pytexMB` logger; call `logging.basicConfig(level=logging.INFO)` to see it.

## Writing the manuscript

The YAML header supplies the front matter:

```yaml
---
title: "Full title"
short-title: "Running head"       # optional
article-type: "Review"            # optional; printed above the title by iet-rpg
template: "iet-rpg"               # optional; the journal (default applied-energy)
bibliography: "refs.bib"          # optional; see Use
author: "Given Surname"
affiliation: "Department, University, Country"   # optional
corresponding-author: "name@example.org"         # optional
abstract: |
  One paragraph.
keywords: [first keyword, second keyword]
---
```

The template picks the reference style, so a `csl:` line in the header is
ignored.

- **Headings** are printed as written. Number them yourself (`# 1. Introduction`).
- **Citations** use Pandoc syntax: `[@key]`, `[@a; @b]`.
- **Equations** labelled `\label{eq:name}` inside `$$ ... $$` are numbered.
- **Tables** are pipe tables followed by a caption line with an identifier:
  `Table: Caption. {#tab:name width=full}`. Use `width=half` for one column,
  and optionally `columns=30,70` for relative column widths.
- **Abbreviations**: a table with no caption becomes the framed
  abbreviations glossary. Put it under a `# Abbreviations` heading; the
  heading is folded into the box.
- **Figures** are Markdown images with an identifier and a width:
  `![Caption.](figures/plot.svg){#fig:name width=full}`. Use `width=half`
  for one column; `width` defaults to `full`. pytexMB writes the LaTeX
  figure from this line alone: no layout file or raw LaTeX is needed. The
  path may point into any folder; each figure is copied into the LaTeX
  package's `figures/`, so two figures need different file names. SVG
  figures are converted to PDF for LaTeX and to PNG for Word; PNG and JPEG
  are used as they are; a TikZ `.tex` path in place of the SVG is `\input`
  and scaled to the same width.

`abstract` and `keywords` are optional; the templates leave out what is
missing.

## Wiley class files (for iet-rpg)

Wiley's NJD v5 class is "copyright by Wiley, all rights reserved" and comes
with commercial fonts, so pytexMB cannot include it. Get it from
[Wiley's NJD page](https://authorservices.wiley.com/author-resources/Journal-Authors/Prepare/new-journal-design.html)
or the Overleaf template
[Wiley New Journal Design version 5](https://www.overleaf.com/latex/templates/wiley-new-journal-design-version-5-njd-v5/nrvzqjmwtrdw),
and put these four files in one folder:

    WileyNJDv5.cls  NJDnatbib.sty  NJDapacite.sty  LETTERSP.STY

The easiest way is `pytexMB install-files iet-rpg <the download>`. Builds
look for the files in this order:

1. `class_dir=` / `--class-dir`
2. the `WILEY_NJD_DIR` environment variable
3. `~/.local/share/pytexMB/wiley-njd-v5/` (where `install-files` puts them)

The class also needs the free LaTeX packages `ebgaramond`, `algorithms`, and
`algorithmicx` (Debian/Ubuntu: `texlive-fonts-extra`, `texlive-science`).
It is tested with TeX Live 2023 and XeLaTeX.

## UiA thesis files (for uia-phd)

The `uia-phd` template follows the structure of the University of Agder's
official thesis template: UiA front pages; preface, acknowledgements,
abstract, and publications; contents and lists of figures and tables;
automatically numbered chapters (one per `#` heading); bibliography. It
builds with pdfLaTeX, as UiA's template does.

The UiA layout itself lives in UiA's `header/` files, so use your own copy
of the template:

1. On Overleaf, open
   [PhD Thesis Template, University of Agder (UiA) 2026](https://www.overleaf.com/latex/templates/phd-thesis-template-university-of-agder-uia-2026/gghyfkchxxzw)
   with **Open as Template**.
2. Fill in `header/information.tex`; the front pages are built from it.
3. **Menu > Download > Source**, then
   `pytexMB install-files uia-phd <the downloaded .zip>`.

pytexMB copies that folder into the LaTeX package, leaving out `thesis.tex`,
`chapters/`, and `appendix/`, which the Markdown replaces. It looks in
`class_dir=` / `--class-dir`, then `$UIA_THESIS_DIR`, then
`~/.local/share/pytexMB/uia-phd/`.

The thesis front matter comes from the YAML header:

```yaml
preface: |
  ...
acknowledgements: |
  ...
abstract: |
  ...
publications: |
  1. First paper ...
```

Write chapter headings without numbers (`# Introduction`); LaTeX numbers
them.

## Adding a journal

A template is a folder containing:

- `template.json`: title, LaTeX template, CSL file, files to ship with the
  `.tex`, and optionally files that must come from elsewhere (see
  `templates/iet-rpg/template.json`, or `templates/uia-phd/template.json`
  for a whole project folder), a default `engine`, extra `pandoc_args`,
  and `fonts` the template prefers, which `pytexMB check` reports on;
- `template.tex`: a Pandoc LaTeX template. Put these two lines around
  `$body$` so the Word copy can find the manuscript:

  ```
  % pytexMB:body-start
  $body$
  % pytexMB:body-end
  ```

  It must also define an `abbreviationsbox` environment for the glossary;
- a CSL style, for example from the
  [CSL styles repository](https://github.com/citation-style-language/styles).
  Use a numeric style.

Pass the folder as `template=` / `-t`, or add it to `src/pytexMB/templates/`
to make it built in.

## Development

```
git clone https://github.com/sreespg/pytextMB.git
cd pytextMB
python -m venv .venv && . .venv/bin/activate
pip install -e '.[test]'
pytest
```

With `-e`, edits to the source take effect without reinstalling. Tests that
build real PDFs skip themselves when Pandoc, XeLaTeX, or rsvg-convert is
missing. The version is `__version__` in `src/pytexMB/__init__.py`; tag a
release as `v<version>` so it can be pinned. Changes are listed in
[CHANGELOG.md](CHANGELOG.md).

## Licences of bundled files

- Elsevier CAS class files (`templates/applied-energy/cas-*`): LaTeX Project
  Public License, unmodified from the CAS bundle v2.4.
- CSL styles (`*.csl`): Creative Commons BY-SA 3.0, from the Citation Style
  Language project.
- The `uia-phd` template follows the UiA doctoral thesis template by
  UiA-Universitetsbiblioteket and UiAdoc (CC BY 4.0); UiA's own files are
  not included.

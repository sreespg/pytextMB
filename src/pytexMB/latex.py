"""Generate <output>/latex/: the .tex file plus everything it needs to compile
on its own, which is also the package a journal submission takes. The PDF and
the DOCX are both cut from this one file."""
import re
import shutil

from .compose import compose
from .errors import BuildError
from .tables import tables
from .tools import convert_svgs, log, require, run

CITATION = re.compile(r'\[@[A-Za-z0-9_:-]+(?:\s*;\s*@[A-Za-z0-9_:-]+)*\]')


def build_tex(paths, strict=False):
    require('pandoc', 'rsvg-convert')
    stage(paths)
    compose(paths.stage / paths.source.name)
    shutil.rmtree(paths.latex, ignore_errors=True)
    paths.latex.mkdir(parents=True)
    shutil.copytree(paths.stage / 'figures', paths.latex / 'figures')
    for source, target in paths.template.support_files:
        (paths.latex / target).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, paths.latex / target)
    log(f'Generating LaTeX package ({paths.template.title})')
    # Command-line --bibliography and --csl override the manuscript's YAML, so
    # the template decides the reference style and the .bib may have any name.
    result = run(['pandoc', paths.source.name, '--citeproc', '--standalone', '--to=latex',
                  f'--bibliography={paths.bibliography.name}',
                  f'--csl={paths.template.csl}',
                  f'--template={paths.template.latex}', *paths.template.pandoc_args,
                  '--resource-path=.', f'--output={paths.tex}'],
                 cwd=paths.stage, what='pandoc (Markdown to LaTeX)')
    # Citeproc prints a missing key as `???` and carries on.
    missing = re.findall(r'citation (\S+) not found', result.stderr)
    if missing and strict:
        raise BuildError(f'--strict: citations not in {paths.bibliography.name}: ' + ', '.join(missing))
    number_labeled_equations(paths.tex)
    tables(paths.tex)
    resolve_raw_latex_citations(paths.tex, paths.template.csl)
    check_rendering_hazards(paths.tex)


def stage(paths):
    """Copy the sources to <output>/.stage, where compose() may rewrite them and
    the SVG figures get the PDF versions LaTeX includes. Sources are never
    modified in place."""
    shutil.rmtree(paths.stage, ignore_errors=True)
    paths.stage.mkdir(parents=True)
    shutil.copy2(paths.source, paths.stage)
    shutil.copy2(paths.bibliography, paths.stage)
    if paths.figures.is_dir():
        shutil.copytree(paths.figures, paths.stage / 'figures')
    else:
        (paths.stage / 'figures').mkdir()
    convert_svgs(sorted((paths.stage / 'figures').rglob('*.svg')),
                 lambda svg: svg.with_suffix('.pdf'), ['--format=pdf'])


def number_labeled_equations(tex):
    """Pandoc writes every display equation as unnumbered \\[...\\]; the ones
    carrying an eq: label become numbered equation environments."""
    text = tex.read_text(encoding='utf-8')
    pattern = re.compile(
        r'\\\[\s*((?:(?!\\\]).)*?\\label\{eq:[^}]+\}(?:(?!\\\]).)*)\s*\\\]', re.DOTALL)
    text = pattern.sub(
        lambda match: '\\begin{equation}\n' + match.group(1).strip() + '\n\\end{equation}', text)
    tex.write_text(text, encoding='utf-8')


def resolve_raw_latex_citations(tex, csl):
    """Citeproc never sees raw LaTeX blocks, so a figure-caption citation
    arrives as literal [@key]. Citeproc emits one target anchor per
    bibliography entry; map each key to its rendered number and write the
    citation the way ordinary citations appear, with the CSL's separator.
    Numeric styles only: an author-date style has no number to map to."""
    text = tex.read_text(encoding='utf-8')
    # The label is `[1]` in some styles and a bare `1` in others.
    numbers = dict(re.findall(
        r'\\hypertarget\{ref-([^}]+)\}\{\}.*?\\CSLLeftMargin\{(?:\{\[\})?(\d+)', text, re.DOTALL))
    layout = re.search(r'<citation\b.*?<layout\b([^>]*)>', csl.read_text(encoding='utf-8'), re.S)
    separator = re.search(r'delimiter="([^"]*)"', layout.group(1)) if layout else None
    separator = separator.group(1) if separator else ','

    def replace(match):
        keys = re.findall(r'@([A-Za-z0-9_:-]+)', match.group(0))
        missing = [key for key in keys if key not in numbers]
        if missing:
            raise BuildError('No rendered bibliography entry for: ' + ', '.join(missing))
        citations = separator.join(
            rf'\protect\hyperlink{{ref-{key}}}{{{numbers[key]}}}' for key in keys)
        return r'{[}' + citations + r'{]}'

    tex.write_text(CITATION.sub(replace, text), encoding='utf-8')


def check_rendering_hazards(tex):
    latex_dir = tex.parent
    problems = []
    if '\\textasciitilde' in tex.read_text(encoding='utf-8'):
        problems.append(
            f"{tex.name} contains \\textasciitilde, which typesets a visible "
            "'~'.  Markdown '~' is not a LaTeX tie: write a plain space, as in "
            "'Equation (1)', or a U+00A0 non-breaking space.")
    # Figure sources pulled in with \input are only checked, not rewritten: a
    # citation belongs in the prose beside a figure, not in it.
    for path in [tex, *sorted(latex_dir.glob('figures/*.tex'))]:
        unresolved = sorted(set(CITATION.findall(path.read_text(encoding='utf-8'))))
        if unresolved:
            problems.append(f'{path.name} prints unresolved citations: {", ".join(unresolved)}')
    if problems:
        raise BuildError('Rendering hazards:\n- ' + '\n- '.join(problems))

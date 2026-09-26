"""Compile the generated LaTeX package into the journal-style PDF."""
import os
import re
import shutil
import subprocess

from .errors import BuildError
from .tools import log, require, warn

# LaTeX asks for another pass when cross-references moved. At least two
# passes always run, since a fresh package has no .aux to resolve them from.
RERUN = re.compile(r'Rerun to get|Label\(s\) may have changed')
MAX_PASSES = 4


def build_pdf(paths, engine, strict=False):
    require(engine)
    log(f'Compiling journal-style PDF with {engine}')
    logfile = paths.tex.with_suffix('.log')
    for passes in range(1, MAX_PASSES + 1):
        result = subprocess.run(
            [engine, '-interaction=nonstopmode', '-halt-on-error', '-file-line-error',
             paths.tex.name],
            cwd=paths.latex, capture_output=True, text=True, encoding='utf-8', errors='replace')
        text = logfile.read_text(encoding='utf-8', errors='replace') if logfile.is_file() else ''
        if result.returncode:
            raise BuildError(f'{engine} failed on pass {passes}:\n'
                             f'{latex_errors(text or result.stdout)}\nFull log: {logfile}')
        if passes >= 2 and not RERUN.search(text):
            break
    report_warnings(text, logfile, strict)
    # Replace the published copy in one step, so a reader never finds half a PDF.
    temporary = paths.pdf_output.with_suffix('.pdf.tmp')
    shutil.copy2(paths.tex.with_suffix('.pdf'), temporary)
    os.replace(temporary, paths.pdf_output)
    log(f'Created {paths.pdf_output} ({passes} passes)')


def latex_errors(text, context=3):
    """The `! ...` or `file:line:` error lines of a LaTeX log with the lines
    that follow them, which is where LaTeX says what it was reading."""
    lines = text.splitlines()
    marks = [index for index, line in enumerate(lines)
             if line.startswith('!') or re.match(r'^\./[^:]+:\d+: ', line)]
    if not marks:
        return '\n'.join(lines[-30:])
    shown = []
    for index in marks[:3]:
        shown += lines[index:index + context] + ['...']
    return '\n'.join(shown)


def report_warnings(text, logfile, strict):
    problems = sorted(set(re.findall(
        r"LaTeX Warning: ((?:Reference|Citation) `[^']+' on page \d+ undefined)", text)))
    if RERUN.search(text):
        problems.append(f'cross-references still unsettled after {MAX_PASSES} passes')
    for problem in problems:
        warn(problem)
    if problems and strict:
        raise BuildError(f'--strict: {len(problems)} LaTeX warning(s); see {logfile}')

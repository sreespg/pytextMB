"""The public API: file_settings(), build_settings(), build(), and clean(). The command line is a
thin layer over these, so a script and the terminal build exactly the same
way."""
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .docx import build_docx
from .errors import BuildError
from .latex import build_tex
from .paths import Paths, default_output
from .pdf import build_pdf
from .settings import current
from .state import State
from .template import available as templates
from .tools import log, version

FORMATS = ('tex', 'pdf', 'docx')
DEFAULT_ENGINE = 'xelatex'


@dataclass(frozen=True)
class BuildResult:
    """Where the outputs are. A format that was not requested is None."""
    tex: Path
    pdf: Optional[Path] = None
    docx: Optional[Path] = None
    output_dir: Optional[Path] = None


def build(manuscript=None, formats=None, *, fresh=False, **overrides):
    """Build a manuscript and return where the outputs are.

    Every argument is optional: anything not given comes from
    file_settings() and build_settings().
    manuscript    the Markdown file
    formats       any of 'pdf', 'docx', 'tex', overriding the pdf and word
                  settings; the LaTeX package is always generated, since
                  both other formats are cut from it
    fresh         delete this template's output folder first (implies force)
    **overrides   any file or build setting, for this call only

    Raises BuildError, with a message saying what to fix, if a step fails.
    """
    files, chosen = current(manuscript=manuscript, **overrides)
    source = files.resolved('manuscript')
    if source is None:
        raise BuildError('No manuscript: pass it to build() or set '
                         "pytexMB.file_settings(manuscript='paper.md')")
    if formats is None:
        formats = [name for name, wanted in (('pdf', chosen.pdf), ('docx', chosen.word)) if wanted]
    elif isinstance(formats, str):
        formats = (formats,)
    unknown = set(formats) - set(FORMATS)
    if unknown:
        raise BuildError(f'Unknown format(s) {", ".join(sorted(unknown))}; '
                         f'choose from {", ".join(FORMATS)}')
    paths = Paths.create(source, files.resolved('bibliography'), files.resolved('figures'),
                         files.resolved('layouts'), chosen.template,
                         files.resolved('class_dir'), files.resolved('output_dir'))
    force = chosen.force
    if fresh:
        _remove(paths.output, source)
        force = True
    # An explicit choice wins, then the environment, then what the template
    # is made for.
    engine = (chosen.engine or os.environ.get('PANDOC_PDF_ENGINE')
              or paths.template.engine or DEFAULT_ENGINE)
    builder = _Builder(paths, engine, force, chosen.strict)
    builder.tex()
    if 'pdf' in formats:
        builder.pdf()
    if 'docx' in formats:
        builder.docx()
    return BuildResult(
        tex=paths.tex,
        pdf=paths.pdf_output if 'pdf' in formats else None,
        docx=paths.docx_output if 'docx' in formats else None,
        output_dir=paths.output)


def clean(manuscript=None, *, output_dir=None, input_dir=None):
    """Remove the output folder, holding every template's outputs: the
    output_dir setting, or build/ beside the manuscript."""
    files, _ = current(manuscript=manuscript, output_dir=output_dir, input_dir=input_dir)
    source = files.resolved('manuscript')
    if source is None:
        raise BuildError('No manuscript: pass it to clean() or set it in file_settings()')
    _remove(files.resolved('output_dir') or default_output(source), source)


def _remove(output, source):
    source = Path(source).expanduser().resolve()
    if output in [source.parent, *source.parent.parents]:
        raise BuildError(f'Refusing to delete {output}: it contains the sources')
    if output.is_dir():
        shutil.rmtree(output)
    log(f'Removed {output}')


class _Builder:
    """Builds each stale output once. Content hashes decide what is stale."""

    def __init__(self, paths, engine, force, strict):
        self.paths = paths
        self.engine = engine
        self.strict = strict
        self.state = State(paths, force)
        self.tex_done = False

    def tex(self):
        # Generating the package clears <output>/latex/, which would delete
        # the PDF just compiled there, so it happens at most once per run.
        if self.tex_done:
            return
        self.tex_done = True
        key = self.state.key('tex', version('pandoc'), version('rsvg-convert'), str(self.strict))
        if self.state.current('tex', self.paths.tex, key):
            log(f'Up to date: {self.paths.tex}')
            return
        build_tex(self.paths, self.strict)
        self.state.record('tex', key)

    def pdf(self):
        self.tex()
        key = self.state.key('pdf', self.state.recorded['tex'], self.engine, version(self.engine))
        if self.state.current('pdf', self.paths.pdf_output, key):
            log(f'Up to date: {self.paths.pdf_output}')
            return
        build_pdf(self.paths, self.engine, self.strict)
        self.state.record('pdf', key)

    def docx(self):
        self.tex()
        key = self.state.key('docx', self.state.recorded['tex'])
        if self.state.current('docx', self.paths.docx_output, key):
            log(f'Up to date: {self.paths.docx_output}')
            return
        build_docx(self.paths)
        self.state.record('docx', key)

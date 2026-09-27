"""Where a build reads from and writes to. Nothing outside the output folder
is written. Every input defaults to its place beside the manuscript and can be
pointed elsewhere."""
import os
from dataclasses import dataclass
from pathlib import Path

from .errors import BuildError
from .template import Template

def _resolve(value, default):
    return Path(value).expanduser().resolve() if value is not None else default


def default_output(source):
    return Path(source).expanduser().resolve().parent / 'build'


@dataclass(frozen=True)
class Paths:
    source: Path
    bibliography: Path
    figures: Path
    template: Template
    output: Path

    @classmethod
    def create(cls, source, bibliography=None, figures=None,
               template=None, class_dir=None, output_dir=None):
        source = Path(source).expanduser().resolve()
        if not source.is_file():
            raise BuildError(f'Manuscript not found: {source}')
        if source.suffix.lower() != '.md':
            raise BuildError(f'Manuscript must be a Markdown (.md) file: {source}')
        root = source.parent
        journal = Template.load(template, class_dir)
        paths = cls(
            source=source,
            bibliography=_resolve(bibliography, root / 'references.bib'),
            figures=_resolve(figures, root / 'figures'),
            template=journal,
            # One subfolder per template, so each journal's outputs coexist.
            output=_resolve(output_dir, default_output(source)) / journal.name,
        )
        paths.check()
        return paths

    def check(self):
        """Fail before any work starts, naming every missing input at once."""
        # The figure folder is optional: a manuscript may have no figures, and
        # compose() names any figure file that is missing.
        missing = [path for path in [self.bibliography] if not path.is_file()]
        if missing:
            raise BuildError('Missing build inputs:\n- ' + '\n- '.join(map(str, missing)))
        if self.output in [self.source.parent, *self.source.parent.parents]:
            raise BuildError(f'Output folder {self.output} would contain the sources; '
                             'choose a dedicated folder')

    @property
    def name(self): return self.source.stem
    @property
    def root(self): return self.source.parent
    @property
    def code(self): return Path(__file__).resolve().parent

    @property
    def stage(self): return self.output / '.stage'
    @property
    def latex(self): return self.output / 'latex'
    @property
    def tex(self): return self.latex / f'{self.name}.tex'
    @property
    def docx_stage(self): return self.output / 'docx-stage'
    @property
    def pdf_output(self): return self.output / f'{self.name}.pdf'
    @property
    def docx_output(self): return self.output / f'{self.name}.docx'
    @property
    def state(self): return self.output / '.build-state.json'

    def label(self, path):
        """A path as it reads best in the freshness key: relative to the
        manuscript's folder where possible, so moving the project whole does
        not look like a change."""
        return os.path.relpath(path, self.root)

    def inputs(self):
        """Every file whose content can change an output. The build code and
        the template are included, so editing either rebuilds without --force."""
        files = [self.source, self.bibliography, *self.template.inputs()]
        files += [path for path in self.figures.rglob('*') if path.is_file()]
        files += [path for path in self.code.glob('*.py')] + [self.code / 'docx_front.tex']
        return sorted(set(files))

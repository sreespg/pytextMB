"""Where a build reads from and writes to. Nothing outside the output folder
is written. Everything is worked out from the manuscript: the references from
its YAML header or the .bib beside it, the figures from its image lines, and
the journal from its header. Any of these can be pointed elsewhere."""
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional

from .compose import FIGURE, citation_keys
from .errors import BuildError
from .template import Template
from .tools import require, run

HEADER = Path(__file__).resolve().parent / 'header.plain'


def _resolve(value, default):
    return Path(value).expanduser().resolve() if value is not None else default


def default_output(source):
    return Path(source).expanduser().resolve().parent / 'build'


def find_manuscript(start):
    """manuscript.md in `start` or a folder above it, or else the only
    Markdown file in `start`."""
    start = Path(start).expanduser().resolve()
    for folder in [start, *start.parents]:
        if (folder / 'manuscript.md').is_file():
            return folder / 'manuscript.md'
    candidates = sorted(path for path in start.glob('*.md')
                        if not path.name.upper().startswith('README'))
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        raise BuildError(f'Several Markdown files in {start} ('
                         + ', '.join(path.name for path in candidates)
                         + '); name the manuscript')
    raise BuildError(f'No Markdown manuscript in {start}; name the .md file')


def read_header(source):
    """The YAML header entries pytexMB uses: `bibliography` (one file or a
    list), `template`, and `after-build`. Pandoc reads the header, so any
    YAML it accepts works; without smart punctuation, `--flag` stays as
    written."""
    require('pandoc')
    text = run(['pandoc', str(source), '--from=markdown-smart', '--to=plain', '--wrap=none',
                f'--template={HEADER}'],
               what='pandoc (reading the YAML header)').stdout
    header = {'bibliography': [], 'template': None, 'after-build': None}
    for line in text.splitlines():
        key, _, value = line.partition('=')
        if key == 'bibliography' and value.strip():
            header['bibliography'].append(value.strip())
        elif key in ('template', 'after-build') and value.strip():
            header[key] = value.strip()
    return header


def find_bibliographies(root, chosen, header):
    """The bibliography setting, else the header's, else references.bib
    beside the manuscript, else the only .bib there. None at all is fine for
    a manuscript that cites nothing."""
    if chosen is not None:
        return [Path(chosen).expanduser().resolve()]
    if header:
        return [(root / Path(name).expanduser()).resolve() for name in header]
    if (root / 'references.bib').is_file():
        return [root / 'references.bib']
    found = sorted(root.glob('*.bib'))
    return found if len(found) == 1 else []


@dataclass(frozen=True)
class Paths:
    source: Path
    bibliographies: tuple        # may be empty when nothing is cited
    figures: tuple               # (path as written in the Markdown, file)
    template: Template
    output: Path
    after_build: Optional[str] = None  # the header's command to run after a build

    @classmethod
    def create(cls, source, bibliography=None, template=None, class_dir=None, output_dir=None):
        source = Path(source).expanduser().resolve()
        if not source.is_file():
            raise BuildError(f'Manuscript not found: {source}')
        if source.suffix.lower() != '.md':
            raise BuildError(f'Manuscript must be a Markdown (.md) file: {source}')
        root = source.parent
        header = read_header(source)
        # An explicit choice wins over the header, which wins over the default.
        journal = Template.load(template or header['template'], class_dir)
        text = source.read_text(encoding='utf-8')
        paths = cls(
            source=source,
            bibliographies=tuple(find_bibliographies(root, bibliography, header['bibliography'])),
            figures=tuple((match.group(2), (root / match.group(2)).resolve())
                          for match in FIGURE.finditer(text)),
            template=journal,
            # One subfolder per template, so each journal's outputs coexist.
            output=_resolve(output_dir, default_output(source)) / journal.name,
            after_build=header['after-build'],
        )
        paths.check(citation_keys(text))
        return paths

    def check(self, cited):
        """Fail before any work starts, naming every problem at once."""
        problems = [f'Not found: {path}' for path in self.bibliographies if not path.is_file()]
        problems += [f'Figure not found: {asset}' for asset, path in self.figures
                     if not path.is_file()]
        assets = [asset for asset, _ in self.figures]
        problems += [f'Figure used twice: {asset}'
                     for asset in sorted({asset for asset in assets if assets.count(asset) > 1})]
        # Every figure lands in the package's figures/ folder under its own name.
        names = {}
        for _, path in self.figures:
            names.setdefault(path.name, set()).add(path)
        problems += [f'Two figures are both named {name}; rename one'
                     for name, files in sorted(names.items()) if len(files) > 1]
        bibs = [path.name for path in self.bibliographies]
        problems += [f'Two bibliographies are both named {name}; rename one'
                     for name in sorted({name for name in bibs if bibs.count(name) > 1})]
        if cited and not self.bibliographies:
            problems.append(
                'The manuscript cites ' + ', '.join('@' + key for key in cited[:5])
                + (' ...' if len(cited) > 5 else '') + ' but no bibliography was found: put '
                'references.bib beside it, or add "bibliography: your.bib" to its YAML header')
        if problems:
            raise BuildError('Cannot build:\n- ' + '\n- '.join(problems))
        if self.output in [self.source.parent, *self.source.parent.parents]:
            raise BuildError(f'Output folder {self.output} would contain the sources; '
                             'choose a dedicated folder')

    @staticmethod
    def staged(asset):
        """Where a figure sits inside the LaTeX package."""
        return 'figures/' + PurePosixPath(asset).name

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
    def docx_stage(self): return self.output / '.docx-stage'
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
        files = [self.source, *self.bibliographies, *self.template.inputs()]
        files += [path for _, path in self.figures]
        files += [path for path in self.code.glob('*.py')]
        files += [self.code / 'docx_front.tex', HEADER]
        return sorted(set(files))

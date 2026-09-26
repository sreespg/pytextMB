"""Settings kept between calls, in two groups, so a script states its
choices once:

    import pytexMB

    pytexMB.file_settings(input_dir='~/papers/review', manuscript='paper.md',
                          bibliography='refs/library.bib', output_dir='~/out')
    pytexMB.build_settings(template='iet-rpg', word=False)
    pytexMB.build()                  # uses both
    pytexMB.build(word=True)         # one call may override any setting

File settings say where things are; build settings say what to make."""
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Optional

from .errors import BuildError


def _show(value):
    return '(default)' if value is None else value


class _Group:
    """Shared behaviour of the two settings groups."""

    def __str__(self):
        width = max(len(item.name) for item in fields(self))
        return '\n'.join(f'{item.name:<{width}}  {_show(getattr(self, item.name))}'
                         for item in fields(self))

    def updated(self, **changes):
        """A copy with `changes` applied; None leaves a setting as it is."""
        unknown = sorted(set(changes) - set(names(type(self))))
        if unknown:
            raise BuildError(f'Unknown {self.kind} setting(s) {", ".join(unknown)}; '
                             f'available: {", ".join(names(type(self)))}')
        return replace(self, **{name: self.check(name, value)
                                for name, value in changes.items() if value is not None})


@dataclass(frozen=True)
class FileSettings(_Group):
    """Where things are. Relative paths are taken relative to input_dir, or
    to the current folder when input_dir is not set. None means the default
    beside the manuscript."""
    input_dir: Optional[Path] = None     # base folder for the relative paths below
    manuscript: Optional[Path] = None    # the Markdown file
    bibliography: Optional[Path] = None  # default: references.bib beside the manuscript
    figures: Optional[Path] = None       # default: figures/ beside the manuscript
    layouts: Optional[Path] = None       # default: asset/templates/latex-blocks.md
    class_dir: Optional[Path] = None     # a template's unshipped class files
    output_dir: Optional[Path] = None    # default: build/ beside the manuscript;
                                         # each template writes to a subfolder
    kind = 'file'

    def check(self, name, value):
        path = Path(value).expanduser()
        # input_dir is fixed when set, so changing folder later cannot move it.
        return path.resolve() if name == 'input_dir' else path

    def resolved(self, name):
        """A path setting made absolute against input_dir (or the current
        folder), or None when it is not set."""
        value = getattr(self, name)
        if value is None:
            return None
        return ((self.input_dir or Path.cwd()) / value).resolve()


@dataclass(frozen=True)
class BuildSettings(_Group):
    """What to make and how."""
    template: Optional[str] = None       # name or folder; default 'applied-energy'
    pdf: bool = True                     # build the PDF
    word: bool = True                    # build the Word copy
    engine: Optional[str] = None         # default: $PANDOC_PDF_ENGINE or xelatex
    strict: bool = False                 # fail on missing citations or references
    force: bool = False                  # rebuild even when outputs are current
    kind = 'build'

    def check(self, name, value):
        if name in ('pdf', 'word', 'strict', 'force') and not isinstance(value, bool):
            raise BuildError(f'Build setting {name} must be True or False, not {value!r}')
        return str(value) if name in ('template', 'engine') else value


def names(group):
    return [item.name for item in fields(group)]


_files = FileSettings()
_build = BuildSettings()


def file_settings(**changes):
    """Set where things are and return all file settings; with no
    arguments, only return them. Settings not named keep their value."""
    global _files
    _files = _files.updated(**changes)
    return _files


def build_settings(**changes):
    """Set what to build and return all build settings; with no arguments,
    only return them. Settings not named keep their value."""
    global _build
    _build = _build.updated(**changes)
    return _build


def reset_settings():
    """Put both groups back to their defaults."""
    global _files, _build
    _files, _build = FileSettings(), BuildSettings()


def current(**overrides):
    """Both groups with one call's overrides applied, each override sent to
    the group that owns it."""
    unknown = sorted(set(overrides) - set(names(FileSettings)) - set(names(BuildSettings)))
    if unknown:
        raise BuildError(f'Unknown setting(s) {", ".join(unknown)}; file settings: '
                         f'{", ".join(names(FileSettings))}; build settings: '
                         f'{", ".join(names(BuildSettings))}')
    files = _files.updated(**{key: value for key, value in overrides.items()
                              if key in names(FileSettings)})
    build = _build.updated(**{key: value for key, value in overrides.items()
                              if key in names(BuildSettings)})
    return files, build

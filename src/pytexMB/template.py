"""Journal templates. Each is a folder holding template.json, a Pandoc LaTeX
template, a CSL style, and any class files it may ship. Built-in templates
live in templates/ beside this file; any folder laid out the same way works
too. A template may also need files that cannot be shipped (a publisher's
proprietary class); template.json's "external" entry says which files and
where to look for them."""
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .errors import BuildError

BUILTIN = Path(__file__).resolve().parent / 'templates'
DEFAULT = 'applied-energy'
# Every template marks where the manuscript body starts and ends, so the Word
# copy can take the body without any journal-specific LaTeX.
BODY_START = '% pytexMB:body-start'
BODY_END = '% pytexMB:body-end'
# Where external files are looked for when no folder is given.
USER_DATA = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'pytexMB'


def available():
    """Built-in template names and titles."""
    return {folder.name: json.loads((folder / 'template.json').read_text(encoding='utf-8'))['title']
            for folder in sorted(BUILTIN.iterdir()) if (folder / 'template.json').is_file()}


def manifest(name):
    """A built-in template's template.json."""
    if name not in available():
        raise BuildError(f'Unknown template {name!r}; built-in templates: ' + ', '.join(available()))
    return json.loads((BUILTIN / name / 'template.json').read_text(encoding='utf-8'))


@dataclass(frozen=True)
class Template:
    name: str
    title: str
    folder: Path
    latex: Path
    csl: Path
    files: tuple                 # (source, path inside the LaTeX package)
    external: tuple              # the same, for files the template cannot ship
    engine: Optional[str] = None # the LaTeX engine the template is made for
    pandoc_args: tuple = ()      # extra Pandoc options, e.g. chapter headings

    @classmethod
    def load(cls, spec=None, class_dir=None):
        """`spec` is a built-in template name or a template folder."""
        spec = spec or DEFAULT
        folder = BUILTIN / spec if (BUILTIN / spec / 'template.json').is_file() else Path(spec).expanduser().resolve()
        manifest_path = folder / 'template.json'
        if not manifest_path.is_file():
            raise BuildError(f'Unknown template {spec!r}; built-in templates: '
                             + ', '.join(available()) + ' (or give a folder with template.json)')
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        except ValueError as error:
            raise BuildError(f'{manifest_path} is not valid JSON: {error}') from None
        try:
            template = cls(
                name=folder.name,
                title=manifest.get('title', folder.name),
                folder=folder,
                latex=folder / manifest['latex'],
                csl=folder / manifest['csl'],
                files=tuple((folder / name, Path(name)) for name in manifest.get('files', [])),
                external=tuple(_external(manifest['external'], class_dir, folder.name))
                if manifest.get('external') else (),
                engine=manifest.get('engine'),
                pandoc_args=tuple(manifest.get('pandoc_args', [])))
        except KeyError as error:
            raise BuildError(f'{manifest_path} is missing the {error} entry') from None
        missing = [path for path in [template.latex, template.csl,
                                     *(source for source, _ in template.files)]
                   if not path.is_file()]
        if missing:
            raise BuildError(f'Template {template.name} is incomplete; missing:\n- '
                             + '\n- '.join(map(str, missing)))
        latex = template.latex.read_text(encoding='utf-8')
        if not (BODY_START in latex and BODY_END in latex):
            raise BuildError(f'{template.latex} must put "{BODY_START}" and "{BODY_END}" '
                             'lines around $body$, so the Word copy can find the manuscript')
        return template

    @property
    def support_files(self):
        """(source, path inside the LaTeX package) for every file copied
        beside the .tex so the package compiles alone."""
        return [*self.files, *self.external]

    def inputs(self):
        return ([path for path in self.folder.rglob('*') if path.is_file()]
                + [source for source, _ in self.external])


def _external(entry, class_dir, template):
    """Find the files a template cannot ship, in the first folder that has
    all of entry["files"]: class_dir, then $<env>, then the user data folder.
    Normally just those files are used. With "copy": "folder", the whole
    folder is (an unpacked project, say), keeping its layout and leaving out
    entry["exclude"]; "files" then only lists what must be present."""
    candidates = [Path(class_dir).expanduser()] if class_dir else []
    if os.environ.get(entry['env']):
        candidates.append(Path(os.environ[entry['env']]).expanduser())
    default = USER_DATA / entry['folder']
    candidates.append(default)
    for folder in candidates:
        if all((folder / name).is_file() for name in entry['files']):
            folder = folder.resolve()
            if entry.get('copy') != 'folder':
                return [(folder / name, Path(name)) for name in entry['files']]
            excluded = set(entry.get('exclude', []))
            return [(path, path.relative_to(folder)) for path in sorted(folder.rglob('*'))
                    if path.is_file() and not excluded & {part for part in
                                                          path.relative_to(folder).parts}]
    checked = '\n'.join(f'  {folder}' for folder in candidates)
    raise BuildError(
        f'{entry["name"]} not found. Needed: {", ".join(entry["files"])}\n'
        f'Looked in:\n{checked}\n'
        f'Run `pytexMB install-files {template} <the download, .zip or folder>`, '
        f'or pass class_dir= (--class-dir), or set {entry["env"]}.\n'
        f'{entry["instructions"]}')

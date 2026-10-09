"""Setting up a machine: check() reports which programs, fonts, and template
files a build can find, and install_files() puts a template's unshipped files
(Wiley's class, UiA's thesis project) where every build looks for them, from
the folder or .zip the publisher's site downloads."""
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .api import DEFAULT_ENGINE
from .errors import BuildError
from .template import USER_DATA, Template, available, manifest
from .tools import log, version


@dataclass(frozen=True)
class Item:
    """One line of the check: what, whether it is usable, and the detail."""
    name: str
    ok: bool
    detail: str


def check():
    """What a build can use on this machine, one Item per program and
    built-in template. A template is ready when its engine and any unshipped
    files are found."""
    items = [_pandoc(), _program('rsvg-convert', 'not found; needed for SVG figures '
                                                '(Debian/Ubuntu: librsvg2-bin)')]
    engines = sorted({manifest(name).get('engine') or DEFAULT_ENGINE for name in available()})
    items += [_program(engine, 'not found; install TeX Live or MiKTeX') for engine in engines]
    installed = _font_families()
    for name in available():
        items.append(_template(name, installed))
    return items


def _pandoc():
    if not shutil.which('pandoc'):
        return Item('pandoc', False, 'not found; install Pandoc 3: https://pandoc.org/installing.html')
    found = version('pandoc')
    major = re.search(r'(\d+)\.', found)
    if not major or int(major.group(1)) < 3:
        return Item('pandoc', False, f'{found}; pytexMB needs Pandoc 3 or newer')
    return Item('pandoc', True, found)


def _program(command, missing):
    found = shutil.which(command)
    return Item(command, bool(found), version(command) if found else missing)


def _template(name, installed):
    entry = manifest(name)
    engine = entry.get('engine') or DEFAULT_ENGINE
    if not shutil.which(engine):
        return Item(name, False, f'needs {engine}')
    try:
        Template.load(name)
    except BuildError:
        return Item(name, False, f'needs the {entry["external"]["name"]}: run '
                                 f'`pytexMB install-files {name} <download.zip or folder>`')
    fonts = [font for font in entry.get('fonts', []) if installed is not None
             and font.lower() not in installed]
    if fonts:
        return Item(name, True, 'ready; fonts ' + ', '.join(fonts)
                    + ' not installed, so substitutes are used')
    return Item(name, True, 'ready')


def _font_families():
    """Lower-cased font family names fontconfig knows, or None when
    fc-list is not available to ask."""
    try:
        result = subprocess.run(['fc-list', ':', 'family'], capture_output=True, text=True)
    except OSError:
        return None
    return {family.strip().lower() for line in result.stdout.splitlines()
            for family in line.split(',')}


def install_files(template, source):
    """Copy a template's unshipped files from `source`, a folder or a .zip
    as downloaded from the publisher or Overleaf, into the folder every
    build looks in. The files may sit anywhere inside `source`. Returns
    that folder."""
    entry = manifest(template).get('external')
    if not entry:
        raise BuildError(f'Template {template} needs no extra files')
    source = Path(source).expanduser().resolve()
    if not source.exists():
        raise BuildError(f'Not found: {source}')
    target = USER_DATA / entry['folder']
    with tempfile.TemporaryDirectory() as unpacked:
        if source.is_file():
            if not zipfile.is_zipfile(source):
                raise BuildError(f'{source} is neither a folder nor a .zip file')
            with zipfile.ZipFile(source) as archive:
                # extractall() keeps every member inside `unpacked`.
                archive.extractall(unpacked)
            source = Path(unpacked)
        folder = _containing(source, entry['files'])
        if folder is None:
            raise BuildError(f'{source} does not contain all of: ' + ', '.join(entry['files'])
                             + f'\n{entry["instructions"]}')
        if target.exists():
            shutil.rmtree(target)
        if entry.get('copy') == 'folder':
            shutil.copytree(folder, target)
        else:
            target.mkdir(parents=True)
            for name in entry['files']:
                shutil.copy2(folder / name, target / name)
    log(f'Installed the {entry["name"]} for {template} into {target}')
    return target


def _containing(root, files):
    """The shallowest folder under `root` holding every one of `files`.
    Folders that cannot be read are skipped."""
    def holds(folder):
        try:
            return all((folder / name).is_file() for name in files)
        except OSError:
            return False
    folders = [Path(folder) for folder, _, _ in os.walk(root)]
    found = [folder for folder in folders if holds(folder)]
    return min(found, key=lambda folder: len(folder.parts)) if found else None

import shutil
from pathlib import Path

import pytest

import pytexMB

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'minimal'

needs_pandoc = pytest.mark.skipif(shutil.which('pandoc') is None, reason='Pandoc not installed')
needs_latex = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ('pandoc', 'xelatex', 'rsvg-convert')),
    reason='Pandoc, XeLaTeX, or rsvg-convert not installed')

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
       '<rect width="200" height="100" fill="#4a8"/></svg>\n')
BIB = '@article{smith, title={A title}, author={Smith, J}, journal={J}, year={2020}}\n'


@pytest.fixture(autouse=True)
def fresh_settings():
    """Settings are module state; no test sees another's."""
    pytexMB.reset_settings()
    yield
    pytexMB.reset_settings()


@pytest.fixture
def example(tmp_path):
    """A copy of examples/minimal, so builds never write into the repository."""
    folder = tmp_path / 'minimal'
    shutil.copytree(EXAMPLE, folder)
    return folder


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def manuscript(folder, body='Text.\n', name='paper.md', **header):
    lines = ['---', 'title: "T"', 'author: "A"']
    lines += [f"{key.replace('_', '-')}: {value}" for key, value in header.items()]
    return write(folder / name, '\n'.join(lines + ['---', '', body]))

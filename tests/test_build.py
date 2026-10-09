import logging
import zipfile

import pytest

import pytexMB
from pytexMB.cli import main

from conftest import BIB, SVG, manuscript, needs_latex, write


@needs_latex
def test_example_builds_with_no_settings(example, monkeypatch, caplog):
    monkeypatch.chdir(example)
    result = pytexMB.build()
    assert result.pdf.is_file() and result.docx.is_file() and result.tex.is_file()
    assert result.output_dir == example / 'build' / 'applied-energy'
    caplog.set_level(logging.INFO, logger='pytexMB')
    pytexMB.build()
    assert sum('Up to date' in message for message in caplog.messages) == 3


@needs_latex
def test_figures_anywhere_and_header_bibliography(tmp_path):
    write(tmp_path / 'shared' / 'lib.bib', BIB)
    write(tmp_path / 'paper' / 'img' / 'plot.svg', SVG)
    source = manuscript(tmp_path / 'paper',
                        'As shown [@smith].\n\n![A plot.](img/plot.svg){#fig:p width=half}\n',
                        bibliography='../shared/lib.bib')
    result = pytexMB.build(source, strict=True)
    assert (result.output_dir / 'latex' / 'figures' / 'plot.pdf').is_file()
    assert 'Smith' in result.tex.read_text(encoding='utf-8')
    with zipfile.ZipFile(result.docx) as docx:
        assert any(name.startswith('word/media/') for name in docx.namelist())


@needs_latex
def test_cli_tex_only_then_clean(example, monkeypatch):
    monkeypatch.chdir(example)
    assert main(['tex', '-q']) == 0
    output = example / 'build' / 'applied-energy'
    assert (output / 'latex' / 'note.tex').is_file() and not (output / 'note.pdf').exists()
    assert main(['clean', '-q']) == 0
    assert not (example / 'build').exists()


@needs_latex
def test_after_build_command_learns_what_was_built(tmp_path):
    write(tmp_path / 'scripts' / 'supplements.py',
          'import os, sys, pathlib\n'
          'pathlib.Path("seen.txt").write_text(" ".join(sys.argv[1:]) + "\\n"\n'
          '    + os.environ["PYTEXMB_TEX"] + "\\n" + os.environ["PYTEXMB_PDF"] + "|")\n')
    source = manuscript(tmp_path, after_build='"python scripts/supplements.py --fast data_1"')
    result = pytexMB.build(source, formats='tex')
    flags, tex, pdf = (tmp_path / 'seen.txt').read_text().split('\n')
    assert flags == '--fast data_1'
    assert tex == str(result.tex) and pdf == '|'


@needs_latex
def test_failing_after_build_command_fails_the_build(tmp_path):
    source = manuscript(tmp_path, after_build='"python -c \'raise SystemExit(3)\'"')
    with pytest.raises(pytexMB.BuildError, match='exit 3'):
        pytexMB.build(source, formats='tex')
    assert main(['tex', '-q', '--no-after-build', str(source)]) == 0


@needs_latex
def test_cli_leaves_unflagged_settings_alone(example, monkeypatch):
    monkeypatch.chdir(example)
    pytexMB.build_settings(pdf=False, word=False)
    assert main(['-q']) == 0
    output = example / 'build' / 'applied-energy'
    assert (output / 'latex' / 'note.tex').is_file()
    assert not (output / 'note.pdf').exists() and not (output / 'note.docx').exists()


def script(folder, body):
    return write(folder / 'build.py', 'import pytexMB\n\npytexMB.run(' + body + ')\n')


def run_script(path, *argv):
    import subprocess
    import sys
    # From another folder, as a user might run it.
    return subprocess.run([sys.executable, str(path), *argv], cwd=path.parent.parent,
                          capture_output=True, text=True)


def test_run_script_help_shows_its_settings(tmp_path):
    result = run_script(script(tmp_path / 'p', "manuscript='paper.md', word=False"), '-h')
    assert result.returncode == 0
    assert result.stdout.startswith('usage: build.py')
    assert "manuscript = 'paper.md'" in result.stdout and 'word = False' in result.stdout


def test_run_script_rejects_unknown_settings(tmp_path):
    result = run_script(script(tmp_path / 'p', "manuscript='paper.md', output='x'"))
    assert result.returncode == 1 and 'Unknown setting(s) output' in result.stderr


@needs_latex
def test_run_script_builds_beside_itself(example):
    path = script(example, "manuscript='note.md', word=False")
    assert run_script(path).returncode == 0
    output = example / 'build' / 'applied-energy'
    assert (output / 'note.pdf').is_file() and not (output / 'note.docx').exists()
    assert run_script(path, 'docx', '-q').returncode == 0
    assert (output / 'note.docx').is_file()

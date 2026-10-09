import zipfile

import pytest

import pytexMB
from pytexMB import BuildError, environment, template
from pytexMB.cli import main

WILEY = ['WileyNJDv5.cls', 'NJDnatbib.sty', 'NJDapacite.sty', 'LETTERSP.STY']


@pytest.fixture
def user_data(tmp_path, monkeypatch):
    folder = tmp_path / 'data'
    monkeypatch.setattr(template, 'USER_DATA', folder)
    monkeypatch.setattr(environment, 'USER_DATA', folder)
    return folder


def test_install_from_a_zip_with_files_nested(tmp_path, user_data):
    archive = tmp_path / 'wiley.zip'
    with zipfile.ZipFile(archive, 'w') as zip_file:
        for name in WILEY:
            zip_file.writestr(f'njd-v5/latex/{name}', '% stub\n')
        zip_file.writestr('njd-v5/sample.tex', '')
    target = pytexMB.install_files('iet-rpg', archive)
    assert sorted(path.name for path in target.iterdir()) == sorted(WILEY)
    assert template.Template.load('iet-rpg').external


def test_install_a_whole_project_folder(tmp_path, user_data):
    project = tmp_path / 'download' / 'thesis'
    for name in ['header/header.tex', 'header/information.tex', 'header/math.tex', 'thesis.tex']:
        (project / name).parent.mkdir(parents=True, exist_ok=True)
        (project / name).write_text('', encoding='utf-8')
    target = pytexMB.install_files('uia-phd', tmp_path / 'download')
    assert (target / 'header' / 'information.tex').is_file()


def test_install_refuses_what_it_cannot_use(tmp_path, user_data):
    with pytest.raises(BuildError, match='needs no extra files'):
        pytexMB.install_files('applied-energy', tmp_path)
    with pytest.raises(BuildError, match='does not contain'):
        pytexMB.install_files('iet-rpg', tmp_path)
    with pytest.raises(BuildError, match='Unknown template'):
        pytexMB.install_files('nature', tmp_path)


def test_check_lists_programs_and_templates(user_data):
    names = [item.name for item in pytexMB.check()]
    assert names[:2] == ['pandoc', 'rsvg-convert']
    assert set(pytexMB.templates()) <= set(names)


def test_cli_setup_commands(capsys, user_data):
    assert main(['install-files', 'iet-rpg']) == 1
    assert 'usage' in capsys.readouterr().err
    main(['check'])
    assert 'applied-energy' in capsys.readouterr().out


def test_cli_flags_in_any_order():
    from pytexMB.cli import parse
    for argv in (['pdf', '-f', 'paper.md', '-t', 'iet-rpg'], ['-f', 'paper.md', 'pdf', '-t', 'iet-rpg']):
        command, source, args = parse(argv)
        assert (command, source, args.force, args.template) == ('pdf', 'paper.md', True, 'iet-rpg')

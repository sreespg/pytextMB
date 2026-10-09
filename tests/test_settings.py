import pytest

import pytexMB
from pytexMB import BuildError
from pytexMB.settings import current


def test_settings_persist_and_reset():
    pytexMB.build_settings(template='iet-rpg', word=False)
    assert pytexMB.build_settings().template == 'iet-rpg'
    assert pytexMB.build_settings().word is False
    pytexMB.reset_settings()
    assert pytexMB.build_settings().template is None


def test_one_call_override_does_not_stick():
    pytexMB.build_settings(template='iet-rpg')
    files, build = current(template='uia-phd', output_dir='out')
    assert build.template == 'uia-phd' and files.output_dir.name == 'out'
    assert pytexMB.build_settings().template == 'iet-rpg'


def test_relative_paths_start_at_input_dir(tmp_path):
    pytexMB.file_settings(input_dir=tmp_path, manuscript='paper.md')
    assert pytexMB.file_settings().resolved('manuscript') == tmp_path / 'paper.md'


def test_unknown_and_invalid_settings():
    with pytest.raises(BuildError, match='figures'):
        current(figures='img')
    with pytest.raises(BuildError, match='True or False'):
        pytexMB.build_settings(pdf='yes')

import pytest

import pytexMB
from pytexMB import BuildError
from pytexMB.paths import Paths, find_bibliographies, find_manuscript

from conftest import BIB, SVG, manuscript, needs_pandoc, write


def test_manuscript_md_in_a_folder_above(tmp_path):
    write(tmp_path / 'manuscript.md', 'x')
    (tmp_path / 'sub').mkdir()
    assert find_manuscript(tmp_path / 'sub') == tmp_path / 'manuscript.md'


def test_only_markdown_file_ignoring_readme(tmp_path):
    write(tmp_path / 'draft.md', 'x')
    write(tmp_path / 'README.md', 'x')
    assert find_manuscript(tmp_path) == tmp_path / 'draft.md'


def test_several_or_no_markdown_files(tmp_path):
    with pytest.raises(BuildError, match='No Markdown'):
        find_manuscript(tmp_path)
    write(tmp_path / 'a.md', 'x')
    write(tmp_path / 'b.md', 'x')
    with pytest.raises(BuildError, match='a.md, b.md'):
        find_manuscript(tmp_path)


def test_bibliography_order(tmp_path):
    chosen = tmp_path / 'chosen.bib'
    assert find_bibliographies(tmp_path, chosen, ['h.bib']) == [chosen]
    assert find_bibliographies(tmp_path, None, ['../h.bib']) == [(tmp_path.parent / 'h.bib')]
    assert find_bibliographies(tmp_path, None, []) == []
    write(tmp_path / 'only.bib', BIB)
    assert find_bibliographies(tmp_path, None, []) == [tmp_path / 'only.bib']
    write(tmp_path / 'other.bib', BIB)
    assert find_bibliographies(tmp_path, None, []) == []
    write(tmp_path / 'references.bib', BIB)
    assert find_bibliographies(tmp_path, None, []) == [tmp_path / 'references.bib']


@needs_pandoc
def test_header_names_journal_bibliographies_and_figures(tmp_path):
    write(tmp_path / 'refs' / 'a.bib', BIB)
    write(tmp_path / 'refs' / 'b.bib', BIB.replace('smith', 'jones'))
    write(tmp_path / 'img' / 'plot.svg', SVG)
    source = manuscript(tmp_path, '![Cap.](img/plot.svg){#fig:p}\n',
                        template='uia-phd', bibliography='[refs/a.bib, refs/b.bib]')
    with pytest.raises(BuildError, match='UiA thesis project files'):
        Paths.create(source)        # the header's template was chosen
    paths = Paths.create(source, template='applied-energy')
    assert [path.name for path in paths.bibliographies] == ['a.bib', 'b.bib']
    assert paths.figures == (('img/plot.svg', tmp_path / 'img' / 'plot.svg'),)
    assert paths.staged('img/plot.svg') == 'figures/plot.svg'
    assert paths.output == tmp_path / 'build' / 'applied-energy'


@needs_pandoc
def test_no_bibliography_needed_without_citations(tmp_path):
    assert Paths.create(manuscript(tmp_path)).bibliographies == ()


@needs_pandoc
def test_every_problem_reported_at_once(tmp_path):
    write(tmp_path / 'a' / 'plot.svg', SVG)
    write(tmp_path / 'b' / 'plot.svg', SVG)
    source = manuscript(tmp_path, 'See [@smith].\n\n'
                        '![A.](a/plot.svg){#fig:a}\n\n![B.](b/plot.svg){#fig:b}\n\n'
                        '![C.](missing.svg){#fig:c}\n')
    with pytest.raises(BuildError) as error:
        Paths.create(source)
    message = str(error.value)
    assert 'Figure not found: missing.svg' in message
    assert 'both named plot.svg' in message
    assert 'cites @smith but no bibliography' in message


def test_clean_never_deletes_the_sources(tmp_path):
    source = manuscript(tmp_path / 'sub')
    with pytest.raises(BuildError, match='Refusing to delete'):
        pytexMB.clean(source, output_dir=tmp_path)
    assert source.is_file()

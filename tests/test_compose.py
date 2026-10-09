import pytest

from pytexMB import BuildError
from pytexMB.compose import citation_keys, compose, figure


def test_citation_keys_in_order_without_duplicates_or_emails():
    text = 'See [@b; @a] and [@b]. Write to name@example.org.'
    assert citation_keys(text) == ['b', 'a']


def test_figure_widths():
    full = figure('Cap.', 'figures/p.svg', '#fig:p width=full')
    half = figure('Cap.', 'figures/p.svg', '#fig:p width=half')
    assert '\\begin{figure*}' in full and '\\textwidth' in full
    assert '\\begin{figure}' in half and '\\linewidth' in half
    assert 'figures/p.pdf' in full and '\\label{fig:p}' in full


def test_tikz_figure_is_input():
    assert '\\input{figures/p.tex}' in figure('Cap.', 'figures/p.tex', '#fig:p')


def test_figure_needs_identifier_and_known_width():
    with pytest.raises(BuildError, match='identifier'):
        figure('Cap.', 'p.svg', 'width=full')
    with pytest.raises(BuildError, match='width'):
        figure('Cap.', 'p.svg', '#fig:p width=third')


def test_compose_moves_figures_and_cites_caption_keys(tmp_path):
    path = tmp_path / 'm.md'
    path.write_text('![Cap [@k].](img/plot.svg){#fig:p}\n', encoding='utf-8')
    compose(path, lambda asset: 'figures/' + asset.split('/')[-1])
    text = path.read_text(encoding='utf-8')
    assert '\\includegraphics[width=\\textwidth]{figures/plot.pdf}' in text
    assert '[@k]\n```{=latex}\n\\fi' in text


def test_compose_without_citations_adds_no_hidden_block(tmp_path):
    path = tmp_path / 'm.md'
    path.write_text('Plain text.\n', encoding='utf-8')
    compose(path, str)
    assert '\\iffalse' not in path.read_text(encoding='utf-8')

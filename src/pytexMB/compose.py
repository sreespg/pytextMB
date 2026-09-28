"""Write each Markdown figure as its PDF figure environment. The Markdown line
holds everything the layout needs: caption, figure path, label, and column
width, as in

    ![Caption.](figures/name.svg){#fig:name width=full}

width=full spans both columns and width=half fits one (default: full). An SVG
is included as the PDF that stage() converts it to; a .tex figure (TikZ) is
\\input and scaled to the same width."""
import re

from .errors import BuildError

FIGURE = re.compile(r'^!\[(.*)\]\(([^)\s]+)\)(?:\{([^}]*)\})?[ \t]*$', re.M)


def figure(caption, asset, attributes):
    identifier = re.search(r'#(fig:[^\s}]+)', attributes)
    if not identifier:
        raise BuildError(f'Figure {asset} has no identifier: add {{#fig:name}} after it')
    width = re.search(r'\bwidth=(\w+)', attributes)
    width = width.group(1) if width else 'full'
    if width not in ('full', 'half'):
        raise BuildError(f'Figure {asset}: width must be full or half, not {width}')
    environment = 'figure*' if width == 'full' else 'figure'
    length = r'\textwidth' if width == 'full' else r'\linewidth'
    if asset.endswith('.tex'):
        graphic = r'\resizebox{' + length + r'}{!}{\input{' + asset + '}}'
    else:
        graphic = r'\includegraphics[width=' + length + ']{' + re.sub(r'\.svg$', '.pdf', asset) + '}'
    return ('```{=latex}\n\\begin{' + environment + '}[t]\n\\centering\n' + graphic
            + '\n\\caption{' + caption + '}\n\\label{' + identifier.group(1) + '}\n\\end{'
            + environment + '}\n```')


def compose(path):
    source = path.read_text(encoding='utf-8')
    assets = [match.group(2) for match in FIGURE.finditer(source)]
    duplicates = sorted({asset for asset in assets if assets.count(asset) > 1})
    if duplicates:
        raise BuildError('Duplicate figure(s): ' + ', '.join(duplicates))
    missing = [asset for asset in assets if not (path.parent / asset).is_file()]
    if missing:
        raise BuildError('Figure file(s) not found: ' + ', '.join(missing))
    source = FIGURE.sub(lambda match: figure(match.group(1), match.group(2), match.group(3) or ''),
                        source)
    # Captions are raw LaTeX now, which citeproc never reads; cite every key
    # once in a hidden block so each still gets a bibliography entry, and
    # resolve_raw_latex_citations() numbers the caption citations afterwards.
    keys = list(dict.fromkeys(re.findall(r'(?<![\w.])@([A-Za-z0-9_:-]+)', source)))
    source += '\n```{=latex}\n\\iffalse\n```\n[' + '; '.join('@' + k for k in keys) + ']\n```{=latex}\n\\fi\n```\n'
    path.write_text(source, encoding='utf-8')

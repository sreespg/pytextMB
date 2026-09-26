"""Merge the PDF-only figure layouts into the staged manuscript."""
import re

from .errors import BuildError


def compose(path, layouts):
    source = path.read_text(encoding='utf-8')
    layout_text = layouts.read_text(encoding='utf-8') if layouts.is_file() else ''
    blocks = re.findall(r'<!-- latex-block:\d+ -->\n(```\{=latex\}\n.*?\n```)', layout_text, re.S)
    figures = {}
    for block in blocks:
        asset = re.search(r'\\(?:includegraphics(?:\[[^]]*\])?|input)\{([^}]+)\}', block).group(1)
        figures[re.sub(r'\.(svg|pdf)$', '', asset)] = block
    used = set()
    def set_width(block, width):
        environment = 'figure*' if width == 'full' else 'figure'
        length = r'\textwidth' if width == 'full' else r'\linewidth'
        block = re.sub(r'\\begin\{figure\*?\}', lambda _: r'\begin{' + environment + '}', block, count=1)
        if r'\includegraphics' in block:
            return re.sub(r'\\includegraphics(?:\[[^]]*\])?\{', lambda _: r'\includegraphics[width=' + length + ']{', block, count=1)
        if r'\resizebox' in block:
            return re.sub(r'\\resizebox\{[^}]+\}', lambda _: r'\resizebox{' + length + '}', block, count=1)
        return re.sub(r'(\\input\{[^}]+\})', lambda match: r'\resizebox{' + length + r'}{!}{' + match.group(1) + '}', block, count=1)
    def image(match):
        caption, asset, attributes = match.groups()
        width_match = re.search(r'\bwidth=(full|half)\b', attributes or '')
        width = width_match.group(1) if width_match else 'full'
        key = re.sub(r'\.(svg|pdf)$', '', asset)
        if key not in figures:
            raise BuildError(f'Figure layout missing for {asset}: add a latex-block for it to {layouts}')
        if key in used:
            raise BuildError(f'Duplicate figure: {asset}')
        used.add(key)
        return set_width(figures[key], width or 'full').replace('CAPTION_FROM_MANUSCRIPT', caption)
    # Pandoc image attributes may include both a stable identifier and a width,
    # for example `{#fig:methodological-aspects width=full}`. Parse the whole
    # attribute block so forced builds do not mistake every layout for unused.
    source = re.sub(r'^!\[(.*)\]\(([^)\s]+)\)(?:\{([^}]*)\})?$', image, source, flags=re.M)
    if used != figures.keys():
        raise BuildError(f'Unused figure layouts: {figures.keys() - used}')
    keys = list(dict.fromkeys(re.findall(r'@([A-Za-z0-9_:-]+)', source)))
    source += '\n```{=latex}\n\\iffalse\n```\n[' + '; '.join('@' + k for k in keys) + ']\n```{=latex}\n\\fi\n```\n'
    path.write_text(source, encoding='utf-8')

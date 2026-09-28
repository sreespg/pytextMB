"""Make the generated LaTeX readable by Pandoc and finish the Word copy."""
import os
import re
import shutil
import zipfile
from pathlib import Path

from .errors import BuildError
from .template import BODY_END, BODY_START
from .tools import convert_svgs, log, require, run

# Wide enough for a full-page figure to stay sharp when zoomed in Word.
FIGURE_PIXELS = 1800
FRONT_MATTER = Path(__file__).resolve().parent / 'docx_front.tex'


def build_docx(paths):
    """Convert the generated LaTeX to the Word review copy. Only the
    manuscript body is kept; the front matter comes from the manuscript's
    YAML, so no journal template's LaTeX reaches Word. Figures switch to PNG,
    and the print-only constructs Pandoc's LaTeX reader cannot read back are
    smoothed over first."""
    require('pandoc', 'rsvg-convert')
    log('Converting generated LaTeX to a Word review copy')
    stage = paths.docx_stage
    tex = stage / paths.tex.name
    docx = tex.with_suffix('.docx')
    shutil.rmtree(stage, ignore_errors=True)
    (stage / 'figures').mkdir(parents=True)
    front = run(['pandoc', str(paths.source), '--to=latex', f'--template={FRONT_MATTER}'],
                what='pandoc (Word front matter)').stdout
    tex.write_text(front + '\n\n' + manuscript_body(paths.tex) + '\n\\end{document}\n', encoding='utf-8')
    convert_svgs(sorted(paths.figures.rglob('*.svg')),
                 lambda svg: stage / 'figures' / (svg.stem + '.png'), ['-w', str(FIGURE_PIXELS)])
    prepare_tex(tex)
    missing = sorted(set(re.findall(r'\\includegraphics(?:\[[^]]*\])?\{(figures/[^}]+)\}',
                                    tex.read_text(encoding='utf-8')))
                     - {str(path.relative_to(stage)) for path in stage.rglob('figures/*')})
    if missing:
        raise BuildError('Word figures missing (only SVG figures are converted): ' + ', '.join(missing))
    run(['pandoc', tex.name, '--resource-path=.', f'--output={docx.name}'],
        cwd=stage, what='pandoc (LaTeX to Word)')
    styles(docx)
    os.replace(docx, paths.docx_output)
    log(f'Created {paths.docx_output}')


def manuscript_body(tex):
    """The generated manuscript between the journal template's body markers."""
    text = tex.read_text(encoding='utf-8')
    start, end = text.find(BODY_START), text.find(BODY_END)
    if start < 0 or end < start:
        raise BuildError(f'{tex} has no manuscript body between the template markers')
    return text[text.index('\n', start) + 1:end]


def prepare_tex(path):
    """Adjust the build's generated LaTeX so Pandoc's LaTeX reader can read
    back what Pandoc's own LaTeX writer (plus tables()'s print layout) put
    there, for the DOCX review copy. Left as generated, this LaTeX silently
    breaks under Pandoc: starred float captions are dropped, the \\real{}
    column-width arithmetic used for print typesetting is not parsed,
    minipage-wrapped header cells abort table parsing entirely, and the
    abbreviationsbox glossary, defined only in the journal templates, loses
    its title. Word also cannot display PDF
    images inline, so \\includegraphics targets switch to the PNG figures
    build_docx() renders alongside this file."""
    text = path.read_text(encoding='utf-8')
    # A `>{...\arraybackslash}` column prefix makes the reader swallow a
    # leading number in every cell of that column, so `12` is lost outright
    # and `2020 study` arrives as `study`. The prefix only sets print
    # alignment, which Word supplies itself.
    text = text.replace('>{\\raggedright\\arraybackslash}', '')
    text = re.sub(
        r'p\{\((\\(?:text|line)width) - \d+\\tabcolsep\) \* \\real\{([\d.]+)\}\}',
        r'p{\2\1}', text)
    text = re.sub(r'\\begin\{(table|figure)\*\}', r'\\begin{\1}', text)
    text = re.sub(r'\\end\{(table|figure)\*\}', r'\\end{\1}', text)
    text = re.sub(r'(\\includegraphics(?:\[[^]]*\])?\{figures/[^}]+)\.pdf\}', r'\1.png}', text)
    text = re.sub(
        r'\\begin\{minipage\}\[b\]\{\\linewidth\}\\raggedright\n(.*?)\n\\end\{minipage\}',
        r'\1', text, flags=re.S)
    text = re.sub(
        r'\\begin\{abbreviationsbox\}\n(.*?)\n\\end\{abbreviationsbox\}',
        lambda match: '\\textbf{Abbreviations}\\par\\smallskip\n\\footnotesize\n' + match.group(1),
        text, flags=re.S)
    text = number_docx_captions(text)
    # Citeproc splits each reference into a margin label and an inline body.
    # Pandoc reads the two back as separate blocks, so Word strands `[1]` on a
    # line of its own above its reference. Joining them restores `[1] Ye M, ...`.
    text = unwrap_command(text, 'CSLLeftMargin')
    text = unwrap_command(text, 'CSLRightInline')
    path.write_text(text, encoding='utf-8')


def unwrap_command(text, command):
    """Drop every `\\command{...}` wrapper, keeping its braced content."""
    token = '\\' + command + '{'
    pieces = []
    index = 0
    while True:
        start = text.find(token, index)
        if start < 0:
            pieces.append(text[index:])
            return ''.join(pieces)
        pieces.append(text[index:start])
        cursor = start + len(token)
        depth = 1
        while depth:
            character = text[cursor]
            if character == '\\':
                cursor += 1
            elif character == '{':
                depth += 1
            elif character == '}':
                depth -= 1
            cursor += 1
        pieces.append(text[start + len(token):cursor - 1])
        index = cursor


def number_docx_captions(text):
    """Write the float number into each caption. LaTeX supplies `Figure 1:` and
    `Table 1` from the counters, but Word gets a caption with no number at all,
    leaving the prose's `Figure 1` pointing at nothing a reader can find. The
    counters follow the order the floats appear in, which is the order Pandoc
    numbers the matching \\ref by, so the caption and the prose agree."""
    counters = {'figure': 0, 'table': 0}

    def number(match):
        environment, body = match.groups()
        counters[environment] += 1
        name = 'Figure' if environment == 'figure' else 'Table'
        body, count = re.subn(
            r'\\caption\{', '\\\\caption{' + f'{name} {counters[environment]}. ',
            body, count=1)
        if not count:
            raise BuildError(f'A {environment} reaching the DOCX has no caption to number')
        return f'\\begin{{{environment}}}{body}\\end{{{environment}}}'

    # Only the body: a template's preamble may define environments that
    # contain a float of their own.
    preamble, marker, body = text.partition('\\begin{document}')
    if not marker:
        raise BuildError('The generated LaTeX has no \\begin{document}')
    return preamble + marker + re.sub(
        r'\\begin\{(figure|table)\}(.*?)\\end\{\1\}', number, body, flags=re.S)


def styles(path):
    """Give the DOCX the print copy's table and figure presentation. None of it
    survives Pandoc: the booktabs \\toprule and \\bottomrule have no Word
    equivalent, leaving a table open at the top and bottom where Pandoc's style
    draws only the rule under the header row; the \\small setting table text a
    step below the body is dropped, so Word sets tables at full body size; and
    \\centering is lost from both floats, so tables and figures sit against the
    left margin. What can live on a style does, so later edits in Word keep it;
    table alignment cannot, because Pandoc writes it into each table."""
    # The PDF sets 9pt tables against 10pt body text; Word's body is 12pt, and
    # w:sz counts half-points, so 22 holds the same ratio.
    table_text = '<w:rPr><w:sz w:val="22" /><w:szCs w:val="22" /></w:rPr>'
    rules = ('<w:tblBorders>'
             '<w:top w:val="single" w:sz="8" w:space="0" w:color="auto"/>'
             '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="auto"/>'
             '</w:tblBorders>')
    centred = '<w:pPr><w:jc w:val="center" /></w:pPr>'

    def rule_table(style):
        if '<w:tblBorders>' in style:
            return style
        # Word requires tblBorders between tblInd and tblCellMar.
        style = anchor(style, r'<w:tblCellMar>', rules, 'cell margins')
        # The header row carries its own alignment, which would otherwise pull
        # that one row back to the left of a centred table.
        return style.replace('<w:jc w:val="left" />', '<w:jc w:val="center" />')

    def size_cells(style):
        if '<w:rPr>' in style:
            return style
        # Word requires rPr after pPr.
        return anchor(style, r'</w:pPr>', table_text, 'paragraph properties', after=True)

    def centre_figures(style):
        if '<w:jc ' in style:
            return style
        # Word requires pPr after basedOn.
        return anchor(style, r'<w:basedOn[^>]*/>', centred, 'a parent style', after=True)

    def anchor(style, pattern, addition, what, after=False):
        replacement = (r'\g<0>' + addition) if after else (addition + r'\g<0>')
        updated, count = re.subn(pattern, replacement, style, count=1)
        if not count:
            raise BuildError(f'The DOCX styles have no {what} to anchor the layout to')
        return updated

    def set_page(document):
        """Pin the page setup. Pandoc leaves the section properties empty, so
        Word falls back to whatever the local default is: US Letter on one
        machine, A4 on the next, and the review copy repaginates as it travels.
        A4 with 1in margins is the usual manuscript page; the print copy's own
        210x280mm and 18mm margins belong to its two-column layout and would
        set a single column far too wide to read."""
        if '<w:pgSz' in document:
            return document
        page = ('<w:pgSz w:w="11906" w:h="16838" />'
                '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"'
                ' w:header="708" w:footer="708" w:gutter="0" />')
        document, count = re.subn(r'<w:sectPr\s*/>', f'<w:sectPr>{page}</w:sectPr>',
                                  document, count=1)
        if not count:
            document, count = re.subn(r'<w:sectPr(?:\s[^>]*)?>', lambda match: match.group() + page,
                                      document, count=1)
        if not count:
            raise BuildError('The generated DOCX has no section properties to size')
        return document

    def centre_tables(document):
        """Centre each table itself, leaving the cell text alone. The alignment
        sits on the table, not on the style, so it has to be reached here."""
        def centre(match):
            block, count = re.subn(r'<w:jc w:val="\w+" ?/>', '<w:jc w:val="center" />',
                                   match.group(), count=1)
            if not count:
                raise BuildError('A DOCX table carries no alignment to centre')
            return block
        # A manuscript without tables has nothing to centre.
        return re.sub(r'<w:tblPr>.*?</w:tblPr>', centre, document, flags=re.S)

    edits = {'Table': rule_table, 'Compact': size_cells, 'Figure': centre_figures}
    with zipfile.ZipFile(path) as archive:
        entries = [(item, archive.read(item.filename)) for item in archive.infolist()]
    patched = set()
    temporary = path.with_suffix('.docx.new')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
        for item, content in entries:
            if item.filename == 'word/styles.xml':
                text = content.decode()
                for identifier, edit in edits.items():
                    text, count = re.subn(
                        r'<w:style [^>]*w:styleId="' + identifier + r'"[^>]*>.*?</w:style>',
                        lambda match: edit(match.group()), text, count=1, flags=re.S)
                    if not count:
                        raise BuildError(f'The generated DOCX has no {identifier} style')
                content = text.encode()
                patched.add(item.filename)
            elif item.filename == 'word/document.xml':
                content = set_page(centre_tables(content.decode())).encode()
                patched.add(item.filename)
            archive.writestr(item, content)
    missing = {'word/styles.xml', 'word/document.xml'} - patched
    if missing:
        raise BuildError(f'The generated DOCX is missing {", ".join(sorted(missing))}')
    shutil.move(temporary, path)


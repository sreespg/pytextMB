"""Replace Pandoc's longtables with the print table layout."""
import re
from math import sqrt

from .errors import BuildError


def tables(path):
    text = path.read_text(encoding='utf-8')

    def automatic_column_weights(body, count):
        """Allocate print width from the relative amount of text per column."""
        totals = [0.0] * count
        rows = [0] * count
        for row in re.split(r'\\\\\s*', body):
            cells = row.split('&')
            if len(cells) != count:
                continue
            for index, cell in enumerate(cells):
                # Citations and TeX wrappers should not make a label column appear
                # wider than prose-rich columns.
                plain = re.sub(r'\\protect\\hyperlink\{[^}]*\}\{([^}]*)\}', r'\1', cell)
                plain = re.sub(r'\\[A-Za-z@]+\*?(?:\[[^]]*\])?', '', plain)
                plain = re.sub(r'[{}\\$~^_]|\s+', ' ', plain).strip()
                totals[index] += len(plain)
                rows[index] += 1
        scores = [sqrt(total / row) if row else 1.0 for total, row in zip(totals, rows)]
        score_total = sum(scores)
        if not score_total:
            return [1 / count] * count
        # Guarantee usable label/citation columns while giving the remaining space
        # to the columns that would otherwise create most wrapped lines.
        minimum = .18 if count == 2 else (.13 if count == 3 else .10)
        available = 1 - count * minimum
        return [minimum + available * score / score_total for score in scores]

    def convert(match):
        spec, body = match.groups()
        caption = ''
        width = 'half'
        column_weights = None
        cap = re.search(r'\\caption\{.*?\\tabularnewline\s*', body, re.S)
        if cap:
            caption = cap.group().replace('\\tabularnewline', '').strip()
            marker = re.search(r'\\\{\\#(tab:[^\s}]+)([^}]*)\\\}', caption)
            if not marker:
                raise BuildError('A Markdown table caption is missing its identifier')
            attributes = marker.group(2)
            width_match = re.search(r'\bwidth=(full|half)\b', attributes)
            width = width_match.group(1) if width_match else 'full'
            columns_match = re.search(r'\bcolumns=([0-9.,]+)\b', attributes)
            column_weights = ([float(value) for value in columns_match.group(1).split(',')]
                              if columns_match else None)
            caption = caption[:marker.start()] + '\\label{' + marker.group(1) + '}' + caption[marker.end():]
            body = body[:cap.start()] + body[cap.end():]
        body = re.sub(r'\\endfirsthead.*?\\endhead\s*', '', body, flags=re.S)
        body = body.replace('\\endhead', '')
        body = re.sub(r'\\bottomrule\\noalign\{\}\s*\\endlastfoot\s*', '', body)
        body = body.replace('\\endlastfoot', '').replace('\\noalign{}', '')
        # Pandoc emits `\multirow{n}{*}{...}` for row-spanning cells, where `*`
        # sizes the box to the text's natural (unwrapped) width and lets it
        # overrun into the next column. `=` wraps it to the surrounding p{}
        # column's actual width instead.
        body = re.sub(r'\\multirow\{(\d+)\}\{\*\}', r'\\multirow{\1}{=}', body)
        if not caption:
            # The valid Markdown header is needed by Pandoc, but the framed
            # glossary already supplies its own title.
            body = re.sub(r'\\toprule.*?\\midrule\s*', '', body, count=1, flags=re.S)
            body = body.replace('\\bottomrule', '')
        # Equal, wrapping columns avoid inferring print widths from Markdown padding.
        n = len(re.findall(r'\\real\{', spec)) or len(re.findall('[lcr]', spec))
        if not n:
            raise BuildError('Cannot determine table column count')
        weights = automatic_column_weights(body, n)
        if column_weights:
            if len(column_weights) != n or any(weight <= 0 for weight in column_weights):
                raise BuildError('Table column widths must provide one positive value per column')
            total = sum(column_weights)
            weights = [weight / total for weight in column_weights]
        elif 'tab:scope-boundary' in caption:
            weights = [.18, .82]
        elif not caption:
            weights = [.16, .84]
        length = '\\textwidth' if width == 'full' else '\\linewidth'
        environment = 'table*' if width == 'full' else 'table'
        columns = ''.join('>{\\raggedright\\arraybackslash}p{(' + length + ' - ' + str(2*(n-1)) + '\\tabcolsep) * \\real{' + str(w) + '}}' for w in weights)
        closing_rule = '' if not caption else '\n\\bottomrule'
        # Result tables use a relaxed row pitch. The first-page abbreviation
        # glossary is tighter so it remains in the left column below the abstract
        # instead of jumping to the right and leaving a large blank area.
        row_pitch = '1.08' if not caption else '1.25'
        table = ('{\\renewcommand{\\arraystretch}{' + row_pitch + '}\n\\begin{tabular}{@{}' + columns + '@{}}\n'
                  + body.strip() + closing_rule + '\n\\end{tabular}}')
        if not caption:
            # The uncaptioned table immediately below the Abbreviations heading is
            # a glossary, not a numbered result table. Keep its editable Markdown
            # source; each journal template defines abbreviationsbox, which
            # frames and titles it and places it to suit that first page.
            return '\\begin{abbreviationsbox}\n' + table + '\n\\end{abbreviationsbox}'
        # \small matches the CAS-dc table environment's own default size.
        return '\\begin{' + environment + '}[tp]\n\\centering\n\\small\n' + caption + '\n' + table + '\n\\end{' + environment + '}'
    text, count = re.subn(r'\\begin\{longtable\}\[\]\{@\{\}(.*?)@\{\}\}(.*?)\\end\{longtable\}', convert, text, flags=re.S)
    if '\\begin{longtable}' in text:
        raise BuildError('An unsupported table layout remains in the generated TeX')
    # The glossary title is placed inside its framed PDF presentation. The Markdown
    # heading remains the editable source and is retained for non-PDF outputs.
    # It is a chapter when the template puts chapters at the top level.
    text = re.sub(
        r'\\hypertarget\{abbreviations\}\{%\s*'
        r'\\(?:section|chapter)\{Abbreviations\}\\label\{abbreviations\}\}\s*',
        '', text)
    path.write_text(text, encoding='utf-8')

"""Command line: `pytexMB [command] [manuscript.md] [options]`."""
import argparse
import logging
import os
import sys
from pathlib import Path

from .api import build, clean, templates
from .errors import BuildError

COMMANDS = {
    'all': ('pdf', 'docx'),
    'pdf': ('pdf',),
    'docx': ('docx',),
    'tex': ('tex',),
    'rebuild': ('pdf', 'docx'),
    'clean': (),
}

DESCRIPTION = """\
Build a manuscript's PDF, Word copy, and LaTeX package from Markdown.

commands:
  all       build the PDF and the DOCX (default)
  pdf       build the journal-style PDF
  docx      build the Word review copy
  tex       generate the LaTeX package only
  clean     remove build/ (every template's outputs), or the -o folder
  rebuild   clear this template's outputs, then build the PDF and the DOCX

The manuscript defaults to the nearest manuscript.md in this folder or one
above it. Its references and figures default to their places
beside it; the options below point them elsewhere."""

EPILOG = """\
outputs (for paper.md and the default template):
  build/applied-energy/paper.pdf, .../paper.docx, .../latex/paper.tex

An output is rebuilt only when the content of its inputs (manuscript,
references, templates, figures, this build code, or the tool versions)
has changed. Sources are never modified."""


def find_manuscript(start):
    for folder in [start, *start.parents]:
        if (folder / 'manuscript.md').is_file():
            return folder / 'manuscript.md'
    raise BuildError(f'No manuscript.md in {start} or any folder above; name the Markdown file')


class _Format(logging.Formatter):
    def format(self, record):
        prefix = '---> ' if record.levelno < logging.WARNING else f'{record.levelname.title()}: '
        return prefix + record.getMessage()


def parse(argv):
    parser = argparse.ArgumentParser(
        prog=os.environ.get('BUILD_PROG', 'pytexMB'),
        description=DESCRIPTION, epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('arguments', nargs='*', metavar='[command] [manuscript.md]',
                        help='a command from the list above (default: all) and/or '
                             'the Markdown manuscript')
    inputs = parser.add_argument_group('inputs and outputs')
    inputs.add_argument('-i', '--input-dir', metavar='DIR',
                        help='folder that relative input paths start from (default: here)')
    inputs.add_argument('-t', '--template', metavar='NAME|DIR',
                        help='journal template (default: applied-energy; see --list-templates)')
    inputs.add_argument('--list-templates', action='store_true', help='list built-in templates and exit')
    inputs.add_argument('-b', '--bibliography', metavar='FILE', help='BibTeX file')
    inputs.add_argument('--figures', metavar='DIR', help='figure folder')
    inputs.add_argument('--class-dir', metavar='DIR',
                        help="folder with a template's unshipped class files (Wiley's, for iet-rpg)")
    inputs.add_argument('-o', '--output-dir', metavar='DIR',
                        help='output folder; each template writes to a subfolder (default: build/)')
    parser.add_argument('-e', '--engine', help='LaTeX engine (default: $PANDOC_PDF_ENGINE or xelatex)')
    parser.add_argument('-f', '--force', action='store_true',
                        help='rebuild even when an output is current')
    parser.add_argument('--strict', action='store_true',
                        help='fail on missing citations or undefined LaTeX references')
    parser.add_argument('-q', '--quiet', action='store_true', help='show warnings and errors only')
    args = parser.parse_args(argv)

    # A command, a manuscript, or both, in either order.
    commands = [argument for argument in args.arguments if argument in COMMANDS]
    sources = [argument for argument in args.arguments if argument not in COMMANDS]
    if len(commands) > 1 or len(sources) > 1:
        parser.error('give at most one command and one manuscript')
    return (commands or ['all'])[0], (sources or [None])[0], args


def main(argv=None):
    command, source, args = parse(argv)
    if args.list_templates:
        for name, title in templates().items():
            print(f'{name:16} {title}')
        return 0
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_Format())
    logger = logging.getLogger('pytexMB')
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING if args.quiet else logging.INFO)
    try:
        base = Path(args.input_dir).expanduser().resolve() if args.input_dir else Path.cwd()
        source = source or find_manuscript(base)
        if command == 'clean':
            clean(source, output_dir=args.output_dir, input_dir=args.input_dir)
            return 0
        build(source, COMMANDS[command], template=args.template,
              bibliography=args.bibliography, figures=args.figures,
              class_dir=args.class_dir, output_dir=args.output_dir,
              input_dir=args.input_dir, engine=args.engine,
              force=args.force, fresh=command == 'rebuild', strict=args.strict)
    except BuildError as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Interrupted', file=sys.stderr)
        return 130
    return 0


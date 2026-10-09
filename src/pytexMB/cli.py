"""Command line: `pytexMB [command] [manuscript.md] [options]`, and run(),
which gives a project's own build script the same command line."""
import argparse
import logging
import os
import sys
from pathlib import Path

from .api import build, clean, templates
from .environment import check, install_files
from .errors import BuildError
from .settings import FileSettings, build_settings, current, file_settings, names

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

setting up a machine:
  check                            show which programs, fonts, and template
                                   files a build can find
  install-files TEMPLATE SOURCE    install a template's unshipped files from
                                   the publisher's download (.zip or folder)

The manuscript defaults to the nearest manuscript.md in this folder or one
above it, or else the only .md file here. The journal and the references
come from its YAML header (template:, bibliography:), else references.bib
or the only .bib beside it; figures are found from its image lines. The
options below override any of these. A header after-build: command runs
after each build."""

EPILOG = """\
outputs (for paper.md and the default template):
  build/applied-energy/paper.pdf, .../paper.docx, .../latex/paper.tex

An output is rebuilt only when the content of its inputs (manuscript,
references, templates, figures, this build code, or the tool versions)
has changed. Sources are never modified."""


class _Format(logging.Formatter):
    def format(self, record):
        prefix = '---> ' if record.levelno < logging.WARNING else f'{record.levelname.title()}: '
        return prefix + record.getMessage()


class _Handler(logging.StreamHandler):
    def __init__(self, stream):
        super().__init__(stream)
        self.setFormatter(_Format())


def parse(argv, prog=None, preset=''):
    parser = argparse.ArgumentParser(
        prog=prog or os.environ.get('BUILD_PROG', 'pytexMB'),
        description=DESCRIPTION, epilog=preset + EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('arguments', nargs='*', metavar='[command] [manuscript.md]',
                        help='a command from the list above (default: all) and/or '
                             'the Markdown manuscript')
    inputs = parser.add_argument_group('inputs and outputs')
    inputs.add_argument('-i', '--input-dir', metavar='DIR',
                        help='folder that relative input paths start from (default: here)')
    inputs.add_argument('-t', '--template', metavar='NAME|DIR',
                        help="journal template (default: the header's template:, else "
                             'applied-energy; see --list-templates)')
    inputs.add_argument('--list-templates', action='store_true', help='list built-in templates and exit')
    inputs.add_argument('-b', '--bibliography', metavar='FILE',
                        help="BibTeX file (default: the header's bibliography:, else "
                             'references.bib or the only .bib beside the manuscript)')
    inputs.add_argument('--class-dir', metavar='DIR',
                        help="folder with a template's unshipped class files (Wiley's, for iet-rpg)")
    inputs.add_argument('-o', '--output-dir', metavar='DIR',
                        help='output folder; each template writes to a subfolder (default: build/)')
    parser.add_argument('-e', '--engine', help='LaTeX engine (default: $PANDOC_PDF_ENGINE or xelatex)')
    parser.add_argument('-f', '--force', action='store_true',
                        help='rebuild even when an output is current')
    parser.add_argument('--strict', action='store_true',
                        help='fail on missing citations or undefined LaTeX references')
    parser.add_argument('--no-after-build', action='store_true',
                        help="skip the manuscript header's after-build: command")
    parser.add_argument('-q', '--quiet', action='store_true', help='show warnings and errors only')
    # Flags may come before, between, or after the command and manuscript.
    args = parser.parse_intermixed_args(argv)

    # A command, a manuscript, or both, in either order.
    commands = [argument for argument in args.arguments if argument in COMMANDS]
    sources = [argument for argument in args.arguments if argument not in COMMANDS]
    if len(commands) > 1 or len(sources) > 1:
        parser.error('give at most one command and one manuscript')
    return (commands or [None])[0], (sources or [None])[0], args


def show_check():
    items = check()
    width = max(len(item.name) for item in items)
    for item in items:
        print(f'{"ok" if item.ok else "--":2}  {item.name:<{width}}  {item.detail}')
    return 0 if all(item.ok for item in items if item.name in ('pandoc', 'xelatex')) else 1


def setup(argv):
    """The machine-setup commands, which take their own arguments."""
    if argv[0] == 'check':
        if len(argv) > 1:
            raise BuildError('check takes no arguments')
        return show_check()
    if len(argv) != 3:
        raise BuildError('usage: pytexMB install-files TEMPLATE SOURCE\n'
                         'SOURCE is the .zip or folder downloaded from the publisher')
    print(f'Installed into {install_files(argv[1], argv[2])}')
    return 0


def run(**settings):
    """A whole build script: name the settings, and the script takes the
    same commands and flags as `pytexMB` (python build.py -f, pdf, clean,
    -h, ...).

        import pytexMB

        pytexMB.run(manuscript='paper.md', template='iet-rpg', word=False)

    Any file or build setting may be named. Relative paths start at the
    script's folder, so the script works from any folder. A flag given on
    the command line wins over the script for that run. Exits with status 1
    if the build fails."""
    script = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else None
    folder = script.parent if script and script.is_file() else Path.cwd()
    settings.setdefault('input_dir', folder)
    try:
        current(**settings)          # names every unknown setting at once
        file_settings(**{key: value for key, value in settings.items()
                         if key in names(FileSettings)})
        build_settings(**{key: value for key, value in settings.items()
                          if key not in names(FileSettings)})
    except BuildError as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
    shown = {key: value for key, value in settings.items() if key != 'input_dir'}
    preset = ('settings in this script (a flag overrides them for one run):\n'
              + ''.join(f'  {key} = {value!r}\n' for key, value in shown.items()) + '\n'
              if shown else '')
    code = main(prog=script.name if script else None, preset=preset)
    if code:
        sys.exit(code)


def main(argv=None, prog=None, preset=''):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ('check', 'install-files'):
        try:
            return setup(argv)
        except BuildError as error:
            print(f'Error: {error}', file=sys.stderr)
            return 1
    command, source, args = parse(argv, prog, preset)
    if args.list_templates:
        for name, title in templates().items():
            print(f'{name:16} {title}')
        return 0
    logger = logging.getLogger('pytexMB')
    # One handler however often main() runs in a process.
    if not any(isinstance(handler, _Handler) for handler in logger.handlers):
        logger.addHandler(_Handler(sys.stdout))
    logger.setLevel(logging.WARNING if args.quiet else logging.INFO)
    try:
        if command == 'clean':
            clean(source, output_dir=args.output_dir, input_dir=args.input_dir)
            return 0
        # Only what was typed overrides the settings; a flag not given, or no
        # command, leaves file_settings() and build_settings() in charge.
        build(source, COMMANDS[command] if command else None, template=args.template,
              bibliography=args.bibliography,
              class_dir=args.class_dir, output_dir=args.output_dir,
              input_dir=args.input_dir, engine=args.engine,
              force=args.force or None, fresh=command == 'rebuild',
              strict=args.strict or None, after_build=not args.no_after_build)
    except BuildError as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Interrupted', file=sys.stderr)
        return 130
    return 0


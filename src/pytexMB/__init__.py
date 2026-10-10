"""Build a manuscript's PDF, Word copy, and LaTeX package from Markdown.

From Python, with the journal and references named in the manuscript's
YAML header (template:, bibliography:), or left to their defaults:

    import pytexMB

    result = pytexMB.build()             # manuscript.md, or the only .md here
    print(result.pdf, result.tex)

Settings override what is worked out from the manuscript:

    # Where things are
    pytexMB.file_settings(input_dir='~/papers/review', manuscript='paper.md',
                          bibliography='refs/library.bib', output_dir='out')
    # What to make
    pytexMB.build_settings(template='iet-rpg', word=False)

    result = pytexMB.build()             # builds with both
    print(result.pdf, result.tex)

    pytexMB.build(template='applied-energy', word=True)  # override for one call
    print(pytexMB.file_settings())       # show the file settings
    print(pytexMB.build_settings())      # show the build settings
    print(pytexMB.templates())           # built-in templates

Setting up a machine:

    pytexMB.check()                      # programs, fonts, and template files found
    pytexMB.install_files('iet-rpg', '~/Downloads/wiley-njd.zip')

From the terminal: `pytexMB --help` (after `pip install -e .`) or
`python3 -m pytexMB --help`.

Progress is logged to the `pytexMB` logger; call
`logging.basicConfig(level=logging.INFO)` to see it from a script.
Failures raise BuildError with a message saying what to fix.

Stages, each in its own module:

  settings.py file_settings(), build_settings(), reset_settings()
  paths.py    find the manuscript, references, and figures it names
  environment.py  check() and install_files(), for setting up a machine
  api.py      build() and clean(); decides which outputs are stale
  template.py load a journal template (templates/<name>/template.json)
  latex.py    stage sources, run Pandoc, and post-process the .tex file
  compose.py  write each Markdown figure as its LaTeX figure environment
  tables.py   replace Pandoc's longtables with the print table layout
  pdf.py      compile the LaTeX package, rerunning until references settle
  docx.py     turn the same LaTeX into the Word review copy and style it
  state.py    content-hash freshness, so only stale outputs rebuild
"""
from .api import BuildResult, build, clean, templates
from .cli import run
from .environment import check, install_files
from .errors import BuildError
from .settings import (BuildSettings, FileSettings, build_settings, file_settings,
                       reset_settings)

__all__ = ['file_settings', 'build_settings', 'reset_settings', 'build', 'clean',
           'templates', 'check', 'install_files', 'run', 'FileSettings', 'BuildSettings',
           'BuildResult', 'BuildError']
__version__ = '1.2.0'

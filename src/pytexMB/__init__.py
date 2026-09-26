"""Build a manuscript's PDF, Word copy, and LaTeX package from Markdown.

From Python:

    import pytexMB

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

From the terminal: `pytexMB --help` (after `pip install -e .`) or
`python3 -m pytexMB --help`.

Progress is logged to the `pytexMB` logger; call
`logging.basicConfig(level=logging.INFO)` to see it from a script.
Failures raise BuildError with a message saying what to fix.

Stages, each in its own module:

  settings.py file_settings(), build_settings(), reset_settings()
  api.py      build() and clean(); decides which outputs are stale
  template.py load a journal template (templates/<name>/template.json)
  latex.py    stage sources, run Pandoc, and post-process the .tex file
  compose.py  merge the manuscript's figure layouts (latex-blocks.md)
  tables.py   replace Pandoc's longtables with the print table layout
  pdf.py      compile the LaTeX package, rerunning until references settle
  docx.py     turn the same LaTeX into the Word review copy and style it
  state.py    content-hash freshness, so only stale outputs rebuild
"""
from .api import BuildResult, build, clean, templates
from .errors import BuildError
from .settings import (BuildSettings, FileSettings, build_settings, file_settings,
                       reset_settings)

__all__ = ['file_settings', 'build_settings', 'reset_settings', 'build', 'clean',
           'templates', 'FileSettings', 'BuildSettings', 'BuildResult', 'BuildError']
__version__ = '1.0.0'

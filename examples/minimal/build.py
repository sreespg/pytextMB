"""Build note.md. Run it from any folder:

    python build.py             PDF and Word copy, in build/applied-energy/
    python build.py -f          rebuild even if nothing changed
    python build.py pdf         the PDF only
    python build.py clean       delete build/
    python build.py -h          every command and flag
"""
import pytexMB

pytexMB.run(
    manuscript='note.md',          # path to the Markdown file
    template='applied-energy',     # see `pytexMB --list-templates`, or a template folder

    # Optional
    output_dir='build',            # default: build/ beside the manuscript
    word=True,                     # also make the Word copy (default: True)
)

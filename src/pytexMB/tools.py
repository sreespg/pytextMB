"""External programs: finding them, running them, and reporting their failures."""
import logging
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

from .errors import BuildError

# Progress goes to the `pytexMB` logger. The command line shows it;
# a script sees only warnings unless it configures logging itself.
logger = logging.getLogger('pytexMB')


def log(message):
    logger.info(message)


def warn(message):
    logger.warning(message)


def require(*commands):
    missing = [command for command in commands if shutil.which(command) is None]
    if missing:
        raise BuildError(f'{", ".join(missing)} not installed or not on PATH')


def run(command, cwd=None, what=None):
    """Run a program, passing its warnings through. On failure the error names
    the step and shows the program's own output instead of hiding it."""
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
    what = what or command[0]
    if result.returncode:
        output = (result.stderr or result.stdout).strip()
        raise BuildError(f'{what} failed (exit {result.returncode})'
                         + (f':\n{output}' if output else ''))
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines():
            warn(f'[{command[0]}] {line}')
    return result


def version(command):
    """First line of `command --version`; part of the freshness key, so a tool
    upgrade rebuilds outputs it might render differently."""
    try:
        result = subprocess.run([command, '--version'], capture_output=True, text=True)
    except OSError:
        return ''
    return (result.stdout or result.stderr).split('\n', 1)[0]


def convert_svgs(svgs, target, arguments=()):
    """Render each SVG with rsvg-convert, in parallel. `target` maps an SVG
    path to its output path."""
    def convert(svg):
        output = target(svg)
        run(['rsvg-convert', *arguments, f'--output={output}', str(svg)],
            what=f'rsvg-convert {svg.name}')
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        # list() re-raises the first conversion error here.
        list(pool.map(convert, svgs))

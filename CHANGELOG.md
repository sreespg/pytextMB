# Changelog

## 1.2.0

- An author list in the header: each author's `name`, `affiliation` (an
  `id` from the `affiliations:` list), and optionally `orcid`,
  `corresponding: true` and `email`; `short-authors:` sets the running head.
  `applied-energy`, `iet-rpg` and the Word copy print the authors,
  affiliations and corresponding author. A single `author:` string still
  works.
- `applied-energy` ships the CAS e-mail and URL icons, so `\ead` compiles.
- References keep their link: Elsevier Vancouver prints the URL of any
  entry that has one, and the IET style adds the DOI (or URL) to journal
  papers, software, theses and proceedings.

## 1.1.0

- `pytexMB.run(manuscript=..., template=..., ...)`: a whole build script in
  one call. The script takes the same commands and flags as `pytexMB`
  (`python build.py -f`, `pdf`, `clean`, `-h`), and its relative paths start
  at its own folder.
- Works out the inputs from the manuscript, so no settings are needed:
  `manuscript.md` or the only `.md` file in the folder; the header's
  `bibliography:` (one file or a list), else `references.bib` or the only
  `.bib` beside the manuscript, and none at all when nothing is cited; the
  header's `template:` for the journal; figures from the image lines, in any
  folder.
- `pytexMB.build()` and `pytexMB.clean()` find the manuscript themselves.
- `pytexMB check` / `pytexMB.check()`: which programs, fonts, and template
  files this machine has.
- `pytexMB install-files TEMPLATE SOURCE` / `pytexMB.install_files()`:
  install the Wiley or UiA files from the downloaded `.zip` or folder.
- `applied-energy` falls back to TeX Gyre Termes and Latin Modern Mono, with
  a warning, when STIX or Inconsolata is not installed.
- PNG and JPEG figures reach the Word copy.
- `after-build:` in the header runs a project's own step (supplementary
  material, say) after each build, told the outputs through `PYTEXMB_*`
  environment variables; `--no-after-build` skips it.
- The command line no longer overrides `build_settings()` with its own
  defaults: `force`, `strict`, `pdf` and `word` change only when a flag or
  command says so.
- Flags may come anywhere: `pytexMB pdf -f paper.md` works.
- Removed: the `figures` setting and `--figures` option; figure paths come
  from the Markdown.
- A pytest suite (`pip install -e '.[test]'`, then `pytest`).

## 1.0.0

- First release: journal PDF, LaTeX package, and Word copy from Markdown,
  for `applied-energy`, `iet-rpg`, and `uia-phd`.

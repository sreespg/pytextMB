# Applied Energy template

Layout: Elsevier's CAS double-column class (`cas-dc.cls`, `cas-common.sty`,
`cas-model2-names.bst`), shipped here unmodified from the CAS bundle v2.4
under the LaTeX Project Public License (see CAS-README).

References: `elsevier-vancouver.csl` (CC BY-SA 3.0, from the Citation Style
Language repository), the parent style of the Applied Energy CSL entry.

Fonts: STIX, Latin Modern Sans, and Inconsolata, matching Elsevier's own
CAS sample PDF (on Debian/Ubuntu: fonts-stix, fonts-inconsolata), and STIX
Two Math for equations (https://github.com/stipub/stixfonts, or TeX Live's
stix2-otf). The STIX Math font in fonts-stix has no OpenType math script,
so XeLaTeX cannot use it for equations.

# Maintaining the publication lists

The homepage and `/publications/` share `_data/publications.yml` and the
`publication-list.html` / `publication-citation.html` includes. The existing
`_publications/` detail pages and their URLs remain available.

## Update the bibliography

1. Update `files/publications.bib` with the verified BibTeX records. The initial
   DBLP records came from `10769.bib`; the two MIT Sloan Management Review
   articles were supplemented from the publisher.
2. Install the generator dependencies if needed: `python -m pip install pybtex PyYAML`.
3. From the repository root, run `python scripts/generate_publications.py`.
4. Review the generated `_data/publications.yml`, especially the author order,
   publication year, venue, page range or article identifier, and access URL.
5. Build the site with `bundle exec jekyll build` in a configured Ruby/Jekyll
   environment.

Run `python scripts/generate_publications.py --check` to verify that the checked-in
YAML matches the bibliography without rewriting it.

Python 3.10+ is needed only to regenerate the bibliography. GitHub Pages reads the
checked-in YAML using standard Liquid includes; no citation plugin is required.
The old TSV generator does not update these shared lists.

## Formatting and selection

Entries use the Chicago 18th edition notes-and-bibliography format: the first
author's name is inverted; titles are quoted; publication titles are italicized;
available volume, issue, year, and pages are included. Up to six authors are
listed; longer author lists use the first three followed by "et al." Each entry
ends with an **Access link** to its DOI or publisher page.

The website groups entries by descending year, with alphabetical author order
within each year. This is a portfolio arrangement of Chicago-formatted entries.
The homepage retains its ten selected works. Selection and explicit preprint
aliases are maintained in the generator. Published versions replace their
matching preprints in these lists; works available only as preprints are labeled
separately. Bibliographic source records are retained for provenance.

Sources:

- [Chicago citation quick guide](https://www.chicagomanualofstyle.org/tools_citationguide/citation-guide-1.html)
- [Casting the Dark Web in a New Light](https://sloanreview.mit.edu/article/casting-the-dark-web-in-a-new-light/)
- [Design for Cybersecurity from the Start](https://sloanreview.mit.edu/article/design-for-cybersecurity-from-the-start/)

The Sloan entries cite the print editions: [Fall 2019, volume 61, issue 1](https://sloanreview.mit.edu/issue/2019-fall/) and [Winter 2022, volume 63, issue 2](https://sloanreview.mit.edu/issue/2022-winter/). Print pagination was cross-checked against the [ZBW catalog for Casting](https://www.econbiz.de/10012107499) and the [ZBW catalog for Design](https://www.econbiz.de/10012821970).

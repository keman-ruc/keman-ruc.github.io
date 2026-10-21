#!/usr/bin/env python3
"""Build the site's Chicago-style bibliography from files/publications.bib.

Requires pybtex and PyYAML. Run from any directory with Python 3.10+.
The committed YAML is consumed by GitHub Pages, so Python is not needed there.
Style: Chicago Manual of Style, 18th ed., notes-and-bibliography bibliography.
https://www.chicagomanualofstyle.org/tools_citationguide/citation-guide-1.html
"""

import argparse
import html
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from pybtex.database import parse_file
from pybtex.richtext import Text


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "files" / "publications.bib"
OUTPUT = ROOT / "_data" / "publications.yml"

SELECTED = {
    "DBLP:conf/aaai/ZhongHD26",
    "DBLP:conf/aaai/WangHLLD26",
    "DBLP:journals/tse/WangLHD26",
    "DBLP:conf/kdd/LiFJLLHD26",
    "DBLP:journals/compsec/WangTHL25",
    "DBLP:conf/icws/WangL0H024",
    "DBLP:journals/pacmhci/HuangZC22",
    "DBLP:journals/compsec/QuXSHQL22",
    "Manual:sloan/PearlsonHuang2022",
    "Manual:sloan/HuangSiegelPearlsonMadnick2019",
}

# This preprint's title changed slightly on publication; title matching alone
# cannot identify the two records as the same work. Keep the journal version.
PUBLISHED_VERSIONS = {
    "DBLP:journals/corr/abs-2403-01507": "DBLP:journals/jwe/YanHS25",
}

JOURNALS = {
    "Int. J. Inf. Manag.": "International Journal of Information Management",
    "IEEE Trans. Software Eng.": "IEEE Transactions on Software Engineering",
    "Comput. Secur.": "Computers & Security",
    "J. Web Eng.": "Journal of Web Engineering",
    "Inf. Secur. J. A Glob. Perspect.": "Information Security Journal: A Global Perspective",
    "Proc. ACM Hum. Comput. Interact.": "Proceedings of the ACM on Human-Computer Interaction",
    "Concurr. Comput. Pract. Exp.": "Concurrency and Computation: Practice and Experience",
    "IEEE Trans. Serv. Comput.": "IEEE Transactions on Services Computing",
    "ACM Comput. Surv.": "ACM Computing Surveys",
    "IEEE Internet Things J.": "IEEE Internet of Things Journal",
    "Int. J. Web Serv. Res.": "International Journal of Web Services Research",
    "IEEE Trans Autom. Sci. Eng.": "IEEE Transactions on Automation Science and Engineering",
    "Int. J. Comput. Integr. Manuf.": "International Journal of Computer Integrated Manufacturing",
    "IEEE Trans. Cybern.": "IEEE Transactions on Cybernetics",
    "Int. J. Networked Distributed Comput.": "International Journal of Networked and Distributed Computing",
}

# Retain the collection names and edition information, omitting event venues
# and dates (which are not needed in a published proceedings citation).
COLLECTIONS = {
    "DBLP:conf/aaai/ZhongHD26": "Fortieth AAAI Conference on Artificial Intelligence",
    "DBLP:conf/aaai/WangHLLD26": "Fortieth AAAI Conference on Artificial Intelligence",
    "DBLP:conf/web/HuangM20": "The Role of e-Business during the Time of Grand Challenges: 19th Workshop on e-Business, WeB 2020, Revised Selected Papers",
    "DBLP:conf/ksem/HuFCHH18": "Knowledge Science, Engineering and Management: KSEM 2018, Proceedings, Part II",
    "DBLP:conf/sate/ZhangCHFH18": "Software Analysis, Testing, and Evolution: SATE 2018, Proceedings",
    "DBLP:conf/icsoc/HuangHCF16": "Service-Oriented Computing: ICSOC 2016, Proceedings",
    "DBLP:conf/apscc/HuFCH15": "Advances in Services Computing: APSCC 2015, Proceedings",
    "DBLP:conf/icsoc/NiFHBT14": "Service-Oriented Computing: ICSOC 2014, Proceedings",
    "DBLP:conf/icsoc/HuangLNFCT14": "Service-Oriented Computing: ICSOC 2014, Proceedings",
    "DBLP:conf/icsoc/DuanHKD13": "Service-Oriented Computing: ICSOC 2013 Workshops, Revised Selected Papers",
    "DBLP:conf/icsoc/HuangYFTNNC13": "Service-Oriented Computing: ICSOC 2013, Proceedings",
    "DBLP:conf/compsac/HuFHC17": "41st IEEE Annual Computer Software and Applications Conference, Volume 1",
}

LOWERCASE = set("a an the and but or nor for so yet as at by down from in into of off on onto out over per through to up via with without towards toward during among against between under beyond within behind".split())


def plain(value):
    """Decode BibTeX braces, accents, and escaped URL characters."""
    return " ".join(Text.from_latex(value).render_as("text").split())


def escape(value):
    return html.escape(value, quote=False)


def headline(value):
    """Apply English headline capitalization without damaging acronyms/names."""
    words = re.split(r"(\s+|[-–—])", value)
    word_indices = [i for i, word in enumerate(words) if re.search(r"[A-Za-z]", word)]
    first = True
    for i in word_indices:
        word = words[i]
        match = re.search(r"[A-Za-z][A-Za-z0-9'’+]*", word)
        if not match:
            continue
        token = match.group()
        # All-caps abbreviations, internal capitals (iRUC, MapReduce), and
        # digit-bearing names (D3L, K-12) are already intentionally styled.
        protected = token.lower() not in LOWERCASE and (token.isupper() or any(c.isupper() for c in token[1:]) or any(c.isdigit() for c in token))
        if not protected:
            last = i == word_indices[-1]
            token = token.lower() if token.lower() in LOWERCASE and not (first or last) else token[0].upper() + token[1:]
            words[i] = word[:match.start()] + token + word[match.end():]
        first = word.endswith((":", "?", "!"))
    return "".join(words)


def person_name(person, inverted=False):
    given = plain(" ".join(person.first_names + person.middle_names))
    family = plain(" ".join(person.prelast_names + person.last_names))
    suffix = plain(" ".join(person.lineage_names))
    if inverted:
        return ", ".join(part for part in (family, given, suffix) if part)
    name = " ".join(part for part in (given, family) if part)
    return name + (", " + suffix if suffix else "")


def people(persons, invert_first=True):
    displayed = persons[:3] if len(persons) > 6 else persons
    names = [person_name(person, invert_first and i == 0) for i, person in enumerate(displayed)]
    if len(persons) > 6:
        return ", ".join(names) + ", et al."
    if len(names) == 2:
        return (", and " if invert_first else " and ").join(names)
    if len(names) > 2:
        return ", ".join(names[:-1]) + ", and " + names[-1]
    return "".join(names)


def page_range(value):
    value = plain(value).replace("--", "–")
    match = re.fullmatch(r"(\d+)–(\d+)", value)
    if not match:
        return value
    start, end = match.groups()
    a, b = int(start), int(end)
    # Retain full numbers across hundreds and when starting at an exact
    # hundred. Within a hundred, retain the changed digits (at least two,
    # except starts 101–109, 201–209, etc.). Article:page ranges stay intact.
    if a < 100 or a % 100 == 0 or a // 100 != b // 100:
        return value
    minimum = 1 if a % 100 < 10 else 2
    common = 0
    while common < min(len(start), len(end)) and start[common] == end[common]:
        common += 1
    return start + "–" + end[min(common, len(end) - minimum):]


def normalized_title(entry):
    value = unicodedata.normalize("NFKD", plain(entry.fields["title"]))
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def is_preprint(entry):
    return plain(entry.fields.get("journal", "")) == "CoRR"


def access_url(entry):
    fields = entry.fields
    url = plain(fields.get("url", ""))
    doi = plain(fields.get("doi", ""))
    # Use the supplied DOI resolver URL to preserve its original casing.
    if doi and "doi.org/" not in url:
        url = "https://doi.org/" + re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
    url = re.sub(r"^http://(?:dx\.)?doi\.org/", "https://doi.org/", url)
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or "\\" in url or any(c.isspace() for c in url):
        raise ValueError("Missing or invalid access URL: " + url)
    return url


def book_title(key, fields):
    if key in COLLECTIONS:
        return COLLECTIONS[key]
    title = plain(fields["booktitle"])
    # The first comma separates the collection title from acronym/location
    # metadata in these DBLP records. ACL's Findings title includes its year.
    if key.startswith("DBLP:conf/acl/"):
        return ", ".join(title.split(", ")[:2])
    return title.split(", ")[0]


def citation(key, entry):
    f = entry.fields
    authors = people(entry.persons.get("author", []))
    title = headline(plain(f["title"]))
    title_end = "" if title.endswith(("?", "!", ".")) else "."
    author_end = "" if authors.endswith(".") else "."
    result = escape(authors + author_end) + " “" + escape(title + title_end) + "” "
    year = f["year"]
    if is_preprint(entry):
        arxiv_id = plain(f.get("volume", "")).removeprefix("abs/")
        return result + "arXiv preprint, arXiv:" + escape(arxiv_id) + " (" + year + ")."
    if entry.type == "inproceedings":
        result += "In <em>" + escape(book_title(key, f)) + "</em>"
        editors = entry.persons.get("editor", [])
        if editors:
            result += ", edited by " + escape(people(editors, invert_first=False))
        if f.get("pages"):
            result += ", " + escape(page_range(f["pages"]))
        result += ". "
        if f.get("series"):
            result += escape(plain(f["series"]))
            if f.get("volume"):
                result += " " + escape(plain(f["volume"]))
            result += ". "
        if f.get("publisher"):
            result += escape(plain(f["publisher"])) + ", "
        return result + year + "."
    journal = plain(f["journal"])
    result += "<em>" + escape(JOURNALS.get(journal, journal)) + "</em>"
    if f.get("entrysubtype") == "magazine":
        date = " ".join(plain(f.get(k, "")) for k in ("month", "day")).strip()
        return result + ", " + escape(date + ", " if date else "") + year + "."
    if f.get("volume"):
        result += " " + escape(plain(f["volume"]))
    if f.get("number"):
        result += ", no. " + escape(plain(f["number"]))
    result += " (" + year + ")"
    if f.get("pages"):
        pages = page_range(f["pages"])
        if f.get("eid"):
            eid = plain(f["eid"])
            pages = "–".join(eid + ":" + part for part in pages.split("–"))
        result += ": " + escape(pages)
    elif f.get("eid"):
        result += ": " + escape(plain(f["eid"]))
    return result + "."


def generate():
    entries = parse_file(str(SOURCE)).entries
    published_titles = {normalized_title(e): k for k, e in entries.items() if not is_preprint(e)}
    records, suppressed = [], []
    for key, entry in entries.items():
        preprint = is_preprint(entry)
        replacement = PUBLISHED_VERSIONS.get(key) or published_titles.get(normalized_title(entry))
        if preprint and replacement:
            if replacement not in entries:
                raise ValueError("Published replacement is absent: " + replacement)
            suppressed.append((key, replacement))
            continue
        records.append({
            "id": re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-"),
            "source_id": key,
            "title": headline(plain(entry.fields["title"])),
            "year": int(entry.fields["year"]),
            "authors": people(entry.persons.get("author", [])),
            "citation": citation(key, entry),
            "url": access_url(entry),
            "selected": key in SELECTED,
            "preprint": preprint,
        })
    missing = SELECTED - {r["source_id"] for r in records}
    if missing:
        raise ValueError("Selected records are absent: " + ", ".join(sorted(missing)))
    records.sort(key=lambda r: (-r["year"], r["authors"].casefold(), r["title"].casefold()))
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate publication IDs")
    content = "# Generated by scripts/generate_publications.py; edit files/publications.bib.\n"
    content += yaml.safe_dump(records, allow_unicode=True, sort_keys=False, width=120)
    print(f"Source: {len(entries)}; displayed: {len(records)}; published: {sum(not r['preprint'] for r in records)}; preprints: {sum(r['preprint'] for r in records)}; selected: {sum(r['selected'] for r in records)}")
    for preprint, published in suppressed:
        print(f"Suppressed duplicate: {preprint} -> {published}")
    return content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the committed YAML needs regeneration")
    args = parser.parse_args()
    content = generate()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
            raise SystemExit("publications.yml is out of date; run this script without --check")
        print("publications.yml is current.")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(content, encoding="utf-8", newline="\n")
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()

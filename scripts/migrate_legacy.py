#!/usr/bin/env python3
"""Rebuild hugo-site/content and hugo-site/static/images from legacy-site.

The legacy site is the 2005 static Dumile Feni Foundation site. This script is
the single record of how each legacy page maps to the new site, so it can be
re-run after the legacy copy or the mapping changes.
"""
import html
import json
import os
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "legacy-site"
CONTENT = ROOT / "hugo-site" / "content"
IMAGES = ROOT / "hugo-site" / "static" / "images"

BLOCK = {"p", "div", "td", "tr", "table", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol"}
NOISE = re.compile(
    r"^(\*\*)?\s*(HISTORY|GALLERY|RESOURCES|NEWS|BOOKS / CATALOGUES|Biographies|Timeline|"
    r"Newspaper articles|enlarge|BACK TO TOP|<\s*BACK|<\s*EXHIBITIONS|BACK|EXHIBITIONS:?|view photos from the exhibition|"
    r"< PREVIOUS PAGE|NEXT PAGE >)\s*(\*\*)?$",
    re.I,
)


def slug(name):
    stem, ext = os.path.splitext(name)
    stem = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return stem + ext.lower()


def read(rel):
    return (LEGACY / rel).read_text(encoding="cp1252", errors="replace")


class Markdown(HTMLParser):
    def __init__(self, base, links, images):
        super().__init__(convert_charrefs=True)
        self.base, self.links, self.images = base, links, images
        self.out, self.skip, self.href, self.list = [], 0, [], []

    def emit(self, text):
        if not self.skip:
            self.out.append(text)

    def resolve(self, target):
        target = target.split("#")[0]
        return os.path.normpath(os.path.join(os.path.dirname(self.base), target)).replace("\\", "/")

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "head"):
            self.skip += 1
        elif tag in BLOCK:
            self.emit("\n\n")
            if tag in ("ul", "ol"):
                self.list.append(tag)
        elif tag == "br":
            self.emit("  \n")
        elif tag in ("strong", "b"):
            self.emit("\x01")
        elif tag in ("em", "i"):
            self.emit("\x02")
        elif tag == "li":
            self.emit("\n- ")
        elif tag == "sup":
            self.emit("<sup>")
        elif tag == "a":
            href = a.get("href", "")
            url = None
            if href.startswith("http"):
                url = href
            elif href and not href.startswith(("javascript", "#", "mailto")):
                url = self.links.get(self.resolve(href))
            self.href.append(url)
            if url:
                self.emit("[")
        elif tag == "img":
            src = self.resolve(a.get("src", ""))
            if src in self.images:
                self.emit(f"\n\n![]({self.images[src]})\n\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head"):
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK:
            self.emit("\n\n")
            if tag in ("ul", "ol") and self.list:
                self.list.pop()
        elif tag in ("strong", "b"):
            self.emit("\x01")
        elif tag in ("em", "i"):
            self.emit("\x02")
        elif tag == "sup":
            self.emit("</sup>")
        elif tag == "a" and self.href:
            url = self.href.pop()
            if url:
                self.emit(f"]({url})")

    def handle_data(self, data):
        self.emit(re.sub(r"\s+", " ", data))


def emphasis(text, mark, md):
    def wrap(match):
        inner = match.group(1)
        if not inner.strip():
            return inner
        lead = inner[: len(inner) - len(inner.lstrip())]
        trail = inner[len(inner.rstrip()):]
        return f"{lead}{md}{inner.strip()}{md}{trail}"

    text = re.sub(mark + "([^" + mark + "\n]*)" + mark, wrap, text)
    return text.replace(mark, "")


def to_markdown(rel, links, images):
    parser = Markdown(rel, links, images)
    parser.feed(read(rel))
    text = "".join(parser.out).replace("\xa0", " ")
    text = text.replace("\u201d\u00a6", "\u2026").replace("\u201d\u009d", "\u201d")
    text = re.sub(r"[\u0080-\u009f\ufffd]", "", text)
    text = re.sub(r"\u201c[ \t]+", "\u201c", text)
    text = re.sub(r"(?<=\w)[ \t]+([,;])", r"\1", text)
    text = re.sub(r"(?<=[a-z])[ \t]+\.(?=[ \t\n]|$)", ".", text)
    text = emphasis(text, "\x01", "**")
    text = emphasis(text, "\x02", "*")
    paragraphs = []
    for block in re.split(r"\n\s*\n", text):
        lines = [re.sub(r"[ \t]+", " ", l).strip() for l in block.split("\n")]
        lines = [l + "  " if raw.endswith("  ") else l for l, raw in zip(lines, block.split("\n"))]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        block = "\n".join(lines).strip()
        block = re.sub(r"^(\s*\n)+", "", block)
        block = "\n".join(l for l in block.split("\n") if "[number removed]" not in l and "[email removed]" not in l).strip()
        plain = re.sub(r"[*<>|\s]", "", block)
        unlinked = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", block).replace("\n", " ").strip()
        if not plain or NOISE.match(unlinked):
            continue
        paragraphs.append(block)
    return paragraphs


def headings(paragraphs):
    out = []
    for p in paragraphs:
        m = re.fullmatch(r"\*\*([^*\n]{3,110})\*\*:?", p.strip())
        out.append(f"## {m.group(1).strip().rstrip(':')}" if m else p)
    return out


def write(path, front, body=""):
    target = CONTENT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(front, indent=2, ensure_ascii=False) + "\n\n" + body.strip() + "\n", encoding="utf-8")


def copy_image(src_rel, dest_rel):
    src = LEGACY / src_rel
    dest = IMAGES / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    return "/images/" + dest_rel


LINKS = {
    "about/about.htm": "/foundation/",
    "menu.htm": "/",
    "frameset.htm": "/",
    "history/history.htm": "/life/",
    "history/history_bios.htm": "/life/",
    "history/history_dumile-profile.htm": "/life/profile/",
    "history/history_smith-b_01.htm": "/life/the-artist-and-the-work/",
    "history/history_smith-b_02.htm": "/life/a-biographical-sketch/",
    "history/timelines/timeline_omar.htm": "/life/chronology/",
    "history/history_exhibs_JAG.htm": "/exhibitions/exhibition-history/",
    "history/history_newspapers.htm": "/press/",
    "gallery/gallery.htm": "/exhibitions/",
    "gallery/gallery_JAG.htm": "/exhibitions/johannesburg-art-gallery/",
    "gallery/artist-in-exile/menu.htm": "/exhibitions/artist-in-exile/",
    "gallery/retrospective/gallery_retro.htm": "/exhibitions/retrospective/",
    "gallery/retrospective/gallery_retro_curator-statement.htm": "/exhibitions/retrospective/curators-statement/",
    "gallery/retrospective/gallery_retro_curator.htm": "/exhibitions/retrospective/curator/",
    "gallery/retrospective/menu.htm": "/exhibitions/retrospective/",
    "gallery/retrospective/menu_01_b4-exile.htm": "/exhibitions/retrospective/before-exile/",
    "gallery/retrospective/menu_02_london.htm": "/exhibitions/retrospective/london/",
    "gallery/retrospective/menu_03_USA.htm": "/exhibitions/retrospective/usa/",
    "books/books.htm": "/publications/",
    "books/catalogue_artist-in-exile.htm": "/publications/artist-in-exile-catalogue/",
    "books/catalogue_NSA-gallery.htm": "/publications/nsa-gallery-catalogue/",
    "books/catalogue_statements.htm": "/publications/statements-catalogue/",
    "news/news.htm": "/news/",
    "news/news_sunday-indie_2005-01-23.htm": "/news/dumile-never-pandered-to-white-whims/",
    "resources/resources.htm": "/writing/",
    "resources/resources_article_simon-b.htm": "/writing/dumile-barney-simon-1968/",
    "resources/resources_article_dejager-ej.htm": "/writing/contemporary-african-sculpture-de-jager/",
    "resources/resources_proposal_cover.htm": "/writing/work-study-grant-proposal-1989/",
}

INLINE_IMAGES = {}


def essay(rel, path, title, weight, extra=None, drop_title=True, keep_headings=True):
    paragraphs = to_markdown(rel, LINKS, INLINE_IMAGES)
    if keep_headings:
        paragraphs = headings(paragraphs)
    if drop_title and paragraphs:
        first = re.sub(r"[#*]", "", paragraphs[0]).strip().lower()
        key = re.sub(r"[^a-z]", "", title.lower())[:18]
        if key and key in re.sub(r"[^a-z]", "", first):
            paragraphs = paragraphs[1:]
    # Several 2005 pages end with a contact block of phone numbers and staff.
    if "## Contact" in paragraphs:
        paragraphs = paragraphs[:paragraphs.index("## Contact")]
    front = {"title": title, "weight": weight, "legacy_path": rel}
    front.update(extra or {})
    if front.get("layout") == "chronology":
        paragraphs = [f"## {p}" if re.fullmatch(r"(19|20)\d\d", p.strip()) else p for p in paragraphs]
    write(path, front, "\n\n".join(paragraphs))
    return paragraphs


def works_from_room(rel, legacy_dir, dest_dir):
    order = re.findall(r'(?i)<img[^>]+src="images/thumbs/' + re.escape(legacy_dir) + r'/([^"]+)"', read(rel))
    works = []
    for name in order:
        if (LEGACY / "gallery/retrospective/images" / legacy_dir / name).exists():
            url = copy_image(f"gallery/retrospective/images/{legacy_dir}/{name}", f"retrospective/{dest_dir}/{slug(name)}")
            works.append({"image": url})
    return works


def artist_in_exile():
    works = []
    for n in range(1, 32):
        rel = f"gallery/artist-in-exile/{n:02d}.htm"
        if not (LEGACY / rel).exists():
            continue
        raw = read(rel)
        img = re.search(r'(?i)<img[^>]+src="images/([^"]+)"', raw)
        cells = re.findall(r"(?is)<td[^>]*>(.*?)</td>", raw)
        caption = cells[-1] if cells else ""
        caption = re.sub(r"(?i)<br\s*/?>", "\n", caption)
        caption = html.unescape(re.sub(r"<[^>]+>", "", caption)).replace("\xa0", " ")
        lines = [re.sub(r"\s+", " ", l).strip() for l in caption.split("\n")]
        lines = [l for l in lines if l]
        work = {"image": copy_image(f"gallery/artist-in-exile/images/{img.group(1)}", f"artist-in-exile/{n:02d}.jpg")}
        year_at = next((i for i, l in enumerate(lines) if re.fullmatch(r"(c\.?\s*)?\(?(1[89]\d\d|20\d\d)[^a-z]*\)?|\(?no date\)?|n\.d\.?|undated", l, re.I)), None)
        if year_at is None:
            work["title"] = " ".join(lines[:1]).replace("Unititled", "Untitled")
            rest = lines[1:]
        else:
            work["title"] = " ".join(lines[:year_at]).replace("Unititled", "Untitled")
            work["year"] = lines[year_at]
            rest = lines[year_at + 1:]
        if rest:
            work["medium"] = rest[0]
        if len(rest) > 1:
            work["dimensions"] = "; ".join(rest[1:])
        works.append(work)
    return works


def main():
    for d in (CONTENT, IMAGES):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    for name in ("logo.jpg", "logo-splash.jpg", "header.jpg", "left.jpg", "dumile-feni.jpg", "saho-logo.jpg") + tuple(f"icon{i:02d}.jpg" for i in range(1, 13)):
        copy_image(f"graphics/{name}", f"site/{name}")
    portrait = copy_image("gallery/photos/dumile.jpg", "photos/dumile-feni.jpg")
    durban = copy_image("gallery/photos/dumile_durban1966.jpg", "photos/dumile-durban-1966.jpg")
    heads = copy_image("gallery/photos/01_heads.jpg", "photos/heads.jpg")
    guernica = copy_image("gallery/retrospective/images/guernica.jpg", "retrospective/african-guernica.jpg")
    for n, name in enumerate(sorted(os.listdir(LEGACY / "resources/images/de-jager"))):
        if name.lower().endswith(".jpg"):
            INLINE_IMAGES[f"resources/images/de-jager/{name}"] = copy_image(f"resources/images/de-jager/{name}", f"writing/de-jager/{slug(name)}")

    featured = [copy_image(f"gallery/artist-in-exile/images/index-images/{n}JPEG.jpg", f"home/{n}.jpg") for n in ("07", "12", "20", "27")]

    about = headings(to_markdown("about/about.htm", LINKS, INLINE_IMAGES))
    about = [p for p in about if "DUMILE FENI FOUNDATION" not in p.upper() or len(p) > 60]
    # The 2005 contact block (phone numbers, named staff) is out of date.
    if "## Contact" in about:
        about = about[:about.index("## Contact")]
    about.append("## Contact\n\nFor enquiries about Dumile Feni, the Foundation or the images on this site, [contact South African History Online](https://sahistory.org.za/contact-us).")
    quote = [p for p in to_markdown("history/history.htm", LINKS, {}) if "Dumile Feni: The artist" not in p]

    write("_index.md", {
        "title": "Dumile Feni",
        "tagline": "Celebrating the life of one of Africa's greatest artists of the 20th century",
        "feature": {"image": guernica, "title": "African Guernica", "year": "no date", "medium": "Charcoal on paper", "dimensions": "330 x 270 cm"},
        "featured_works": featured,
        "portrait": portrait,
        "legacy_path": "index.html",
    }, "\n\n".join(p if not p.startswith("(Simon") else p for p in quote))

    write("foundation/_index.md", {"title": "The Dumile Feni Foundation", "menu_title": "Foundation", "icon": "/images/site/icon05.jpg", "weight": 60, "summary": "Established in 2004 to promote the work of Dumile Feni and to research his life.", "legacy_path": "about/about.htm"}, "\n\n".join(about))

    write("life/_index.md", {"title": "Life", "icon": "/images/site/icon07.jpg", "weight": 10, "summary": "Biographies, a chronology and a profile of Zwelidumile Jeremiah Mgxaji Mslaba Feni, 1942 - 1991.", "portrait": portrait, "legacy_path": "history/history.htm"})
    essay("history/history_dumile-profile.htm", "life/profile.md", "Profile of Dumile Feni", 10, {"author": "Dumile Feni Foundation", "year": "2005"})
    essay("history/history_smith-b_01.htm", "life/the-artist-and-the-work.md", "Dumile Feni: The artist and the work", 20, {"author": "Bruce Smith", "year": "August 2004"})
    essay("history/history_smith-b_02.htm", "life/a-biographical-sketch.md", "Dumile Feni: A biographical sketch", 30, {"author": "Bruce Smith"})
    essay("history/timelines/timeline_omar.htm", "life/chronology.md", "A short chronology", 40, {"layout": "chronology"}, keep_headings=False)

    write("exhibitions/_index.md", {"title": "Exhibitions", "icon": "/images/site/icon08.jpg", "weight": 20, "summary": "The 2005 retrospective, Artist in Exile, and a record of exhibitions from 1965.", "legacy_path": "gallery/gallery.htm"},
          "Selected works (drawings, sculptures and mixed media) exhibited at Gallery 101 Johannesburg in January 1966 and June 1967 and at the Durban Art Gallery have been documented by [The PELMAMA Museums Project](http://www.pelmama.org/default.htm#Dumile).\n\n![Dumile Feni at the Durban Art Gallery, 1966](" + durban + ")")
    write("exhibitions/artist-in-exile.md", {"title": "Artist in Exile", "type": "gallery", "weight": 10, "summary": "Thirty-one drawings and sculptures made in exile.", "cover": "/images/artist-in-exile/07.jpg", "works": artist_in_exile(), "legacy_path": "gallery/artist-in-exile/menu.htm"})
    essay("gallery/retrospective/gallery_retro.htm", "exhibitions/retrospective/_index.md", "Dumile Feni: A Retrospective", 20, {"summary": "Johannesburg Art Gallery, 30 January - 10 April 2005.", "cover": guernica})
    essay("gallery/retrospective/gallery_retro_curator-statement.htm", "exhibitions/retrospective/curators-statement.md", "Curator's statement", 10, {"author": "Prince Mbusi Dube"})
    essay("gallery/retrospective/gallery_retro_curator.htm", "exhibitions/retrospective/curator.md", "Prince Mbusi Dube - curator", 20)
    for weight, (rel, legacy_dir, dest, title) in enumerate([
        ("gallery/retrospective/menu_01_b4-exile.htm", "01_b4-exile", "before-exile", "Before exile"),
        ("gallery/retrospective/menu_02_london.htm", "02_london", "london", "London"),
        ("gallery/retrospective/menu_03_USA.htm", "03_USA", "usa", "USA"),
    ]):
        works = works_from_room(rel, legacy_dir, dest)
        write(f"exhibitions/retrospective/{dest}.md", {"title": title, "type": "gallery", "weight": 30 + weight, "summary": f"{len(works)} works from the retrospective.", "cover": works[0]["image"] if works else "", "works": works, "legacy_path": rel})
    essay("gallery/gallery_JAG.htm", "exhibitions/johannesburg-art-gallery.md", "The Johannesburg Art Gallery", 30)
    essay("history/history_exhibs_JAG.htm", "exhibitions/exhibition-history.md", "Exhibition history", 40, keep_headings=False)
    covers = [
        {"image": copy_image("gallery/editorials/images/classic_1968.jpg", "work/classic-1968.jpg"), "title": "Cover of The Classic, Vol. 2, No. 4", "year": "1968"},
        {"image": copy_image("gallery/editorials/images/cover_1990-06.jpg", "work/arekopaneng-1990.jpg"), "title": "Cover of Arekopaneng Journal, Vol. 2, No. 1", "year": "1990"},
        {"image": copy_image("gallery/images/mural_NY.jpg", "work/mural-new-york.jpg"), "title": "Mural, New York"},
    ]
    write("exhibitions/covers-and-murals.md", {"title": "Covers and outdoor work", "type": "gallery", "variant": "scans", "weight": 50, "summary": "Journal covers and a mural in New York.", "cover": covers[0]["image"], "works": covers, "legacy_path": "gallery/gallery.htm"})

    press = []
    listing = read("history/history_newspapers.htm")
    labels = [html.unescape(re.sub(r"\s+", " ", m)).strip() for m in re.findall(r"(?is)<strong>\s*([^<]*?\d{4})\s*:?\s*</strong>", listing)]
    scans = sorted(n for n in os.listdir(LEGACY / "history/newspapers/scans") if n.lower().endswith(".jpg"))
    names = {"natal-mercury": "The Natal Mercury", "ep-herald": "The Eastern Province Herald", "sunday-tribune": "The Sunday Tribune", "mail-guardian": "The Mail & Guardian", "m-g": "The Mail & Guardian", "weekend-argus": "The Weekend Argus"}
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    def scan_key(n):
        m = re.search(r"(\d{4})-(\d{2})-(\d{1,2})", n)
        return (m.group(1), m.group(2), m.group(3).zfill(2), n) if m else ("9999", "", "", n)
    for name in sorted(scans, key=scan_key):
        paper, _, rest = name.rpartition("_")
        m = re.search(r"(\d{4})-(\d{2})-(\d{1,2})", name)
        date = f"{int(m.group(3))} {months[int(m.group(2)) - 1]} {m.group(1)}" if m else ""
        press.append({"image": copy_image(f"history/newspapers/scans/{name}", f"press/{slug(name)}"), "title": names.get(paper, paper.replace("-", " ").title()), "year": date})
    write("press/_index.md", {"title": "Press", "type": "gallery", "variant": "scans", "icon": "/images/site/icon01.jpg", "weight": 30, "summary": "Newspaper coverage from 1966 to 2002.", "works": press, "legacy_path": "history/history_newspapers.htm"})

    write("writing/_index.md", {"title": "Writing", "icon": "/images/site/icon03.jpg", "weight": 40, "summary": "Articles on Dumile and an original grant proposal in his own hand.", "legacy_path": "resources/resources.htm"})
    essay("resources/resources_article_simon-b.htm", "writing/dumile-barney-simon-1968.md", "Dumile", 10, {"author": "Barney Simon", "year": "The Classic, Vol. 2, No. 4, 1968"}, drop_title=False)
    essay("resources/resources_article_dejager-ej.htm", "writing/contemporary-african-sculpture-de-jager.md", "Contemporary African Sculpture in South Africa", 20, {"author": "E.J. de Jager"})
    def page_label(n):
        m = re.search(r"pg(\d+)", n)
        return f"Page {int(m.group(1))}" if m else "Cover"
    proposal = [{"image": copy_image(f"resources/proposal/content/{n}", f"proposal/{slug(n.replace('content_', ''))}"), "title": page_label(n)} for n in sorted(os.listdir(LEGACY / "resources/proposal/content")) if n.endswith(".jpg")]
    write("writing/work-study-grant-proposal-1989.md", {"title": "Work-study grant proposal", "type": "gallery", "variant": "scans", "weight": 30, "author": "Dumile Feni", "year": "7 August 1989", "summary": "A proposal prepared by Dumile Feni in New York.", "cover": proposal[0]["image"], "works": proposal, "legacy_path": "resources/resources_proposal_cover.htm"})

    write("publications/_index.md", {"title": "Publications", "icon": "/images/site/icon12.jpg", "weight": 50, "summary": "Exhibition catalogues.", "legacy_path": "books/books.htm"})
    scan = lambda n, d: copy_image(f"books/catalogues/scans/{n}", f"publications/{d}")
    essay("books/catalogue_artist-in-exile.htm", "publications/artist-in-exile-catalogue.md", "Artist in exile", 10, {"cover": scan("artist-in-exile_cover.jpg", "artist-in-exile-cover.jpg")})
    write("publications/nsa-gallery-catalogue.md", {"title": "NSA Gallery catalogue", "type": "gallery", "variant": "scans", "weight": 20, "cover": scan("NSA-gallery-cover.jpg", "nsa-gallery-cover.jpg"), "works": [
        {"image": "/images/publications/nsa-gallery-cover.jpg", "title": "Cover"},
        {"image": scan("NSA-gallery-pg2.jpg", "nsa-gallery-spread.jpg"), "title": "Spread"},
        {"image": scan("NSA-gallery-back.jpg", "nsa-gallery-back.jpg"), "title": "Back"}], "legacy_path": "books/catalogue_NSA-gallery.htm"})
    write("publications/statements-catalogue.md", {"title": "Statements catalogue", "type": "gallery", "variant": "scans", "weight": 30, "cover": scan("statements_cover.jpg", "statements-cover.jpg"), "works": [
        {"image": "/images/publications/statements-cover.jpg", "title": "Cover"},
        {"image": scan("statements_pg1.jpg", "statements-page-1.jpg"), "title": "Page 1"},
        {"image": scan("statements_pg2.jpg", "statements-page-2.jpg"), "title": "Page 2"},
        {"image": scan("statements_back.jpg", "statements-back.jpg"), "title": "Back"}], "legacy_path": "books/catalogue_statements.htm"})

    write("news/_index.md", {"title": "News", "icon": "/images/site/icon11.jpg", "weight": 70, "summary": "News from the launch of the Foundation in 2005.", "legacy_path": "news/news.htm"},
          "- **23 January 2005** - [\"Dumile never pandered to white whims\"](/news/dumile-never-pandered-to-white-whims/), Mary Stuart for the Sunday Independent\n- **28 January 2005** - Launch of the Dumile Feni Foundation website\n- **30 January 2005** - Opening of *Dumile Feni: A Retrospective Exhibition* at the [Johannesburg Art Gallery](/exhibitions/johannesburg-art-gallery/). The exhibition ran until 10 April 2005.")
    news_scans = [n for n in sorted(os.listdir(LEGACY / "news/scans")) if n.lower().endswith(".jpg")]
    extra = {"author": "Mary Stuart", "year": "Sunday Independent, 23 January 2005"}
    if news_scans:
        extra["cover"] = copy_image(f"news/scans/{news_scans[0]}", f"news/{slug(news_scans[0])}")
    essay("news/news_sunday-indie_2005-01-23.htm", "news/dumile-never-pandered-to-white-whims.md", "\"Dumile never pandered to white whims\"", 10, extra)

    suspicious = re.compile(r"[\u0080-\u009f\ufffd\u00a6]|\u00e2\u20ac|\u00c3.|\u00c2[^a-zA-Z]|&[a-z]+;|&#\d+;")
    broken = [f"{page.relative_to(CONTENT)}: {m.group(0)!r}" for page in CONTENT.rglob("*.md") for m in suspicious.finditer(page.read_text(encoding="utf-8"))]
    if broken:
        raise SystemExit("broken characters in migrated content:\n" + "\n".join(broken[:40]))

    pages = sum(1 for _ in CONTENT.rglob("*.md"))
    images = sum(1 for _ in IMAGES.rglob("*.jpg"))
    print(f"wrote {pages} pages, {images} images")


if __name__ == "__main__":
    main()

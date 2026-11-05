#!/usr/bin/env python3
"""
Turns the Markdown posts in src/posts/ into plain HTML pages in posts/.

    python3 build.py

No installs needed: this uses only Python's standard library, and the
website itself stays plain HTML, CSS and JS. If this script ever breaks,
every page it already made is still an ordinary HTML file.

Your text is copied as written. Apostrophes, quotes, em dashes and so on
are not changed; the only characters touched are &, < and >, which HTML
needs written as &amp; &lt; &gt; (they still display normally).

Each post is a .md file that starts with a small block of details:

    ---
    title: Dismantle Mercury!
    date: 2026/10/30
    tags: futurism
    substack: https://blueprintingheaven.substack.com/p/...   (optional)
    lesswrong: https://www.lesswrong.com/posts/...            (optional)
    ---

    Then the post, exactly as written in Obsidian.

The output file name comes from the .md file name
(src/posts/dismantle-mercury.md -> posts/dismantle-mercury.html).

Supported Markdown: paragraphs, *italics* and _italics_, **bold**,
==highlights==, `code`, [links](https://...), [[wikilinks]] and
[[wikilinks|with text]], images ![alt](file.png) and ![[file.png]],
# headings, > quotes, - and 1. lists, --- dividers, footnotes [^1],
and %%Obsidian comments%% (removed).
"""

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "src" / "posts"
OUTPUT_DIR = ROOT / "posts"
TEMPLATE = ROOT / "src" / "post-template.html"

# Wikilinks to other posts: [[Post title]] -> its page. Add entries here
# as posts move onto the site; unknown wikilinks become plain text.
WIKILINKS = {
    # "A Year of Atheism": "a-year-of-atheism.html",
}


# ---------- inline formatting ----------

def inline(text, footnote_ids):
    """Format one paragraph's worth of text."""
    stash = []

    def keep(fragment):
        stash.append(fragment)
        return "\x00%d\x00" % (len(stash) - 1)

    # Obsidian comments vanish
    text = re.sub(r"%%.*?%%", "", text, flags=re.S)

    # `code` is protected from all other formatting
    text = re.sub(r"`([^`]+)`",
                  lambda m: keep("<code>%s</code>" % html.escape(m.group(1), quote=False)),
                  text)

    # Images: ![[file.png]] and ![alt](file.png)
    def image(src, alt):
        return keep('<img src="%s" alt="%s" loading="lazy">'
                    % (html.escape(src), html.escape(alt)))
    text = re.sub(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]",
                  lambda m: image("images/" + m.group(1).strip(), ""), text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                  lambda m: image(m.group(2), m.group(1)), text)

    # Links: [text](url) -- the text itself can contain formatting
    def link(m):
        label, url = m.group(1), m.group(2)
        return (keep('<a href="%s">' % html.escape(url))
                + label + keep("</a>"))
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)

    # Wikilinks: [[Page]] or [[Page|shown text]]
    def wikilink(m):
        target, shown = m.group(1).strip(), (m.group(2) or m.group(1)).strip()
        page = WIKILINKS.get(target)
        if page:
            return keep('<a href="%s">' % html.escape(page)) + shown + keep("</a>")
        return shown
    text = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", wikilink, text)

    # Footnote references: [^name]
    def footref(m):
        name = m.group(1)
        if name not in footnote_ids:
            footnote_ids.append(name)
        n = footnote_ids.index(name) + 1
        return keep('<sup class="footnote-ref" id="fnref-%s"><a href="#fn-%s">%d</a></sup>'
                    % (n, n, n))
    text = re.sub(r"\[\^([^\]]+)\]", footref, text)

    # From here on, everything left is plain text: escape &, <, >
    text = html.escape(text, quote=False)

    # **bold**, then *italics* / _italics_, then ==highlights==
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(?=\S)(.+?)(?<=\S)__", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(?=\S)(.+?)(?<=\S)\*", r"<em>\1</em>", text)
    text = re.sub(r"(?<![\w])_(?=\S)(.+?)(?<=\S)_(?![\w])", r"<em>\1</em>", text)
    text = re.sub(r"==(?=\S)(.+?)(?<=\S)==", r"<mark>\1</mark>", text)

    # Put the protected pieces back
    return re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)


# ---------- blocks ----------

def convert(markdown):
    """Convert a post body to HTML. Returns (html, footnotes_html)."""
    markdown = re.sub(r"%%.*?%%", "", markdown, flags=re.S)
    lines = markdown.replace("\r\n", "\n").split("\n")

    # Pull out footnote definitions: [^name]: text (+ indented continuation lines)
    definitions, body = {}, []
    i = 0
    while i < len(lines):
        m = re.match(r"\[\^([^\]]+)\]:\s?(.*)", lines[i])
        if m:
            name, parts = m.group(1), [m.group(2)]
            i += 1
            while i < len(lines) and (lines[i].startswith("    ") or lines[i].startswith("\t")):
                parts.append(lines[i].strip())
                i += 1
            definitions[name] = " ".join(parts)
        else:
            body.append(lines[i])
            i += 1

    footnote_ids = []
    out = []
    blocks = re.split(r"\n\s*\n", "\n".join(body).strip())

    for block in blocks:
        block = block.strip("\n")
        if not block.strip():
            continue
        rows = block.split("\n")

        heading = re.match(r"(#{1,6})\s+(.*)", block)
        if heading and len(rows) == 1:
            level = min(len(heading.group(1)) + 1, 6)   # the post title is the main heading
            out.append("<h%d>%s</h%d>" % (level, inline(heading.group(2).strip(), footnote_ids), level))
        elif re.fullmatch(r"\s*([-*_])(\s*\1){2,}\s*", block):
            out.append('<hr>')
        elif all(r.startswith(">") for r in rows):
            inner = "\n".join(re.sub(r"^>\s?", "", r) for r in rows)
            paragraphs = [p for p in re.split(r"\n\s*\n", inner) if p.strip()]
            out.append("<blockquote>\n%s\n</blockquote>" % "\n".join(
                "<p>%s</p>" % inline(" ".join(x.strip() for x in p.split("\n")), footnote_ids)
                for p in paragraphs))
        elif all(re.match(r"\s*[-*+]\s+", r) for r in rows):
            items = [re.sub(r"^\s*[-*+]\s+", "", r) for r in rows]
            out.append("<ul>\n%s\n</ul>" % "\n".join(
                "<li>%s</li>" % inline(x.strip(), footnote_ids) for x in items))
        elif all(re.match(r"\s*\d+[.)]\s+", r) for r in rows):
            items = [re.sub(r"^\s*\d+[.)]\s+", "", r) for r in rows]
            out.append("<ol>\n%s\n</ol>" % "\n".join(
                "<li>%s</li>" % inline(x.strip(), footnote_ids) for x in items))
        else:
            # A paragraph. A single line break inside it stays a line break,
            # the way Obsidian shows it by default.
            out.append("<p>%s</p>" % "<br>\n".join(inline(r.strip(), footnote_ids) for r in rows))

    notes = ""
    if footnote_ids:
        items = []
        for n, name in enumerate(footnote_ids, 1):
            text = inline(definitions.get(name, ""), [])
            items.append('<li id="fn-%d">%s <a href="#fnref-%d" class="footnote-back" '
                         'aria-label="Back to the text">↩\ufe0e</a></li>' % (n, text, n))
        notes = ('<section class="footnotes" aria-label="Footnotes">\n<ol>\n%s\n</ol>\n</section>'
                 % "\n".join(items))
    return "\n".join(out), notes


def read_post(path):
    """Split a post file into its details block and its body."""
    raw = path.read_text(encoding="utf-8")
    meta = {}
    m = re.match(r"---\n(.*?)\n---\n", raw.replace("\r\n", "\n"), flags=re.S)
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip().lower()] = value.strip()
        raw = raw.replace("\r\n", "\n")[m.end():]
    return meta, raw


def build():
    template = TEMPLATE.read_text(encoding="utf-8")
    OUTPUT_DIR.mkdir(exist_ok=True)
    for path in sorted(SOURCE_DIR.glob("*.md")):
        meta, markdown = read_post(path)
        body, notes = convert(markdown)

        title = meta.get("title", path.stem)
        tags = [t.strip().lstrip("#") for t in meta.get("tags", "").split(",") if t.strip()]
        discuss = []
        if meta.get("substack"):
            discuss.append('<a href="%s">Substack</a>' % html.escape(meta["substack"]))
        if meta.get("lesswrong"):
            discuss.append('<a href="%s">LessWrong</a>' % html.escape(meta["lesswrong"]))

        canonical = ('<link rel="canonical" href="%s">' % html.escape(meta["substack"])
                     if meta.get("substack") else "")
        page = (template
                .replace("{{canonical}}", canonical)
                .replace("{{title}}", html.escape(title, quote=False))
                .replace("{{date}}", html.escape(meta.get("date", "")))
                .replace("{{tags}}", " · ".join(html.escape(t) for t in tags))
                .replace("{{discuss}}", " ✦ ".join(discuss) if discuss else "")
                .replace("{{content}}", body)
                .replace("{{footnotes}}", notes))
        if not discuss:
            page = re.sub(r"\s*<!-- discuss -->.*?<!-- /discuss -->", "", page, flags=re.S)
        if not tags:
            page = re.sub(r"\s*<!-- tags -->.*?<!-- /tags -->", "", page, flags=re.S)

        out = OUTPUT_DIR / (path.stem + ".html")
        out.write_text(page, encoding="utf-8")
        print("built", out.relative_to(ROOT))


if __name__ == "__main__":
    build()
